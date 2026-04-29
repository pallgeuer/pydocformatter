import argparse
import logging
import re
import sys

from pydocformatter.config import load_config
from pydocformatter.formatters.pydocfmt import format_docstrings
from pydocformatter.utils import collect_files


def main() -> None:
    """Main entry point for the script."""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("pydocfmt")

    config = load_config("pydocfmt", logger)

    parser = argparse.ArgumentParser(description="Format Python docstrings.")
    parser.add_argument("files", nargs="+", help="Python files to format.")
    parser.add_argument(
        "--line-length",
        type=int,
        default=config.get("line_length", 88),
        help="Maximum line length for docstrings (default: 88).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files are formatted correctly without modifying them.",
    )
    parser.add_argument(
        "--include",
        default=config.get("include", r"\.pyi?$"),
        help="Regex pattern for files to include.",
    )
    parser.add_argument(
        "--exclude",
        default=config.get("exclude", ""),
        help="Regex pattern for files to exclude.",
    )

    args = parser.parse_args()
    modified = False

    compiled_include = re.compile(args.include)
    compiled_exclude = re.compile(args.exclude) if args.exclude else None

    # Expand all files from directories, and apply filters
    target_files = collect_files(args.files, compiled_include, compiled_exclude)

    for path in target_files:
        changed = format_docstrings(path, args.line_length, args.check)
        if changed:
            modified = True

    if args.check and modified:
        sys.exit(1)
