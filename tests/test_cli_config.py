"""CLI config command tests."""

# Standard library imports
import json
import tempfile
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
from pydocformatter.cli import settings_check
from tests import cli_helpers


pytestmark = pytest.mark.isolated_cwd


def test_pydocfmt_config_lists_available_keys() -> None:
    argv = ["pydocfmt", "config"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml]


def test_pydocfmt_config_prints_option_details() -> None:
    argv = ["pydocfmt", "config", "line-length"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = result.stdout
    assert "Maximum line length for docstrings and comments." in output
    assert "Default value: 88" in output
    assert "Type: int" in output
    assert "Example usage:\n```toml\nline-length = 88\n```" in output


def test_pydocfmt_config_prints_option_json() -> None:
    argv = ["pydocfmt", "config", "--output-format", "json", "line-ending"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["doc"] == 'Line ending to use when rewriting files; one of "auto", "lf", "cr-lf", or "native".'
    assert output["default"] == '"auto"'
    assert output["value_type"] == '"auto" | "lf" | "cr-lf" | "native"'
    assert output["example"] == 'line-ending = "auto"'
    assert "scope" not in output
    assert "deprecated" not in output


def test_pydocfmt_config_prints_all_json() -> None:
    argv = ["pydocfmt", "config", "--output-format", "json"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert tuple(output) == tuple(definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml)
    assert output["line-length"]["default"] == "88"
    assert output["docstring-convention"]["default"] == '"pep257"'
    assert output["select"]["value_type"] == "list[str]"
    assert output["extension"]["default"] == "{}"
    assert output["extension"]["value_type"] == "dict[str, str]"
    assert output["per-file-ignores"]["value_type"] == "dict[str, list[str]]"


def test_pydocfmt_config_describes_custom_extension_mapping() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "config", "extension"])

    assert result.exit_code == 0
    assert "Default value: {}" in result.stdout
    assert "Type: dict[str, str]" in result.stdout
    assert '[tool.pydocfmt.extension]\nrpy = "python"\nmdx = "markdown"' in result.stdout


@pytest.mark.parametrize("setting", ["source-context", "docstring-missing-documentation"])
def test_pydocfmt_config_describes_markdown_language_defaults(setting: str) -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "config", setting])

    assert result.exit_code == 0
    assert "Sources assigned to Markdown default to" in result.stdout
    assert "matching per-file settings" in result.stdout


def test_pydocfmt_config_rejects_unknown_option() -> None:
    argv = ["pydocfmt", "config", "unknown-key"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Invalid value 'unknown-key'" in result.stderr


def test_pydocfmt_config_rejects_invalid_output_format() -> None:
    argv = ["pydocfmt", "config", "--output-format", "yaml"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=True)

    assert result.exit_code == 2
    assert "invalid choice: 'yaml'" in result.stderr


def test_pydocfmt_config_help_and_help_config_print_config_help() -> None:
    for argv in (["pydocfmt", "config", "--help"], ["pydocfmt", "help", "config"]):
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=argv[-1] == "--help")
        assert result.exit_code == 0
        assert "Usage: pydocfmt config" in result.stdout
        assert "--output-format {text,json}" in result.stdout


def test_pydocfmt_config_ignores_invalid_config_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["src/"]\n', encoding="utf-8")
        argv = ["pydocfmt", "config", "line-length"]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 0
    assert "Default value: 88" in result.stdout
    assert result.stderr == ""
