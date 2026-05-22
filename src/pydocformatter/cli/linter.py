from __future__ import annotations

import argparse
import json
from typing import TypedDict

import pydocformatter.cli.global_args as global_args
import pydocformatter.rules.base as rule_base
import pydocformatter.rules.collection as rule_collection
import pydocformatter.utils.argparser as argparser


class LinterMetadataOutput(TypedDict, total=False):
    """JSON metadata for one rule-prefix linter."""

    prefix: str
    name: str
    url: str


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    """Add the linter subcommand parser."""
    parser = argparser.create_subparser(
        subparsers,
        name="linter",
        description="List all supported rule-prefix linters.",
        help="List all supported rule-prefix linters",
    )
    parser.add_argument(
        "--output-format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    global_args.add_global_arguments(parser, dest_prefix="command")
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace) -> int:
    """Run the linter subcommand."""
    linters = rule_collection.RULE_COLLECTION.linters
    if args.output_format == "json":
        print(json.dumps([linter_json(linter) for linter in linters], indent=2))
    else:
        print(format_linters_text(linters), end="")
    return 0


def linter_json(linter: rule_base.RuleLinterMetadata) -> LinterMetadataOutput:
    """Return Ruff-style JSON metadata for one linter."""
    output = LinterMetadataOutput(prefix=linter.prefix, name=linter.name)
    if linter.url is not None:
        output["url"] = linter.url
    return output


def format_linters_text(linters: tuple[rule_base.RuleLinterMetadata, ...]) -> str:
    """Return Ruff-style text metadata for linters."""
    if not linters:
        return ""
    prefix_width = max(len(linter.prefix) for linter in linters)
    return "".join(f"{linter.prefix:>{prefix_width}} {linter.name}\n" for linter in linters)
