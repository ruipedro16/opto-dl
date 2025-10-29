import sys
import logging
import re
import time
import json
import os


try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
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


logger = logging.getLogger(__name__)


def get_manifest_and_license(url: str, headless: bool = True) -> tuple[str, str]:
    def log_requests():
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

                except Exception as e:
                    logger.warning(f"Error parsing log entry: {e}")

    if url is None:
        raise ValueError()  # TODO: Message

    logger.info("Configuring Chrome driver")
    options = Options()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_argument("--disable-gpu")

    if headless:
        options.add_argument("--headless=new")

    try:
        driver = webdriver.Chrome(options=options)
        logger.info("Initialized Chrome WebDriver")
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        sys.exit(1)

    logger.info(f"Navigating to: {url}")
    driver.get(url)

    logger.info("Waiting for page to fully load...")
    time.sleep(5)

    logger.info("Fetching requests from browser...")
    logs = driver.get_log("performance")

    driver.quit()
    logger.info("Browser session closed successfully.")

    try:
        log_requests()

        with open(REQUESTS_FILE, "r") as f:
            req_text = f.read()

        if manifest := re.search(
            r"\b(?:GET|POST)\s+(https?://[^\s]+manifest\.mpd)", req_text
        ).group(1):
            logger.info(f"Captured manifest URL: {manifest}")
        else:
            logger.warning("No manifest found")

        if license_url := re.search(r"\bPOST\s+(https://[^\s]*license\?[^\s]+)", req_text).group(1):
            logger.info(f"Captured License URL: {license_url}")
        else:
            logger.warning("No License URL found")

        return manifest, license_url
    finally:
        try:
            if os.path.exists("requests.txt"):
                os.remove("requests.txt")
                logger.info("Removed requests.txt")
        except Exception as e:
            logger.warning(f"Failed to remove requests.txt: {e}")
