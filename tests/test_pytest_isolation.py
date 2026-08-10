"""Downstream wiring checks for shared pytest CWD isolation."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    # Third-party imports
    import pytest


def test_unmarked_tests_use_project_specific_shared_guard(pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Check the configured poison, boundary, and writable temporary layer."""
    cwd = Path.cwd()
    boundary = cwd.parent
    temporary_root = boundary / "tmp"

    assert cwd.name == "cwd"
    assert pytestconfig.getini("la_dev_cwd_isolation_cleanup") == "pytest_retained"
    assert pytestconfig.getini("tmp_path_retention_policy") == "all"
    assert int(pytestconfig.getini("tmp_path_retention_count")) == 3
    assert boundary.parent == tmp_path_factory.getbasetemp()
    assert (cwd / "pyproject.toml").read_text(encoding="utf-8") == "[tool.pydocfmt\n"
    assert (boundary / "pyproject.toml").read_text(encoding="utf-8") == '[tool.pydocfmt]\ncache-dir = "tmp/.pydocfmt_cache"\n'
    assert {os.environ[name] for name in ("TMPDIR", "TEMP", "TMP")} == {str(temporary_root)}
    assert tempfile.tempdir is None
    with tempfile.TemporaryDirectory() as directory:
        assert Path(directory).parent == temporary_root
