"""Cache ownership, cleanup, and quarantine boundary tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import pathlib
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cache.directory as cache_directory


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


def test_clean_cache_rejects_a_regular_file_root(tmp_path: Path) -> None:
    """Cleanup must never interpret a configured file as an owned directory."""
    root = tmp_path / "cache"
    root.write_text("user data", encoding="utf-8")

    with pytest.raises(cache_directory.CacheDirectoryError, match="not a regular directory"):
        cache_directory.clean_cache(root)

    assert root.read_text(encoding="utf-8") == "user data"


def test_clean_cache_rejects_an_untagged_empty_directory(tmp_path: Path) -> None:
    """Even an empty directory requires exact ownership before cleanup."""
    root = tmp_path / "cache"
    root.mkdir()

    with pytest.raises(cache_directory.CacheDirectoryError, match="untagged empty cache directory"):
        cache_directory.clean_cache(root)

    assert root.is_dir()


def test_clean_cache_reports_lock_contention_without_removing_data(tmp_path: Path) -> None:
    """A concurrent cache user must prevent cleanup rather than risk mutation."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    proof = layout.version_dir / "proof"
    proof.write_text("retained", encoding="utf-8")
    lock = cache_directory.mutation_lock(layout, timeout=1)

    with lock, pytest.raises(cache_directory.CacheDirectoryError, match=r"Timed out waiting.*cache lock"):
        cache_directory.clean_cache(layout.root, lock_timeout=0.001)

    assert proof.read_text(encoding="utf-8") == "retained"


def test_partial_cleanup_failure_reports_safe_retry_context(tmp_path: Path, mocker: MockerFixture) -> None:
    """Cleanup failures after a removal must say that retrying is safe."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    second = layout.root / "v2"
    second.mkdir()
    original_rmtree = cache_directory.shutil.rmtree

    def fail_second(path: Path) -> None:
        if path == second:
            raise OSError("device failure")
        original_rmtree(path)

    mocker.patch("pydocformatter.cache.directory.shutil.rmtree", side_effect=fail_second, autospec=True)

    with pytest.raises(cache_directory.CacheDirectoryError, match=r"device failure.*already removed 1 owned path.*rerunning.*safe"):
        cache_directory.clean_cache(layout.root)

    assert not layout.version_dir.exists()
    assert second.is_dir()


def test_cleanup_rejects_owned_version_names_that_are_not_directories(tmp_path: Path) -> None:
    """Version-like user files must not be deleted by recursive cleanup."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    cache_directory.shutil.rmtree(layout.version_dir)
    layout.version_dir.write_text("not a directory", encoding="utf-8")

    with pytest.raises(cache_directory.CacheDirectoryError, match="unexpected owned-version path"):
        cache_directory.clean_cache(layout.root)

    assert layout.version_dir.read_text(encoding="utf-8") == "not a directory"


def test_quarantine_pruning_is_inert_for_unowned_or_unversioned_roots(tmp_path: Path) -> None:
    """Retention must not touch quarantine-shaped files without the full owned layout."""
    unowned = cache_directory.cache_layout(tmp_path / "unowned")
    unowned.version_dir.mkdir(parents=True)
    candidate = unowned.version_dir / "cache.sqlite3.corrupt-1-1"
    candidate.write_text("user data", encoding="utf-8")

    cache_directory.prune_quarantine_files(unowned, max_count=0)

    assert candidate.read_text(encoding="utf-8") == "user data"

    owned = cache_directory.cache_layout(tmp_path / "owned")
    cache_directory.ensure_cache_layout(owned)
    cache_directory.shutil.rmtree(owned.version_dir)
    cache_directory.prune_quarantine_files(owned)
    assert not owned.version_dir.exists()


def test_quarantine_pruning_ignores_nonregular_candidates(tmp_path: Path, mocker: MockerFixture) -> None:
    """Retention must not unlink directories that merely resemble quarantine files."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    candidate = layout.version_dir / "cache.sqlite3.corrupt-1-1"
    candidate.mkdir()
    unlink = mocker.patch("pathlib.Path.unlink", autospec=True)

    cache_directory.prune_quarantine_files(layout, now=100, max_count=0)

    unlink.assert_not_called()
    assert candidate.is_dir()


def test_quarantine_pruning_swallows_enumeration_failures(tmp_path: Path, mocker: MockerFixture) -> None:
    """Best-effort retention must not disrupt a successful cache operation."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    original_iterdir = pathlib.Path.iterdir

    def fail_version_directory(path: Path) -> Iterator[Path]:
        if path == layout.version_dir:
            raise OSError("directory unavailable")
        return original_iterdir(path)

    mocker.patch("pathlib.Path.iterdir", side_effect=fail_version_directory, autospec=True)

    cache_directory.prune_quarantine_files(layout)


