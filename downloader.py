import logging
import subprocess
import shutil
import sys

import extractor
import stream
from stream import is_audio_stream, get_pssh, fix_video, fix_audio, merge_streams
from extractor import get_keys

try:
    from mpegdash.parser import MPEGDASHParser
    from mpegdash.nodes import Representation
except ImportError:
    sys.stderr.write("")  # TODO:
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def download_by_url(url: str, output_filename: str=None):
    if url is None:
        raise ValueError()

    manifest, license_url = extractor.get_manifest_and_license(url)

    download_by_manifest_and_license_url(manifest, license_url, output_filename)


def download_by_manifest_and_license_url(manifest: str, license_url: str, output_filename: str=None):
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
    audio_streams, video_streams = stream.get_streams(mpd)
    best_audio = stream.choose_best_audio(audio_streams)
    best_video = stream.choose_best_video(video_streams)
    download_stream(manifest, best_video)
    download_stream(manifest, best_audio)
    pssh = get_pssh(best_video)
    decryption_keys = get_keys(pssh, license_url)
    fix_video(decryption_keys)
    fix_audio(decryption_keys)
    merge_streams(output_filename)


def download_stream(manifest_url: str, stream: Representation):
    if not manifest_url:
        raise ValueError()

    if not stream:
        raise ValueError()

    if not isinstance(manifest_url, str):
        logger.warning(
            f"Invalid type for manifest_url: Expected str, got {type(manifest_url).__name__}"
        )

    if not isinstance(stream, Representation):
        logger.warning(
            f"Invalid type for stream: Expected Representation, got {type(stream).__name__}"
        )

    if shutil.which("yt-dlp") is None:
        logger.fatal("yt-dlp is not installed or not found in PATH")
        sys.exit(1)

    stream_type = (
        "audio" if is_audio_stream(stream) else "video"
    )  # if is_video_stream(stream) else ""

    logger.info(f"Downloading encrypted {stream_type} stream: {stream.id}")

    command = ["yt-dlp", "-f", stream.id, "--allow-unplayable-formats", manifest_url]

    logger.info(f'Command: {" ".join(command)}')

    subprocess.run(command, capture_output=True, text=True, check=True)
