# Future imports
from __future__ import annotations

# Standard library imports
import re
import copy
import enum
import json
import math
import typing
import tomllib
import argparse
import tempfile
import subprocess
import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party imports
import pytest


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture

# First-party imports
import pydocformatter.settings as pydocformatter_settings_core
import pydocformatter.cli.global_args as pydocformatter_global_args
import pydocformatter.cli.settings_check as pydocformatter_settings
from pydocformatter.cli.settings_check import DEFAULT_EXCLUDE, DEFAULT_INCLUDE, CheckSettings, CheckSettingsOverrides, CommentTaskMarkerMode, IndentStyle, LineEnding, OutputFormat, SettingsGroup
from pydocformatter.settings import MultiStringMap, SettingCLIDefinition, SettingCLIOptions, SettingCLIValueKind, SettingDefinition, SettingsError, SettingsSchema, StringList
from tests import git_helpers


FRACTIONAL_PARALLELISM = 0.5


pytestmark = pytest.mark.isolated_cwd


def _repo_root() -> Path:
    """Return the repository root used for subprocess-based tool checks."""
    return Path(__file__).resolve().parents[1]


def _markdown_section_lines(path: Path, heading: str) -> list[str]:
    """Return non-empty lines from a level-two Markdown section."""
    lines = path.read_text(encoding="utf-8").splitlines()
    heading_index = lines.index(f"## {heading}")
    section_lines: list[str] = []
    for line in lines[heading_index + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            section_lines.append(line)
    return section_lines


def test_check_settings_schema_uses_generic_settings_definitions() -> None:
    assert pydocformatter_settings.SETTINGS_SCHEMA.settings_type is CheckSettings
    assert pydocformatter_settings.SETTINGS_SCHEMA.overrides_type is CheckSettingsOverrides
    assert all(isinstance(definition, SettingDefinition) for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions)
    assert "tags" not in tuple(field.name for field in dataclasses.fields(SettingDefinition))
    assert "render" not in tuple(field.name for field in dataclasses.fields(SettingDefinition))
    assert tuple(field.name for field in dataclasses.fields(SettingDefinition)) == (
        "field",
        "value_type",
        "group",
        "help",
        "key",
        "available_in_cli",
        "available_in_toml",
        "validator",
        "cli",
        "documentation",
        "example",
    )
    assert tuple(field.name for field in dataclasses.fields(SettingsSchema)) == ("settings_type", "overrides_type", "group_type", "definitions", "table_path", "table_name", "post_validate")
    assert not next(field for field in dataclasses.fields(SettingsSchema) if field.name == "table_name").init
    assert pydocformatter_settings.SETTINGS_SCHEMA.table_name == "tool.pydocfmt"
    assert pydocformatter_settings.SETTINGS_SCHEMA.group_type is SettingsGroup
    assert SettingsError is pydocformatter_settings_core.SettingsError
    assert hasattr(pydocformatter_settings_core, "SettingCLIDefinition")
    assert hasattr(pydocformatter_settings_core, "SettingCLIOptions")
    assert not hasattr(pydocformatter_settings_core, "SettingCliDefinition")
    assert hasattr(pydocformatter_settings_core, "StringList")
    assert hasattr(pydocformatter_settings_core, "MultiStringMap")
    assert not hasattr(pydocformatter_settings, "RuleSelectorMap")


def test_cli_options_and_resolved_definition_fields_match() -> None:
    options_hints = typing.get_type_hints(SettingCLIOptions)
    definition_hints = typing.get_type_hints(SettingCLIDefinition)

    assert not SettingCLIOptions.__total__
    assert options_hints == definition_hints
    assert tuple(options_hints) == tuple(field.name for field in dataclasses.fields(SettingCLIDefinition))


def test_cli_definition_stores_resolved_show_default() -> None:
    assert SettingCLIDefinition().show_default
    assert SettingCLIDefinition(value_kind=SettingCLIValueKind.COMMA_LIST).show_default
    assert not SettingCLIDefinition(show_default=False).show_default
    assert SettingCLIDefinition(value_kind=SettingCLIValueKind.COMMA_LIST, show_default=True).show_default


def test_setting_definition_resolves_default_key_and_cli_flags() -> None:
    definition = SettingDefinition(field="line_length", value_type=int, group=SettingsGroup.FORMATTING, help="Maximum line length.", validator=pydocformatter_settings_core.validate_int())
    empty_documentation_definition = SettingDefinition(field="line_length", value_type=int, group=SettingsGroup.FORMATTING, help="Maximum line length.", documentation="")
    none_documentation_definition = SettingDefinition(field="line_length", value_type=int, group=SettingsGroup.FORMATTING, help="Maximum line length.", documentation=None)
    example_definition = SettingDefinition(field="line_length", value_type=int, group=SettingsGroup.FORMATTING, help="Maximum line length.", example="line-length = 120")

    assert definition.key == "line-length"
    assert definition.documentation == definition.help
    assert definition.example == ""
    assert empty_documentation_definition.documentation == empty_documentation_definition.help
    assert none_documentation_definition.documentation == none_documentation_definition.help
    assert example_definition.example == "line-length = 120"
    assert definition.cli is not None
    cli = definition.cli
    assert cli is not None
    assert cli.flags == ("--line-length",)


def test_setting_definition_respects_explicit_key_and_cli_flags() -> None:
    definition = SettingDefinition(
        field="config_options",
        value_type=StringList,
        group=SettingsGroup.FORMATTING,
        help="Configuration options.",
        key="config",
        validator=pydocformatter_settings_core.validate_string_list,
        cli={"flags": ("-c", "--config")},
    )

    assert definition.key == "config"
    assert definition.cli is not None
    cli = definition.cli
    assert cli is not None
    assert cli.flags == ("-c", "--config")


def test_setting_definition_uses_explicit_key_for_default_cli_flags() -> None:
    definition = SettingDefinition(
        field="config_options", value_type=StringList, group=SettingsGroup.FORMATTING, help="Configuration options.", key="config", validator=pydocformatter_settings_core.validate_string_list
    )

    assert definition.key == "config"
    assert definition.cli is not None
    cli = definition.cli
    assert cli is not None
    assert cli.flags == ("--config",)


def test_setting_definition_respects_explicit_no_cli() -> None:
    definition = SettingDefinition(field="force_exclude", value_type=bool, group=SettingsGroup.FORMATTING, help="Force excludes.", available_in_cli=False)

    assert not definition.available_in_cli
    assert definition.cli is None


def test_setting_definition_derives_defaults_from_type() -> None:
    enum_definition = SettingDefinition(field="line_ending", value_type=LineEnding, group=SettingsGroup.FORMATTING, help="Line ending.")
    bool_definition = SettingDefinition(field="force_exclude", value_type=bool, group=SettingsGroup.FORMATTING, help="Force excludes.")
    int_definition = SettingDefinition(field="line_length", value_type=int, group=SettingsGroup.FORMATTING, help="Line length.")
    float_definition = SettingDefinition(field="parallelism", value_type=float, group=SettingsGroup.FORMATTING, help="Parallelism.")
    string_list_definition = SettingDefinition(field="include", value_type=StringList, group=SettingsGroup.FILE_SELECTION, help="Include.")
    string_map_definition = SettingDefinition(field="per_file_ignores", value_type=MultiStringMap, group=SettingsGroup.RULE_SELECTION, help="Per-file ignores.")

    assert enum_definition.cli is not None
    assert bool_definition.cli is not None
    assert int_definition.cli is not None
    assert string_list_definition.cli is not None
    assert string_map_definition.cli is not None
    assert enum_definition.cli.choices == tuple(member.value for member in LineEnding)
    assert bool_definition.cli.action is argparse.BooleanOptionalAction
    assert int_definition.cli.type is int
    assert float_definition.cli is not None
    assert float_definition.cli is not None
    assert float_definition.cli.type is float
    assert string_list_definition.cli.action == "append"
    assert string_list_definition.cli.value_kind == SettingCLIValueKind.COMMA_LIST
    assert not string_list_definition.cli.show_default
    assert string_map_definition.cli.action == "append"
    assert string_map_definition.cli.value_kind == SettingCLIValueKind.TOML_MAP
    assert not string_map_definition.cli.show_default
    assert enum_definition.validator("lf", "line-ending") == LineEnding.LF
    force_exclude = True
    assert bool_definition.validator(force_exclude, "force-exclude")
    assert int_definition.validator(1, "line-length") == 1
    assert float_definition.validator(FRACTIONAL_PARALLELISM, "parallelism") == FRACTIONAL_PARALLELISM
    assert string_list_definition.validator(["*.py"], "include") == ("*.py",)
    assert string_map_definition.validator({"tests/*.py": ["PCF000"]}, "per-file-ignores") == (("tests/*.py", ("PCF000",)),)


def test_setting_definition_respects_explicit_cli_options_during_defaulting() -> None:
    default_int_definition = SettingDefinition(field="line_length", value_type=int, group=SettingsGroup.FORMATTING, help="Line length.")
    raw_list_definition = SettingDefinition(field="include", value_type=StringList, group=SettingsGroup.FILE_SELECTION, help="Include.", cli={"value_kind": SettingCLIValueKind.RAW})
    show_default_list_definition = SettingDefinition(field="include", value_type=StringList, group=SettingsGroup.FILE_SELECTION, help="Include.", cli={"show_default": True})

    assert default_int_definition.cli is not None
    assert raw_list_definition.cli is not None
    assert show_default_list_definition.cli is not None
    assert default_int_definition.cli.value_kind == SettingCLIValueKind.RAW
    assert default_int_definition.cli.show_default
    assert raw_list_definition.cli.value_kind == SettingCLIValueKind.RAW
    assert raw_list_definition.cli.show_default
    assert show_default_list_definition.cli.value_kind == SettingCLIValueKind.COMMA_LIST
    assert show_default_list_definition.cli.show_default


def test_global_args_defaults_without_parser_values() -> None:
    args = argparse.Namespace()

    assert pydocformatter_global_args.global_values_from_arguments(args, dest_prefixes=("global", "command")) == pydocformatter_global_args.GlobalArgs()


def test_global_args_parse_all_parser_levels() -> None:
    parser = argparse.ArgumentParser()
    pydocformatter_global_args.add_global_arguments(parser, dest_prefix="global")
    subparsers = parser.add_subparsers(dest="command")
    command = subparsers.add_parser("check")
    pydocformatter_global_args.add_global_arguments(command, dest_prefix="command")

    args = parser.parse_args(["--config", "line-length = 90", "check", "--config", "line-length = 91", "--isolated"])

    global_values = pydocformatter_global_args.global_values_from_arguments(args, dest_prefixes=("global", "command"))

    assert global_values.config_options == ("line-length = 90", "line-length = 91")
    assert global_values.isolated


def test_setting_definitions_match_formatter_settings_fields() -> None:
    setting_fields = tuple(field.name for field in dataclasses.fields(CheckSettings))
    setting_annotations = typing.get_type_hints(CheckSettings)
    override_annotations = typing.get_type_hints(CheckSettingsOverrides)
    definition_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions)

    assert definition_fields == setting_fields
    assert tuple(definition.value_type for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions) == tuple(setting_annotations[field] for field in setting_fields)
    assert set(override_annotations) == set(setting_fields)
    assert override_annotations == {field: setting_annotations[field] for field in setting_fields}
    assert tuple(getattr(CheckSettings(), definition.field) for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions) == tuple(getattr(CheckSettings(), field) for field in setting_fields)


