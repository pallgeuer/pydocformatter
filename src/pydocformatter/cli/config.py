"""`pydocfmt config` command."""

# Future imports
from __future__ import annotations

# Standard library imports
import sys
import enum
import json
from typing import TYPE_CHECKING, Any, TypedDict

# First-party imports
import pydocformatter.settings as settings_core
from pydocformatter.cli import global_args, settings_check
from pydocformatter.settings import MultiStringMap, PerFileSettingsMap, StringList, StringMap
from pydocformatter.utils import argparser


if TYPE_CHECKING:
    # Standard library imports
    import argparse

    # First-party imports
    from pydocformatter.settings import SettingDefinition


_DEFAULT_OUTPUT_FORMAT = "text"


class ConfigOptionMetadata(TypedDict):
    """JSON metadata for one configuration option.

    Attributes:
        doc (str): User-facing configuration documentation.
        default (str): TOML-formatted default value.
        value_type (str): User-facing value type description.
        example (str): TOML usage example.
    """

    doc: str
    default: str
    value_type: str
    example: str


def add_parser(subparsers: argparser.SubparserCollection) -> argparse.ArgumentParser:
    """Add the config subcommand parser.

    Args:
        subparsers (argparser.SubparserCollection): Top-level subparser collection.

    Returns:
        argparse.ArgumentParser: Configured `config` subcommand parser.
    """
    parser = argparser.create_subparser(subparsers, name="config", description="List or describe the available configuration options.", help="List or describe the available configuration options")
    parser.add_argument("option", nargs="?", metavar="OPTION", help="Config key to show.")
    parser.add_argument("--output-format", choices=("text", "json"), default=_DEFAULT_OUTPUT_FORMAT, help="Output format (default: %(default)s).")
    global_args.add_global_arguments(parser, dest_prefix="command")
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace) -> int:
    """Run the config subcommand.

    Args:
        args (argparse.Namespace): Parsed command arguments.

    Returns:
        int: Process exit status code.
    """
    toml_definitions = tuple(definition for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml)
    definitions_by_key = {definition.key: definition for definition in toml_definitions}
    if args.option is not None and args.option not in definitions_by_key:
        print(f"pydocfmt config: Argument error: Invalid value {args.option!r} for 'OPTION'", file=sys.stderr)
        return 2

    settings = settings_check.CheckSettings()
    if args.output_format == "json":
        output: ConfigOptionMetadata | dict[str, ConfigOptionMetadata]
        if args.option is None:
            output = {definition.key: metadata_for_definition(definition, settings) for definition in toml_definitions}
        else:
            output = metadata_for_definition(definitions_by_key[args.option], settings)
        print(json.dumps(output, indent=2))
    elif args.option is None:
        for definition in toml_definitions:
            print(definition.key)
    else:
        print(format_definition(definitions_by_key[args.option], settings), end="")

    return 0


def metadata_for_definition(definition: SettingDefinition[Any], settings: settings_check.CheckSettings) -> ConfigOptionMetadata:
    """Return Ruff-style JSON metadata for one setting.

    Args:
        definition (SettingDefinition[Any]): Setting definition to describe.
        settings (settings_check.CheckSettings): Settings object that provides the current default value.

    Returns:
        ConfigOptionMetadata: JSON-serializable metadata for the setting.
    """
    default = settings_core.format_value(getattr(settings, definition.field), definition.value_type)
    return ConfigOptionMetadata(doc=definition.documentation, default=default, value_type=value_type_name(definition.value_type), example=definition.example or f"{definition.key} = {default}")


def format_definition(definition: SettingDefinition[Any], settings: settings_check.CheckSettings) -> str:
    """Return Ruff-style text metadata for one setting.

    Args:
        definition (SettingDefinition[Any]): Setting definition to describe.
        settings (settings_check.CheckSettings): Settings object that provides the current default value.

    Returns:
        str: Text block describing the configuration option.
    """
    metadata = metadata_for_definition(definition, settings)
    lines = [metadata["doc"].rstrip(), "", f"Default value: {metadata['default']}", f"Type: {metadata['value_type']}", "Example usage:", "```toml", metadata["example"], "```", ""]
    return "\n".join(lines)


def value_type_name(value_type: object) -> str:
    """Return a user-facing setting type name.

    Args:
        value_type (object): Python type or generic alias stored in a setting definition.

    Returns:
        str: User-facing type name for help and JSON output.
    """
    if value_type is bool:
        return "bool"
    if value_type is int:
        return "int"
    if value_type is float:
        return "float"
    if value_type is str:
        return "str"
    if value_type == StringList:
        return "list[str]"
    if value_type == StringMap:
        return "dict[str, str]"
    if value_type == MultiStringMap:
        return "dict[str, list[str]]"
    if value_type == PerFileSettingsMap:
        return "dict[str, dict[str, value]]"
    if isinstance(value_type, type) and issubclass(value_type, enum.StrEnum):
        return " | ".join(json.dumps(member.value) for member in value_type)
    return str(value_type)
