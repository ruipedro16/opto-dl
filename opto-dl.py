#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging

import downloader
import utils

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(prog="opto-dl", description="Download media from Opto")

parser.add_argument("-f", "--file", help="File with multiple URLs")

parser.add_argument(
    "--url",
    help="URL of the video (from https://opto.sic.pt/)",
)


parser.add_argument(
    "--manifest",
    help="URL of the manifest",
)

# TODO: Use this
parser.add_argument(
    "--timeout",
    type=int,
    help="Timeout in seconds",
)

# TODO: Use this
parser.add_argument(
    "--skip-subtitles",
    action="store_true",
    help="Skip downloading subtitles",
)

# TODO: Use this
parser.add_argument(
    "--list-streams",
    type=str,
    help="List available streams",
)

# TODO: Use this
parser.add_argument(
    "--audio-stream",
    help="Audio stream ID",
)

# TODO: Use this
parser.add_argument(
    "--video-stream",
    help="Video stream ID",
)

parser.add_argument(
    "--license-url",
    type=str,
    help="License URL",
)

parser.add_argument(
    "-o",
    "--output",
    help="Output file",
)

args = parser.parse_args()

try:
    if args.file is not None:
        downloader.download_by_file(args.file)
    if args.url is not None:
        downloader.download_by_url(args.url, args.output)
    elif args.manifest is not None and args.license_url is not None:
        downloader.download_by_manifest_and_license_url(
            args.manifest, args.license_url, args.output
        )
finally:
    utils.cleanup()
