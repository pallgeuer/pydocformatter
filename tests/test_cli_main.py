"""Top-level CLI command tests."""

# Standard library imports
import re
import tempfile
from collections.abc import Callable
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
from tests import cli_helpers


pytestmark = pytest.mark.isolated_cwd


def _assert_help_ignores_invalid_config(main: Callable[[], int], program: str) -> None:
    """Assert that help output is available despite invalid local config."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["src/"]\n', encoding="utf-8")
        argv = [program, "--help"]
        result = cli_helpers.run_cli(main, argv, cwd=root, expect_system_exit=True)

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert result.stderr == ""


def test_pydocfmt_help_ignores_invalid_config() -> None:
    _assert_help_ignores_invalid_config(pydocfmt_cli.main, "pydocfmt")


def test_pydocfmt_help_check_prints_check_help() -> None:
    argv = ["pydocfmt", "help", "check"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert "Usage: pydocfmt check" in result.stdout


def test_pydocfmt_version_flag_and_command_print_version() -> None:
    outputs = []
    for argv in (["pydocfmt", "--version"], ["pydocfmt", "version"]):
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)
        assert result.exit_code == 0
        outputs.append(result.stdout)

    assert outputs[0] == outputs[1]
    assert re.search(r"^pydocfmt \d+\.\d+\.\d+\n$", outputs[0])


def test_pydocfmt_without_command_exits_with_usage_error() -> None:
    argv = ["pydocfmt"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 2
    assert "Usage: pydocfmt" in result.stderr


def test_pydocfmt_top_level_check_flag_is_rejected() -> None:
    argv = ["pydocfmt", "--check"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=True)

    assert result.exit_code == 2
    assert "unrecognized arguments: --check" in result.stderr
