#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import shutil
import psutil
import tempfile
import logging

from pathlib import Path
from typing import Optional
from subprocess import run, Popen
from psutil import Process

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def setup_vpn() -> Optional[int]:
    vpn_username: Optional[str] = os.environ.get("VPN_USERNAME")
    vpn_password: Optional[str] = os.environ.get("VPN_PASSWORD")
    vpn_config: Optional[str] = os.environ.get("VPN_CONFIG")

    logger.info(f"VPN_USERNAME={vpn_username}")
    logger.info(f"VPN_PASSWORD={vpn_password}")
    logger.info(f"VPN_CONFIG={vpn_config}")

    if not (vpn_username and vpn_password and vpn_config):
        return None

    if not os.path.isfile(vpn_config):
        print(f"Error: VPN config file does not exist: {vpn_config}", file=sys.stderr)
        sys.exit(1)

    if (openvpn_path := shutil.which("openvpn")) is None:
        print("Error: openvpn is not installed or not in PATH", file=sys.stderr)
        sys.exit(1)

    # Create a temporary file with credentials
    auth_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    auth_file.write(f"{vpn_username}\n{vpn_password}\n")
    auth_file.close()

    proc = Popen(
        ["sudo", openvpn_path, "--config", vpn_config, "--auth-user-pass", auth_file.name],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    pid: int = proc.pid
    logger.info(f"VPN PID: {pid}")

    return pid


def kill_process(pid: int) -> None:
    proc: list[Process] = [p for p in psutil.process_iter() if p.pid == pid]
    if len(proc) == 0:
        print("Could not find the vpn process")

    if len(proc) != 1:
        print("Could not find the vpn process: len > 1")

    p: Process = proc[0]
    p.kill


if __name__ == "__main__":

    urls: list[str] = sys.argv[1:]

    vpn_pid: Optional[int] = setup_vpn() if len(urls) > 0 else None

    # create data directory if it doesn't exist
    (Path(__file__).resolve().parent / "data").mkdir(exist_ok=True)

    try:
        for url in urls:

            fields: list[str] = [
                f for f in url.replace("https://", "").replace("http://", "").split("/") if f
            ]

            print(fields)

            if "opto.sic.pt" in fields:
                run(
                    [
                        "./opto-dl.py",
                        "-v",
                        "--url",
                        url,
                        "-o",
                        f"data/{fields[2]}.mp4",
                    ]
                )
            elif "www.rtp.pt" in fields:
                run(
                    [
                        "./third-party/yt-dlp-rtp-support",
                        "-P",
                        "data/",
                        "-o",
                        '"%(title)s.%(ext)s"',
                        url,
                    ],
                    cwd=Path(__file__).resolve().parent,
                )
            else:
                sys.stderr.write("Unrecognized URL format: " + url + "\n")
                sys.exit(1)

    finally:
        if vpn_pid is not None:
            logger.info(f"Killing VPN process (PID: {vpn_pid})")
            kill_process(vpn_pid)
