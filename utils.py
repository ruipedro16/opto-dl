import re
import logging
import time

from pathlib import Path
from urllib.parse import urlparse, unquote

import requests
import requests.exceptions

from defaults import DEFAULT_TIMEOUT


def setup_logging(verbose: bool = False):
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


logger = logging.getLogger(__name__)


def get_urls(text: str) -> list[str]:
    if text is None:
        raise ValueError("Input text cannot be None")

    if not isinstance(text, str):
        logger.fatal("Invalid type for text: Expected str, got %s", type(text).__name__)

    url_pattern = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)

    return url_pattern.findall(text)


def download_file(
    url: str,
    output_path: str,  # TODO: FIXME: Replace str with Path
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    timeout: int = DEFAULT_TIMEOUT,
) -> bool:
    if not url:
        raise ValueError("url cannot be empty")

    if not isinstance(url, str):
        logger.fatal(f"Invalid type for url: Expected str, got {type(url).__name__}")

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
