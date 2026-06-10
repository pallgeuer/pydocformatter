from __future__ import annotations

import argparse
import json
import sys
from typing import TypedDict

import pydocformatter.cli.global_args as global_args
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
import pydocformatter.utils.argparser as argparser
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.models import FixAvailability


class RuleSourceLocationMetadata(TypedDict):
    """JSON metadata for a rule source location."""

    file: str
    line: int


class RuleStatusMetadata(TypedDict):
    """JSON metadata for a rule status entry."""

    since: str


class RuleMetadataOutput(TypedDict):
    """JSON metadata for one rule explanation."""

    name: str
    code: str
    linter: str
    summary: str
    message_formats: list[str]
    fix: str
    fix_availability: FixAvailability
    explanation: str
    preview: bool
    status: dict[str, RuleStatusMetadata]
    source_location: RuleSourceLocationMetadata | None


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    """Add the rule subcommand parser."""
    parser = argparser.create_subparser(
        subparsers,
        name="rule",
        description="Explain a rule or all rules.",
        help="Explain a rule or all rules",
    )
    parser.add_argument(
        "rule",
        nargs="?",
        metavar="RULE",
        help="Rule to explain.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Explain all rules.",
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
    """Run the rule subcommand."""
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
        if args.all:
            output = [rule_json(rule_class) for rule_class in rules]
        else:
            output = rule_json(rules[0])
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
    """Return Ruff-style JSON metadata for one rule."""
    rule = rule_class.meta
    source_location = rule_documentation.rule_source_location(rule_class)
    source_location_json: RuleSourceLocationMetadata | None
    if source_location is None:
        source_location_json = None
    else:
        source_location_json = {"file": source_location.file, "line": source_location.line}
    return RuleMetadataOutput(
        name=rule.name,
        code=rule.code.tag,
        linter="pydocformatter",
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
    """Return Ruff-style Markdown text for one rule."""
    return f"{rule_documentation.load_rule_explanation(rule_class).rstrip()}\n"
