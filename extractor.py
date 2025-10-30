import sys
import logging
import re
import time
import json
import os

from collections import namedtuple

from selenium.webdriver.ie.webdriver import WebDriver

from defaults import DEFAULT_TIMEOUT

try:
    import requests
except ImportError:
    sys.stderr.write("Error: 'requests' is not installed. Install it with: pip install requests\n")
    sys.exit(1)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
except ImportError:
    sys.stderr.write("Error: 'selenium' is not installed. Install it with: pip install selenium\n")
    sys.exit(1)

# File to where the requests are logged
REQUESTS_FILE = "requests.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

DecryptionKeys = namedtuple("DecryptionKeys", ["Key", "KeyId"])


def get_manifest_and_license(
    url: str, headless: bool = True, max_retries: int = 5
) -> tuple[str, str]:
    def log_requests(logs):
        with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
            for log in logs:
                try:
                    message = json.loads(log["message"])["message"]
                    method = message.get("method")

                    if method == "Network.requestWillBeSent":
                        req = message["params"]["request"]
                        request_method = req.get("method", "UNKNOWN")
                        request_url = req.get("url", "")
                        f.write(f"{request_method} {request_url}\n")
                    elif method == "Network.responseReceived":
                        resp = message["params"]["response"]
                        f.write(f"{request_method} {resp}\n")
                except Exception as e:
                    logger.warning(f"Error parsing log entry: {e}")

    def visit_page(driver: WebDriver, page_url):
        if driver is None:
            raise ValueError("")

        if url is None:
            raise ValueError("URL must not be empty")

        if not isinstance(page_url, str):
            logger.warning(
                f"Invalid type for page_url: Expected str, got {type(page_url).__name__}"
            )

        logger.info(f"Navigating to: {url}")
        driver.get(url)

        logger.info("Waiting for page to fully load...")
        time.sleep(DEFAULT_TIMEOUT)

        logger.info("Fetching requests from browser...")
        logs = driver.get_log("performance")

        log_requests(logs)

    if url is None:
        raise ValueError("")  # TODO: Message

    logger.info("Configuring Chrome driver")
    options = Options()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_argument("--disable-gpu")

    if headless:
        options.add_argument("--headless=new")

    try:
        driver: WebDriver = webdriver.Chrome(options=options)
        logger.info("Initialized Chrome WebDriver")
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        sys.exit(1)

    manifest_url = None
    license_url = None

    for attempt in range(1, max_retries + 1):
        logger.info(f"Attempt {attempt}/{max_retries}...")

        try:
            # This populates the requests file
            visit_page(driver, url)

            with open(REQUESTS_FILE, "r") as f:
                req_text = f.read()

            manifest_match = re.search(r"\b(?:GET|POST)\s+(https?://[^\s]+manifest\.mpd)", req_text)
            license_match = re.search(r"\bPOST\s+(https://[^\s]*license\?[^\s]+)", req_text)

            if manifest_match is not None:
                manifest_url = manifest_match.group(1)
                logger.info(f"Captured manifest URL: {manifest_url}")
            else:
                logger.warning("No manifest found")

            if license_match is not None:
                license_url = license_match.group(1)
                logger.info(f"Captured License URL: {license_url}")
            else:
                logger.warning("No License URL found")

            if manifest_url and license_url:
                break  # Success

        except Exception as e:
            logger.warning(f"Error during attempt {attempt}: {e}")
        finally:
            try:
                if os.path.exists("requests.txt"):
                    os.remove("requests.txt")
                    logger.info("Removed requests.txt")
            except Exception as e:
                logger.warning(f"Failed to remove requests.txt: {e}")

    driver.quit()
    logger.info("Browser session closed.")

    if not manifest_url or not license_url:
        logger.fatal("Failed to capture both manifest and license URLs after retries.")
        sys.exit(1)

    return manifest_url, license_url


def get_keys(pssh: str, license_url: str, max_retries=3) -> list[DecryptionKeys]:
    # TODO: Implement retries. If no respose is ok, log.fatal and sys.exit(1)
    response = requests.post(
        url="https://cdrm-project.com/api/decrypt",
        headers={
            "Content-Type": "application/json",
        },
        json={
            "pssh": pssh,
            "licurl": license_url,
            "headers": str(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.7",
                }
            ),
        },
    )

    response.raise_for_status()

    text: str = response.json()["message"]

    r: list[DecryptionKeys] = []
    for line in text.splitlines():
        try:
            key_id, key = line.split(":")
            r.append(DecryptionKeys(key, key_id))
            logger.info(f"Found Key: {key} ; KeyID: {key_id}")
        except ValueError as e:
            logger.error(f"Invalid line: {line} ==> {e}")
            continue

    return r