def test_check_setting_definitions_exhaustively_match_schema_and_settings_fields() -> None:
    definition_fields = tuple(definition.field for definition in pydocformatter_settings.CHECK_SETTING_DEFINITIONS)
    setting_fields = tuple(field.name for field in dataclasses.fields(CheckSettings))

    assert len(definition_fields) == len(set(definition_fields))
    assert len(setting_fields) == len(set(setting_fields))
    assert pydocformatter_settings.SETTINGS_SCHEMA.definitions == pydocformatter_settings.CHECK_SETTING_DEFINITIONS
    assert set(definition_fields) == set(setting_fields)


def test_cache_identity_roles_have_exact_current_field_membership() -> None:
    expected = {
        pydocformatter_settings.CacheIdentityRole.DIRECT_ANALYSIS_VALUE: (
            "line_length",
            "url_aware_wrapping",
            "line_ending",
            "indent_style",
            "indent_width",
            "docstring_convention",
            "docstring_blank_line_style",
            "docstring_blank_line_after_last_section",
            "docstring_missing_documentation",
            "docstring_missing_documentation_public_only",
            "docstring_require_init_attribute_documentation",
            "docstring_include_assertion_errors",
            "docstring_class_attribute_no_type_base_classes",
            "docstring_forbidden_function_decorators",
            "docstring_optional_function_decorators",
            "docstring_placeholder_markers",
            "docstring_property_decorators",
            "docstring_parse_list_items",
            "docstring_parse_headings",
            "docstring_parse_doctests",
            "docstring_parse_code_fences",
            "docstring_parse_block_quotes",
            "docstring_parse_tables",
            "docstring_parse_directives",
            "docstring_parse_literal_blocks",
            "comment_join_standalone_lines",
            "comment_format_list_items",
            "comment_task_marker_mode",
            "comment_task_markers",
            "comment_preserve_headings",
            "comment_preserve_doctests",
            "comment_preserve_code_fences",
            "comment_format_block_quotes",
            "comment_preserve_tables",
            "comment_preserve_directives",
            "comment_trailing_extraction_syntax_aware",
            "comment_trailing_extraction_content_aware",
            "comment_detect_code",
            "comment_detect_statements",
            "comment_detect_expressions",
        ),
        pydocformatter_settings.CacheIdentityRole.FINAL_RULE_CODES: ("select", "ignore", "extend_select", "require_explicit", "per_file_ignores", "extend_per_file_ignores"),
        pydocformatter_settings.CacheIdentityRole.CLEAN_PROOF_IRRELEVANT: ("output_format", "cache", "cache_dir", "parallelism", "fixable", "unfixable", "extend_fixable"),
        pydocformatter_settings.CacheIdentityRole.DISCOVERY_ONLY: ("include", "extend_include", "exclude", "extend_exclude", "respect_gitignore", "force_exclude"),
        pydocformatter_settings.CacheIdentityRole.APPLIED_CONFIGURATION: ("per_file_settings",),
    }

    for role, expected_fields in expected.items():
        assert tuple(definition.field for definition in pydocformatter_settings.CHECK_SETTING_DEFINITIONS if definition.cache_identity_role is role) == expected_fields


def test_settings_group_does_not_determine_cache_identity_role() -> None:
    definitions = {definition.field: definition for definition in pydocformatter_settings.CHECK_SETTING_DEFINITIONS}

    assert definitions["select"].group is definitions["fixable"].group is SettingsGroup.RULE_SELECTION
    assert definitions["select"].cache_identity_role is pydocformatter_settings.CacheIdentityRole.FINAL_RULE_CODES
    assert definitions["fixable"].cache_identity_role is pydocformatter_settings.CacheIdentityRole.CLEAN_PROOF_IRRELEVANT


def test_last_section_blank_line_setting_documents_every_affected_rule() -> None:
    definition = next(definition for definition in pydocformatter_settings.CHECK_SETTING_DEFINITIONS if definition.field == "docstring_blank_line_after_last_section")

    assert all(rule_code in definition.documentation for rule_code in ("PDF108", "PDF200", "PDF201"))


def test_analysis_settings_identity_and_precomputed_definitions_follow_schema_order() -> None:
    profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))
    expected_fields = tuple(
        definition.field for definition in pydocformatter_settings.CHECK_SETTING_DEFINITIONS if definition.cache_identity_role is pydocformatter_settings.CacheIdentityRole.DIRECT_ANALYSIS_VALUE
    )
    identity = pydocformatter_settings.analysis_settings_identity(profile)
    identity_fields = tuple(field for field, _ in identity)

    assert identity_fields == expected_fields
    assert len(identity_fields) == len(set(identity_fields))
    assert tuple(definition.field for definition in pydocformatter_settings.DIRECT_ANALYSIS_DEFINITIONS) == expected_fields


def test_setting_definitions_are_iterable_by_group() -> None:
    run_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.RUN)
    formatting_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.FORMATTING)
    docstring_formatting_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.DOCSTRING_FORMATTING)
    comment_formatting_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.COMMENT_FORMATTING)
    rule_selection_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.RULE_SELECTION)
    file_selection_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.FILE_SELECTION)
    configuration_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.CONFIGURATION)

    assert run_fields == ("output_format", "cache", "cache_dir", "parallelism")
    assert formatting_fields == ("line_length", "url_aware_wrapping", "line_ending", "indent_style", "indent_width")
    assert docstring_formatting_fields == (
        "docstring_convention",
        "docstring_blank_line_style",
        "docstring_blank_line_after_last_section",
        "docstring_missing_documentation",
        "docstring_missing_documentation_public_only",
        "docstring_require_init_attribute_documentation",
        "docstring_include_assertion_errors",
        "docstring_class_attribute_no_type_base_classes",
        "docstring_forbidden_function_decorators",
        "docstring_optional_function_decorators",
        "docstring_placeholder_markers",
        "docstring_property_decorators",
        "docstring_parse_list_items",
        "docstring_parse_headings",
        "docstring_parse_doctests",
        "docstring_parse_code_fences",
        "docstring_parse_block_quotes",
        "docstring_parse_tables",
        "docstring_parse_directives",
        "docstring_parse_literal_blocks",
    )
    assert comment_formatting_fields == (
        "comment_join_standalone_lines",
        "comment_format_list_items",
        "comment_task_marker_mode",
        "comment_task_markers",
        "comment_preserve_headings",
        "comment_preserve_doctests",
        "comment_preserve_code_fences",
        "comment_format_block_quotes",
        "comment_preserve_tables",
        "comment_preserve_directives",
        "comment_trailing_extraction_syntax_aware",
        "comment_trailing_extraction_content_aware",
        "comment_detect_code",
        "comment_detect_statements",
        "comment_detect_expressions",
    )
    assert rule_selection_fields == ("select", "ignore", "extend_select", "require_explicit", "per_file_ignores", "extend_per_file_ignores", "fixable", "unfixable", "extend_fixable")
    assert file_selection_fields == ("include", "extend_include", "exclude", "extend_exclude", "respect_gitignore", "force_exclude")
    assert configuration_fields == ("per_file_settings",)


def test_settings_schema_add_arguments_adds_groups_in_order() -> None:
    parser = argparse.ArgumentParser()

    pydocformatter_settings.SETTINGS_SCHEMA.add_arguments(parser, CheckSettings())

    group_titles = tuple(group.title for group in parser._action_groups)
    assert group_titles.index(SettingsGroup.RUN.value) < group_titles.index(SettingsGroup.FORMATTING.value)
    assert group_titles.index(SettingsGroup.FORMATTING.value) < group_titles.index(SettingsGroup.COMMENT_FORMATTING.value)
    assert group_titles.index(SettingsGroup.FORMATTING.value) < group_titles.index(SettingsGroup.DOCSTRING_FORMATTING.value)
    assert group_titles.index(SettingsGroup.DOCSTRING_FORMATTING.value) < group_titles.index(SettingsGroup.COMMENT_FORMATTING.value)
    assert group_titles.index(SettingsGroup.COMMENT_FORMATTING.value) < group_titles.index(SettingsGroup.RULE_SELECTION.value)
    assert group_titles.index(SettingsGroup.RULE_SELECTION.value) < group_titles.index(SettingsGroup.FILE_SELECTION.value)
    assert group_titles.index(SettingsGroup.FILE_SELECTION.value) < group_titles.index(SettingsGroup.CONFIGURATION.value)
    option_strings = {option for action in parser._actions for option in action.option_strings}
    schema_option_strings = {
        flag for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.available_in_cli for flag in typing.cast("SettingCLIDefinition", definition.cli).flags
    }
    assert schema_option_strings <= option_strings


