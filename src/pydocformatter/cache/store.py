"""Parent-process-only SQLite storage for persistent clean proofs."""

# Future imports
from __future__ import annotations

# Standard library imports
import time
import typing
import sqlite3
import contextlib
import dataclasses
from collections.abc import Iterable

# Third-party imports
import filelock

# First-party imports
from pydocformatter.cache import directory
from pydocformatter.cache.models import CACHE_SCHEMA_VERSION, DIGEST_SIZE, CleanProof


_BUSY_TIMEOUT_MS = 100
_LOOKUP_CHUNK_SIZE = 200
_PROOF_TTL_DAYS = 30
_LAST_PRUNE_KEY = "last-prune-day"
_ENGINE_STATE_PREFIX = "engine:"
_CLEAN_PROOF_COLUMNS = (
    ("engine_key", "BLOB", 1, 1),
    ("analysis_key", "BLOB", 1, 2),
    ("path_key", "TEXT", 1, 3),
    ("path_context_key", "BLOB", 1, 0),
    ("source_digest", "BLOB", 1, 0),
    ("source_size", "INTEGER", 1, 0),
    ("mtime_ns", "INTEGER", 0, 0),
    ("last_seen_day", "INTEGER", 1, 0),
)
_CACHE_STATE_COLUMNS = (("key", "TEXT", 1, 1), ("value", "INTEGER", 1, 0))


@dataclasses.dataclass(frozen=True)
class StoreFailure:
    """One explicitly reported best-effort store failure.

    Attributes:
        message (str): Debug description excluded from normal command output.
    """

    message: str


@dataclasses.dataclass(frozen=True)
class StoreLookupResult:
    """Validated lookup proofs and explicitly counted failures.

    Attributes:
        proofs (dict[tuple[bytes, bytes, str], CleanProof]): Valid proofs keyed by requested namespace identity.
        failures (tuple[StoreFailure, ...]): Malformed rows and store operations that failed.
    """

    proofs: dict[tuple[bytes, bytes, str], CleanProof]
    failures: tuple[StoreFailure, ...]


@dataclasses.dataclass(frozen=True)
class StoreCommitResult:
    """Successful proof writes and explicitly counted failures.

    Attributes:
        writes (int): Valid proof rows committed successfully.
        failures (tuple[StoreFailure, ...]): Validation, locking, recovery, or transaction failures.
    """

    writes: int
    failures: tuple[StoreFailure, ...]


