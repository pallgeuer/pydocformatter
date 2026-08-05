"""Downstream wiring checks for shared pytest CWD isolation."""

# Standard library imports
import os
import tempfile
from pathlib import Path


def test_unmarked_tests_use_project_specific_shared_guard() -> None:
    """Check the configured poison, boundary, and writable temporary layer."""
    cwd = Path.cwd()
    boundary = cwd.parent
    temporary_root = boundary / "tmp"

    assert cwd.name == "cwd"
    assert (cwd / "pyproject.toml").read_text(encoding="utf-8") == "[tool.pydocfmt\n"
    assert (boundary / "pyproject.toml").read_text(encoding="utf-8") == '[tool.pydocfmt]\ncache-dir = "tmp/.pydocfmt_cache"\n'
    assert {os.environ[name] for name in ("TMPDIR", "TEMP", "TMP")} == {str(temporary_root)}
    assert tempfile.tempdir is None
    with tempfile.TemporaryDirectory() as directory:
        assert Path(directory).parent == temporary_root
