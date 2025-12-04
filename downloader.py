import logging
import subprocess
import shutil
import sys
import os
import tempfile

from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import extractor
import stream
from defaults import (
    DEFAULT_MAX_WORKERS,
    DEFAULT_ENCRYPTED_VIDEO_FILENAME,
    DEFAULT_ENCRYPTED_AUDIO_FILENAME,
)

from stream import (
    get_pssh,
    fix_video,
    fix_audio,
    merge_streams,
    Stream,
    get_stream_by_id,
    choose_best_video,
    StreamType,
    choose_best_audio,
)
from utils import get_urls, download_file


try:
    from mpegdash.parser import MPEGDASHParser
except ImportError:
    sys.stderr.write("Error: mpegdash module not found. Install it with: pip install mpegdash\n")
    sys.exit(1)


logger = logging.getLogger(__name__)


def download_by_file(
    filepath: str,
    to_download_subtitles: bool = False,
    to_download_manifest: bool = False,
    multithreading: bool = False,
    workers: int = DEFAULT_MAX_WORKERS,
    verbose: bool = False,
):
    if filepath is None:
        raise ValueError("filepath cannot be None")

    if not isinstance(filepath, str):
        logger.fatal(f"Invalid type for filepath: Expected str, got {type(filepath).__name__}")

    if not os.path.exists(filepath):
        logger.fatal(f"File {filepath} does not exist")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    logger.info(f"Downloading from {filepath}")

    urls: list[str] = get_urls(text)
    logger.info(f'URLs found: {"\n".join(urls)}')

    if not multithreading:
        for counter, url in enumerate(urls, start=1):
            logger.info(f"Downloading {url} [{counter}/{len(urls)}]")
            download_by_url(
                url,
                to_download_subtitles,
                to_download_manifest,
                f"file_{counter}.mp4",
                verbose=verbose,
            )
    else:
        # Step 1: Sequentially collect manifests and license URLs
        logger.info(f"Collecting manifests for {len(urls)} URLs...")
        manifest_data: list[tuple[int, str, str, str]] = []
        for counter, url in enumerate(urls, start=1):
            try:
                logger.info(f"Getting manifest for {url} [{counter}/{len(urls)}]")
                manifest, license_url = extractor.get_manifest_and_license(url)

                if manifest and license_url:
                    manifest_data.append((counter, url, manifest, license_url))
                else:
                    logger.error(f"Failed to get manifest for {url}")

            except Exception as e:
                logger.error(f"Failed to get manifest for {url}: {e}")

        if not manifest_data:
            logger.error("No valid manifests collected")
            return

        # Step 2: Download concurrently using manifests
        def download_task(counter: int, url: str, manifest: str, license_url: str):
            try:
                logger.info(f"Downloading {url} [{counter}/{len(urls)}]")
                download_by_manifest_and_license_url(
                    manifest,
                    license_url,
                    to_download_subtitles,
                    to_download_manifest,
                    None,  # audio_stream_id (not specified when downloading by file)
                    None,  # video_stream_id (not specified when downloading by file)
                    f"file_{counter}.mp4",
                    verbose=verbose,
                )
                return counter, url, True, None
            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")
                return counter, url, False, str(e)

        logger.info(
            f"Starting parallel download of {len(manifest_data)} files with {workers} workers"
        )

        with ThreadPoolExecutor(max_workers=min(len(manifest_data), workers)) as executor:
            futures = {
                executor.submit(download_task, counter, url, manifest, license_url): (counter, url)
                for counter, url, manifest, license_url in manifest_data
            }

            completed = 0
            failed = 0

            for future in as_completed(futures):
                counter, url, success, error = future.result()
                completed += 1

                if success:
                    logger.info(f"Completed download {completed}/{len(manifest_data)}: {url}")
                else:
                    failed += 1
                    logger.error(
                        f"Failed download {completed}/{len(manifest_data)}: {url} - {error}"
                    )

        logger.info(f"Download complete: {completed - failed} succeeded, {failed} failed")
        # TODO: FIXME: Implement retries for the failed downloads


def download_by_url(
    url: str,
    to_download_subtitles: bool,
    to_download_manifest: bool,
    output_filename: Optional[str] = None,
    audio_stream_id: Optional[str] = None,
    video_stream_id: Optional[str] = None,
    verbose: bool = False,
):
    if url is None:
        raise ValueError("url cannot be None")

    if not isinstance(url, str):
        logger.fatal(f"Invalid type for url: Expected str, got {type(url).__name__}")

    if output_filename is not None and not isinstance(output_filename, str):
        logger.fatal(
            f"Invalid type for output_filename: Expected str, got {type(output_filename).__name__}"
        )

    manifest, license_url = extractor.get_manifest_and_license(url)

    if manifest is None or license_url is None:
        sys.exit(1)

    download_by_manifest_and_license_url(
        manifest,
        license_url,
        to_download_subtitles,
        to_download_manifest,
        audio_stream_id,
        video_stream_id,
        output_filename,
        verbose=verbose,
    )