def test_quarantine_rejects_unknown_classifications(tmp_path: Path) -> None:
    """Callers cannot create quarantine files outside the fixed naming policy."""
    layout = cache_directory.cache_layout(tmp_path / "cache")

    with pytest.raises(ValueError, match="Unknown cache quarantine kind"):
        cache_directory.quarantine_database(layout, kind="unsafe")


def test_quarantine_without_a_database_is_a_safe_noop(tmp_path: Path) -> None:
    """Recovery may race with another process that already removed the database."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)

    assert cache_directory.quarantine_database(layout, kind="corrupt") is None


def test_quarantine_refuses_to_overwrite_an_existing_destination(tmp_path: Path) -> None:
    """Timestamp and process collisions must retain both the live and prior files."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    layout.database.write_text("live", encoding="utf-8")
    now = 123.0
    destination = layout.version_dir / f"cache.sqlite3.corrupt-{int(now)}-{os.getpid()}"
    destination.write_text("prior", encoding="utf-8")

    assert cache_directory.quarantine_database(layout, kind="corrupt", now=now) is None
    assert layout.database.read_text(encoding="utf-8") == "live"
    assert destination.read_text(encoding="utf-8") == "prior"


def test_quarantine_rolls_back_a_partial_database_group_move(tmp_path: Path, mocker: MockerFixture) -> None:
    """A sidecar move failure must restore the already moved main database."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    layout.database.write_text("database", encoding="utf-8")
    wal = Path(f"{layout.database}-wal")
    wal.write_text("wal", encoding="utf-8")
    original_replace = pathlib.Path.replace

    def fail_wal_move(source: Path, destination: Path) -> Path:
        if source == wal:
            raise OSError("sidecar unavailable")
        return original_replace(source, destination)

    mocker.patch("pathlib.Path.replace", side_effect=fail_wal_move, autospec=True)

    assert cache_directory.quarantine_database(layout, kind="corrupt", now=123) is None
    assert layout.database.read_text(encoding="utf-8") == "database"
    assert wal.read_text(encoding="utf-8") == "wal"
    assert not tuple(layout.version_dir.glob("cache.sqlite3.corrupt-123-*"))


def test_ensure_layout_rejects_nonregular_version_and_lock_paths(tmp_path: Path) -> None:
    """Owned path leaves must retain their expected filesystem types."""
    version_layout = cache_directory.cache_layout(tmp_path / "version-file")
    cache_directory.ensure_cache_layout(version_layout)
    version_layout.version_dir.rmdir()
    version_layout.version_dir.write_text("user data", encoding="utf-8")
    with pytest.raises(cache_directory.CacheDirectoryError, match="not a regular directory"):
        cache_directory.ensure_cache_layout(version_layout)

    lock_layout = cache_directory.cache_layout(tmp_path / "lock-directory")
    cache_directory.ensure_cache_layout(lock_layout)
    lock_layout.lock_file.mkdir()
    with pytest.raises(cache_directory.CacheDirectoryError, match="non-regular cache lock"):
        cache_directory.prepare_cache_root_for_lock(lock_layout)


def test_symlinked_marker_prevents_layout_claiming(tmp_path: Path) -> None:
    """Layout claiming must not follow or overwrite marker symlinks."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    layout.root.mkdir()
    external = tmp_path / "external"
    external.write_text("user data", encoding="utf-8")
    (layout.root / "CACHEDIR.TAG").symlink_to(external)

    with pytest.raises(cache_directory.CacheDirectoryError, match="Refusing to claim non-empty cache directory"):
        cache_directory.ensure_cache_layout(layout)

    assert external.read_text(encoding="utf-8") == "user data"


def test_malformed_marker_encoding_does_not_establish_ownership(tmp_path: Path) -> None:
    """Ownership requires a readable marker with exact UTF-8 content."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    layout.root.mkdir()
    (layout.root / "CACHEDIR.TAG").write_bytes(b"\xff")

    assert not cache_directory.cache_root_is_owned(layout.root)


def test_clean_cache_wraps_lock_operating_system_failures(tmp_path: Path, mocker: MockerFixture) -> None:
    """Lock setup failures must be reported as cache-specific operational errors."""
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    mocker.patch("pydocformatter.cache.directory.mutation_lock", side_effect=OSError("lock filesystem unavailable"), autospec=True)

    with pytest.raises(cache_directory.CacheDirectoryError, match=r"Unable to lock.*lock filesystem unavailable"):
        cache_directory.clean_cache(layout.root)
