from __future__ import annotations

import argparse
import importlib.metadata
import sys
import typing
from collections.abc import Callable

import pydocformatter.cli.check as check
import pydocformatter.cli.config as config_command
import pydocformatter.cli.global_args as global_args
import pydocformatter.cli.utils as cli_utils


def main() -> int:
    """Run the pydocfmt command-line entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        return run_version(args)
    elif args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    else:
        func = typing.cast(Callable[[argparse.Namespace], int], args.func)
        return func(args)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level pydocfmt argument parser."""
    parser = cli_utils.create_parser(prog="pydocfmt", description="Format Python docstrings and comments.")
    parser.add_argument("-V", "--version", action="store_true", help="Print version and exit.")

    SUBCOMMANDS = {
        "check": check.add_parser,
        "config": config_command.add_parser,
        "version": add_version_parser,
    }

    subparsers = parser.add_subparsers(title="Commands", dest="command", metavar="COMMAND")
    command_parsers = {command: add_command_func(subparsers) for command, add_command_func in SUBCOMMANDS.items()}
    add_parser_help(parser, subparsers, command_parsers=command_parsers)

    global_args.add_global_arguments(parser, dest_prefix="global")

    return parser


def add_version_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    """Add the version subcommand parser."""
    version_parser = cli_utils.create_subparser(
        subparsers,
        name="version",
        help="Print version and exit",
        description="Print pydocfmt version and exit.",
    )
    version_parser.set_defaults(func=run_version)
    return version_parser


def add_parser_help(
    parser: argparse.ArgumentParser, subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, command_parsers: dict[str, argparse.ArgumentParser]
) -> argparse.ArgumentParser:
    """Add the help subcommand parser."""
    help_parser = cli_utils.create_subparser(
        subparsers,
        name="help",
        help="Print this message or the help of the given subcommand",
        description="Print this message or the help of the given subcommand.",
    )
    command_parsers["help"] = help_parser
    help_parser.add_argument(
        "topic",
        nargs="?",
        choices=tuple(command_parsers.keys()),
        metavar="COMMAND",
        help="Subcommand to show help for.",
    )
    help_parser.set_defaults(func=lambda args: run_help(args, parser, command_parsers=command_parsers))
    return help_parser


def run_version(args: argparse.Namespace) -> int:
    """Run the version subcommand."""
    del args
    print(f"pydocfmt {importlib.metadata.version('pydocformatter')}")
    return 0


def run_help(args: argparse.Namespace, parser: argparse.ArgumentParser, *, command_parsers: dict[str, argparse.ArgumentParser]) -> int:
    """Run the help subcommand."""
    if args.topic is None:
        parser.print_help()
    else:
        command_parsers[args.topic].print_help()
    return 0