def download_by_manifest_and_license_url(
    manifest: str,
    license_url: str,
    to_download_subtitles: bool,
    to_download_manifest: bool,
    audio_stream_id: Optional[str] = None,
    video_stream_id: Optional[str] = None,
    output_filename: Optional[str] = None,
    verbose: bool = False,
):
    if manifest is None:
        raise ValueError("manifest cannot be None")

    if not isinstance(manifest, str):
        logger.fatal(f"Invalid type for manifest: Expected str, got {type(manifest).__name__}")
        sys.exit(1)

    if license_url is None:
        raise ValueError("license_url cannot be None")

    if not isinstance(license_url, str):
        logger.fatal(
            f"Invalid type for license_url: Expected str, got {type(license_url).__name__}"
        )
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="opto-dl-") as temp_dir:
        working_dir = Path(temp_dir)
        logger.info(f"Using temporary directory: {working_dir}")

        mpd = MPEGDASHParser.parse(manifest)

        if to_download_manifest:
            download_file(manifest, "manifest.mpd")
            logger.info("Saving manifest to manifest.mpd")

        streams: list[Stream] = stream.get_streams(mpd)

        subtitle_streams: list[Stream] = [
            s for s in streams if s.stream_type == StreamType.SUBTITLES
        ]

        if not subtitle_streams:
            logger.info("No subtiles found")

        if to_download_subtitles:
            for subtitle_stream in subtitle_streams:
                download_subtitles(subtitle_stream)

        if video_stream_id is not None:
            logger.info("Video stream ID provided: %s", video_stream_id)
            video_stream: Optional[Stream] = get_stream_by_id(video_stream_id, streams)

            if video_stream is None:
                sys.stderr.write(f"No video stream {video_stream_id} found\n")
                sys.exit(1)
        else:
            video_stream: Stream = choose_best_video(streams)

        logger.info("Chosen video stream: %s", video_stream.id)

        if audio_stream_id is not None:
            logger.info("Audio stream ID provided: %s", audio_stream_id)
            audio_stream: Optional[Stream] = get_stream_by_id(audio_stream_id, streams)

            if audio_stream is None:
                sys.stderr.write(f"No audio stream {video_stream_id} found\n")
                sys.exit(1)
        else:
            audio_stream: Stream = choose_best_audio(streams)

        logger.info(f"Chosen audio stream: {audio_stream.id}")

        if audio_stream.stream_type != StreamType.AUDIO:
            logger.warning(f"Stream {audio_stream.id} is not audio")

        if video_stream.stream_type != StreamType.VIDEO:
            logger.warning(f"Stream {video_stream.id} is not video")

        pssh, is_joyn = get_pssh(video_stream, mpd)
        download_stream(manifest, video_stream, working_dir, verbose)
        download_stream(manifest, audio_stream, working_dir, verbose)
        decryption_keys = extractor.get_keys(pssh, license_url)
        fix_video(decryption_keys, working_dir, verbose, is_joyn)
        fix_audio(decryption_keys, working_dir, verbose, is_joyn)
        merge_streams(output_filename, working_dir, verbose)


def download_stream(
    manifest_url: str, stream: Stream, working_dir: Optional[Path] = None, verbose: bool = False
):
    if manifest_url is None:
        raise ValueError("manifest_url cannot be empty or None")

    if stream is None:
        raise ValueError("stream cannot be empty or None")

    if not isinstance(manifest_url, str):
        logger.warning(
            f"Invalid type for manifest_url: Expected str, got {type(manifest_url).__name__}"
        )

    if not isinstance(stream, Stream):
        logger.warning(f"Invalid type for stream: Expected Stream, got {type(stream).__name__}")

    if shutil.which("yt-dlp") is None:
        logger.fatal("yt-dlp is not installed or not found in PATH")
        sys.exit(1)

    if working_dir is None:
        working_dir = Path.cwd()

    logger.info(f"Downloading encrypted {str(stream.stream_type)} stream: {stream.id}")

    filename: str = (
        DEFAULT_ENCRYPTED_VIDEO_FILENAME
        if stream.stream_type == StreamType.VIDEO
        else DEFAULT_ENCRYPTED_AUDIO_FILENAME if stream.stream_type == StreamType.AUDIO else "zzzz"
    )

    command = [
        "yt-dlp",
        "-f",
        stream.id,
        "--allow-unplayable-formats",
        "-o",
        str(working_dir / filename),
        manifest_url,
    ]

    logger.info(f'Command (cwd: {working_dir}): {" ".join(command)}')

    subprocess.run(
        command, capture_output=(not verbose), text=True, check=True, cwd=str(working_dir)
    )


def download_subtitles(subtitle_stream: Stream, output_path: Optional[str] = None):
    # TODO: Use the output path

    if subtitle_stream is None:
        raise ValueError("subtitle_stream cannot be None")

    if not isinstance(subtitle_stream, Stream):
        logger.fatal(
            f"Invalid type for subtitle_stream: Expected Stream, got {type(subtitle_stream).__name__}"
        )

    if subtitle_stream.stream_type != StreamType.SUBTITLES:
        logger.warning(f"Stream {subtitle_stream.id} is not a subtitle stream")

    for url in subtitle_stream.subtitle_urls:
        logger.info(f"Downloading subtitle URL {url} for stream {subtitle_stream.id}")
        # TODO: Append this to output_path if it is a directory.
        # TODO: Replace the extension if it is a file
        o_path = url.split("/")[-1]
        if not download_file(url, o_path):
            logger.error(f"Failed to download subtitles for {url}")
