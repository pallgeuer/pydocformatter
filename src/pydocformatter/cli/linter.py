"""`pydocfmt linter` command."""

# Future imports
from __future__ import annotations

# Standard library imports
import json
from typing import TYPE_CHECKING, TypedDict

# First-party imports
import pydocformatter.rules.collection as rule_collection
from pydocformatter.cli import global_args
from pydocformatter.utils import argparser


if TYPE_CHECKING:
    # Standard library imports
    import argparse

    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryBase


_DEFAULT_OUTPUT_FORMAT = "text"


class CategoryMetadataOutput(TypedDict, total=False):
    """JSON metadata for one rule category in Ruff linter format.

    Attributes:
        prefix (str): Rule-code prefix for the category.
        name (str): User-facing category name.
        url (str): Documentation or project URL associated with the category.
    """

    prefix: str
    name: str
    url: str


def add_parser(subparsers: argparser.SubparserCollection) -> argparse.ArgumentParser:
    """Add the linter subcommand parser.

    Args:
        subparsers (argparser.SubparserCollection): Parent parser collection that receives the subcommand.

    Returns:
        argparse.ArgumentParser: Configured `linter` subcommand parser.
    """
    parser = argparser.create_subparser(
        subparsers, name="linter", description="List all supported rule-prefix linters (rule categories).", help="List all supported rule-prefix linters (rule categories)"
    )
    parser.add_argument("--output-format", choices=("text", "json"), default=_DEFAULT_OUTPUT_FORMAT, help="Output format (default: %(default)s).")
    global_args.add_global_arguments(parser, dest_prefix="command")
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace) -> int:
    """Run the linter subcommand.

    Args:
        args (argparse.Namespace): Parsed linter command arguments.

    Returns:
        int: Process exit status code.
    """
    categories = rule_collection.RULE_COLLECTION.categories
    if args.output_format == "json":
        print(json.dumps([category_json(category) for category in categories], indent=2))
    else:
        print(format_categories_text(categories), end="")
    return 0


def category_json(category: type[RuleCategoryBase]) -> CategoryMetadataOutput:
    """Return Ruff-style linter JSON metadata for one rule category.

    Args:
        category (type[RuleCategoryBase]): Rule category class whose public metadata should be serialized.

    Returns:
        CategoryMetadataOutput: JSON-ready metadata using Ruff's linter-listing field names.
    """
    output = CategoryMetadataOutput(prefix=category.meta.prefix, name=category.meta.name)
    if category.meta.url is not None:
        output["url"] = category.meta.url
    return output


def format_categories_text(categories: tuple[type[RuleCategoryBase], ...]) -> str:
    """Return Ruff-style linter text metadata for rule categories.

    Args:
        categories (tuple[type[RuleCategoryBase], ...]): Rule category classes to render in listing order.

    Returns:
        str: Aligned text table of category prefixes and names.
    """
    if not categories:
        return ""
    prefix_width = max(len(category.meta.prefix) for category in categories)
    return "".join(f"{category.meta.prefix:>{prefix_width}} {category.meta.name}\n" for category in categories)
