"""
The function for checking if a stream is video or audio are based on
https://github.com/emarsden/dash-mpd-rs
"""

import shutil
import sys
import subprocess
import os
import logging

from enum import Enum, auto
from typing import Optional

from defaults import (
    DEFAULT_ENCRYPTED_VIDEO_FILENAME,
    DEFAULT_ENCRYPTED_AUDIO_FILENAME,
    DEFAULT_DECRYPTED_AUDIO_FILENAME,
    DEFAULT_DECRYPTED_VIDEO_FILENAME,
    DEFAULT_MERGED_VIDEO_FILENAME,
)

from extractor import DecryptionKeys

try:
    from mpegdash.nodes import AdaptationSet, Representation
except ImportError:
    sys.stderr.write("Error: mpegdash module not found. Install it with: pip install mpegdash\n")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class StreamType(Enum):
    AUDIO = auto()
    VIDEO = auto()
    SUBTITLES = auto()

    def __str__(self):
        mapping = {
            StreamType.AUDIO: "audio",
            StreamType.VIDEO: "video",
            StreamType.SUBTITLES: "subtitle",
        }

        return mapping.get(self, "unknown stream type")


# A stream represents the same as a Representation
class Stream:
    def __init__(
        self,
        stream_id: str,
        stream_type: StreamType,
        bandwidth: Optional[int],
        width: Optional[int],
        height: Optional[int],
        fps: Optional[int],
        subtitle_urls: list[str],
        content_protections,
    ):
        # TODO: Perform some sanity checks
        self.id: str = stream_id
        self.stream_type: StreamType = stream_type

        # Audio Only
        self.bandwidth: Optional[int] = bandwidth

        # Video Only
        self.width: Optional[int] = width
        self.height: Optional[int] = height
        self.fps: Optional[int] = fps

        # Subtitles
        self.subtitle_urls: list[str] = subtitle_urls

        # for finding pssh
        self.content_protections = content_protections

    @staticmethod
    def from_representation(r: Representation, stream_type: StreamType):
        if r is None:
            raise ValueError("")

        if not isinstance(r, Representation):
            logger.fatal(f"Invalid type for r: Expected Representation, got {type(r).__name__}")

        subtitle_urls = (
            [url.base_url_value for url in r.base_urls]
            if stream_type == StreamType.SUBTITLES
            else []
        )

        instance = Stream(
            r.id,
            stream_type,
            r.bandwidth,
            r.width,
            r.height,
            r.frame_rate,
            subtitle_urls,
            r.content_protections,
        )
        return instance


def get_stream_by_id(stream_id: str, streams: list[Stream]) -> Optional[Stream]:
    if stream_id is None:
        raise ValueError("stream_id cannot be None")

    if streams is None:
        raise ValueError("streams cannot be None")

    if not isinstance(stream_id, str):
        logger.fatal(f"Invalid type for stream_id: Expected str, got {type(stream_id).__name__}")

    if not isinstance(streams, list):
        logger.fatal(f"Invalid type for streams: Expected list, got {type(streams).__name__}")

    if not all(isinstance(x, Stream) for x in streams):
        logger.fatal("all items in streams list must be Stream instances")

    logger.info(f"Searching for stream with id: {stream_id}")
    logger.info(f'Existing streams: {",".join(s.id for s in streams)}')

    return next((stream for stream in streams if stream.id == id), None)


def get_streams(manifest) -> list[Stream]:
    if len(manifest.periods) != 1:
        sys.stderr.write("Not implemented for len(periods) != 1")
        sys.exit(1)

    period = manifest.periods[0]

    audio_streams: list[Stream] = [
        Stream.from_representation(s, StreamType.AUDIO)
        for adaptation in period.adaptation_sets
        if is_audio_adaptation(adaptation)
        for s in adaptation.representations
    ]

    subtitle_streams: list[Stream] = [
        Stream.from_representation(s, StreamType.SUBTITLES)
        for adaptation in period.adaptation_sets
        if is_subtitle_adaptation(adaptation)
        for s in adaptation.representations
    ]

    video_streams: list[Stream] = [
        Stream.from_representation(s, StreamType.VIDEO)
        for adaptation in period.adaptation_sets
        if is_video_adaptation(adaptation)
        for s in adaptation.representations
    ]

    logger.info(f"Audio Streams: {[s.id for s in audio_streams]}")
    logger.info(f"Video Streams: {[s.id for s in video_streams]}")

    if len(subtitle_streams) > 0:
        logger.info(f"Subtitle Streams: {[s.id for s in subtitle_streams]}")
    else:
        logger.info("No subtitle streams found")

    return video_streams + audio_streams + subtitle_streams


def is_audio_codec(name: str) -> bool:
    return name.startswith(
        (
            "mp4a",
            "aac",
            "vorbis",
            "opus",
            "ogg",
            "webm",
            "flac",
            "mp3",
            "mpeg",
            "3gpp",
            "wav",
            "ec-3",
            "ac-4",
            "dtsc",
            "aptx",
            "aiff",
            "mha1",  # MPEG-H 3D Audio
        )
    )


def is_audio_stream(s: Representation):
    if not s:
        raise ValueError()

    if not isinstance(s, Representation):
        logger.warning(f"Invalid type: Expected Representation, got {type(s).__name__}")

    return s.mime_type and s.mime_type.startswith("audio/")


def is_audio_adaptation(a: AdaptationSet) -> bool:
    if a is None:
        return False

    if a.codecs is not None and is_audio_codec(a.codecs):
        return True

    if a.content_type == "audio":
        return True

    if a.mime_type is not None and a.mime_type.startswith("audio/"):
        return True

    if any(is_audio_stream(stream) for stream in a.representations):
        return True

    return False


