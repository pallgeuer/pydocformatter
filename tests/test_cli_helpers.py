"""Tests for shared CLI invocation helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import sys

# First-party imports
from tests import cli_helpers


def test_run_cli_restores_process_globals() -> None:
    original_argv = sys.argv
    original_stdin = sys.stdin

    def main() -> int:
        assert sys.argv == ["pydocfmt", "check", "-"]
        assert sys.stdin.read() == "source\n"
        print("stdout text")
        print("stderr text", file=sys.stderr)
        return 7

    result = cli_helpers.run_cli(main, ["pydocfmt", "check", "-"], stdin="source\n")

    assert result.exit_code == 7
    assert result.stdout == "stdout text\n"
    assert result.stderr == "stderr text\n"
    assert sys.argv is original_argv
    assert sys.stdin is original_stdin
