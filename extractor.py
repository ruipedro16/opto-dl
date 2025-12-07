import logging
import sys
import re
import time
import json
import os

from collections import namedtuple
from pathlib import Path

from defaults import DEFAULT_TIMEOUT

try:
    import requests
except ImportError:
    sys.stderr.write("Error: 'requests' is not installed. Install it with: pip install requests\n")
    sys.exit(1)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.ie.webdriver import WebDriver
except ImportError:
    sys.stderr.write("Error: 'selenium' is not installed. Install it with: pip install selenium\n")
    sys.exit(1)

# File to where the requests are logged
REQUESTS_FILE: Path = Path.cwd() / "requests.txt"

logger = logging.getLogger(__name__)

DecryptionKeys = namedtuple("DecryptionKeys", ["Key", "KeyId"])


def get_manifest_and_license(
    url: str, headless: bool = True, max_retries: int = 5, timeout=None
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
                        request_method = resp.get("method", "UNKNOWN")
                        f.write(f"{request_method} {resp}\n")
                except Exception as e:
                    logger.warning(f"Error parsing log entry: {e}")

    def visit_page(driver: WebDriver, page_url: str, timeout: int):
        if driver is None:
            raise ValueError("driver cannot be None")

        if page_url is None:
            raise ValueError("URL must not be empty")

        if not isinstance(page_url, str):
            logger.fatal(f"Invalid type for page_url: Expected str, got {type(page_url).__name__}")

        if timeout is None:
            raise ValueError("timeout cannot be None")

        if isinstance(timeout, str):
            logger.fatal(f"Invalid type for timeout: Expected int, got {type(timeout).__name__}")
            logger.info("Converting timeout from str to int")
            try:
                timeout = int(timeout)
            except ValueError:
                logger.fatal("Failed to convert timeout to int")

        if not isinstance(timeout, int) and not isinstance(timeout, str):
            logger.fatal(f"Invalid type for timeout: Expected int, got {type(timeout).__name__}")

        logger.info(f"Navigating to: {page_url}")
        driver.get(page_url)

        logger.info("Waiting for page to fully load [timeout=%d]...", timeout)

        time.sleep(timeout)

        logger.info("Fetching requests from browser...")
        logs = driver.get_log("performance")

        log_requests(logs)

    if url is None:
        raise ValueError("url cannot be None")

    if not isinstance(url, str):
        logger.fatal(f"Invalid type for url: Expected str, got {type(url).__name__}")

    timeout = timeout or DEFAULT_TIMEOUT
    if not isinstance(timeout, int):
        raise TypeError(f"timeout must be int, got {type(timeout).__name__}")

    logger.info("Configuring Chrome driver")
    options = Options()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
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
        logger.info("Attempt %d/%d...", attempt, max_retries)

        try:
            # This populates the requests file
            visit_page(driver, url, timeout)

            with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
                req_text = f.read()

            manifest_match = re.search(r"\b(?:GET|POST)\s+(https?://[^\s]+manifest\.mpd)", req_text)
            license_match = re.search(r"\bPOST\s+(https://[^\s]*license\?[^\s]+)", req_text)

            if manifest_match is not None:
                manifest_url = manifest_match.group(1)
                logger.info("Captured manifest URL: %s", manifest_url)
            else:
                logger.warning("No manifest found")

            if license_match is not None:
                license_url = license_match.group(1)
                logger.info("Captured License URL: %s", license_url)
            else:
                logger.warning("No License URL found")

            if manifest_url and license_url:
                break  # Success

            timeout *= 1.5  # TODO: this should be an argument
            logger.info("Timeout increased to %d", timeout)
        except Exception as e:
            logger.warning(f"Error during attempt {attempt}: {e}")
        finally:
            try:
                if os.path.exists(REQUESTS_FILE):
                    os.remove(REQUESTS_FILE)
                    logger.info("Removed %s", Path(REQUESTS_FILE).resolve())
            except Exception as e:
                logger.warning(f"Failed to remove %s: {e}", Path(REQUESTS_FILE).resolve())

    driver.quit()
    logger.info("Browser session closed.")

    if not manifest_url or not license_url:
        logger.fatal("Failed to capture both manifest and license URLs after retries.")
        sys.exit(1)

    return manifest_url, license_url


def get_keys(pssh: str, license_url: str, max_retries=5) -> list[DecryptionKeys]:
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Attempt %d/%d to get decryption keys...", attempt, max_retries)
            timeout = 5 * attempt  # Increase timeout with each retry
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
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) "
                                "Gecko/20100101 Firefox/134.0"
                            ),
                            "Accept": "*/*",
                            "Accept-Language": "en-US,en;q=0.7",
                        }
                    ),
                },
                timeout=timeout,
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
                    logger.error(f"Invalid line during key parsing: {line} => {e}")
                    continue
            return r
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network or HTTP error during attempt {attempt}: {e}")
            time.sleep(2**attempt)  # Exponential backoff
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decoding error during attempt {attempt}: {e}")
            time.sleep(2**attempt)
        except KeyError as e:
            logger.warning(f"Key error in response during attempt {attempt}: {e}")
            time.sleep(2**attempt)
        except Exception as e:
            logger.warning(f"Unexpected error during attempt {attempt}: {e}")
            time.sleep(2**attempt)

    logger.fatal("Failed to get decryption keys after multiple retries.")
    sys.exit(1)
