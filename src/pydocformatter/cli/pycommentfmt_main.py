import argparse
import logging
import re
import sys

from pydocformatter.config import load_config
from pydocformatter.formatters.pycommentfmt import format_comments
from pydocformatter.utils import collect_file_decisions


def main() -> None:
    """Main entry point for the script."""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("pycommentfmt")

    config = load_config("pycommentfmt", logger)

    parser = argparse.ArgumentParser(description="Format Python comments.")
    parser.add_argument("files", nargs="+", help="Python files to format.")
    parser.add_argument(
        "--line-length",
        type=int,
        default=config.get("line_length", 88),
        help="Maximum line length for comments (default: 88).",
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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit messages about included and ignored files.",
    )

    args = parser.parse_args()
    modified = False

    compiled_include = re.compile(args.include)
    compiled_exclude = re.compile(args.exclude) if args.exclude else None

    # Expand all files from directories, and apply filters
    decisions = collect_file_decisions(args.files, compiled_include, compiled_exclude)

    if args.verbose:
        for decision in decisions:
            if decision.accepted:
                print(f"{decision.path} included")
            else:
                print(f"{decision.path} ignored: {decision.reason}")

    target_files = [decision.path for decision in decisions if decision.accepted]

    for path in target_files:
        changed = format_comments(path, args.line_length, args.check)
        if changed:
            modified = True

    if args.check and modified:
        sys.exit(1)