def test_settings_schema_rejects_invalid_definition_group() -> None:
    class OtherGroup(enum.StrEnum):
        OTHER = "Other"

    with pytest.raises(TypeError, match=r"must belong to SettingsGroup.*line_length"):
        SettingsSchema(
            settings_type=CheckSettings,
            overrides_type=CheckSettingsOverrides,
            group_type=SettingsGroup,
            definitions=(SettingDefinition(field="line_length", value_type=int, group=OtherGroup.OTHER, help="Maximum line length."),),
            table_path=("tool", "custom"),
        )


def test_settings_schema_rejects_empty_table_path() -> None:
    with pytest.raises(ValueError, match=r"table_path.*non-empty"):
        SettingsSchema(settings_type=CheckSettings, overrides_type=CheckSettingsOverrides, group_type=SettingsGroup, definitions=pydocformatter_settings.SETTINGS_SCHEMA.definitions, table_path=())


def test_settings_schema_rejects_empty_table_path_segment() -> None:
    with pytest.raises(ValueError, match=r"table_path.*non-empty"):
        SettingsSchema(
            settings_type=CheckSettings, overrides_type=CheckSettingsOverrides, group_type=SettingsGroup, definitions=pydocformatter_settings.SETTINGS_SCHEMA.definitions, table_path=("tool", "")
        )


def test_validation_context_uses_explicit_key() -> None:
    @dataclasses.dataclass(frozen=True)
    class CustomSettings:
        config_options: StringList = ()

    schema = SettingsSchema(
        settings_type=CustomSettings,
        overrides_type=dict[str, object],
        group_type=SettingsGroup,
        definitions=(SettingDefinition(field="config_options", value_type=StringList, group=SettingsGroup.FORMATTING, help="Configuration options.", key="config"),),
        table_path=("tool", "custom"),
    )

    with pytest.raises(SettingsError) as context:
        schema.load(field_overrides={"config_options": "not-a-list"}, global_values=pydocformatter_global_args.GlobalArgs(isolated=True))

    assert "<overrides>.config" in str(context.value)
    assert "config-options" not in str(context.value)


def test_load_toml_file_does_not_check_exists_before_open(mocker: MockerFixture) -> None:
    mocker.patch("pydocformatter.settings.os.path.exists", side_effect=AssertionError("exists should not be called"), autospec=True)
    assert pydocformatter_settings_core._load_toml_file("missing.toml", required=False) is None


def test_direct_load_profile_parses_one_auto_config_once_for_discovery_and_application(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    config_path = tmp_path / "pyproject.toml"
    target = tmp_path / "src"
    target.mkdir()
    config_path.write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    load_toml_file = mocker.spy(pydocformatter_settings_core, "_load_toml_file")

    profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(path=str(target))

    assert profile.settings.line_length == 91
    assert load_toml_file.call_count == 1
    assert load_toml_file.call_args.args == (str(config_path),)


def test_separate_direct_load_profile_calls_are_fresh_and_observe_edits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    load_toml_file = mocker.spy(pydocformatter_settings_core, "_load_toml_file")

    first = pydocformatter_settings.SETTINGS_SCHEMA.load_profile()
    config_path.write_text("[tool.pydocfmt]\nline-length = 92\n", encoding="utf-8")
    second = pydocformatter_settings.SETTINGS_SCHEMA.load_profile()

    assert first.settings.line_length == 91
    assert second.settings.line_length == 92
    assert load_toml_file.call_count == 2


def test_resolver_reuses_one_parsed_config_and_profile_across_many_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    config_path = tmp_path / "pyproject.toml"
    directories = tuple(tmp_path / name for name in ("a", "b", "c"))
    for directory in directories:
        directory.mkdir()
    config_path.write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    load_toml_file = mocker.spy(pydocformatter_settings_core, "_load_toml_file")
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    profiles = tuple(resolver.profile_for_path(str(directory)) for directory in directories)

    assert all(profile is profiles[0] for profile in profiles)
    assert load_toml_file.call_count == 1
    assert len(resolver._profiles_by_start_dir) == len(directories)
    assert len(resolver._context.profiles_by_source) == 1
    assert len(resolver._context.parsed_toml_by_path) == 1


def test_resolver_context_does_not_change_equality_or_repr_contract() -> None:
    fields = {field.name: field for field in dataclasses.fields(pydocformatter_settings_core.SettingsResolver)}

    assert fields["_profiles_by_start_dir"].compare
    assert fields["_profiles_by_start_dir"].repr
    assert not fields["_context"].compare
    assert not fields["_context"].repr


def test_resolution_context_normalizes_lexical_toml_paths_without_resolving_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    config_path = tmp_path / "config.toml"
    intermediate = tmp_path / "intermediate"
    alias = tmp_path / "alias.toml"
    intermediate.mkdir()
    config_path.write_text("line-length = 91\n", encoding="utf-8")
    alias.symlink_to(config_path)
    monkeypatch.chdir(tmp_path)
    load_toml_file = mocker.spy(pydocformatter_settings_core, "_load_toml_file")
    context = pydocformatter_settings_core._SettingsResolutionContext()

    relative = context.load_toml_file("config.toml", required=True)
    absolute = context.load_toml_file(str(config_path), required=True)
    normalized = context.load_toml_file(str(intermediate / ".." / "config.toml"), required=True)
    symlinked = context.load_toml_file(str(alias), required=True)

    assert relative is absolute is normalized
    assert symlinked == relative
    assert symlinked is not relative
    assert load_toml_file.call_count == 2
    assert len(context.parsed_toml_by_path) == 2


def test_cached_toml_document_is_unchanged_after_repeated_application(tmp_path: Path) -> None:
    config_path = tmp_path / "pydocfmt.toml"
    config_path.write_text('line-length = 91\n[docstring]\nconvention = "google"\n', encoding="utf-8")
    context = pydocformatter_settings_core._SettingsResolutionContext()
    cached = context.load_toml_file(str(config_path), required=True)
    assert cached is not None
    original = copy.deepcopy(cached)
    base_profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))

    for _ in range(2):
        applied = pydocformatter_settings_core._apply_toml_file_profile(
            pydocformatter_settings.SETTINGS_SCHEMA,
            base_profile,
            path=str(config_path),
            required=True,
            source_base=str(tmp_path),
            source_priority=pydocformatter_settings_core.CONFIG_FILE_SOURCE_PRIORITY,
            context=context,
        )
        assert applied.settings.line_length == 91

    assert cached == original
    assert context.load_toml_file(str(config_path), required=True) is cached


