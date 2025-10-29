import argparse
import pprint

parser = argparse.ArgumentParser(
    prog="opto-dl",
    description="Download media from Opto"
)

parser.add_argument(
    "--manifest",
    required=False,
    help="URL of the manifest",
)

parser.add_argument(
    "-v", "--verbose",
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
    help="License URL",
)

parser.add_argument(
    "-o", "--output",
    help="Output file",
)

args = parser.parse_args()

if args.verbose:
    pprint.pprint(args)
