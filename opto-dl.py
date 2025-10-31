#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys

from mpegdash.parser import MPEGDASHParser

import downloader
import extractor
import pp
import stream
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

parser.add_argument(
    "--list-streams",
    action="store_true",
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

if args.list_streams:
    if args.manifest is None and args.url is None:
        sys.stderr.write("Must provide URL or manifest\n")
        sys.exit(1)
    elif args.manifest is not None:
        manifest = args.manifest
    elif args.url is not None:
        manifest, _ = extractor.get_manifest_and_license(args.url)

    mpd = MPEGDASHParser.parse(manifest)
    streams = stream.get_streams(mpd)
    pp.pp_streams(streams)
    sys.exit(0)

try:
    if args.file is not None:
        downloader.download_by_file(args.file)
    elif args.url is not None:
        downloader.download_by_url(args.url, args.output)
    if args.manifest is not None and args.license_url is not None:
        downloader.download_by_manifest_and_license_url(
            args.manifest, args.license_url, args.output
        )
finally:
    utils.cleanup()
