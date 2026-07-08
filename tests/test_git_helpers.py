"""Tests for shared git-related test helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
from pathlib import Path

# First-party imports
from tests import git_helpers


def test_fake_git_check_ignore_reports_matches(tmp_path: Path) -> None:
    fake_run = git_helpers.fake_git_check_ignore_for_root(tmp_path, {"skip.py"})

    process = fake_run(["git", "-C", str(tmp_path), "check-ignore", "--stdin", "--no-index", "-z"], input=b"keep.py\0skip.py\0")

    assert process.returncode == 0
    assert process.stdout == b"skip.py\0"
    assert process.stderr == b""


def test_fake_git_check_ignore_reports_no_matches(tmp_path: Path) -> None:
    fake_run = git_helpers.fake_git_check_ignore_for_root(tmp_path, {"skip.py"})

    process = fake_run(["git", "-C", str(tmp_path), "check-ignore", "--stdin", "--no-index", "-z"], input=b"keep.py\0")

    assert process.returncode == 1
    assert process.stdout == b""
    assert process.stderr == b""