def test_nested_auto_configs_use_distinct_profiles_and_closest_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nested = tmp_path / "nested"
    sibling = tmp_path / "sibling"
    nested.mkdir()
    sibling.mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    (nested / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 92\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    root_profile = resolver.profile_for_path(str(sibling))
    nested_profile = resolver.profile_for_path(str(nested))

    assert root_profile is not nested_profile
    assert root_profile.settings.line_length == 91
    assert nested_profile.settings.line_length == 92
    assert len(resolver._context.profiles_by_source) == 2


def test_equal_auto_config_values_keep_distinct_project_roots_and_field_bases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    config = '[tool.pydocfmt]\ninclude = ["*.py"]\n'
    (left / "pyproject.toml").write_text(config, encoding="utf-8")
    (right / "pyproject.toml").write_text(config, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    left_profile = resolver.profile_for_path(str(left))
    right_profile = resolver.profile_for_path(str(right))

    assert left_profile.settings == right_profile.settings
    assert left_profile is not right_profile
    assert left_profile.project_root == str(left)
    assert right_profile.project_root == str(right)
    assert left_profile.base_for_field("include") == str(left)
    assert right_profile.base_for_field("include") == str(right)


def test_resolver_source_identity_tracks_lookup_cwd_while_exact_aliases_remain_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    monkeypatch.chdir(first_dir)
    first_profile = resolver.profile_for_path(str(first_dir))
    monkeypatch.chdir(second_dir)
    second_profile = resolver.profile_for_path(str(second_dir))
    cached_first_profile = resolver.profile_for_path(str(first_dir))

    assert first_profile is cached_first_profile
    assert first_profile is not second_profile
    assert first_profile.base_for_field("exclude") == str(first_dir)
    assert second_profile.base_for_field("exclude") == str(second_dir)
    assert len(resolver._context.profiles_by_source) == 2


def test_config_option_containing_equals_is_classified_per_lookup_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    explicit_cwd = tmp_path / "explicit"
    inline_cwd = tmp_path / "inline"
    explicit_cwd.mkdir()
    inline_cwd.mkdir()
    option = "line-length=101"
    (explicit_cwd / option).write_text("line-length = 99\n", encoding="utf-8")
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver(global_values=pydocformatter_global_args.GlobalArgs(config_options=(option,)))

    monkeypatch.chdir(explicit_cwd)
    explicit_profile = resolver.profile_for_path(str(explicit_cwd))
    monkeypatch.chdir(inline_cwd)
    inline_profile = resolver.profile_for_path(str(inline_cwd))

    assert explicit_profile.settings.line_length == 99
    assert inline_profile.settings.line_length == 101
    assert resolver._context.config_inputs_by_cwd[str(explicit_cwd)].explicit_path == option
    assert resolver._context.config_inputs_by_cwd[str(inline_cwd)].inline_options == (option,)


def test_cached_parent_does_not_hide_existing_child_config_on_first_child_lookup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    (child / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 92\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    root_profile = resolver.profile_for_path(str(tmp_path))
    child_profile = resolver.profile_for_path(str(child))

    assert root_profile.settings.line_length == 91
    assert child_profile.settings.line_length == 92


def test_discovery_finds_new_config_in_unsearched_child_but_snapshots_searched_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fresh_child = tmp_path / "fresh"
    searched_child = tmp_path / "searched"
    searched_grandchild = searched_child / "grandchild"
    fresh_child.mkdir()
    searched_grandchild.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    root_profile = resolver.profile_for_path(str(tmp_path))
    assert resolver.profile_for_path(str(searched_child)) is root_profile
    (fresh_child / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 92\n", encoding="utf-8")
    (searched_child / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 93\n", encoding="utf-8")

    assert resolver.profile_for_path(str(fresh_child)).settings.line_length == 92
    assert resolver.profile_for_path(str(searched_grandchild)) is root_profile
    assert pydocformatter_settings.SETTINGS_SCHEMA.resolver().profile_for_path(str(searched_grandchild)).settings.line_length == 93


def test_nearer_pyproject_without_settings_table_shares_ancestor_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    (child / "pyproject.toml").write_text("[tool.other]\nenabled = true\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    load_toml_file = mocker.spy(pydocformatter_settings_core, "_load_toml_file")
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    root_profile = resolver.profile_for_path(str(tmp_path))
    child_profile = resolver.profile_for_path(str(child))

    assert child_profile is root_profile
    assert child_profile.settings.line_length == 91
    assert load_toml_file.call_count == 2


def test_negative_auto_discovery_reuses_cached_ancestors(tmp_path: Path, mocker: MockerFixture) -> None:
    first = tmp_path / "common" / "first"
    second = tmp_path / "common" / "second"
    first.mkdir(parents=True)
    second.mkdir()
    exists = mocker.patch("pydocformatter.settings.os.path.exists", return_value=False, autospec=True)
    load_toml_file = mocker.patch("pydocformatter.settings._load_toml_file", side_effect=AssertionError("no config should be loaded"), autospec=True)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    first_profile = resolver.profile_for_path(str(first))
    first_exists_calls = exists.call_count
    second_profile = resolver.profile_for_path(str(second))

    assert second_profile is first_profile
    assert exists.call_count == first_exists_calls + 1
    assert not load_toml_file.called
    assert all(config_path is None for config_path in resolver._context.closest_auto_config_by_start_dir.values())


def test_explicit_config_shares_profile_and_never_runs_auto_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    config_path = tmp_path / "pydocfmt.toml"
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    config_path.write_text("line-length = 91\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    mocker.patch("pydocformatter.settings._auto_discovered_pyproject_path_for_path_with_context", side_effect=AssertionError("explicit config must disable discovery"), autospec=True)
    load_toml_file = mocker.spy(pydocformatter_settings_core, "_load_toml_file")
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

    first_profile = resolver.profile_for_path(str(first))
    second_profile = resolver.profile_for_path(str(second))

    assert second_profile is first_profile
    assert first_profile.settings.line_length == 91
    assert load_toml_file.call_count == 1


def test_isolated_mode_shares_profile_applies_all_overrides_and_reads_no_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.chdir(tmp_path)
    mocker.patch("pydocformatter.settings._load_toml_file", side_effect=AssertionError("isolated mode must not read config files"), autospec=True)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver(
        global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 91",), isolated=True),
        args=argparse.Namespace(indent_width=3),
        field_overrides=CheckSettingsOverrides(line_ending=LineEnding.LF),
    )

    first_profile = resolver.profile_for_path(str(first))
    second_profile = resolver.profile_for_path(str(second))

    assert second_profile is first_profile
    assert first_profile.settings.line_length == 91
    assert first_profile.settings.indent_width == 3
    assert first_profile.settings.line_ending is LineEnding.LF


def test_inline_argparse_and_field_overrides_are_identical_across_distinct_nested_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 89\n", encoding="utf-8")
    (child / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 90\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver(
        global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 91",)),
        args=argparse.Namespace(indent_width=3),
        field_overrides=CheckSettingsOverrides(line_ending=LineEnding.LF),
    )

    root_profile = resolver.profile_for_path(str(tmp_path))
    child_profile = resolver.profile_for_path(str(child))

    assert root_profile is not child_profile
    assert (root_profile.settings.line_length, root_profile.settings.indent_width, root_profile.settings.line_ending) == (91, 3, LineEnding.LF)
    assert (child_profile.settings.line_length, child_profile.settings.indent_width, child_profile.settings.line_ending) == (91, 3, LineEnding.LF)


def test_resolver_is_snapshot_while_separate_resolver_observes_config_edit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "pyproject.toml"
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    config_path.write_text("[tool.pydocfmt]\nline-length = 91\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver()

    first_profile = resolver.profile_for_path(str(first))
    config_path.write_text("[tool.pydocfmt]\nline-length = 92\n", encoding="utf-8")
    same_resolver_profile = resolver.profile_for_path(str(second))
    fresh_resolver_profile = pydocformatter_settings.SETTINGS_SCHEMA.resolver().profile_for_path(str(second))

    assert same_resolver_profile is first_profile
    assert same_resolver_profile.settings.line_length == 91
    assert fresh_resolver_profile.settings.line_length == 92


@pytest.mark.parametrize("initial_content", [None, "not = [valid"])
def test_missing_or_malformed_explicit_config_is_not_cached_and_can_be_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, initial_content: str | None) -> None:
    config_path = tmp_path / "pydocfmt.toml"
    target = tmp_path / "target"
    target.mkdir()
    if initial_content is not None:
        config_path.write_text(initial_content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = pydocformatter_settings.SETTINGS_SCHEMA.resolver(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

    with pytest.raises(SettingsError):
        resolver.profile_for_path(str(target))
    assert not resolver._context.parsed_toml_by_path
    assert not resolver._profiles_by_start_dir

    config_path.write_text("line-length = 91\n", encoding="utf-8")
    profile = resolver.profile_for_path(str(target))

    assert profile.settings.line_length == 91
    assert len(resolver._context.parsed_toml_by_path) == 1


def test_layer_error_precedence_remains_file_then_inline_then_argparse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "pydocfmt.toml"
    config_path.write_text("not = [valid", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    global_values = pydocformatter_global_args.GlobalArgs(config_options=(str(config_path), "also = [invalid"))
    args = argparse.Namespace(per_file_ignores=["{invalid"])

    with pytest.raises(SettingsError, match=f"Failed to decode {re.escape(str(config_path))}"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=global_values, args=args)

    config_path.write_text("line-length = 91\n", encoding="utf-8")
    with pytest.raises(SettingsError, match="Failed to decode --config inline TOML"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=global_values, args=args)

    valid_global_values = pydocformatter_global_args.GlobalArgs(config_options=(str(config_path), "line-length = 92"))
    with pytest.raises(tomllib.TOMLDecodeError):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=valid_global_values, args=args)


def test_inline_config_error_precedence_follows_option_order() -> None:
    global_values = pydocformatter_global_args.GlobalArgs(config_options=("unknown-setting = 1", "line-length = ["), isolated=True)

    with pytest.raises(SettingsError, match=r"^<--config> contains unknown setting\(s\): unknown-setting$"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=global_values)


def test_settings_resolution_preserves_exact_global_config_errors(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    first = tmp_path / "first.toml"
    second = tmp_path / "second.toml"
    first.write_text("line-length = 91\n", encoding="utf-8")
    second.write_text("line-length = 92\n", encoding="utf-8")

    with pytest.raises(SettingsError, match=f"^Configuration file not found: {re.escape(str(missing))}$"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(missing),)))
    with pytest.raises(SettingsError, match=re.escape("Only one --config=PATH configuration file can be supplied")):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(first), str(second))))
    with pytest.raises(SettingsError, match=re.escape("The argument --config=PATH cannot be used with --isolated")):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(first),), isolated=True))


def test_settings_overrides_are_dict_like_and_omit_unspecified_values() -> None:
    overrides = CheckSettingsOverrides(line_length=103)

    assert overrides == {"line_length": 103}
    assert "line_ending" not in overrides


def test_file_selection_spec_defaults_match_settings_defaults() -> None:
    defaults_lines = _markdown_section_lines(_repo_root() / "docs" / "public" / "file_selection_spec.md", "Defaults")
    defaults = tomllib.loads("\n".join(line.removeprefix("- `").removesuffix("`") for line in defaults_lines))
    file_selection_definitions = tuple(definition for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.FILE_SELECTION)
    config = CheckSettings()

    assert tuple(defaults) == tuple(definition.key for definition in file_selection_definitions)
    for definition in file_selection_definitions:
        expected = getattr(config, definition.field)
        if isinstance(expected, tuple):
            expected = list(expected)
        assert defaults[definition.key] == expected


def test_load_settings_defaults_in_isolated_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.chdir(td)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))

    assert config.line_length == 88
    assert config.url_aware_wrapping
    assert config.line_ending is LineEnding.AUTO
    assert config.indent_style is IndentStyle.SPACE
    assert config.indent_width == 4
    assert config.parallelism == 0.0  # ruff: ignore[float-equality-comparison]
    assert config.docstring_convention is pydocformatter_settings.DocstringConvention.PEP257
    assert not config.docstring_include_assertion_errors
    assert config.docstring_placeholder_markers == pydocformatter_settings.DEFAULT_DOCSTRING_PLACEHOLDER_MARKERS
    assert not config.comment_join_standalone_lines
    assert config.comment_format_list_items
    assert config.comment_task_marker_mode is CommentTaskMarkerMode.NO_WRAP
    assert config.comment_task_markers == pydocformatter_settings.DEFAULT_COMMENT_TASK_MARKERS
    assert config.comment_preserve_headings
    assert config.comment_preserve_doctests
    assert config.comment_preserve_code_fences
    assert config.comment_format_block_quotes
    assert config.comment_preserve_tables
    assert config.comment_preserve_directives
    assert config.comment_trailing_extraction_syntax_aware
    assert config.comment_trailing_extraction_content_aware
    assert not config.comment_detect_code
    assert config.comment_detect_statements
    assert not config.comment_detect_expressions
    assert config.include == DEFAULT_INCLUDE
    assert config.extend_include == ()
    assert config.exclude == DEFAULT_EXCLUDE
    assert config.extend_exclude == ()
    assert config.respect_gitignore
    assert not config.force_exclude
    assert config.output_format is OutputFormat.GROUPED
    assert config.select == ("ALL",)
    assert config.extend_select == ()
    assert config.require_explicit == pydocformatter_settings.DEFAULT_REQUIRE_EXPLICIT
    assert config.ignore == ()
    assert config.fixable == ("ALL",)
    assert config.extend_fixable == ()
    assert config.unfixable == ()
    assert config.per_file_ignores == ()
    assert config.extend_per_file_ignores == ()
    assert config.per_file_settings == ()


def test_default_exclude_extends_ruff_default_with_cache_directory() -> None:
    result = subprocess.run(["uv", "run", "ruff", "config", "exclude"], cwd=_repo_root(), shell=False, check=True, capture_output=True, text=True)
    default_match = re.search(r"^Default value: (?P<value>\[.*\])$", result.stdout, re.MULTILINE)
    assert default_match is not None

    assert tuple(json.loads(default_match.group("value"))) == tuple(directory for directory in DEFAULT_EXCLUDE if directory != ".pydocfmt_cache")


def test_programmatic_cache_directory_rejects_embedded_nul() -> None:
    with pytest.raises(SettingsError, match=r"cache_dir.*NUL"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(cache_dir="\0"))


def test_inline_cache_directory_rejects_embedded_nul_escape() -> None:
    with pytest.raises(SettingsError, match=r"cache-dir.*NUL"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=('cache-dir = "\\u0000"',), isolated=True))


