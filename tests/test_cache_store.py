"""Tests for persistent cache directory ownership and SQLite storage."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import sys
import time
import typing
import sqlite3
import subprocess
import dataclasses
import concurrent.futures
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cache.store as cache_store
import pydocformatter.cache.directory as cache_directory
from pydocformatter.cache.models import CleanProof


if typing.TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


def _digest(value: int) -> bytes:
    """Return one valid distinguishable digest."""
    return bytes([value]) * 32


def _proof(index: int, *, path: str | None = None, analysis: int = 2, day: int | None = None) -> CleanProof:
    """Return a valid clean proof for store tests."""
    if day is None:
        day = cache_store.utc_day()
    return CleanProof(
        engine_key=_digest(1),
        analysis_key=_digest(analysis),
        path_key=path or f"path-{index}",
        path_context_key=_digest(3),
        source_digest=_digest(4 + index),
        source_size=10 + index,
        mtime_ns=100 + index,
        last_seen_day=day,
    )


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"engine_key": b"short"}, "engine key"),
        ({"analysis_key": bytearray(_digest(2))}, "analysis key"),
        ({"path_key": ""}, "path key"),
        ({"path_context_key": b"short"}, "path context key"),
        ({"source_digest": b"short"}, "source digest"),
        ({"source_size": -1}, "source size"),
        ({"source_size": True}, "source size"),
        ({"mtime_ns": "100"}, "modification time"),
        ({"last_seen_day": -1}, "last-seen day"),
        ({"last_seen_day": False}, "last-seen day"),
    ],
)
def test_clean_proof_rejects_malformed_fields_at_construction(updates: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        dataclasses.replace(_proof(0), **typing.cast("typing.Any", updates))


def _store(tmp_path: Path, **kwargs: int) -> cache_store.CacheStore:
    """Return a store below a test cache root."""
    return cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"), **kwargs)


def test_missing_database_is_empty_without_creating_directory(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)

    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs == {}
    assert not store.layout.root.exists()


def test_first_clean_upsert_creates_owned_layout_schema_and_row(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)

    assert store.commit(touches=(), proofs=(proof,)).writes == 1

    assert (store.layout.root / "CACHEDIR.TAG").read_text(encoding="utf-8") == "Signature: 8a477f597d28d172789f06886806bc55\n# This file is a cache directory tag created by pydocfmt.\n"
    assert (store.layout.root / ".gitignore").read_text(encoding="utf-8") == "*\n"
    assert store.layout.version_dir.stat().st_mode & 0o077 == 0
    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs == {(proof.engine_key, proof.analysis_key, proof.path_key): proof}
    with sqlite3.connect(store.layout.database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM clean_proofs").fetchone() == (1,)
        assert connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall() == [("cache_state",), ("clean_proofs",)]


def test_settings_namespaces_keep_separate_proofs_for_one_path(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _proof(0, path="module.py", analysis=2)
    second = _proof(1, path="module.py", analysis=5)

    assert store.commit(touches=(), proofs=(first, second)).writes == 2
    found = store.lookup(((first.engine_key, first.analysis_key, first.path_key), (second.engine_key, second.analysis_key, second.path_key))).proofs

    assert found[first.engine_key, first.analysis_key, first.path_key] == first
    assert found[second.engine_key, second.analysis_key, second.path_key] == second


def test_dirty_mismatch_does_not_delete_an_older_proof(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)
    store.commit(touches=(), proofs=(proof,))

    store.commit(touches=(), proofs=())

    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs[proof.engine_key, proof.analysis_key, proof.path_key] == proof


def test_hit_touch_changes_last_seen_at_most_once_per_day(tmp_path: Path) -> None:
    store = _store(tmp_path)
    today = cache_store.utc_day()
    proof = _proof(0, day=today)
    store.commit(touches=(), proofs=(proof,))
    key = (proof.engine_key, proof.analysis_key, proof.path_key)

    store.commit(touches=((*key, today + 1),), proofs=())
    store.commit(touches=((*key, today + 1),), proofs=())

    assert store.lookup((key,)).proofs[key].last_seen_day == today + 1


def test_hit_touch_moves_future_retention_day_back_to_current_wall_clock(tmp_path: Path) -> None:
    store = _store(tmp_path)
    today = cache_store.utc_day()
    proof = _proof(0, day=today + 100)
    store.commit(touches=(), proofs=(proof,))
    key = (proof.engine_key, proof.analysis_key, proof.path_key)

    store.commit(touches=((*key, today),), proofs=())

    assert store.lookup((key,)).proofs[key].last_seen_day == today


def test_ttl_pruning_removes_old_rows_and_preserves_recent_rows(tmp_path: Path) -> None:
    store = _store(tmp_path)
    today = cache_store.utc_day()
    old = _proof(0, day=today - 31)
    recent = _proof(1, day=today)

    store.commit(touches=(), proofs=(old, recent))
    found = store.lookup(((old.engine_key, old.analysis_key, old.path_key), (recent.engine_key, recent.analysis_key, recent.path_key))).proofs

    assert (old.engine_key, old.analysis_key, old.path_key) not in found
    assert found[recent.engine_key, recent.analysis_key, recent.path_key] == recent


def test_invalid_digest_row_is_ignored_without_affecting_valid_rows(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)
    store.commit(touches=(), proofs=(proof,))
    with sqlite3.connect(store.layout.database) as connection:
        connection.execute(
            "INSERT INTO clean_proofs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (b"short", proof.analysis_key, "bad.py", proof.path_context_key, proof.source_digest, proof.source_size, None, proof.last_seen_day),
        )

    lookup = store.lookup(((b"short", proof.analysis_key, "bad.py"), (proof.engine_key, proof.analysis_key, proof.path_key)))
    found = lookup.proofs

    assert (b"short", proof.analysis_key, "bad.py") not in found
    assert found[proof.engine_key, proof.analysis_key, proof.path_key] == proof
    assert len(lookup.failures) == 1


def test_malformed_requested_path_context_is_reported_as_a_store_failure(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)
    store.commit(touches=(), proofs=(proof,))
    with sqlite3.connect(store.layout.database) as connection:
        connection.execute("UPDATE clean_proofs SET path_context_key = ? WHERE engine_key = ? AND analysis_key = ? AND path_key = ?", (b"short", proof.engine_key, proof.analysis_key, proof.path_key))

    lookup = store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),))

    assert lookup.proofs == {}
    assert len(lookup.failures) == 1


@pytest.mark.parametrize("database_bytes", [b"random bytes", b"SQLite format 3\x00truncated"])
def test_corrupt_database_is_quarantined_and_recreated(tmp_path: Path, database_bytes: bytes) -> None:
    store = _store(tmp_path)
    cache_directory.ensure_cache_layout(store.layout)
    store.layout.database.write_bytes(database_bytes)
    proof = _proof(0)

    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs == {}
    assert store.commit(touches=(), proofs=(proof,)).writes == 1
    assert tuple(store.layout.version_dir.glob("cache.sqlite3.corrupt-*-*"))
    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs[proof.engine_key, proof.analysis_key, proof.path_key] == proof


@pytest.mark.parametrize("schema_kind", ["version", "missing-table", "wrong-column"])
def test_incompatible_schema_is_replaced_on_next_write(tmp_path: Path, schema_kind: str) -> None:
    store = _store(tmp_path)
    cache_directory.ensure_cache_layout(store.layout)
    with sqlite3.connect(store.layout.database) as connection:
        if schema_kind == "version":
            connection.execute("PRAGMA user_version = 99")
        elif schema_kind == "missing-table":
            connection.execute("PRAGMA user_version = 1")
        else:
            connection.execute("CREATE TABLE clean_proofs (wrong INTEGER)")
            connection.execute("CREATE TABLE cache_state (key TEXT PRIMARY KEY, value INTEGER NOT NULL) WITHOUT ROWID")
            connection.execute("PRAGMA user_version = 1")
    proof = _proof(0)

    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs == {}
    assert store.commit(touches=(), proofs=(proof,)).writes == 1
    assert tuple(store.layout.version_dir.glob("cache.sqlite3.incompatible-*-*"))
    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs[proof.engine_key, proof.analysis_key, proof.path_key] == proof


def test_stale_incompatible_lookup_cannot_replace_a_fresh_database(tmp_path: Path) -> None:
    stale_store = _store(tmp_path)
    cache_directory.ensure_cache_layout(stale_store.layout)
    with sqlite3.connect(stale_store.layout.database) as connection:
        connection.execute("PRAGMA user_version = 99")
    stale_lookup = stale_store.lookup(((_digest(1), _digest(2), "module.py"),))
    fresh_proof = _proof(0, path="fresh.py")
    stale_proof = _proof(1, path="stale.py")
    fresh_store = cache_store.CacheStore(stale_store.layout)

    assert stale_lookup.failures
    assert fresh_store.commit(touches=(), proofs=(fresh_proof,)).writes == 1
    assert stale_store.commit(touches=(), proofs=(stale_proof,)).writes == 1

    found = fresh_store.lookup(((fresh_proof.engine_key, fresh_proof.analysis_key, fresh_proof.path_key), (stale_proof.engine_key, stale_proof.analysis_key, stale_proof.path_key))).proofs
    assert found[fresh_proof.engine_key, fresh_proof.analysis_key, fresh_proof.path_key] == fresh_proof
    assert found[stale_proof.engine_key, stale_proof.analysis_key, stale_proof.path_key] == stale_proof


def test_quarantine_moves_wal_and_shm_with_committed_wal_only_data(tmp_path: Path) -> None:
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    script = "import os, sqlite3, sys; c = sqlite3.connect(sys.argv[1]); c.execute('PRAGMA journal_mode = WAL'); c.execute('PRAGMA wal_autocheckpoint = 0'); c.execute('CREATE TABLE clean_proofs (value TEXT)'); c.execute('CREATE TABLE cache_state (key TEXT)'); c.execute('PRAGMA user_version = 99'); c.execute(\"INSERT INTO clean_proofs VALUES ('from-wal')\"); c.commit(); os._exit(0)"
    subprocess.run([sys.executable, "-c", script, str(layout.database)], check=True, shell=False)  # noqa: S603

    assert Path(f"{layout.database}-wal").is_file()
    quarantine = cache_directory.quarantine_database(layout, kind="incompatible")

    assert quarantine is not None
    assert Path(f"{quarantine}-wal").is_file()
    with sqlite3.connect(quarantine) as connection:
        assert connection.execute("SELECT value FROM clean_proofs").fetchall() == [("from-wal",)]


def test_database_lock_degrades_persistence_without_escaping(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _proof(0)
    store.commit(touches=(), proofs=(first,))
    locker = sqlite3.connect(store.layout.database)
    locker.execute("BEGIN IMMEDIATE")
    locked_store = cache_store.CacheStore(store.layout, busy_timeout_ms=1)
    try:
        commit = locked_store.commit(touches=(), proofs=(_proof(1),))
    finally:
        locker.rollback()
        locker.close()

    assert locked_store.disabled
    assert commit.writes == 0
    assert commit.failures
    assert store.lookup(((first.engine_key, first.analysis_key, first.path_key),)).proofs[first.engine_key, first.analysis_key, first.path_key] == first


def test_mutation_lock_timeout_degrades_persistence_without_escaping(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.commit(touches=(), proofs=(_proof(0),))
    locked_store = cache_store.CacheStore(store.layout, busy_timeout_ms=1)
    lock = cache_directory.mutation_lock(store.layout, timeout=1)

    with lock:
        commit = locked_store.commit(touches=(), proofs=(_proof(1),))

    assert commit.writes == 0
    assert commit.failures
    assert locked_store.disabled


def test_failed_commit_rolls_back_and_closes_connection_before_releasing_mutation_lock(tmp_path: Path, mocker: MockerFixture) -> None:
    store = _store(tmp_path)
    events: list[str] = []

    class RecordingLock:
        def __enter__(self) -> None:
            events.append("lock-enter")

        def __exit__(self, *args: object) -> None:
            del args
            events.append("lock-exit")

    connection = mocker.Mock(spec=sqlite3.Connection)
    connection.execute.side_effect = sqlite3.OperationalError("forced failure")
    connection.rollback.side_effect = lambda: events.append("rollback")
    connection.close.side_effect = lambda: events.append("close")
    mocker.patch("pydocformatter.cache.store.directory.prepare_cache_root_for_lock", autospec=True)
    mocker.patch("pydocformatter.cache.store.directory.ensure_cache_layout", autospec=True)
    mocker.patch("pydocformatter.cache.store.directory.mutation_lock", return_value=RecordingLock(), autospec=True)
    mocker.patch.object(store, "_open_current_writable_database", return_value=connection)

    commit = store.commit(touches=(), proofs=(_proof(0),))

    assert commit.writes == 0
    assert commit.failures
    assert events == ["lock-enter", "rollback", "close", "lock-exit"]


def test_disk_full_simulation_degrades_without_escaping(tmp_path: Path, mocker: MockerFixture) -> None:
    store = _store(tmp_path)
    mocker.patch("pydocformatter.cache.store.sqlite3.connect", side_effect=sqlite3.OperationalError("database or disk is full"), autospec=True)

    commit = store.commit(touches=(), proofs=(_proof(0),))
    assert commit.writes == 0
    assert store.disabled
    assert tuple(failure.message for failure in commit.failures) == ("database or disk is full",)


def test_failed_corruption_quarantine_disables_store(tmp_path: Path, mocker: MockerFixture) -> None:
    store = _store(tmp_path)
    cache_directory.ensure_cache_layout(store.layout)
    store.layout.database.write_bytes(b"not a database")
    mocker.patch("pydocformatter.cache.directory.quarantine_database", return_value=None, autospec=True)

    assert store.lookup(((_digest(1), _digest(2), "module.py"),)).proofs == {}
    commit = store.commit(touches=(), proofs=(_proof(0),))
    assert commit.writes == 0
    assert commit.failures
    assert store.disabled


@pytest.mark.parametrize(("kind", "database_bytes"), [("corrupt", b"not a database"), ("incompatible", b"SQLite format 3\x00unrelated")])
def test_unowned_database_and_sidecars_are_untouched_by_quarantine(tmp_path: Path, kind: str, database_bytes: bytes) -> None:
    layout = cache_directory.cache_layout(tmp_path / "cache")
    layout.version_dir.mkdir(parents=True)
    layout.database.write_bytes(database_bytes)
    sidecars = tuple(Path(f"{layout.database}{suffix}") for suffix in ("-wal", "-shm"))
    for index, sidecar in enumerate(sidecars):
        sidecar.write_bytes(f"sidecar-{index}".encode())
    original = {path: path.read_bytes() for path in (layout.database, *sidecars)}

    assert cache_directory.quarantine_database(layout, kind=kind) is None

    assert {path: path.read_bytes() for path in original} == original
    assert not tuple(layout.version_dir.glob(f"cache.sqlite3.{kind}-*-*"))


def test_unowned_corrupt_store_lookup_misses_without_mutating_database(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.layout.version_dir.mkdir(parents=True)
    store.layout.database.write_bytes(b"not a database")
    original = store.layout.database.read_bytes()

    lookup = store.lookup(((_digest(1), _digest(2), "module.py"),))

    assert lookup.proofs == {}
    assert lookup.failures == ()
    assert not store.disabled
    assert store.layout.database.read_bytes() == original
    assert not tuple(store.layout.version_dir.glob("cache.sqlite3.corrupt-*-*"))


def test_lookup_requires_exact_ownership_even_for_a_valid_database(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)
    store.commit(touches=(), proofs=(proof,))
    (store.layout.root / "CACHEDIR.TAG").unlink()

    lookup = store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),))

    assert lookup.proofs == {}
    assert lookup.failures == ()


def test_unowned_incompatible_store_is_not_replaced_on_commit(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.layout.version_dir.mkdir(parents=True)
    with sqlite3.connect(store.layout.database) as connection:
        connection.execute("CREATE TABLE unrelated (value INTEGER)")
        connection.execute("PRAGMA user_version = 99")
    original = store.layout.database.read_bytes()

    assert store.lookup(((_digest(1), _digest(2), "module.py"),)).proofs == {}
    commit = store.commit(touches=(), proofs=(_proof(0),))

    assert store.disabled
    assert commit.writes == 0
    assert commit.failures
    assert store.layout.database.read_bytes() == original
    assert not tuple(store.layout.version_dir.glob("cache.sqlite3.incompatible-*-*"))


@pytest.mark.parametrize("error", [sqlite3.ProgrammingError("database disk image is malformed"), sqlite3.IntegrityError("file is encrypted")])
def test_non_corruption_database_errors_never_quarantine(tmp_path: Path, mocker: MockerFixture, error: sqlite3.DatabaseError) -> None:
    store = _store(tmp_path)
    cache_directory.ensure_cache_layout(store.layout)
    store.layout.database.write_bytes(b"preserve")
    quarantine = mocker.spy(cache_directory, "quarantine_database")
    mocker.patch("pydocformatter.cache.store.sqlite3.connect", side_effect=error, autospec=True)

    lookup = store.lookup(((_digest(1), _digest(2), "module.py"),))

    assert lookup.proofs == {}
    assert lookup.failures
    assert not store.disabled
    assert store.layout.database.read_bytes() == b"preserve"
    quarantine.assert_not_called()


@pytest.mark.parametrize("error_code", [sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_CORRUPT | 0x100, sqlite3.SQLITE_NOTADB])
def test_corruption_classifier_uses_sqlite_base_error_codes(error_code: int) -> None:
    error = sqlite3.DatabaseError("opaque database failure")
    error.sqlite_errorcode = error_code

    assert cache_store._looks_corrupt(error)


def test_engine_retention_is_touched_once_per_engine_with_maximum_day(tmp_path: Path, mocker: MockerFixture) -> None:
    store = _store(tmp_path)
    first_engine = _digest(1)
    second_engine = _digest(9)
    first = _proof(0, day=10)
    second = _proof(1, day=12)
    third = dataclasses.replace(_proof(2, day=7), engine_key=second_engine)
    touch_engine = mocker.spy(cache_store, "_touch_engine")

    assert store.commit(touches=((first_engine, _digest(2), "old", 11),), proofs=(first, second, third)).writes == 3

    assert touch_engine.call_count == 2
    assert {(call.args[1], call.args[2]) for call in touch_engine.call_args_list} == {(first_engine, 12), (second_engine, 7)}


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory permission semantics")
def test_read_only_version_directory_degrades_without_escaping(tmp_path: Path) -> None:
    store = _store(tmp_path)
    cache_directory.ensure_cache_layout(store.layout)
    store.layout.version_dir.chmod(0o500)
    try:
        commit = store.commit(touches=(), proofs=(_proof(0),))
    finally:
        store.layout.version_dir.chmod(0o700)

    assert store.disabled
    assert commit.writes == 0
    assert commit.failures


def test_two_concurrent_writers_leave_valid_rows(tmp_path: Path) -> None:
    initial = _store(tmp_path)
    initial.commit(touches=(), proofs=(_proof(0),))
    first = _proof(1)
    second = _proof(2)

    def write(proof: CleanProof) -> int:
        return cache_store.CacheStore(initial.layout, busy_timeout_ms=1000).commit(touches=(), proofs=(proof,)).writes

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        writes = tuple(executor.map(write, (first, second)))

    assert writes == (1, 1)
    found = initial.lookup(((first.engine_key, first.analysis_key, first.path_key), (second.engine_key, second.analysis_key, second.path_key))).proofs
    assert found[first.engine_key, first.analysis_key, first.path_key] == first
    assert found[second.engine_key, second.analysis_key, second.path_key] == second


def test_rolled_back_writer_leaves_the_previous_transaction_readable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)
    store.commit(touches=(), proofs=(proof,))
    connection = sqlite3.connect(store.layout.database)
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("DELETE FROM clean_proofs")
    connection.close()

    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs[proof.engine_key, proof.analysis_key, proof.path_key] == proof


def test_killed_writer_leaves_the_previous_transaction_readable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proof = _proof(0)
    store.commit(touches=(), proofs=(proof,))
    ready = tmp_path / "transaction-ready"
    script = "import pathlib, sqlite3, sys, time; connection = sqlite3.connect(sys.argv[1]); connection.execute('BEGIN IMMEDIATE'); connection.execute('DELETE FROM clean_proofs'); pathlib.Path(sys.argv[2]).write_text('ready', encoding='utf-8'); time.sleep(30)"
    process = subprocess.Popen([sys.executable, "-c", script, str(store.layout.database), str(ready)], shell=False)  # noqa: S603
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
        process.kill()
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert store.lookup(((proof.engine_key, proof.analysis_key, proof.path_key),)).proofs[proof.engine_key, proof.analysis_key, proof.path_key] == proof


def test_nonempty_untagged_root_is_never_claimed(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    (root / "unknown.txt").write_text("user data", encoding="utf-8")

    with pytest.raises(cache_directory.CacheDirectoryError, match="Refusing to claim"):
        cache_directory.ensure_cache_layout(cache_directory.cache_layout(root))


def test_cleanup_refuses_unknown_and_symlinked_roots(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown"
    unknown.mkdir()
    with pytest.raises(cache_directory.CacheDirectoryError, match="exact pydocfmt ownership"):
        cache_directory.clean_cache(unknown)

    owned = tmp_path / "owned"
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(owned))
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(owned, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    with pytest.raises(cache_directory.CacheDirectoryError, match="symlinked"):
        cache_directory.clean_cache(alias)

    broken = tmp_path / "broken"
    broken.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(cache_directory.CacheDirectoryError, match="symlinked"):
        cache_directory.clean_cache(broken)


def test_symlinked_cache_tag_never_establishes_ownership(tmp_path: Path) -> None:
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    tag = layout.root / "CACHEDIR.TAG"
    external_tag = tmp_path / "external-tag"
    external_tag.write_bytes(tag.read_bytes())
    tag.unlink()
    try:
        tag.symlink_to(external_tag)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    assert not cache_directory.cache_root_is_owned(layout.root)
    with pytest.raises(cache_directory.CacheDirectoryError, match="regular file"):
        cache_directory.clean_cache(layout.root)


def test_cleanup_removes_only_owned_paths_and_keeps_root(tmp_path: Path) -> None:
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    (layout.root / "v2").mkdir()
    quarantine = layout.root / "cache.sqlite3.corrupt-1-2"
    quarantine.write_text("", encoding="utf-8")
    unknown = layout.root / "keep.txt"
    unknown.write_text("user data", encoding="utf-8")

    result = cache_directory.clean_cache(layout.root)

    assert result.removed_paths == (layout.version_dir, layout.root / "v2")
    assert layout.root.is_dir()
    assert quarantine.is_file()
    assert unknown.read_text(encoding="utf-8") == "user data"
    assert (layout.root / "CACHEDIR.TAG").is_file()


def test_quarantine_retention_prunes_complete_groups(tmp_path: Path) -> None:
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    groups = []
    for timestamp in range(1, 4):
        base = layout.version_dir / f"cache.sqlite3.corrupt-{timestamp}-1"
        wal = Path(f"{base}-wal")
        base.write_bytes(b"main")
        wal.write_bytes(b"wal")
        os.utime(base, (timestamp, timestamp))
        os.utime(wal, (timestamp, timestamp))
        groups.append((base, wal))

    cache_directory.prune_quarantine_files(layout, now=10, max_count=1, max_age_days=30)

    assert all(path.exists() for path in groups[-1])
    assert all(not path.exists() for group in groups[:-1] for path in group)


def test_quarantine_retention_samples_each_candidate_with_one_lstat(tmp_path: Path, mocker: MockerFixture) -> None:
    layout = cache_directory.cache_layout(tmp_path / "cache")
    cache_directory.ensure_cache_layout(layout)
    quarantine = layout.version_dir / "cache.sqlite3.corrupt-1-1"
    quarantine.write_bytes(b"broken")
    calls = 0
    real_lstat = Path.lstat

    def counting_lstat(path: Path) -> os.stat_result:
        nonlocal calls
        if path == quarantine:
            calls += 1
        return real_lstat(path)

    mocker.patch.object(Path, "lstat", side_effect=counting_lstat, autospec=True)

    cache_directory.prune_quarantine_files(layout, now=10, max_count=3, max_age_days=30)

    assert quarantine.is_file()
    assert calls == 1


def test_symlinked_version_or_database_leaf_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    layout = cache_directory.cache_layout(root)
    try:
        layout.version_dir.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    with pytest.raises(cache_directory.CacheDirectoryError, match="symlinked cache version"):
        cache_directory.validate_existing_layout_paths(layout)