def choose_best_audio(streams: list[Stream]) -> Stream:
    # Note: This list contains all streams : video + audio + subtitles

    if not streams:
        raise ValueError("No streams provided")

    # we have to filter for audio streams because video streams also have a bandwidth field

    audio_streams = filter(lambda s: s.stream_type == StreamType.AUDIO, streams)
    s = max(audio_streams, key=lambda s: s.bandwidth or 0)

    logger.info(f"Best audio: StreamID={s.id}, Bandwidth={s.bandwidth}")

    return s


def choose_best_video(streams: list[Stream]) -> Stream:
    # Note: This list contains all streams : video + audio + subtitles

    if not streams:
        raise ValueError(f"No streams provided: {streams}")

    s = max(streams, key=lambda s: (s.width or 0) * (s.height or 0))

    logger.info(f"Best video: StreamID={s.id}, Resolution={s.height}x{s.width}")

    return s


def is_subtitle_codec(c: str) -> bool:
    return c in ("wvtt", "c608", "stpp", "tx3g") or c.startswith("stpp.")


def is_subtitle_mimetype(mt: str) -> bool:
    return mt in ("text/vtt", "application/ttml+xml", "application/x-sami")


def is_subtitle_adaptation(s: AdaptationSet) -> bool:
    if s.content_type == "text":
        return True

    if s.mime_type is not None and is_subtitle_mimetype(s.mime_type):
        return True

    if s.codecs is not None and is_subtitle_codec(s.codecs):
        return True

    if s.representations:
        for rep in s.representations:
            if rep.mime_type is not None and is_subtitle_mimetype(rep.mime_type):
                return True
            if rep.codecs is not None and is_subtitle_codec(rep.codecs):
                return True

    return False


def is_video_adaptation(s: AdaptationSet) -> bool:
    if is_audio_adaptation(s) or is_subtitle_adaptation(s):
        return False

    if s.content_type is not None and s.content_type == "video":
        return True

    if s.mime_type is not None and s.mime_type.startswith("video/"):
        return True

    for r in s.representations:
        if r.codecs is not None and is_subtitle_codec(r.codecs):
            return False

        if r.mime_type is not None and r.mime_type.startswith("video/"):
            return True

    return False


def get_pssh(stream: Stream) -> str:
    if stream is None:
        raise ValueError("")

    if not isinstance(stream, Stream):
        logger.warning(f"Invalid type for stream: Expected Stream, got {type(stream).__name__}")

    # We only care about elements that have the field pssh
    pssh_list = [p for p in stream.content_protections if p.pssh is not None]

    if len(pssh_list) != 1:
        logger.fatal("Not implemented for len(pssh_list) != 1")
        sys.exit(1)

    pssh = pssh_list[0].pssh

    if len(pssh) != 1:
        logger.fatal("Not implemented for len(pssh) != 1")
        sys.exit(1)

    p = pssh[0].pssh

    logger.info(f"Found PSSH: {p}")
    return p


def fix_audio(decryption_keys: list[DecryptionKeys]):
    if shutil.which("mp4decrypt") is None:
        logger.fatal("mp4decrypt is not installed or not found in PATH")
        sys.exit(1)

    if not os.path.exists(DEFAULT_ENCRYPTED_AUDIO_FILENAME):
        logger.fatal("Encrypted audio file does not exist")
        sys.exit(1)

    logger.info("Decrypting audio stream")

    cmd = ["mp4decrypt"]
    for key_id, key in decryption_keys:
        cmd += ["--key", f"1:{key_id}:{key}"]

    cmd += [DEFAULT_ENCRYPTED_AUDIO_FILENAME, DEFAULT_DECRYPTED_AUDIO_FILENAME]

    logger.info(f'Command: {" ".join(cmd)}')

    subprocess.run(cmd, capture_output=True, text=True, check=True)


def fix_video(decryption_keys: list[DecryptionKeys]):
    if shutil.which("mp4decrypt") is None:
        logger.fatal("mp4decrypt is not installed or not found in PATH")
        sys.exit(1)

    if not os.path.exists(DEFAULT_ENCRYPTED_VIDEO_FILENAME):
        logger.fatal("Encrypted video file does not exist")
        sys.exit(1)

    logger.info("Decrypting video stream")

    cmd = ["mp4decrypt"]
    for key_id, key in decryption_keys:
        cmd += ["--key", f"1:{key_id}:{key}"]

    cmd += [DEFAULT_ENCRYPTED_VIDEO_FILENAME, DEFAULT_DECRYPTED_VIDEO_FILENAME]

    logger.info(f'Command: {" ".join(cmd)}')
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def merge_streams(output_filename: str = None):
    if shutil.which("ffmpeg") is None:
        logger.fatal("ffmpeg is not installed or not found in PATH")
        sys.exit(1)

    if output_filename is None:
        output_filename = DEFAULT_MERGED_VIDEO_FILENAME

    logger.info("Merging (decrypted) audio and video streams")

    cmd = [
        "ffmpeg",
        "-i",
        DEFAULT_DECRYPTED_VIDEO_FILENAME,
        "-i",
        DEFAULT_DECRYPTED_AUDIO_FILENAME,
        "-c",
        "copy",
        output_filename,
    ]
    logger.info(f'Command: {" ".join(cmd)}')
    subprocess.run(cmd, capture_output=True, text=True, check=True)