def test_toml_cache_directory_rejects_embedded_nul_escape(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('cache-dir = "\\u0000"\n', encoding="utf-8")

    with pytest.raises(SettingsError, match=r"cache-dir.*NUL"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config),)))


def test_ty_default_exclude_matches_shared_default_directories() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[project]\nname = "ty-default-excludes"\nversion = "0.0.0"\nrequires-python = ">=3.11"\n', encoding="utf-8")
        (root / "kept.py").write_text("x = 1\n", encoding="utf-8")
        for directory in (directory for directory in DEFAULT_EXCLUDE if directory != ".pydocfmt_cache"):
            ignored_dir = root / directory
            ignored_dir.mkdir(parents=True)
            (ignored_dir / "ignored.py").write_text("x = 1\n", encoding="utf-8")

        result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            ["uv", "run", "ty", "check", "--project", str(root), "-vv", "--no-progress", "--output-format", "concise"], cwd=_repo_root(), shell=False, check=True, capture_output=True, text=True
        )

    assert "Indexed 1 file(s)" in result.stderr
    assert f"Checking file '{root / 'kept.py'}'" in result.stderr
    assert "ignored.py" not in result.stderr
    for directory in (directory for directory in DEFAULT_EXCLUDE if directory != ".pydocfmt_cache"):
        assert f"Skipping directory '{root / directory}'" in result.stderr


def test_setting_documentation_default_mentions_match_resolved_defaults() -> None:
    for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions:
        default_match = re.search(r"defaults to (?P<default>[^.]+)\.", definition.documentation)
        if default_match is None:
            continue
        config = CheckSettings()
        expected_default = pydocformatter_settings_core.format_value(getattr(config, definition.field), definition.value_type)

        assert default_match.group("default") == expected_default


def test_setting_documentation_omits_long_string_list_defaults() -> None:
    short_default = '["PCF200", "PDF003", "PDF516", "PDF517", "PDF518"]'

    assert len(short_default) == 50
    assert pydocformatter_settings._documented_default_text(short_default, pydocformatter_settings_core.StringList) == short_default
    assert pydocformatter_settings._documented_default_text(f"{short_default}x", pydocformatter_settings_core.StringList) is None
    assert pydocformatter_settings._setting_default_text("select", pydocformatter_settings_core.StringList) == '["ALL"]'
    assert pydocformatter_settings._setting_default_text("comment_task_markers", pydocformatter_settings_core.StringList) is None
    assert pydocformatter_settings._setting_default_text("docstring_placeholder_markers", pydocformatter_settings_core.StringList) is None
    assert pydocformatter_settings._setting_default_text("require_explicit", pydocformatter_settings_core.StringList) is None
    assert "has a default value" in pydocformatter_settings._setting_default_clause("require_explicit", pydocformatter_settings_core.StringList)
    assert "defaults to" not in pydocformatter_settings._setting_default_clause("require_explicit", pydocformatter_settings_core.StringList)


def test_load_profile_tracks_field_source_priorities(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\nselect = ["PDF"]\n', encoding="utf-8")
        monkeypatch.chdir(root)
        profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(
            global_values=pydocformatter_global_args.GlobalArgs(config_options=('ignore = ["PDF101"]',)),
            args=argparse.Namespace(extend_select=["PCF"]),
            field_overrides=CheckSettingsOverrides(fixable=("PDF101",)),
        )

    assert profile.priority_for_field("select") == pydocformatter_settings_core.CONFIG_FILE_SOURCE_PRIORITY
    assert profile.priority_for_field("ignore") == pydocformatter_settings_core.INLINE_CONFIG_SOURCE_PRIORITY
    assert profile.priority_for_field("extend_select") == pydocformatter_settings_core.ARGUMENT_SOURCE_PRIORITY
    assert profile.priority_for_field("fixable") == pydocformatter_settings_core.FIELD_OVERRIDE_SOURCE_PRIORITY
    assert profile.priority_for_field("unfixable") == pydocformatter_settings_core.DEFAULT_SOURCE_PRIORITY


def test_settings_profile_key_is_hashable_and_mapping_order_independent() -> None:
    settings = CheckSettings()
    first = pydocformatter_settings_core.SettingsProfile(settings=settings, field_bases={"select": "/a", "ignore": "/b"}, field_priorities={"select": 1, "ignore": 2}, project_root="/project")
    second = pydocformatter_settings_core.SettingsProfile(settings=settings, field_bases={"ignore": "/b", "select": "/a"}, field_priorities={"ignore": 2, "select": 1}, project_root="/project")

    assert isinstance(first.key(), pydocformatter_settings_core.SettingsProfile.Key)
    assert first.key() == second.key()
    assert {first.key(): "value"}[second.key()] == "value"


def test_git_root_pyproject_is_loaded_from_subdirectory(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subdir = root / "src"
        subdir.mkdir()
        git_helpers.write_git_marker(root)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 73\n", encoding="utf-8")
        monkeypatch.chdir(subdir)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.line_length == 73


def test_current_directory_pyproject_overrides_git_root_pyproject(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subdir = root / "src"
        subdir.mkdir()
        git_helpers.write_git_marker(root)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 73\nindent-width = 2\n", encoding="utf-8")
        (subdir / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 74\n", encoding="utf-8")
        monkeypatch.chdir(subdir)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.line_length == 74
    assert config.indent_width == 4


def test_config_options_override_auto_discovered_git_root_and_current_pyprojects(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subdir = root / "src"
        subdir.mkdir()
        git_helpers.write_git_marker(root)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 73\nindent-width = 2\n", encoding="utf-8")
        (subdir / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 74\n", encoding="utf-8")
        config_path = root / "pydocfmt.toml"
        config_path.write_text("line-length = 75\nindent-width = 3\n", encoding="utf-8")
        monkeypatch.chdir(subdir)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path), "line-length = 76")))

    assert config.line_length == 76
    assert config.indent_width == 3


def test_explicit_config_file_ignores_auto_discovered_pyproject(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pydocfmt.toml"
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nindent-width = 2\n", encoding="utf-8")
        config_path.write_text("line-length = 75\n", encoding="utf-8")
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

    assert config.line_length == 75
    assert config.indent_width == 4


def test_isolated_ignores_git_root_and_current_directory_pyprojects(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subdir = root / "src"
        subdir.mkdir()
        git_helpers.write_git_marker(root)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 73\n", encoding="utf-8")
        (subdir / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 74\n", encoding="utf-8")
        monkeypatch.chdir(subdir)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))

    assert config.line_length == 88


def test_auto_discovered_pyproject_path_skips_files_without_pydocfmt_table(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        candidate = root / "pyproject.toml"
        candidate.write_text("[tool.other]\nvalue = true\n", encoding="utf-8")
        monkeypatch.chdir(root)
        path = pydocformatter_settings_core._auto_discovered_pyproject_path_for_path_with_context(
            None, table_path=("tool", "pydocfmt"), context=pydocformatter_settings_core._SettingsResolutionContext()
        )

    assert path is not None
    assert path != str(candidate)


def test_suite_temporary_directories_stay_below_configuration_boundary() -> None:
    temporary_directory = Path(tempfile.gettempdir())
    boundary = next(parent for parent in temporary_directory.parents if (parent / "pyproject.toml").is_file())
    boundary_config = boundary / "pyproject.toml"

    assert boundary_config.read_text(encoding="utf-8") == '[tool.pydocfmt]\ncache-dir = "tmp/.pydocfmt_cache"\n'
    assert temporary_directory.is_relative_to(boundary / "tmp")
    with tempfile.TemporaryDirectory() as td:
        nested = Path(td) / "nested"
        nested.mkdir()
        discovered = pydocformatter_settings_core._auto_discovered_pyproject_path_for_path_with_context(
            str(nested), table_path=("tool", "pydocfmt"), context=pydocformatter_settings_core._SettingsResolutionContext()
        )
        settings = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(path=str(nested)).settings

    assert nested.is_relative_to(boundary)
    assert discovered == str(boundary_config)
    assert settings == dataclasses.replace(CheckSettings(), cache_dir="tmp/.pydocfmt_cache")


def test_rule_settings_accept_all_rule_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            '[tool.pydocfmt]\nselect = ["PDF", "PCF"]\nignore = ["PDF101"]\nfixable = ["ALL"]\n[tool.pydocfmt.per-file-ignores]\n"tests/*.py" = ["PCF000"]\n', encoding="utf-8"
        )
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.select == ("PDF", "PCF")
    assert config.ignore == ("PDF101",)
    assert config.fixable == ("ALL",)
    assert config.per_file_ignores == (("tests/*.py", ("PCF000",)),)


def test_nested_docstring_table_settings_are_loaded_from_pyproject(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            '[tool.pydocfmt.docstring]\nconvention = "google"\nblank-line-style = "aligned"\nblank-line-after-last-section = true\ninclude-assertion-errors = true\nplaceholder-markers = ["WIP", "..."]\nproperty-decorators = ["project.Property"]\nparse-tables = false\n',
            encoding="utf-8",
        )
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.docstring_convention == pydocformatter_settings.DocstringConvention.GOOGLE
    assert config.docstring_blank_line_style == pydocformatter_settings.DocstringBlankLineStyle.ALIGNED
    assert config.docstring_blank_line_after_last_section
    assert config.docstring_include_assertion_errors
    assert config.docstring_placeholder_markers == ("WIP", "...")
    assert config.docstring_property_decorators == ("project.Property",)
    assert not config.docstring_parse_tables


def test_nested_comment_table_settings_are_loaded_from_dedicated_config_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pydocfmt.toml"
        config_path.write_text("[comment]\njoin-standalone-lines = true\npreserve-tables = false\ndetect-expressions = true\n", encoding="utf-8")

        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

    assert config.comment_join_standalone_lines
    assert not config.comment_preserve_tables
    assert config.comment_detect_expressions


def test_nested_setting_tables_are_loaded_from_inline_config_options() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(
        global_values=pydocformatter_global_args.GlobalArgs(config_options=('docstring.convention = "numpy"\ncomment.detect-code = true',), isolated=True)
    )

    assert config.docstring_convention == pydocformatter_settings.DocstringConvention.NUMPY
    assert config.comment_detect_code


def test_nested_setting_table_rejects_duplicate_flat_key() -> None:
    with pytest.raises(SettingsError, match="sets docstring-convention more than once"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(config_options=('docstring-convention = "google"\n[docstring]\nconvention = "numpy"',), isolated=True)
        )


def test_nested_setting_table_rejects_unknown_flattened_key() -> None:
    with pytest.raises(SettingsError, match="docstring-unknown"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("[docstring]\nunknown = true",), isolated=True))


def test_nested_setting_table_rejects_deeper_tables() -> None:
    with pytest.raises(SettingsError, match="docstring-parse must not be a table"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("[docstring.parse]\ntables = false",), isolated=True))


def test_unrelated_nested_setting_table_is_rejected() -> None:
    with pytest.raises(SettingsError, match="formatting"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("[formatting]\nline-length = 99",), isolated=True))


