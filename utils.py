import sys
import os
import re
import logging


from defaults import (
    DEFAULT_ENCRYPTED_VIDEO_FILENAME,
    DEFAULT_DECRYPTED_VIDEO_FILENAME,
    DEFAULT_DECRYPTED_AUDIO_FILENAME,
    DEFAULT_ENCRYPTED_AUDIO_FILENAME,
)

try:
    import requests
except ImportError:
    sys.stderr.write("Error: 'requests' is not installed. Install it with: pip install requests\n")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def cleanup():
    files_to_delete = [
        DEFAULT_ENCRYPTED_AUDIO_FILENAME,
        DEFAULT_DECRYPTED_AUDIO_FILENAME,
        DEFAULT_ENCRYPTED_VIDEO_FILENAME,
        DEFAULT_DECRYPTED_VIDEO_FILENAME,
    ]

    for file in files_to_delete:
        if os.path.exists(file):
            try:
                os.remove(file)
                logger.info(f"Deleted: {file}")
            except Exception as e:
                logger.error(f"Failed to delete {file}: {e}")
        else:
            logger.warning(f"File not found: {file}")


def get_urls(text: str) -> list[str]:
    if text is None:
        raise ValueError("Input text cannot be None")

    if not isinstance(text, str):
        logger.fatal(f"Invalid type for text: Expected str, got {type(text).__name__}")

    url_pattern = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)

    return url_pattern.findall(text)
