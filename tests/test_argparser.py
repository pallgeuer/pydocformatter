"""Tests for project argparse helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import argparse

# First-party imports
from pydocformatter.utils import argparser


def test_parser_uses_project_argument_sections() -> None:
    """Render positional and optional arguments under project sections."""
    parser = argparser.create_parser(prog="example", description="Example command.")
    parser.add_argument("target", metavar="TARGET", help="Target path.")
    parser.add_argument("--verbose", action="store_true", help="Show details.")

    help_text = parser.format_help()

    assert "\nArguments:\n  TARGET" in help_text
    assert "\nOptions:\n  -h, --help" in help_text
    assert "\n  --verbose" in help_text
    assert "\npositional arguments:\n" not in help_text
    assert "\noptions:\n" not in help_text


def test_subparser_uses_project_argument_sections() -> None:
    """Use project argument sections for parsers added through subcommands."""
    parser = argparser.create_parser(prog="example")
    subparsers = parser.add_subparsers(dest="command")
    command_parser = argparser.create_subparser(subparsers, name="run", description="Run the command.")
    command_parser.add_argument("target", metavar="TARGET", help="Target path.")
    command_parser.add_argument("--verbose", action="store_true", help="Show details.")

    help_text = command_parser.format_help()

    assert "\nArguments:\n  TARGET" in help_text
    assert "\nOptions:\n  -h, --help" in help_text
    assert "\n  --verbose" in help_text


def test_parser_groups_inherited_arguments_without_duplicate_headings() -> None:
    """Render parent-parser actions in the standard project sections."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--base-option", action="store_true", help="Inherited option.")
    parser = argparser.create_parser(prog="example", parents=[parent])
    parser.add_argument("target", metavar="TARGET", help="Target path.")

    help_text = parser.format_help()

    assert help_text.count("\nArguments:\n") == 1
    assert help_text.count("\nOptions:\n") == 1
    assert "\nArguments:\n  TARGET" in help_text
    assert "\nOptions:\n  --base-option" in help_text
    assert "\npositional arguments:\n" not in help_text
    assert "\noptions:\n" not in help_text


def test_parser_groups_untitled_subparsers_as_arguments() -> None:
    """Render an untitled subparser collection in the project argument section."""
    parser = argparser.create_parser(prog="example")
    parser.add_subparsers(dest="command", metavar="COMMAND")

    help_text = parser.format_help()

    assert "\nArguments:\n  COMMAND" in help_text
    assert help_text.count("\nArguments:\n") == 1
    assert "\npositional arguments:\n" not in help_text


def test_parser_groups_root_mutually_exclusive_options() -> None:
    """Render root mutually exclusive actions in one project option section."""
    parser = argparser.create_parser(prog="example")
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument("--first", action="store_true", help="Choose the first mode.")
    choices.add_argument("--second", action="store_true", help="Choose the second mode.")

    help_text = parser.format_help()

    assert help_text.count("\nOptions:\n") == 1
    assert "  --first" in help_text
    assert "  --second" in help_text
    assert "\noptions:\n" not in help_text


def test_parser_preserves_explicit_argument_group_heading() -> None:
    """Leave explicitly titled argument groups unchanged."""
    parser = argparser.create_parser(prog="example")
    miscellaneous = parser.add_argument_group("Miscellaneous")
    miscellaneous.add_argument("--details", action="store_true", help="Show details.")

    help_text = parser.format_help()

    assert "\nMiscellaneous:\n  --details" in help_text


def test_subparser_configures_standard_library_parent_collection() -> None:
    """Apply project formatting to a subparser of a standard-library parser."""
    parser = argparse.ArgumentParser(prog="example")
    subparsers = parser.add_subparsers(dest="command")
    command_parser = argparser.create_subparser(subparsers, name="run", description="Run the command.")
    command_parser.add_argument("target", metavar="TARGET", help="Target path.")
    command_parser.add_argument("--verbose", action="store_true", help="Show details.")

    help_text = command_parser.format_help()

    assert help_text.startswith("Usage: example run")
    assert "\nArguments:\n  TARGET" in help_text
    assert "\nOptions:\n  -h, --help" in help_text
    assert "Show this help message and exit" in help_text
    assert "\nusage:" not in help_text
    assert "\noptions:\n" not in help_text


def test_parser_uses_custom_option_prefix_for_explicit_help() -> None:
    """Derive project help flags from the configured option-prefix characters."""
    parser = argparser.create_parser(prog="example", prefix_chars="+")
    parser.add_argument("++verbose", action="store_true", help="Show details.")

    help_text = parser.format_help()

    assert "\nOptions:\n  +h, ++help" in help_text
    assert "\n  ++verbose" in help_text