def test_inline_per_file_rule_settings_are_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\nper-file-ignores = {"tests/*.py" = ["PCF000"]}\nextend-per-file-ignores = {"generated/*.py" = ["PCF001"]}\n', encoding="utf-8")
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.per_file_ignores == (("tests/*.py", ("PCF000",)),)
    assert config.extend_per_file_ignores == (("generated/*.py", ("PCF001",)),)


def test_per_file_settings_are_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            '[tool.pydocfmt.per-file-settings]\n"tests/*.py" = { docstring = { missing-documentation = "has-section", include-assertion-errors = true }, comment = { detect-code = true } }\n"generated/*.py" = { line-length = 100 }\n',
            encoding="utf-8",
        )
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.per_file_settings == (
        (
            "tests/*.py",
            (("docstring-missing-documentation", pydocformatter_settings.DocstringMissingDocumentation.HAS_SECTION), ("docstring-include-assertion-errors", True), ("comment-detect-code", True)),
        ),
        ("generated/*.py", (("line-length", 100),)),
    )


@pytest.mark.parametrize(
    ("config", "key"),
    [
        pytest.param('per-file-settings = {"tests/*.py" = { select = ["PDF101"] }}', "select", id="rule-selection"),
        pytest.param('per-file-settings = {"tests/*.py" = { include = ["*.py"] }}', "include", id="file-selection"),
        pytest.param('per-file-settings = {"tests/*.py" = { parallelism = 1 }}', "parallelism", id="run-setting"),
        pytest.param('per-file-settings = {"tests/*.py" = { docstring-convention = "google" }}', "docstring-convention", id="rule-setting-effect"),
    ],
)
def test_per_file_settings_reject_disallowed_settings(config: str, key: str) -> None:
    with pytest.raises(SettingsError, match=rf"{key} cannot be configured in per-file-settings"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(config,), isolated=True))


@pytest.mark.parametrize(
    ("config", "message"),
    [
        pytest.param('per-file-settings = {"tests/*.py" = {}}', "must not be empty", id="empty-table"),
        pytest.param('per-file-settings = {"" = { line-length = 100 }}', "keys must not be empty", id="empty-key"),
        pytest.param('per-file-settings = {"tests/*.py" = { unknown = true }}', "unknown", id="unknown-key"),
        pytest.param(
            'per-file-settings = {"tests/*.py" = { docstring-missing-documentation = "has-section", docstring = { missing-documentation = "all-docstrings" } }}',
            "sets docstring-missing-documentation more than once",
            id="duplicate-nested-setting",
        ),
    ],
)
def test_per_file_settings_reject_invalid_tables(config: str, message: str) -> None:
    with pytest.raises(SettingsError, match=message):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(config,), isolated=True))


def test_effective_profile_applies_matching_per_file_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        settings = CheckSettings(
            docstring_missing_documentation=pydocformatter_settings.DocstringMissingDocumentation.ALL_DOCSTRINGS,
            per_file_settings=(("tests/*.py", (("docstring-missing-documentation", pydocformatter_settings.DocstringMissingDocumentation.HAS_SECTION), ("line-length", 100))),),
        )
        monkeypatch.chdir(root)
        profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(global_values=pydocformatter_global_args.GlobalArgs(isolated=True), field_overrides=dataclasses.asdict(settings))
        matching = pydocformatter_settings.effective_profile_for_path(profile, str(root / "tests" / "test_example.py"))
        nonmatching = pydocformatter_settings.effective_profile_for_path(profile, str(root / "src" / "example.py"))

    assert matching.settings.docstring_missing_documentation == pydocformatter_settings.DocstringMissingDocumentation.HAS_SECTION
    assert matching.settings.line_length == 100
    assert nonmatching.settings.docstring_missing_documentation == pydocformatter_settings.DocstringMissingDocumentation.ALL_DOCSTRINGS
    assert nonmatching.settings.line_length == 88


def test_effective_profile_supports_negated_per_file_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(per_file_settings=(("!src/*.py", (("line-length", 100),)),))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        monkeypatch.chdir(root)
        profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(global_values=pydocformatter_global_args.GlobalArgs(isolated=True), field_overrides=dataclasses.asdict(settings))
        included = pydocformatter_settings.effective_profile_for_path(profile, str(root / "src" / "example.py"))
        excluded = pydocformatter_settings.effective_profile_for_path(profile, str(root / "tests" / "example.py"))

    assert included.settings.line_length == 88
    assert excluded.settings.line_length == 100


def test_command_line_setting_has_priority_over_config_per_file_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "tests" / "test_example.py"
        target.parent.mkdir()
        target.write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt.per-file-settings]\n"tests/*.py" = { docstring-missing-documentation = "has-section" }\n', encoding="utf-8")
        monkeypatch.chdir(root)
        profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(docstring_missing_documentation="all-docstrings"), path=str(target))
        effective = pydocformatter_settings.effective_profile_for_path(profile, str(target))

    assert profile.settings.docstring_missing_documentation == pydocformatter_settings.DocstringMissingDocumentation.ALL_DOCSTRINGS
    assert effective.settings.docstring_missing_documentation == pydocformatter_settings.DocstringMissingDocumentation.ALL_DOCSTRINGS


def test_cli_rule_overrides_are_applied() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(select=("PCF",), ignore=("PCF001",), per_file_ignores=(("tests/*.py", ("PCF000",)),)))

    assert config.select == ("PCF",)
    assert config.ignore == ("PCF001",)
    assert config.per_file_ignores == (("tests/*.py", ("PCF000",)),)


