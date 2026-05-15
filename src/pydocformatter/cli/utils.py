from __future__ import annotations

import argparse
from collections.abc import Iterable
from typing import Any, TypedDict, Unpack


class ArgumentParserKwargs(TypedDict, total=False):
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
    help: str | None
    aliases: Iterable[str]


class HelpFormatter(argparse.HelpFormatter):
    """Argparse help formatter with a wider argument column."""

    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=32)

    def add_usage(self, usage: str | None, actions: Iterable[argparse.Action], groups: Iterable[argparse._MutuallyExclusiveGroup], prefix: str | None = None) -> None:
        if prefix is None:
            prefix = "Usage: "
        super().add_usage(usage, actions, groups, prefix)


def create_parser(**kwargs: Unpack[ArgumentParserKwargs]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(**kwargs, formatter_class=HelpFormatter, add_help=False)
    return _configure_parser(parser)


def create_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, name: str, **kwargs: Unpack[SubparserKwargs]) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, **kwargs, formatter_class=HelpFormatter, add_help=False)
    return _configure_parser(parser)


def _configure_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser._optionals.title = "Options"
    parser._positionals.title = "Arguments"
    parser.add_argument("-h", "--help", action="help", help="Show this help message and exit")
    return parser
