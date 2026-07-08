"""Shared CLI test invocation helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import sys
import contextlib
import dataclasses
from collections.abc import Callable, Sequence
from io import StringIO
from pathlib import Path

# Third-party imports
import pytest


@dataclasses.dataclass(frozen=True)
class CliRunResult:
    """Captured result of an in-process CLI invocation.

    Attributes:
        exit_code (int): Integer exit status returned by the CLI or carried by an expected ``SystemExit``.
        stdout (str): Text emitted to standard output.
        stderr (str): Text emitted to standard error.
    """

    exit_code: int
    stdout: str
    stderr: str


def run_cli(main: Callable[[], int], argv: Sequence[str], *, cwd: Path | None = None, stdin: str | None = None, expect_system_exit: bool = False) -> CliRunResult:
    """Run a CLI entry point with patched process streams and arguments.

    Args:
        main (Callable[[], int]): CLI entry point to invoke in-process.
        argv (Sequence[str]): Argument vector to expose through ``sys.argv``.
        cwd (Path | None): Working directory to use for the invocation.
        stdin (str | None): Text to expose through ``sys.stdin``.
        expect_system_exit (bool): Whether a ``SystemExit`` from the entry point is an expected result.

    Returns:
        Captured exit status and output streams.
    """
    stdout = StringIO()
    stderr = StringIO()
    with contextlib.ExitStack() as stack:
        monkeypatch = stack.enter_context(pytest.MonkeyPatch.context())
        if cwd is not None:
            stack.enter_context(contextlib.chdir(cwd))
        monkeypatch.setattr(sys, "argv", list(argv))
        if stdin is not None:
            monkeypatch.setattr(sys, "stdin", StringIO(stdin))
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            if expect_system_exit:
                try:
                    exit_code = main()
                except SystemExit as exc:
                    exit_code = _system_exit_code(exc)
            else:
                exit_code = main()
    return CliRunResult(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def _system_exit_code(exc: SystemExit) -> int:
    """Return the integer process status carried by ``SystemExit``.

    Args:
        exc (SystemExit): Exception raised by a CLI parser or entry point.

    Returns:
        Integer process status encoded by the exception.
    """
    if exc.code is None:
        return 0
    if isinstance(exc.code, int):
        return exc.code
    raise AssertionError(f"Expected integer SystemExit code, got {exc.code!r}")
