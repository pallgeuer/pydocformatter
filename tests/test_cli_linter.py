# Future imports
from __future__ import annotations

# Standard library imports
import json

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
from tests import cli_helpers


def test_pydocfmt_linter_prints_linter_table() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "linter"])

    assert result.exit_code == 0
    assert result.stdout == "PCF pydocformatter comment formatting\nPDF pydocformatter docstring formatting\n"


def test_pydocfmt_linter_prints_linter_json() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "linter", "--output-format", "json"])

    output = json.loads(result.stdout)
    assert result.exit_code == 0
    assert output == [
        {"prefix": "PCF", "name": "pydocformatter comment formatting", "url": "https://github.com/pallgeuer/pydocformatter"},
        {"prefix": "PDF", "name": "pydocformatter docstring formatting", "url": "https://github.com/pallgeuer/pydocformatter"},
    ]


def test_pydocfmt_linter_rejects_invalid_output_format() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "linter", "--output-format", "yaml"], expect_system_exit=True)

    assert result.exit_code == 2
    assert "invalid choice: 'yaml'" in result.stderr


def test_pydocfmt_linter_help_and_help_linter_print_linter_help() -> None:
    for argv in (["pydocfmt", "linter", "--help"], ["pydocfmt", "help", "linter"]):
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=argv[-1] == "--help")
        assert result.exit_code == 0
        assert "Usage: pydocfmt linter" in result.stdout
        assert "--output-format {text,json}" in result.stdout


def test_pydocfmt_help_lists_linter_command() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "--help"], expect_system_exit=True)

    assert result.exit_code == 0
    assert "linter" in result.stdout