def test_format_settings_returns_stable_toml_output() -> None:
    settings = CheckSettings(line_ending=LineEnding.LF, select=("PDF", "PCF"), per_file_ignores=(('tests/"quoted"/*.py', ("PCF000",)),))

    output = pydocformatter_settings.SETTINGS_SCHEMA.format(settings)
    expected_require_explicit = ", ".join(f'"{selector}"' for selector in CheckSettings().require_explicit)

    assert "[tool.pydocfmt]\n" in output
    assert output.index("output-format") < output.index("line-length")
    assert output.index("indent-width") < output.index("parallelism")
    assert "parallelism = 0.0\n" in output
    assert 'line-ending = "lf"\n' in output
    assert 'select = ["PDF", "PCF"]\n' in output
    assert f"require-explicit = [{expected_require_explicit}]\n" in output
    assert 'per-file-ignores = {"tests/\\"quoted\\"/*.py" = ["PCF000"]}\n' in output


def test_parallelism_setting_accepts_numbers() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(parallelism=FRACTIONAL_PARALLELISM))

    assert config.parallelism == FRACTIONAL_PARALLELISM


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(-1, id="negative"),
        pytest.param(True, id="bool"),
        pytest.param("auto", id="string"),
        pytest.param(math.inf, id="infinity"),
        pytest.param(math.nan, id="nan"),
        pytest.param(1.5, id="non-integer"),
    ],
)
def test_parallelism_setting_rejects_invalid_values(value: object) -> None:
    with pytest.raises(SettingsError):
        pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"parallelism": value})


def test_url_aware_wrapping_setting_is_loaded_from_toml_and_cli() -> None:
    configured = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=("url-aware-wrapping = true",)))
    overridden = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True), args=argparse.Namespace(url_aware_wrapping=True))
    disabled = pydocformatter_settings.SETTINGS_SCHEMA.load(
        global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=("url-aware-wrapping = true",)), args=argparse.Namespace(url_aware_wrapping=False)
    )

    assert configured.url_aware_wrapping
    assert overridden.url_aware_wrapping
    assert not disabled.url_aware_wrapping


def test_comment_formatting_settings_are_loaded_from_toml_and_cli() -> None:
    configured = pydocformatter_settings.SETTINGS_SCHEMA.load(
        global_values=pydocformatter_global_args.GlobalArgs(
            isolated=True,
            config_options=(
                'comment-join-standalone-lines = true\ncomment-format-list-items = true\ncomment-task-marker-mode = "hanging"\ncomment-task-markers = ["TODO", "BUG"]\ncomment-trailing-extraction-syntax-aware = false\ncomment-trailing-extraction-content-aware = false\ncomment-detect-code = false',
            ),
        )
    )
    overridden = pydocformatter_settings.SETTINGS_SCHEMA.load(
        global_values=pydocformatter_global_args.GlobalArgs(isolated=True),
        args=argparse.Namespace(comment_preserve_tables=True, comment_task_marker_mode="none", comment_task_markers=("FIXME", "TODO_SEC"), comment_detect_code=False),
    )

    assert configured.comment_join_standalone_lines
    assert configured.comment_format_list_items
    assert configured.comment_task_marker_mode is CommentTaskMarkerMode.HANGING
    assert configured.comment_task_markers == ("TODO", "BUG")
    assert not configured.comment_trailing_extraction_syntax_aware
    assert not configured.comment_trailing_extraction_content_aware
    assert not configured.comment_detect_code
    assert overridden.comment_preserve_tables
    assert overridden.comment_task_marker_mode is CommentTaskMarkerMode.NONE
    assert overridden.comment_task_markers == ("FIXME", "TODO_SEC")
    assert not overridden.comment_detect_code


def test_comment_task_marker_setting_validation() -> None:
    valid_empty = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=("comment-task-markers = []",)))

    assert valid_empty.comment_task_markers == ()
    with pytest.raises(SettingsError):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=('comment-task-markers = ["TODO", "TODO"]',)))
    with pytest.raises(SettingsError):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=('comment-task-markers = ["todo"]',)))
    with pytest.raises(SettingsError):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=("comment-format-task-markers = false",)))


def test_docstring_placeholder_marker_setting_validation() -> None:
    valid = pydocformatter_settings.SETTINGS_SCHEMA.load(
        global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=('docstring-placeholder-markers = ["TODO", "NotImplemented", "..."]',))
    )
    empty = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=("docstring-placeholder-markers = []",)))

    assert valid.docstring_placeholder_markers == ("TODO", "NotImplemented", "...")
    assert empty.docstring_placeholder_markers == ()
    for invalid in ('["TODO", "todo"]', '["Not implemented"]', '["TODO."]', '["\u00d6"]', '["...."]'):
        with pytest.raises(SettingsError):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=(f"docstring-placeholder-markers = {invalid}",)))
    with pytest.raises(SettingsError, match=r"entries must be.*\N{LATIN SMALL LETTER SHARP S}"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=('docstring-placeholder-markers = ["ss", "\u00df"]',)))
    with pytest.raises(SettingsError, match="ASCII case-insensitive duplicate markers: todo"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=('docstring-placeholder-markers = ["TODO", "todo"]',)))
    with pytest.raises(SettingsError, match="ASCII case-insensitive duplicate markers: ToDo, todo"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=('docstring-placeholder-markers = ["TODO", "todo", "ToDo"]',)))


def test_docstring_parsing_settings_are_loaded_and_validated() -> None:
    definition = next(definition for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.field == "docstring_convention")
    assert definition.cli is not None
    assert definition.cli.choices == ("none", "pep257", "google", "numpy", "rest")

    for convention in pydocformatter_settings.DocstringConvention:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_convention": convention.value})
        assert config.docstring_convention == convention
    for blank_line_style in pydocformatter_settings.DocstringBlankLineStyle:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_blank_line_style": blank_line_style.value})
        assert config.docstring_blank_line_style == blank_line_style
    for missing_documentation in pydocformatter_settings.DocstringMissingDocumentation:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_missing_documentation": missing_documentation.value})
        assert config.docstring_missing_documentation == missing_documentation

    configured = pydocformatter_settings.SETTINGS_SCHEMA.load(
        global_values=pydocformatter_global_args.GlobalArgs(
            isolated=True,
            config_options=(
                'docstring-convention = "google"\ndocstring-blank-line-style = "aligned"\ndocstring-blank-line-after-last-section = true\ndocstring-missing-documentation = "all-docstrings"\ndocstring-missing-documentation-public-only = false\ndocstring-require-init-attribute-documentation = true\ndocstring-include-assertion-errors = true\ndocstring-class-attribute-no-type-base-classes = ["enum.Enum"]\ndocstring-forbidden-function-decorators = ["project.overload"]\ndocstring-optional-function-decorators = ["project.override"]\ndocstring-placeholder-markers = ["TODO", "NotImplemented", "..."]\ndocstring-property-decorators = ["project.Property"]\ndocstring-parse-tables = false',
            ),
        )
    )
    overridden = pydocformatter_settings.SETTINGS_SCHEMA.load(
        global_values=pydocformatter_global_args.GlobalArgs(isolated=True),
        args=argparse.Namespace(
            docstring_convention="numpy",
            docstring_blank_line_style="blank",
            docstring_blank_line_after_last_section=False,
            docstring_missing_documentation="non-summary-docstrings",
            docstring_missing_documentation_public_only=True,
            docstring_require_init_attribute_documentation=False,
            docstring_include_assertion_errors=False,
            docstring_class_attribute_no_type_base_classes=("Flag,enum.Flag",),
            docstring_forbidden_function_decorators=("typing.overload,overload",),
            docstring_optional_function_decorators=("typing.override,override",),
            docstring_placeholder_markers=("WIP,NotImplemented",),
            docstring_property_decorators=("property,project.Property",),
            docstring_parse_tables=False,
        ),
    )
    assert configured.docstring_convention == pydocformatter_settings.DocstringConvention.GOOGLE
    assert configured.docstring_blank_line_style == pydocformatter_settings.DocstringBlankLineStyle.ALIGNED
    assert configured.docstring_blank_line_after_last_section
    assert configured.docstring_missing_documentation == pydocformatter_settings.DocstringMissingDocumentation.ALL_DOCSTRINGS
    assert not configured.docstring_missing_documentation_public_only
    assert configured.docstring_require_init_attribute_documentation
    assert configured.docstring_include_assertion_errors
    assert configured.docstring_class_attribute_no_type_base_classes == ("enum.Enum",)
    assert configured.docstring_forbidden_function_decorators == ("project.overload",)
    assert configured.docstring_optional_function_decorators == ("project.override",)
    assert configured.docstring_placeholder_markers == ("TODO", "NotImplemented", "...")
    assert configured.docstring_property_decorators == ("project.Property",)
    assert not configured.docstring_parse_tables
    assert overridden.docstring_convention == pydocformatter_settings.DocstringConvention.NUMPY
    assert overridden.docstring_blank_line_style == pydocformatter_settings.DocstringBlankLineStyle.BLANK
    assert not overridden.docstring_blank_line_after_last_section
    assert overridden.docstring_missing_documentation == pydocformatter_settings.DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS
    assert overridden.docstring_missing_documentation_public_only
    assert not overridden.docstring_require_init_attribute_documentation
    assert not overridden.docstring_include_assertion_errors
    assert overridden.docstring_class_attribute_no_type_base_classes == ("Flag", "enum.Flag")
    assert overridden.docstring_forbidden_function_decorators == ("typing.overload", "overload")
    assert overridden.docstring_optional_function_decorators == ("typing.override", "override")
    assert overridden.docstring_placeholder_markers == ("WIP", "NotImplemented")
    assert overridden.docstring_property_decorators == ("property", "project.Property")
    assert not overridden.docstring_parse_tables

    empty_decorator_config = pydocformatter_settings.SETTINGS_SCHEMA.load(
        field_overrides={
            "docstring_forbidden_function_decorators": (),
            "docstring_optional_function_decorators": (),
            "docstring_placeholder_markers": (),
            "docstring_property_decorators": (),
            "docstring_class_attribute_no_type_base_classes": (),
        }
    )
    assert empty_decorator_config.docstring_forbidden_function_decorators == ()
    assert empty_decorator_config.docstring_optional_function_decorators == ()
    assert empty_decorator_config.docstring_placeholder_markers == ()
    assert empty_decorator_config.docstring_property_decorators == ()
    assert empty_decorator_config.docstring_class_attribute_no_type_base_classes == ()

    config = pydocformatter_settings.SETTINGS_SCHEMA.load(
        field_overrides={
            "docstring_parse_list_items": False,
            "docstring_parse_headings": False,
            "docstring_parse_doctests": False,
            "docstring_parse_code_fences": False,
            "docstring_parse_block_quotes": False,
            "docstring_parse_tables": False,
            "docstring_parse_directives": False,
            "docstring_parse_literal_blocks": False,
        }
    )
    assert not config.docstring_parse_list_items
    assert not config.docstring_parse_headings
    assert not config.docstring_parse_doctests
    assert not config.docstring_parse_code_fences
    assert not config.docstring_parse_block_quotes
    assert not config.docstring_parse_tables
    assert not config.docstring_parse_directives
    assert not config.docstring_parse_literal_blocks

    with pytest.raises(SettingsError, match="docstring_convention must be one of"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_convention": "automatic"})

    with pytest.raises(SettingsError, match="Unknown setting: docstring_parse_sphinx_fields"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_parse_sphinx_fields": False})


def test_output_format_setting_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\noutput-format = "grouped"\n', encoding="utf-8")
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.output_format is OutputFormat.GROUPED


def test_output_format_cli_override_is_applied() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(output_format=OutputFormat.GROUPED))

    assert config.output_format is OutputFormat.GROUPED


def test_output_format_setting_must_be_grouped(monkeypatch: pytest.MonkeyPatch) -> None:
    unsupported_output_formats = ("json",)
    unsupported_output_format = unsupported_output_formats[0]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(f'[tool.pydocfmt]\noutput-format = "{unsupported_output_format}"\n', encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="output-format"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_settings_overrides_replace_independent_list_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            "[tool.pydocfmt]\n"
            "line-length = 77\n"
            'line-ending = "cr-lf"\n'
            'indent-style = "space"\n'
            "indent-width = 3\n"
            'include = ["*.pyi"]\n'
            'extend-include = ["*.pyw"]\n'
            'exclude = ["build"]\n'
            'extend-exclude = ["dist"]\n'
            "force-exclude = true\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.line_length == 77
    assert config.line_ending is LineEnding.CR_LF
    assert config.indent_style is IndentStyle.SPACE
    assert config.indent_width == 3
    assert config.include == ("*.pyi",)
    assert config.extend_include == ("*.pyw",)
    assert config.exclude == ("build",)
    assert config.extend_exclude == ("dist",)
    assert config.force_exclude


def test_overrides_replace_extend_lists() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(include=("*.py",), extend_include=("*.pyw",), exclude=(), extend_exclude=("generated.py",)))

    assert config.include == ("*.py",)
    assert config.extend_include == ("*.pyw",)
    assert config.exclude == ()
    assert config.extend_exclude == ("generated.py",)


def test_overrides_replace_indent_settings() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(indent_style=IndentStyle.TAB, indent_width=2))

    assert config.indent_style is IndentStyle.TAB
    assert config.indent_width == 2


