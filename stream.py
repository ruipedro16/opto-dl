"""
The function for checking if a stream is video or audio are based on https://github.com/emarsden/dash-mpd-rs
"""

import sys
import logging


try:
    from mpegdash.nodes import AdaptationSet, Period, Representation
except ImportError:
    sys.stderr.write("")  # TODO: MEssage
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def get_streams(manifest) -> tuple[list[Representation], list[Representation]]:
    if len(manifest.periods) != 1:
        sys.stderr.write("Not implemented for len(periods) != 1")
        sys.exit(1)

    period = manifest.periods[0]

    audio_streams: list[Representation] = [
        s
        for adaptation in period.adaptation_sets
        if is_audio_adaptation(adaptation)
        for s in adaptation.representations
    ]

    video_streams: list[Representation] = [
        s
        for adaptation in period.adaptation_sets
        for s in adaptation.representations
        if s not in audio_streams
    ]

    logger.info(f"Audio Streams: {[s.id for s in audio_streams]}")
    logger.info(f"Video Streams: {[s.id for s in video_streams]}")

    return audio_streams, video_streams


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


def choose_best_audio(audio_streams: list[Representation]) -> Representation:
    if not audio_streams:
        raise ValueError("No audio streams provided")

    if all(is_audio_stream(s) for s in audio_streams):
        logger.warning("Not all streams are audio")

    s = max(audio_streams, key=lambda s: s.bandwidth or 0)

    logger.info(f"Best audio: StreamID={s.id}, Bandwidth={s.bandwidth}")

    return s


def choose_best_video(video_streams: list[Representation]) -> Representation:
    if not video_streams:
        raise ValueError(f"No video streams provided: {video_streams}")

    # if all(is_video_stream(s) for s in video_streams):
    #    logger.warning("Not all streams are video")

    s = max(video_streams, key=lambda s: s.width * s.height or 0)

    logger.info(f"Best video: StreamID={s.id}, Resolution={s.height}x{s.width}")

    return s


def is_subtitle_codec(c: str) -> bool:
    return c in ("wvtt", "c608", "stpp", "tx3g") or c.startswith("stpp.")


def is_subtitle_mimetype(mt: str) -> bool:
    return mt in ("text/vtt", "application/ttml+xml", "application/x-sami")
