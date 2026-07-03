"""Shared pytest fixtures providing test isolation for the whole suite."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolated_test_root(tmp_path_factory: pytest.TempPathFactory) -> Generator[Path, None, None]:
    """Create a session-wide boundary for configuration and temporary files.

    Args:
        tmp_path_factory: Pytest factory used to allocate one temporary root shared by the test session.

    Yields:
        Directory containing neutral configuration and all per-test temporary working directories.
    """
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


@pytest.fixture(scope="session")
def guarded_test_cwd(isolated_test_root: Path) -> Generator[Path, None, None]:
    """Create a poisoned default CWD for tests that did not request isolation.

    Args:
        isolated_test_root: Session boundary under which the guarded directory is created.

    Yields:
        Read-only directory containing malformed local configuration for catching accidental CWD-dependent behavior.
    """
    cwd = isolated_test_root / "guarded-cwd"
    cwd.mkdir()
    config = cwd / "pyproject.toml"
    config.write_text("[tool.pydocfmt\n", encoding="utf-8")
    config.chmod(0o400)
    cwd.chmod(0o500)
    try:
        yield cwd
    finally:
        cwd.chmod(0o700)
        config.chmod(0o600)


@pytest.fixture(autouse=True)
def guard_working_directory(request: pytest.FixtureRequest, isolated_test_root: Path, guarded_test_cwd: Path) -> Generator[None, None, None]:
    """Run tests from a guarded CWD unless they explicitly request isolation.

    The repository ships its own ``[tool.pydocfmt]`` table in ``pyproject.toml``, which the CLI auto-discovers from the
    current working directory. Unmarked tests run from a read-only directory with malformed local configuration, so
    accidental default-CWD writes or config discovery fail loudly. The read-only guard depends on filesystem permissions
    and is bypassed when tests run as root; the malformed config and leaked-CWD checks remain permission-independent.
    Tests marked ``isolated_cwd`` or requesting the ``isolated_cwd`` fixture keep the previous behavior of running in a
    fresh writable directory below the session boundary.

    Args:
        request: Current pytest request, used to detect whether the test opted into a writable isolated CWD.
        isolated_test_root: Session boundary that owns writable per-test directories.
        guarded_test_cwd: Poisoned fallback working directory for tests without explicit isolation.
    """
    previous_cwd = os.getcwd()
    use_isolated_cwd = request.node.get_closest_marker("isolated_cwd") is not None or "isolated_cwd" in request.fixturenames
    if use_isolated_cwd:
        with tempfile.TemporaryDirectory(dir=isolated_test_root) as test_cwd:
            os.chdir(test_cwd)
            try:
                yield
            finally:
                os.chdir(previous_cwd)
        return

    os.chdir(guarded_test_cwd)
    try:
        yield
    finally:
        leaked_cwd = Path.cwd()
        os.chdir(previous_cwd)
        if leaked_cwd.resolve() != guarded_test_cwd.resolve():
            pytest.fail(f"Test leaked working directory change: expected {guarded_test_cwd}, got {leaked_cwd}")


@pytest.fixture
def isolated_cwd(guard_working_directory: None) -> Path:
    """Return the fresh writable working directory requested by this test.

    Args:
        guard_working_directory: Autouse fixture dependency that switches the process into the isolated directory before
            this fixture is read.

    Returns:
        Current working directory allocated for the requesting test.
    """
    del guard_working_directory
    return Path.cwd()