class CacheStore:
    """Best-effort synchronous cache store confined to the parent process.

    Attributes:
        layout (directory.CacheLayout): Owned cache paths used by the store.
        busy_timeout_ms (int): Maximum SQLite lock wait in milliseconds before persistence is skipped.
    """

    def __init__(self, layout: directory.CacheLayout, *, busy_timeout_ms: int = _BUSY_TIMEOUT_MS) -> None:
        """Initialize a lazy cache store without creating or opening filesystem paths.

        Args:
            layout (directory.CacheLayout): Fixed owned paths for this store.
            busy_timeout_ms (int): Maximum SQLite lock wait before persistence is skipped.
        """
        self.layout = layout
        self.busy_timeout_ms = busy_timeout_ms
        self._disabled = False

    @property
    def disabled(self) -> bool:
        """Cache availability after best-effort failures.

        Returns:
            bool: Whether reads and writes are disabled for the remainder of the run.
        """
        return self._disabled

    def lookup(self, keys: Iterable[tuple[bytes, bytes, str]]) -> StoreLookupResult:
        """Load strictly validated candidate proofs without creating or mutating the store.

        Args:
            keys (Iterable[tuple[bytes, bytes, str]]): Engine, analysis, and lexical path identities to query.

        Returns:
            StoreLookupResult: Valid proofs and explicitly reported row or store failures.
        """
        ordered_keys = tuple(dict.fromkeys(keys))
        if self._disabled or not ordered_keys:
            return StoreLookupResult(proofs={}, failures=())
        if not directory.cache_root_is_owned(self.layout.root):
            return StoreLookupResult(proofs={}, failures=())
        if not self.layout.database.exists():
            return StoreLookupResult(proofs={}, failures=())
        connection: sqlite3.Connection | None = None
        try:
            directory.validate_existing_layout_paths(self.layout)
            connection = sqlite3.connect(f"{self.layout.database.as_uri()}?mode=ro", uri=True, timeout=self.busy_timeout_ms / 1000)
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
            if not _schema_is_supported(connection):
                return StoreLookupResult(proofs={}, failures=(StoreFailure("Unsupported cache database schema"),))
            proofs: dict[tuple[bytes, bytes, str], CleanProof] = {}
            failures: list[StoreFailure] = []
            for start in range(0, len(ordered_keys), _LOOKUP_CHUNK_SIZE):
                chunk = ordered_keys[start : start + _LOOKUP_CHUNK_SIZE]
                conditions = " OR ".join("(engine_key = ? AND analysis_key = ? AND path_key = ?)" for _ in chunk)
                parameters = tuple(value for key in chunk for value in key)
                rows = connection.execute(
                    f"SELECT engine_key, analysis_key, path_key, path_context_key, source_digest, source_size, mtime_ns, last_seen_day FROM clean_proofs WHERE {conditions}",  # ruff: ignore[hardcoded-sql-expression]
                    parameters,
                )
                for row in rows:
                    proof = _decode_proof_row(row)
                    if proof is not None:
                        proofs[proof.engine_key, proof.analysis_key, proof.path_key] = proof
                    else:
                        failures.append(StoreFailure("Discarded a malformed requested cache proof row"))
            return StoreLookupResult(proofs=proofs, failures=tuple(failures))
        except (OSError, sqlite3.Error) as error:
            return StoreLookupResult(proofs={}, failures=(StoreFailure(str(error)),))
        finally:
            if connection is not None:
                connection.close()

    def commit(self, *, touches: Iterable[tuple[bytes, bytes, str, int]], proofs: Iterable[CleanProof]) -> StoreCommitResult:
        """Transactionally apply hit touches and clean-proof upserts, returning the upsert count.

        Args:
            touches (Iterable[tuple[bytes, bytes, str, int]]): Proof namespace keys and UTC days requiring retention
                updates.
            proofs (Iterable[CleanProof]): Eligible clean proofs to insert or replace.

        Returns:
            StoreCommitResult: Successful proof writes and explicitly reported failures.
        """
        touch_rows = tuple(dict.fromkeys(touches))
        proof_rows = tuple(proofs)
        if self._disabled or (not touch_rows and not proof_rows):
            return StoreCommitResult(writes=0, failures=())
        try:
            directory.prepare_cache_root_for_lock(self.layout)
            lock = directory.mutation_lock(self.layout, timeout=self.busy_timeout_ms / 1000, allow_claimable=True)
            with lock:
                self._commit_locked(touch_rows, proof_rows)
            return StoreCommitResult(writes=len(proof_rows), failures=())
        except (OSError, sqlite3.Error, filelock.Timeout) as error:
            self._disabled = True
            return StoreCommitResult(writes=0, failures=(StoreFailure(str(error)),))

    def _commit_locked(self, touch_rows: tuple[tuple[bytes, bytes, str, int], ...], proof_rows: tuple[CleanProof, ...]) -> None:
        """Apply one transaction and close its connection while the caller holds the mutation lock."""
        connection: sqlite3.Connection | None = None
        try:
            directory.ensure_cache_layout(self.layout)
            connection = self._open_current_writable_database()
            today = utc_day()
            connection.execute("BEGIN IMMEDIATE")
            engine_days: dict[bytes, int] = {}
            for engine_key, analysis_key, path_key, last_seen_day in touch_rows:
                # Retention follows the latest observed wall-clock day even when the clock moves backward. Cache data is
                # disposable, so bounded cleanup is preferred over pinning a future timestamp.
                connection.execute(
                    "UPDATE clean_proofs SET last_seen_day = ? WHERE engine_key = ? AND analysis_key = ? AND path_key = ? AND last_seen_day != ?",
                    (last_seen_day, engine_key, analysis_key, path_key, last_seen_day),
                )
                engine_days[engine_key] = max(last_seen_day, engine_days.get(engine_key, last_seen_day))
            for proof in proof_rows:
                connection.execute(
                    "INSERT INTO clean_proofs (engine_key, analysis_key, path_key, path_context_key, source_digest, source_size, mtime_ns, last_seen_day) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (engine_key, analysis_key, path_key) DO UPDATE SET path_context_key = excluded.path_context_key, source_digest = excluded.source_digest, source_size = excluded.source_size, mtime_ns = excluded.mtime_ns, last_seen_day = excluded.last_seen_day",
                    (proof.engine_key, proof.analysis_key, proof.path_key, proof.path_context_key, proof.source_digest, proof.source_size, proof.mtime_ns, proof.last_seen_day),
                )
                engine_days[proof.engine_key] = max(proof.last_seen_day, engine_days.get(proof.engine_key, proof.last_seen_day))
            for engine_key, last_seen_day in engine_days.items():
                _touch_engine(connection, engine_key, last_seen_day)
            pruned = _prune_if_due(connection, today=today)
            connection.commit()
            if pruned:
                _cheap_maintenance(connection)
                directory.prune_quarantine_files(self.layout)
        except BaseException:
            if connection is not None:
                with contextlib.suppress(sqlite3.Error):
                    connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()

    def _open_current_writable_database(self) -> sqlite3.Connection:
        """Freshly validate, recover, or initialize the database while holding the mutation lock."""
        directory.validate_existing_layout_paths(self.layout)
        if not directory.cache_root_is_owned(self.layout.root):
            raise directory.CacheDirectoryError(f"Cache root lost exact pydocfmt ownership: {self.layout.root}")
        existed = self.layout.database.exists()
        if existed:
            connection: sqlite3.Connection | None = None
            try:
                connection = self._connect_writable()
                if _schema_is_supported(connection):
                    _set_preferred_journal_mode(connection)
                    supported_connection = connection
                    connection = None
                    return supported_connection
                _checkpoint_before_quarantine(connection)
            except sqlite3.DatabaseError as error:
                if not _looks_corrupt(error):
                    raise
                kind = "corrupt"
            else:
                kind = "incompatible"
            finally:
                if connection is not None:
                    connection.close()
            if directory.quarantine_database(self.layout, kind=kind) is None:
                raise directory.CacheDirectoryError(f"Unable to quarantine {kind} cache database: {self.layout.database}")
        connection = self._connect_writable()
        try:
            _initialize_schema(connection)
            _set_preferred_journal_mode(connection)
        except BaseException:
            connection.close()
            raise
        return connection

    def _connect_writable(self) -> sqlite3.Connection:
        """Open the current database with the configured short busy timeout."""
        connection = sqlite3.connect(self.layout.database, timeout=self.busy_timeout_ms / 1000)
        try:
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        except BaseException:
            connection.close()
            raise
        return connection


