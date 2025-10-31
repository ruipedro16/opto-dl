import sys
import logging

from stream import Stream, StreamType

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    sys.stderr.write("Error: rich module not found. Install it with: pip install rich\n")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def pp_streams(streams: list[Stream]):
    if streams is None:
        raise ValueError("streams cannot be None")

    if not isinstance(streams, list):
        logger.fatal(f"Invalid type for streams: Expected str, list {type(streams).__name__}")

    if not all(isinstance(x, Stream) for x in streams):
        invalid_types = {type(x).__name__ for x in streams if not isinstance(x, Stream)}
        logger.fatal(
            f"Invalid items in streams: Expected all Stream instances, got {', '.join(invalid_types)}"
        )

    if not streams:
        print("No streams found")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold")

    table.add_column("ID")
    table.add_column("Stream Type")
    table.add_column("Resolution")
    table.add_column("Fps")
    table.add_column("Bandwidth")

    for stream in streams:
        if stream.stream_type == StreamType.VIDEO:
            table.add_row(
                stream.id,
                str(stream.stream_type),
                f"{stream.width}x{stream.height}",
                str(stream.fps),
                "--",
            )
        elif stream.stream_type == StreamType.AUDIO:
            table.add_row(stream.id, str(stream.stream_type), "--", "--", str(stream.bandwidth))
        elif stream.stream_type == StreamType.SUBTITLES:
            table.add_row(stream.id, str(stream.stream_type), "--", "--", "--")
        else:
            pass

    console.print(table)
