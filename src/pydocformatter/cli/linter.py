from __future__ import annotations

import argparse
import json
from typing import TypedDict

import pydocformatter.cli.global_args as global_args
import pydocformatter.rules.collection as rule_collection
import pydocformatter.utils.argparser as argparser
from pydocformatter.rules.definition import RuleCategoryBase


class CategoryMetadataOutput(TypedDict, total=False):
    """JSON metadata for one rule category in Ruff linter format."""

    prefix: str
    name: str
    url: str


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    """Add the linter subcommand parser."""
    parser = argparser.create_subparser(
        subparsers,
        name="linter",
        description="List all supported rule-prefix linters (rule categories).",
        help="List all supported rule-prefix linters (rule categories)",
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
    categories = rule_collection.RULE_COLLECTION.categories
    if args.output_format == "json":
        print(json.dumps([category_json(category) for category in categories], indent=2))
    else:
        print(format_categories_text(categories), end="")
    return 0


def category_json(category: type[RuleCategoryBase]) -> CategoryMetadataOutput:
    """Return Ruff-style linter JSON metadata for one rule category."""
    output = CategoryMetadataOutput(prefix=category.meta.prefix, name=category.meta.name)
    if category.meta.url is not None:
        output["url"] = category.meta.url
    return output


def format_categories_text(categories: tuple[type[RuleCategoryBase], ...]) -> str:
    """Return Ruff-style linter text metadata for rule categories."""
    if not categories:
        return ""
    prefix_width = max(len(category.meta.prefix) for category in categories)
    return "".join(f"{category.meta.prefix:>{prefix_width}} {category.meta.name}\n" for category in categories)
