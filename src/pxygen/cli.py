"""Command-line interface entry point.

Parses arguments and dispatches to :mod:`pxygen.modes`.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from . import __version__
from .modes import process_directory_mode, process_json_mode
from .paths import clean_path_input, is_json_file
from .presenter import ConsolePresenter, UserAbort
from .resolve import PxygenError

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "warning", log_file: str | None = None) -> None:
    """Configure application logging with a standard detailed format."""
    level = getattr(logging, log_level.upper())
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


def _build_parser():
    import argparse

    class _Formatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        prog="pxygen",
        description=(
            f"pxygen v{__version__}\n\n"
            "Pass a footage folder or a JSON comparison file to --input;\n"
            "the mode is detected automatically."
        ),
        formatter_class=_Formatter,
        epilog=(
            "Examples:\n"
            "  pxygen -i /Volumes/SSD/Footage -o /Volumes/SSD/Proxy\n"
            "  pxygen -i fcmp_report.json -o /Volumes/SSD/Proxy --group b\n"
            "  pxygen -i /Volumes/SSD/Footage -o /Proxy --select\n"
            "  pxygen -i /Volumes/SSD/Footage -o /Proxy --filter Day1 Day2\n"
        ),
    )

    parser.add_argument(
        "-v", "-V", "--version",
        action="version", version=f"pxygen v{__version__}",
    )
    parser.add_argument("-i", "--input", help="Footage folder or JSON comparison file")
    parser.add_argument("-o", "--output", help="Proxy output folder")
    parser.add_argument(
        "-n", "--in-depth",
        type=int, default=1,
        help="Levels below the input folder to treat as one footage group",
    )
    parser.add_argument(
        "-d", "--out-depth",
        type=int, default=2,
        help="Levels below the input folder to preserve as subfolders",
    )
    parser.add_argument(
        "-g", "--group",
        choices=["a", "b"], default="a",
        help="JSON mode: fcmp side to render (a = unique_in_a, b = unique_in_b)",
    )

    selection_group = parser.add_mutually_exclusive_group()
    selection_group.add_argument(
        "-s", "--select", action="store_true",
        help="Interactively select which folders to process",
    )
    selection_group.add_argument(
        "-f", "--filter", nargs="+", metavar="NAME",
        help="Folder names to process (e.g. Day1 Day2)",
    )

    parser.add_argument(
        "-k", "--codec",
        choices=["auto", "prores", "h265", "hevc", "265"],
        default="auto",
        help="Render codec (h265 for ≤4 audio ch, ProRes otherwise)",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="warning",
        help="Logging verbosity",
    )
    parser.add_argument(
        "--log-file",
        help="Optional file path for detailed runtime logs",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level, args.log_file)
    presenter = ConsolePresenter()

    filter_mode = "select" if args.select else ("filter" if args.filter else None)
    filter_list = args.filter if filter_mode == "filter" else None

    shared = dict(
        filter_mode=filter_mode,
        filter_list=filter_list,
        codec=args.codec,
        input_func=presenter.read_line,
        output=presenter.show,
        confirm_render=lambda: presenter.confirm(
            "\nAll render jobs added. Start rendering now? (y/n)"
        ),
    )

    try:
        if not args.input:
            parser.print_help()
            sys.exit(1)
        if not args.output:
            parser.error("requires -o/--output")
        input_path = clean_path_input(args.input)
        output_path = clean_path_input(args.output)
        if is_json_file(input_path):
            process_json_mode(
                input_path, output_path,
                args.group, args.in_depth, args.out_depth,
                **shared,
            )
        else:
            process_directory_mode(
                input_path, output_path,
                args.in_depth, args.out_depth,
                **shared,
            )

    except UserAbort as exc:
        presenter.show(str(exc) or "Aborted.")
        sys.exit(0)
    except PxygenError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except AttributeError as exc:
        # Typically: Resolve API returned None (Resolve not running or API call failed)
        logger.error("Resolve API error: %s", exc)
        logger.error("Make sure DaVinci Resolve is running.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.error("Aborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
