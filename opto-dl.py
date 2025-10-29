#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import pprint

import downloader
import utils

parser = argparse.ArgumentParser(prog="opto-dl", description="Download media from Opto")

parser.add_argument(
    "--url",
    help="URL of the video (from https://opto.sic.pt/)",
)


parser.add_argument(
    "--manifest",
    help="URL of the manifest",
)

parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Enable verbose output",
)

parser.add_argument(
    "--timeout",
    type=int,
    help="Timeout in seconds",
)

parser.add_argument(
    "--skip-subtitles",
    action="store_true",
    help="Skip downloading subtitles",
)

parser.add_argument(
    "--list-streams",
    type=str,
    help="List available streams",
)

parser.add_argument(
    "--audio-stream",
    help="Audio stream ID",
)

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

if args.verbose:
    pprint.pprint(args)

try:
    if args.url is not None:
        downloader.download_by_url(args.url)
    elif args.manifest is not None and args.license_url is not None:
        downloader.download_by_manifest_and_license_url(args.manifest, args.license_url)

    if args.output:
        pass
finally:
    utils.cleanup()