def test_overrides_replace_line_ending() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(line_ending=LineEnding.NATIVE))

    assert config.line_ending is LineEnding.NATIVE


def test_unknown_hyphenated_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nunknown-key = true\n", encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="unknown-key"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_underscore_alias_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline_length = 100\n", encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="line_length"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_bool_line_length_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = true\n", encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="line-length"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_line_length_accepts_inclusive_bounds() -> None:
    lower = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 1",), isolated=True))
    upper = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 320",), isolated=True))

    assert lower.line_length == 1
    assert upper.line_length == 320


def test_line_length_rejects_values_outside_bounds() -> None:
    with pytest.raises(SettingsError, match=r"line-length.*greater than or equal to 1"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 0",), isolated=True))
    with pytest.raises(SettingsError, match=r"line-length.*less than or equal to 320"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 321",), isolated=True))


def test_indent_width_accepts_inclusive_bounds() -> None:
    lower = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 1",), isolated=True))
    upper = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 255",), isolated=True))

    assert lower.indent_width == 1
    assert upper.indent_width == 255


def test_indent_width_rejects_values_outside_bounds() -> None:
    with pytest.raises(SettingsError, match=r"indent-width.*greater than or equal to 1"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 0",), isolated=True))
    with pytest.raises(SettingsError, match=r"indent-width.*less than or equal to 255"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 256",), isolated=True))


def test_invalid_indent_style_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\nindent-style = "spaces"\n', encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="indent-style"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_invalid_line_ending_lists_enum_options() -> None:
    with pytest.raises(SettingsError, match=r"line-ending.*\{'auto', 'lf', 'cr-lf', 'native'\}"):
        pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=('line-ending = "crlf"',), isolated=True))


def test_invalid_line_ending_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\nline-ending = "crlf"\n', encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="line-ending"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_invalid_indent_width_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nindent-width = 0\n", encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="indent-width"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_formatter_config_must_be_table(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool]\npydocfmt = false\n", encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match=r"\[tool\.pydocfmt\] section must be a table"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_nested_tool_table_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt.pydocfmt]\nline-length = 72\n", encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="pydocfmt"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_invalid_list_type_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = "*.py"\n', encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match="include"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_settings_include_pattern_shape_is_not_file_selection_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["src/"]\n', encoding="utf-8")
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load()

    assert config.include == ("src/",)


def test_empty_config_exclude_string_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\nexclude = [""]\n', encoding="utf-8")
        monkeypatch.chdir(root)
        with pytest.raises(SettingsError, match=r"exclude.*empty strings"):
            pydocformatter_settings.SETTINGS_SCHEMA.load()


def test_empty_cli_include_string_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.chdir(td)
        with pytest.raises(SettingsError, match=r"include.*empty strings"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(include=("",)))


def test_empty_cli_exclude_string_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.chdir(td)
        with pytest.raises(SettingsError, match=r"exclude.*empty strings"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides=CheckSettingsOverrides(exclude=("",)))


def test_explicit_pyproject_config_file_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pyproject.toml"
        config_path.write_text("[tool.pydocfmt]\nline-length = 99\nrespect-gitignore = false\n", encoding="utf-8")
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

    assert config.line_length == 99
    assert not config.respect_gitignore


def test_explicit_dedicated_config_file_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pydocfmt.toml"
        config_path.write_text('line-ending = "lf"\nselect = ["PCF"]\n', encoding="utf-8")
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

    assert config.line_ending is LineEnding.LF
    assert config.select == ("PCF",)


def test_explicit_non_pyproject_file_rejects_pyproject_style_table() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "config.toml"
        config_path.write_text("[tool.pydocfmt]\nline-length = 99\n", encoding="utf-8")

        with pytest.raises(SettingsError, match=r"unknown setting.*tool"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))


def test_inline_config_option_is_applied() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=('line-length = 101\nignore = ["PCF000"]',)))

    assert config.line_length == 101
    assert config.ignore == ("PCF000",)


def test_inline_config_options_override_config_files() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pydocfmt.toml"
        config_path.write_text("line-length = 90\n", encoding="utf-8")
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path), "line-length = 91")))

    assert config.line_length == 91


def test_command_line_overrides_override_inline_config_options() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(
        field_overrides=CheckSettingsOverrides(line_length=103), global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 102",))
    )

    assert config.line_length == 103


def test_load_accepts_argparse_namespace_overrides() -> None:
    args = argparse.Namespace(line_length=103, select=["PDF,PCF"], require_explicit=["PCF200, PDF003"], per_file_ignores=['{"tests/*.py" = ["PCF000"]}'])

    config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 102",)), args=args)

    assert config.line_length == 103
    assert config.select == ("PDF", "PCF")
    assert config.require_explicit == ("PCF200", "PDF003")
    assert config.per_file_ignores == (("tests/*.py", ("PCF000",)),)


def test_toml_map_cli_repeated_patterns_append_values() -> None:
    args = argparse.Namespace(per_file_ignores=['{"tests/*.py" = ["PDF200"], "src/*.py" = ["PDF106"]}', '{"tests/*.py" = ["PDF110"]}'])

    config = pydocformatter_settings.SETTINGS_SCHEMA.load(args=args)

    assert config.per_file_ignores == (("tests/*.py", ("PDF200", "PDF110")), ("src/*.py", ("PDF106",)))


def test_rule_selection_cli_comma_lists_strip_whitespace_as_documented_delta() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(args=argparse.Namespace(select=["PDF200, PDF110"]))

    assert config.select == ("PDF200", "PDF110")


def test_explicit_overrides_override_argparse_namespace_overrides() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(args=argparse.Namespace(line_length=102), field_overrides=CheckSettingsOverrides(line_length=103))

    assert config.line_length == 103


def test_isolated_ignores_auto_discovered_pyproject_config(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 72\n", encoding="utf-8")
        monkeypatch.chdir(root)
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))

    assert config.line_length == 88


def test_isolated_accepts_inline_config_options() -> None:
    config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 104",), isolated=True))

    assert config.line_length == 104


def test_isolated_rejects_explicit_config_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pydocfmt.toml"
        config_path.write_text("line-length = 105\n", encoding="utf-8")

        with pytest.raises(SettingsError, match="--config=PATH"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),), isolated=True))
