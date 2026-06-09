"""Shared pytest fixtures providing test isolation for the whole suite."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

import pydocformatter.rules.collection  # noqa: Explicitly initialize the rule registry


@pytest.fixture(scope="session", autouse=True)
def isolated_test_root(tmp_path_factory: pytest.TempPathFactory) -> Generator[Path, None, None]:
    """Create a session-wide boundary for configuration and temporary files."""
    root = tmp_path_factory.mktemp("pydocformatter")
    (root / "pyproject.toml").write_text("[tool.pydocfmt]\n", encoding="utf-8")
    previous_tempdir = tempfile.tempdir
    temporary_directory_variables = ("TMPDIR", "TEMP", "TMP")
    previous_environment = {name: os.environ.get(name) for name in temporary_directory_variables}
    tempfile.tempdir = str(root)
    for name in temporary_directory_variables:
        os.environ[name] = str(root)
    try:
        yield root
    finally:
        tempfile.tempdir = previous_tempdir
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture(autouse=True)
def isolate_working_directory(isolated_test_root: Path) -> Generator[None, None, None]:
    """Run every test in its own working directory below the config boundary.

    The repository ships its own ``[tool.pydocfmt]`` table in ``pyproject.toml``, which the CLI auto-discovers from the
    current working directory. Without this fixture, tests that invoke the CLI (or otherwise resolve settings) from the
    repository root would silently inherit that configuration instead of the documented defaults. The session root
    provides an explicit empty configuration boundary, including for nested temporary directories and child processes,
    while the per-test directory prevents filesystem state from leaking between tests.
    """
    previous_cwd = os.getcwd()
    with tempfile.TemporaryDirectory(dir=isolated_test_root) as isolated_cwd:
        os.chdir(isolated_cwd)
        try:
            yield
        finally:
            os.chdir(previous_cwd)
