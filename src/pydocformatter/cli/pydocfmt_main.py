import argparse
import importlib.metadata
import sys
import typing
from collections.abc import Callable

import pydocformatter.cli.check as check
import pydocformatter.config as config


class WideHelpFormatter(argparse.HelpFormatter):
    """Argparse help formatter with a wider argument column."""

    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=32)


def main() -> int:
    """Run the pydocfmt command-line entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print_version()
        return 0
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    func = typing.cast(Callable[[argparse.Namespace], int], args.func)
    return func(args)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level pydocfmt argument parser."""
    parser = argparse.ArgumentParser(
        prog="pydocfmt",
        description="Format Python docstrings and comments.",
        formatter_class=WideHelpFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    add_global_arguments(parser, dest_prefix="global")
    subparsers = parser.add_subparsers(
        title="Commands",
        dest="command",
        metavar="<COMMAND>",
    )
    check_parser = check.add_parser(subparsers, config.FormatterSettings(), formatter_class=WideHelpFormatter)

    version_parser = subparsers.add_parser(
        "version",
        help="Print version and exit",
        description="Print pydocfmt version and exit.",
        formatter_class=WideHelpFormatter,
    )
    version_parser.set_defaults(func=run_version)

    help_parser = subparsers.add_parser(
        "help",
        help="Print this message or the help of the given subcommand",
        description="Print this message or the help of the given subcommand.",
        formatter_class=WideHelpFormatter,
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        choices=("check", "version", "help"),
        help="Subcommand to show help for.",
    )
    help_parser.set_defaults(func=lambda args: run_help(args, parser, {"check": check_parser, "version": version_parser, "help": help_parser}))
    return parser


def add_global_arguments(parser: argparse.ArgumentParser, *, dest_prefix: str) -> None:
    """Add Ruff-style global configuration arguments to a parser."""
    global_options = parser.add_argument_group("Global options")
    global_options.add_argument(
        "--config",
        action="append",
        default=None,
        dest=f"{dest_prefix}_config",
        metavar="CONFIG_OPTION",
        help="Path to a TOML configuration file or TOML '<KEY> = <VALUE>' override.",
    )
    global_options.add_argument(
        "--isolated",
        action="store_true",
        default=False,
        dest=f"{dest_prefix}_isolated",
        help="Ignore all configuration files.",
    )


def run_version(args: argparse.Namespace) -> int:
    """Run the version subcommand."""
    del args
    print_version()
    return 0


def run_help(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    command_parsers: dict[str, argparse.ArgumentParser],
) -> int:
    """Run the help subcommand."""
    if args.topic is None:
        parser.print_help()
    else:
        command_parsers[args.topic].print_help()
    return 0


def print_version() -> None:
    """Print the installed package version."""
    print(f"pydocfmt {importlib.metadata.version('pydocformatter')}")
