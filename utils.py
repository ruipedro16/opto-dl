import os
import re
import logging
import time

import requests
import requests.exceptions

from defaults import (
    DEFAULT_ENCRYPTED_VIDEO_FILENAME,
    DEFAULT_DECRYPTED_VIDEO_FILENAME,
    DEFAULT_DECRYPTED_AUDIO_FILENAME,
    DEFAULT_ENCRYPTED_AUDIO_FILENAME,
    DEFAULT_TIMEOUT,
)


def configure_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    return logging.getLogger(__name__)


logger = configure_logger()


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
                logger.info("Deleted: {}".format(file))
            except Exception as e:
                logger.error("Failed to delete {}: {}".format(file, e))
        else:
            logger.warning("File not found: {}".format(file))


def get_urls(text: str) -> list[str]:
    if text is None:
        raise ValueError("Input text cannot be None")

    if not isinstance(text, str):
        logger.fatal("Invalid type for text: Expected str, got %s", type(text).__name__)

    url_pattern = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)

    return url_pattern.findall(text)


def download_file(
    url: str,
    output_path: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    timeout: int = DEFAULT_TIMEOUT,
) -> bool:
    if not url:
        raise ValueError("")

    if not isinstance(url, str):
        logger.fatal("")

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Downloading {url} (attempt {attempt + 1}/{max_retries + 1})")

            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Successfully downloaded {url}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")

            if attempt < max_retries:
                delay = initial_delay * (backoff_factor**attempt)
                logger.info(f"Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to download {url} after {max_retries + 1} attempts")
                return False

    return False
