import logging
import subprocess
import shutil
import sys
import os
from typing import Optional

import extractor
import stream
from defaults import DEFAULT_MAX_WORKERS
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
from utils import get_urls, cleanup

try:
    from mpegdash.parser import MPEGDASHParser
    from mpegdash.nodes import Representation
except ImportError:
    sys.stderr.write("Error: mpegdash module not found. Install it with: pip install mpegdash\n")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def download_by_file(
    filepath: str, multithreading: bool = False, workers: int = DEFAULT_MAX_WORKERS
):
    if filepath is None:
        raise ValueError("")

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
        counter = 1
        for url in urls:
            if not "opto.sic.pt" in url:
                logger.warning(f"Skipping invalid URL: {url}")
                continue

            logger.info(f"Downloading {url} [{counter}/{len(urls)}]")
            download_by_url(url, f"file_{counter}.mp4")
            counter += 1
            cleanup()
    else:
        raise NotImplementedError("")
        """
        # TODO: Check that Url is valid
        urls_with_counter = [(i + 1, url) for i, url in enumerate(urls)]

        def download_task(counter: int, url: str):
            logger.info(f"Downloading {url} [{counter}/{len(urls)}]")
            download_by_url(url, f"file_{counter}.mp4")
            return counter, url

        with ThreadPoolExecutor(max_workers=min(len(urls), workers)) as executor:
            futures = {
                executor.submit(download_task, counter, url): (counter, url)
                for counter, url in urls_with_counter
            }

            for future in as_completed(futures):
                counter, url = futures[future]
                try:
                    future.result()
                    logger.info(f"Completed download {counter}/{len(urls)}")
                except Exception as e:
                    logger.error(f"Failed to download {url}: {e}")
        """


def download_by_url(
    url: str, output_filename: str = None, audio_stream_id: str = None, video_stream_id: str = None
):
    if url is None:
        raise ValueError()

    if not isinstance(url, str):
        pass  # TODO: log actual type

    if output_filename is not None and not isinstance(output_filename, str):
        logger.fatal(
            f"Invalid type for output_filename: Expected str, got {type(output_filename).__name__}"
        )

    manifest, license_url = extractor.get_manifest_and_license(url)

    if manifest is None or license_url is None:
        sys.exit(1)

    download_by_manifest_and_license_url(manifest, license_url, output_filename)


def download_by_manifest_and_license_url(
    manifest: str,
    license_url: str,
    audio_stream_id: Optional[str] = None,
    video_stream_id: Optional[str] = None,
    output_filename: str = None,
):
    if manifest is None:
        raise ValueError("")

    if not isinstance(manifest, str):
        logger.fatal("")
        sys.exit(1)

    if license_url is None:
        raise ValueError()

    if not isinstance(license_url, str):
        logger.fatal("")
        sys.exit(1)

    mpd = MPEGDASHParser.parse(manifest)
    streams: list[Stream] = stream.get_streams(mpd)

    if video_stream_id is not None:
        logger.info(f"Video stream ID provided: {video_stream_id}")
        video_stream: Optional[Stream] = get_stream_by_id(video_stream_id, streams)

        if video_stream is None:
            sys.stderr.write(f"No video stream {video_stream_id} found\n")
            sys.exit(1)
    else:
        video_stream: Stream = choose_best_video(streams)

    logger.info(f"Chosen video stream: {video_stream.id}")

    if audio_stream_id is not None:
        logger.info(f"Audio stream ID provided: {audio_stream_id}")
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

    download_stream(manifest, video_stream)
    download_stream(manifest, audio_stream)
    pssh = get_pssh(video_stream)
    decryption_keys = extractor.get_keys(pssh, license_url)
    fix_video(decryption_keys)
    fix_audio(decryption_keys)
    merge_streams(output_filename)


def download_stream(manifest_url: str, stream: Stream):
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

    logger.info(f"Downloading encrypted {str(stream.stream_type)} stream: {stream.id}")

    command = ["yt-dlp", "-f", stream.id, "--allow-unplayable-formats", manifest_url]

    logger.info(f'Command: {" ".join(command)}')

    subprocess.run(command, capture_output=True, text=True, check=True)
