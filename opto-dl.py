#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys

from pathlib import Path
from mpegdash.parser import MPEGDASHParser

import downloader
import extractor
import pp
import stream
import utils

from defaults import VIDEO_EXTENSIONS


def parse_cli_args():
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

    parser.add_argument(
        "--download-subtitles",
        action="store_true",
        help="Download subtitles",
    )

    parser.add_argument(
        "--store-manifest",
        action="store_true",
        help="Download subtitles",
    )

    parser.add_argument(
        "--list-streams",
        action="store_true",
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

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    return parser.parse_args()


def run(args: argparse.Namespace):
    print(f"Args: {args}")

    if args.output:
        if (
            not args.output.endswith("/")  # is a directory
            and Path(args.output).suffix not in VIDEO_EXTENSIONS
        ):
            sys.stderr.write(
                f"Output file must have a valid video extension: {', '.join(VIDEO_EXTENSIONS)}\n"
            )
            sys.exit(1)

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

    if (
        args.file is not None
        or args.url is not None
        or (args.license_url is not None and args.manifest is not None)
    ):
        if args.file is not None:
            downloader.download_by_file(
                args.file,
                args.download_subtitles,
                args.store_manifest,
            )
        elif args.url is not None:
            downloader.download_by_url(
                args.url,
                args.download_subtitles,
                args.store_manifest,
                args.output,
                args.audio_stream,
                args.video_stream,
            )
        if args.manifest is not None and args.license_url is not None:
            downloader.download_by_manifest_and_license_url(
                args.manifest,
                args.license_url,
                args.download_subtitles,
                args.store_manifest,
                args.audio_stream,
                args.video_stream,
                args.output,
            )


if __name__ == "__main__":
    try:
        args = parse_cli_args()
        utils.setup_logging(args.verbose)
        run(args)
    except KeyboardInterrupt:
        sys.stderr.write("Download interrupted by user\n")
        # Cleanup handled by temp directory context manager
        sys.exit(0)
