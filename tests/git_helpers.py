"""Shared git-related test helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import subprocess
from collections.abc import Callable
from pathlib import Path


def write_git_marker(root: Path) -> None:
    """Write a minimal git worktree marker in a temporary root.

    Args:
        root (Path): Temporary root that should be treated as a git worktree.
    """
    (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")


def fake_git_check_ignore_for_root(root: Path, ignored_paths: set[str]) -> Callable[..., subprocess.CompletedProcess[bytes]]:
    """Return a fake git check-ignore runner for a temporary root.

    Args:
        root (Path): Temporary worktree root expected in the git command.
        ignored_paths (set[str]): Relative paths that should be reported as ignored.

    Returns:
        Fake subprocess runner matching the git check-ignore call shape.
    """

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        expected_command = ["git", "-C", str(root), "check-ignore", "--stdin", "--no-index", "-z"]
        assert args[0] == expected_command
        stdin_bytes = kwargs["input"]
        assert isinstance(stdin_bytes, bytes)
        provided_paths = [path for path in stdin_bytes.decode("utf-8").split("\0") if path]
        ignored = [path for path in provided_paths if path in ignored_paths]
        stdout = ("\0".join(ignored) + ("\0" if ignored else "")).encode("utf-8")
        return subprocess.CompletedProcess(expected_command, 0 if ignored else 1, stdout=stdout, stderr=b"")

    return fake_run
