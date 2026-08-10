"""Project argparse helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import argparse
from collections.abc import Iterable
from typing import Any, Protocol, TypedDict, Unpack


class ArgumentContainer(Protocol):
    """Public argument-adding interface shared by parsers and argument groups."""

    def add_argument(self, *name_or_flags: str, **kwargs: Any) -> argparse.Action:
        """Add an argument and return its argparse action.

        Args:
            *name_or_flags (str): Positional name or optional flag spellings.
            **kwargs (Any): Argparse argument options.
        """
        ...


class SubparserCollection(Protocol):
    """Public subparser-adding interface returned by argparse."""

    def add_parser(self, name: str, **kwargs: Any) -> argparse.ArgumentParser:
        """Add and return a named subparser.

        Args:
            name (str): Subparser command name.
            **kwargs (Any): Argparse parser options.
        """
        ...


class ArgumentParserKwargs(TypedDict, total=False):
    """Keyword arguments accepted by the project argparse parser factory.

    Attributes:
        prog (str | None): Program name shown in help output.
        usage (str | None): Custom usage string.
        description (str | None): Parser description.
        epilog (str | None): Parser epilog.
        parents (Iterable[argparse.ArgumentParser]): Parent parsers to inherit from.
        prefix_chars (str): Characters that prefix optional arguments.
        fromfile_prefix_chars (str | None): Characters that load arguments from files.
        argument_default (Any): Default value for parser arguments.
        conflict_handler (str): Conflict resolution strategy for duplicate options.
        allow_abbrev (bool): Whether long options may be abbreviated.
        exit_on_error (bool): Whether parser errors should exit immediately.
    """

    prog: str | None
    usage: str | None
    description: str | None
    epilog: str | None
    parents: Iterable[argparse.ArgumentParser]
    prefix_chars: str
    fromfile_prefix_chars: str | None
    argument_default: Any
    conflict_handler: str
    allow_abbrev: bool
    exit_on_error: bool


class SubparserKwargs(ArgumentParserKwargs, total=False):
    """Keyword arguments accepted by the project subparser factory.

    Attributes:
        help (str | None): Short help text shown in the parent parser command list.
        aliases (Iterable[str]): Alternate command names for the subparser.
    """

    help: str | None
    aliases: Iterable[str]


class HelpFormatter(argparse.HelpFormatter):
    """Argparse help formatter with a wider argument column.

    Args:
        prog (str): Program name for argparse help output.
    """

    def __init__(self, prog: str) -> None:
        """Initialize the formatter with the project help layout.

        Args:
            prog (str): Program name for argparse help output.
        """
        super().__init__(prog, max_help_position=32)

    def add_usage(self, usage: str | None, actions: Iterable[argparse.Action], groups: Iterable[Any], prefix: str | None = None) -> None:
        """Add a usage line with project-specific capitalization.

        Args:
            usage (str | None): Explicit usage string, or None to let argparse derive one.
            actions (Iterable[argparse.Action]): Parser actions included in the usage line.
            groups (Iterable[Any]): Mutually exclusive groups included in usage.
            prefix (str | None): Usage prefix, defaulting to `Usage: `.
        """
        if prefix is None:
            prefix = "Usage: "
        super().add_usage(usage, actions, groups, prefix)

    def start_section(self, heading: str | None) -> None:
        """Start a help section with project-specific capitalization.

        Args:
            heading (str | None): Section heading selected by argparse.
        """
        if heading == "positional arguments":
            heading = "Arguments"
        elif heading == "options":
            heading = "Options"
        super().start_section(heading)


def create_parser(**kwargs: Unpack[ArgumentParserKwargs]) -> argparse.ArgumentParser:
    """Create a configured top-level argparse parser.

    Args:
        **kwargs (Unpack[ArgumentParserKwargs]): Keyword arguments forwarded to `argparse.ArgumentParser`.

    Returns:
        argparse.ArgumentParser: Parser with project help formatting and explicit help option handling.
    """
    parser = argparse.ArgumentParser(**kwargs, formatter_class=HelpFormatter, add_help=False)
    return _configure_parser(parser)


def create_subparser(subparsers: SubparserCollection, *, name: str, **kwargs: Unpack[SubparserKwargs]) -> argparse.ArgumentParser:
    """Create a project-formatted argparse subparser through a typed boundary.

    Args:
        subparsers (SubparserCollection): Parent subparser collection to add to.
        name (str): Command name for the subparser.
        **kwargs (Unpack[SubparserKwargs]): Keyword arguments forwarded to `add_parser`.

    Returns:
        argparse.ArgumentParser: Subparser with project help formatting and explicit help option handling.
    """
    parser = subparsers.add_parser(name, **kwargs, formatter_class=HelpFormatter, add_help=False)
    return _configure_parser(parser)


def _configure_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add project parser defaults through public argparse interfaces."""
    option_prefix = parser.prefix_chars[0]
    parser.add_argument(f"{option_prefix}h", f"{option_prefix}{option_prefix}help", action="help", help="Show this help message and exit")
    return parser
