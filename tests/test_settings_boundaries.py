"""Boundary tests for generic settings validation and serialization."""

# Future imports
from __future__ import annotations

# Standard library imports
import argparse
import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import pydocformatter.settings as settings_core
import pydocformatter.cli.settings_check as check_settings


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


def test_resolved_cli_definition_can_be_reused_without_losing_options() -> None:
    """Schema composition must preserve every resolved argparse option."""
    cli = settings_core.SettingCLIDefinition(
        flags=("-n", "--number"), action="append", choices=(1, 2), type=int, metavar="COUNT", value_kind=settings_core.SettingCLIValueKind.COMMA_LIST, show_default=False
    )

    definition = settings_core.SettingDefinition(field="number", value_type=int, group=check_settings.SettingsGroup.RUN, help="Number.", cli=cli)

    assert definition.cli == cli


def test_schema_format_omits_settings_unavailable_in_toml() -> None:
    """CLI-only settings must never leak into generated TOML."""

    @dataclasses.dataclass(frozen=True)
    class ExampleSettings:
        visible: int = 1
        secret: int = 2

    visible = settings_core.SettingDefinition(field="visible", value_type=int, group=check_settings.SettingsGroup.RUN, help="Visible.")
    secret = settings_core.SettingDefinition(field="secret", value_type=int, group=check_settings.SettingsGroup.RUN, help="Secret.", available_in_toml=False)
    schema = settings_core.SettingsSchema(
        settings_type=ExampleSettings, overrides_type=dict[str, object], group_type=check_settings.SettingsGroup, definitions=(visible, secret), table_path=("tool", "example")
    )

    assert schema.format(ExampleSettings()) == "[tool.example]\nvisible = 1\n"


def test_add_argument_distinguishes_unknown_and_cli_unavailable_settings() -> None:
    """Callers receive actionable errors for both invalid field categories."""
    parser = argparse.ArgumentParser()

    with pytest.raises(KeyError, match="unknown"):
        check_settings.SETTINGS_SCHEMA.add_argument(parser, check_settings.CheckSettings(), "unknown")
    with pytest.raises(ValueError, match=r"per_file_settings.*not available"):
        check_settings.SETTINGS_SCHEMA.add_argument(parser, check_settings.CheckSettings(), "per_file_settings")


@pytest.mark.parametrize("value", ["[]", "1", "'selectors'"])
def test_toml_map_cli_values_require_inline_tables(value: str) -> None:
    """Repeated map options must reject valid TOML values of the wrong shape."""
    args = argparse.Namespace(per_file_ignores=[value])

    with pytest.raises(settings_core.SettingsError, match="must be a TOML table"):
        check_settings.SETTINGS_SCHEMA.argument_overrides(args)


@pytest.mark.parametrize("value", ["py", "py:", ":python"])
def test_extension_cli_values_require_both_sides_of_the_mapping(value: str) -> None:
    """Malformed extension mappings must identify their required syntax."""
    args = argparse.Namespace(extension=[value])

    with pytest.raises(settings_core.SettingsError, match="EXT:LANGUAGE"):
        check_settings.SETTINGS_SCHEMA.argument_overrides(args)


@pytest.mark.parametrize(
    ("value", "expected"), [(True, "true"), (check_settings.LineEnding.CR_LF, '"cr-lf"'), ("source", '"source"'), (0.5, "0.5"), (("PDF", check_settings.LineEnding.LF), '["PDF", "lf"]'), (3, "3")]
)
def test_per_file_setting_values_serialize_as_valid_toml(value: object, expected: str) -> None:
    """Every supported resolved override type must retain its TOML meaning."""
    assert settings_core._format_resolved_setting_value(value) == expected


@pytest.mark.parametrize(
    ("validator", "value", "message"),
    [
        (settings_core.validate_bool, 1, "must be a boolean"),
        (settings_core.validate_string_list, ["valid", 1], "list of strings"),
        (settings_core.validate_multi_string_map, [], "table mapping"),
        (settings_core.validate_multi_string_map, {1: ["PDF"]}, "keys must be strings"),
        (settings_core.validate_multi_string_map, {"": ["PDF"]}, "keys must not be empty"),
    ],
)
def test_setting_validators_reject_ambiguous_container_values(validator: settings_core.SettingValidator[object], value: object, message: str) -> None:
    """Configuration type errors must be rejected before settings are applied."""
    with pytest.raises(settings_core.SettingsError, match=message):
        validator(value, "setting")


def test_numeric_validators_enforce_upper_bounds() -> None:
    """Maximum bounds are inclusive and reject larger integer and float values."""
    with pytest.raises(settings_core.SettingsError, match="less than or equal to 2"):
        settings_core.validate_int(max_value=2)(3, "count")
    with pytest.raises(settings_core.SettingsError, match=r"less than or equal to 0\.5"):
        settings_core.validate_float(max_value=0.5)(0.75, "ratio")


def test_unknown_setting_types_require_an_explicit_validator() -> None:
    """Custom setting types must not silently accept unchecked values."""
    with pytest.raises(TypeError, match="No default validator"):
        settings_core.SettingDefinition(field="path", value_type=Path, group=check_settings.SettingsGroup.RUN, help="Path.")


def test_toml_read_errors_include_the_source_path(tmp_path: Path, mocker: MockerFixture) -> None:
    """Operational configuration failures must retain actionable path context."""
    config_path = tmp_path / "config.toml"
    mocker.patch("builtins.open", side_effect=OSError("permission denied"), autospec=True)

    with pytest.raises(settings_core.SettingsError, match=f"Failed to read configuration file {config_path}.*permission denied"):
        settings_core._load_toml_file(str(config_path), required=True)


@pytest.mark.parametrize(
    ("config", "required", "message"),
    [
        ({"tool": "invalid"}, False, r"\[tool\] section must be a table"),
        ({"tool": {}}, True, r"Must contain \[tool\.pydocfmt\]"),
        ({"tool": {"pydocfmt": "invalid"}}, True, r"\[tool\.pydocfmt\] section must be a table"),
    ],
)
def test_nested_toml_table_lookup_reports_structural_errors(config: dict[str, object], required: bool, message: str) -> None:
    """Malformed and missing project tables must identify the failing table."""
    with pytest.raises(settings_core.SettingsError, match=message):
        settings_core._toml_section_at_table_path(config, path="pyproject.toml", table_path=("tool", "pydocfmt"), required=required)


@pytest.mark.parametrize(
    ("section", "message"),
    [
        ({"docstring": False}, "docstring must be a table"),
        ({"docstring": {"parse": {"nested": True}}}, "docstring-parse must not be a table"),
        ({"docstring-parse": True, "docstring": {"parse": False}}, "sets docstring-parse more than once"),
    ],
)
def test_prefixed_toml_tables_reject_ambiguous_shapes(section: dict[str, object], message: str) -> None:
    """Nested convenience tables must not overwrite or hide configuration."""
    with pytest.raises(settings_core.SettingsError, match=message):
        settings_core._flatten_prefixed_toml_setting_tables(section, prefixes=("docstring",), context="<config>")