def utc_day(timestamp: float | None = None) -> int:
    """Return a UTC day number used only for retention and touch coalescing.

    Args:
        timestamp (float | None): Unix timestamp, or current wall-clock time by default.

    Returns:
        int: Whole UTC days since the Unix epoch.
    """
    if timestamp is None:
        timestamp = time.time()
    return int(timestamp // 86400)


def _initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the version-one schema in a new SQLite database."""
    connection.execute("PRAGMA auto_vacuum = INCREMENTAL")
    connection.execute(
        "CREATE TABLE clean_proofs (engine_key BLOB NOT NULL, analysis_key BLOB NOT NULL, path_key TEXT NOT NULL, path_context_key BLOB NOT NULL, source_digest BLOB NOT NULL, source_size INTEGER NOT NULL, mtime_ns INTEGER, last_seen_day INTEGER NOT NULL, PRIMARY KEY (engine_key, analysis_key, path_key)) WITHOUT ROWID"
    )
    connection.execute("CREATE TABLE cache_state (key TEXT PRIMARY KEY, value INTEGER NOT NULL) WITHOUT ROWID")
    connection.execute(f"PRAGMA user_version = {CACHE_SCHEMA_VERSION}")
    connection.commit()


def _checkpoint_before_quarantine(connection: sqlite3.Connection) -> None:
    """Checkpoint readable WAL contents before moving an incompatible database group."""
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()


def _set_preferred_journal_mode(connection: sqlite3.Connection) -> None:
    """Prefer WAL while retaining SQLite's rollback-journal fallback."""
    try:
        connection.execute("PRAGMA journal_mode = WAL").fetchone()
    except sqlite3.Error:
        with contextlib.suppress(sqlite3.Error):
            connection.execute("PRAGMA journal_mode = DELETE").fetchone()


def _schema_is_supported(connection: sqlite3.Connection) -> bool:
    """Return whether schema version and strict column shapes match this implementation."""
    user_version_row = connection.execute("PRAGMA user_version").fetchone()
    if user_version_row is None or type(user_version_row[0]) is not int or user_version_row[0] != CACHE_SCHEMA_VERSION:
        return False
    return _table_columns(connection, "clean_proofs") == _CLEAN_PROOF_COLUMNS and _table_columns(connection, "cache_state") == _CACHE_STATE_COLUMNS


def _table_columns(connection: sqlite3.Connection, table: str) -> tuple[tuple[str, str, int, int], ...]:
    """Return strict name, type, not-null, and primary-key metadata for one table."""
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    columns: list[tuple[str, str, int, int]] = []
    for row in rows:
        if len(row) < 6:
            return ()
        name, declared_type, not_null, primary_key = row[1], row[2], row[3], row[5]
        if not isinstance(name, str) or not isinstance(declared_type, str) or type(not_null) is not int or type(primary_key) is not int:
            return ()
        columns.append((name, declared_type.upper(), not_null, primary_key))
    return tuple(columns)


def _decode_proof_row(row: tuple[object, ...]) -> CleanProof | None:
    """Decode one SQLite row only when every field has the expected safe type and bounds."""
    if len(row) != 8:
        return None
    engine_key, analysis_key, path_key, path_context_key, digest, size, mtime_ns, last_seen_day = row
    try:
        return CleanProof(
            engine_key=typing.cast("bytes", engine_key),
            analysis_key=typing.cast("bytes", analysis_key),
            path_key=typing.cast("str", path_key),
            path_context_key=typing.cast("bytes", path_context_key),
            source_digest=typing.cast("bytes", digest),
            source_size=typing.cast("int", size),
            mtime_ns=typing.cast("int | None", mtime_ns),
            last_seen_day=typing.cast("int", last_seen_day),
        )
    except ValueError:
        return None


def _touch_engine(connection: sqlite3.Connection, engine_key: bytes, day: int) -> None:
    """Record the most recent day an engine namespace was inserted or reused."""
    connection.execute(
        "INSERT INTO cache_state (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value WHERE value != excluded.value", (f"{_ENGINE_STATE_PREFIX}{engine_key.hex()}", day)
    )


def _prune_if_due(connection: sqlite3.Connection, *, today: int) -> bool:
    """Prune stale proofs and engine namespaces at most once per UTC day."""
    row = connection.execute("SELECT value FROM cache_state WHERE key = ?", (_LAST_PRUNE_KEY,)).fetchone()
    if row is not None and type(row[0]) is int and row[0] == today:
        return False
    cutoff = today - _PROOF_TTL_DAYS
    stale_engine_rows = connection.execute("SELECT key FROM cache_state WHERE key LIKE ? AND value < ?", (f"{_ENGINE_STATE_PREFIX}%", cutoff)).fetchall()
    stale_engine_keys: list[bytes] = []
    for row in stale_engine_rows:
        if type(row[0]) is not str:
            continue
        try:
            engine_key = bytes.fromhex(row[0].removeprefix(_ENGINE_STATE_PREFIX))
        except ValueError:
            continue
        if len(engine_key) == DIGEST_SIZE:
            stale_engine_keys.append(engine_key)
    for engine_key in stale_engine_keys:
        connection.execute("DELETE FROM clean_proofs WHERE engine_key = ?", (engine_key,))
    connection.execute("DELETE FROM clean_proofs WHERE last_seen_day < ?", (cutoff,))
    connection.execute("DELETE FROM cache_state WHERE key LIKE ? AND value < ?", (f"{_ENGINE_STATE_PREFIX}%", cutoff))
    connection.execute("INSERT INTO cache_state (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value", (_LAST_PRUNE_KEY, today))
    return True


def _cheap_maintenance(connection: sqlite3.Connection) -> None:
    """Run bounded checkpoint and incremental-vacuum work after daily pruning."""
    try:
        connection.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
        connection.execute("PRAGMA incremental_vacuum(64)")
    except sqlite3.Error:
        pass


def _looks_corrupt(error: sqlite3.DatabaseError) -> bool:
    """Return whether SQLite reported a malformed or non-database file."""
    if isinstance(error, (sqlite3.ProgrammingError, sqlite3.IntegrityError)):
        return False
    error_code = getattr(error, "sqlite_errorcode", None)
    if type(error_code) is int and error_code & 0xFF in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}:
        return True
    message = str(error).lower()
    return "malformed" in message or "not a database" in message or "file is encrypted" in message
