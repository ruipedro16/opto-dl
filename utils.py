import sys
import logging

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


def download_file(url: str, output_path: str = None, max_retries=3, multiplier=1.5):
    if not url:
        raise ValueError("The 'url' parameter is empty. Please provide a valid URL.")

    output_path = output_path or url.split("/")[-1]
    logger.info("Starting download from URL: %s", url)


def cleanup():
    pass
