"""The pydocfmt command-line entry point."""

# Future imports
from __future__ import annotations

# Standard library imports
import sys
import typing
import importlib.metadata
from collections.abc import Callable

# First-party imports
import pydocformatter.cli.rule as rule_command
import pydocformatter.cli.clean as clean_command
import pydocformatter.cli.config as config_command
import pydocformatter.cli.linter as linter_command
from pydocformatter.cli import check, global_args
from pydocformatter.utils import argparser


if typing.TYPE_CHECKING:
    # Standard library imports
    import argparse


def main() -> int:
    """Run the pydocfmt command-line entry point.

    Returns:
        int: Process exit status code.
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        return run_version(args)
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    func = typing.cast("Callable[[argparse.Namespace], int]", args.func)
    return func(args)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level pydocfmt argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser for the `pydocfmt` command.
    """
    parser = argparser.create_parser(prog="pydocfmt", description="Format Python docstrings and comments.")
    parser.add_argument("-V", "--version", action="store_true", help="Print version and exit.")

    subcommands = {
        "check": check.add_parser,
        "clean": clean_command.add_parser,
        "config": config_command.add_parser,
        "linter": linter_command.add_parser,
        "rule": rule_command.add_parser,
        "version": add_version_parser,
    }

    subparsers = parser.add_subparsers(title="Commands", dest="command", metavar="COMMAND")
    command_parsers = {command: add_command_func(subparsers) for command, add_command_func in subcommands.items()}
    add_parser_help(parser, subparsers, command_parsers=command_parsers)

    global_args.add_global_arguments(parser, dest_prefix="global")

    return parser


def add_version_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    """Add the version subcommand parser.

    Args:
        subparsers (argparse._SubParsersAction[argparse.ArgumentParser]): Top-level subparser action.

    Returns:
        argparse.ArgumentParser: Configured `version` subcommand parser.
    """
    version_parser = argparser.create_subparser(subparsers, name="version", help="Print version and exit", description="Print pydocfmt version and exit.")
    version_parser.set_defaults(func=run_version)
    return version_parser


def add_parser_help(
    parser: argparse.ArgumentParser, subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, command_parsers: dict[str, argparse.ArgumentParser]
) -> argparse.ArgumentParser:
    """Add the help subcommand parser.

    Args:
        parser (argparse.ArgumentParser): Top-level parser whose help should be shown without a topic.
        subparsers (argparse._SubParsersAction[argparse.ArgumentParser]): Top-level subparser action.
        command_parsers (dict[str, argparse.ArgumentParser]): Existing command parsers keyed by command name.

    Returns:
        argparse.ArgumentParser: Configured `help` subcommand parser.
    """
    help_parser = argparser.create_subparser(
        subparsers, name="help", help="Print this message or the help of the given subcommand", description="Print this message or the help of the given subcommand."
    )
    command_parsers["help"] = help_parser
    help_parser.add_argument("topic", nargs="?", choices=tuple(command_parsers.keys()), metavar="COMMAND", help="Subcommand to show help for.")
    help_parser.set_defaults(func=lambda args: run_help(args, parser, command_parsers=command_parsers))
    return help_parser


def run_version(args: argparse.Namespace) -> int:
    """Run the version subcommand.

    Args:
        args (argparse.Namespace): Parsed command arguments, currently unused.

    Returns:
        int: Process exit status code.
    """
    del args
    print(f"pydocfmt {importlib.metadata.version('pydocformatter')}")
    return 0


def run_help(args: argparse.Namespace, parser: argparse.ArgumentParser, *, command_parsers: dict[str, argparse.ArgumentParser]) -> int:
    """Run the help subcommand.

    Args:
        args (argparse.Namespace): Parsed command arguments containing the optional help topic.
        parser (argparse.ArgumentParser): Top-level parser used when no topic is supplied.
        command_parsers (dict[str, argparse.ArgumentParser]): Command parsers keyed by command name.

    Returns:
        int: Process exit status code.
    """
    if args.topic is None:
        parser.print_help()
    else:
        command_parsers[args.topic].print_help()
    return 0
