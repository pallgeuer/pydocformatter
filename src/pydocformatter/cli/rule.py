"""`pydocfmt rule` command."""

# Future imports
from __future__ import annotations

# Standard library imports
import sys
import json
from typing import TYPE_CHECKING, TypedDict

# First-party imports
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter import docs_urls
from pydocformatter.cli import global_args
from pydocformatter.rules.codes import RuleCode
from pydocformatter.utils import argparser


if TYPE_CHECKING:
    # Standard library imports
    import argparse

    # First-party imports
    from pydocformatter.rules.definition import RuleBase
    from pydocformatter.rules.models import FixAvailability


_DEFAULT_OUTPUT_FORMAT = "text"


class RuleSourceLocationMetadata(TypedDict):
    """JSON metadata for a rule source location.

    Attributes:
        file (str): Source file that defines the rule class.
        line (int): One-based line number where the rule class is defined.
    """

    file: str
    line: int


class RuleStatusMetadata(TypedDict):
    """JSON metadata for a rule status entry.

    Attributes:
        since (str): Version of pydocformatter in which the status became true.
    """

    since: str


class RuleMetadataOutput(TypedDict):
    """JSON metadata for one rule explanation.

    Attributes:
        name (str): Stable rule name used in documentation and JSON output.
        code (str): Full rule code such as `PDF101`.
        linter (str): Rule category prefix that owns the rule.
        url (str): Public documentation URL for the generated rule page.
        summary (str): Short rule summary from the adjacent Markdown documentation.
        message_formats (list[str]): Diagnostic message templates this rule can emit.
        fix (str): Human-readable automatic-fix availability.
        fix_availability (FixAvailability): Machine-readable automatic-fix availability.
        explanation (str): Long-form rule explanation from the adjacent Markdown documentation.
        preview (bool): Whether the rule is preview-only in Ruff-compatible output.
        status (dict[str, RuleStatusMetadata]): Stable status metadata keyed by status name.
        source_location (RuleSourceLocationMetadata | None): Optional source location of the rule class.
    """

    name: str
    code: str
    linter: str
    url: str
    summary: str
    message_formats: list[str]
    fix: str
    fix_availability: FixAvailability
    explanation: str
    preview: bool
    status: dict[str, RuleStatusMetadata]
    source_location: RuleSourceLocationMetadata | None


def add_parser(subparsers: argparser.SubparserCollection) -> argparse.ArgumentParser:
    """Add the rule subcommand parser.

    Args:
        subparsers (argparser.SubparserCollection): Parent parser collection that receives the subcommand.

    Returns:
        argparse.ArgumentParser: Configured `rule` subcommand parser.
    """
    parser = argparser.create_subparser(subparsers, name="rule", description="Explain a rule or all rules.", help="Explain a rule or all rules")
    parser.add_argument("rule", nargs="?", metavar="RULE", help="Rule to explain.")
    parser.add_argument("--all", action="store_true", help="Explain all rules.")
    parser.add_argument("--output-format", choices=("text", "json"), default=_DEFAULT_OUTPUT_FORMAT, help="Output format (default: %(default)s).")
    global_args.add_global_arguments(parser, dest_prefix="command")
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace) -> int:
    """Run the rule subcommand.

    Args:
        args (argparse.Namespace): Parsed rule command arguments.

    Returns:
        int: Process exit status code.
    """
    if args.rule is None and not args.all:
        print("pydocfmt rule: Argument error: Must specify RULE or --all", file=sys.stderr)
        return 2
    if args.rule is not None and args.all:
        print("pydocfmt rule: Argument error: The argument RULE cannot be used with --all", file=sys.stderr)
        return 2

    collection = rule_collection.RULE_COLLECTION
    if args.all:
        rules = collection.rules
    else:
        rule_class = _rule_class_for_tag(args.rule, collection=collection)
        if rule_class is None:
            print(f"pydocfmt rule: Argument error: Invalid value {args.rule!r} for 'RULE'", file=sys.stderr)
            return 2
        rules = (rule_class,)

    if args.output_format == "json":
        output: RuleMetadataOutput | list[RuleMetadataOutput]
        output = [rule_json(rule_class) for rule_class in rules] if args.all else rule_json(rules[0])
        print(json.dumps(output, indent=2))
    else:
        print("\n\n".join(format_rule_text(rule_class).rstrip() for rule_class in rules))

    return 0


def _rule_class_for_tag(rule_tag: str, *, collection: rule_collection.RuleCollection) -> type[RuleBase] | None:
    """Return the rule class for a user-supplied rule code."""
    if not RuleCode.is_valid_tag(rule_tag):
        return None
    return collection.rule_class.get(RuleCode(rule_tag))


def rule_json(rule_class: type[RuleBase]) -> RuleMetadataOutput:
    """Return Ruff-style JSON metadata for one rule.

    Args:
        rule_class (type[RuleBase]): Rule class whose metadata and Markdown explanation should be serialized.

    Returns:
        RuleMetadataOutput: JSON-ready rule explanation metadata using Ruff-compatible field names where possible.
    """
    rule = rule_class.meta
    source_location = rule_documentation.rule_source_location(rule_class)
    source_location_json: RuleSourceLocationMetadata | None
    source_location_json = None if source_location is None else RuleSourceLocationMetadata(file=source_location.file, line=source_location.line)
    return RuleMetadataOutput(
        name=rule.name,
        code=rule.code.tag,
        linter="pydocformatter",
        url=docs_urls.rule_url(rule.name),
        summary=rule.message,
        message_formats=[rule.message],
        fix=rule_documentation.rule_fix_text(rule),
        fix_availability=rule.fix_availability,
        explanation=rule_documentation.rule_explanation_body(rule_class),
        preview=False,
        status={"Stable": {"since": f"v{rule.stable_since}"}},
        source_location=source_location_json,
    )


def format_rule_text(rule_class: type[RuleBase]) -> str:
    """Return Ruff-style Markdown text for one rule.

    Args:
        rule_class (type[RuleBase]): Rule class whose adjacent Markdown explanation should be loaded.

    Returns:
        str: Rule explanation body with exactly one trailing newline.
    """
    return f"{rule_documentation.load_rule_explanation(rule_class).rstrip()}\n"
