"""Cache directory resolution, ownership, creation, and cleanup."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import re
import stat
import time
import shutil
import pathlib
import operator
import contextlib
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import filelock

# First-party imports
import pydocformatter.settings as settings_core


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.cli.settings_check import CheckSettings


_CACHE_TAG_NAME = "CACHEDIR.TAG"
_CACHE_TAG_CONTENT = "Signature: 8a477f597d28d172789f06886806bc55\n# This file is a cache directory tag created by pydocfmt.\n"
_GITIGNORE_NAME = ".gitignore"
_GITIGNORE_CONTENT = "*\n"
_VERSION_DIRECTORY = "v1"
_DATABASE_NAME = "cache.sqlite3"
_LOCK_NAME = ".pydocfmt.lock"
_OWNED_VERSION_RE = re.compile(r"^v[0-9]+$")
_KNOWN_QUARANTINE_RE = re.compile(r"^(cache\.sqlite3\.(?:corrupt|incompatible)-[0-9]+-[0-9]+)(?:-(wal|shm))?$")


class CacheDirectoryError(OSError):
    """Raised when a cache path cannot be used or safely cleaned."""


@dataclasses.dataclass(frozen=True)
class CacheLayout:
    """Owned paths below one configured cache root.

    Attributes:
        root (pathlib.Path): Configured cache root that owns the cache tag.
        version_dir (pathlib.Path): Version-specific pydocfmt-owned directory.
        database (pathlib.Path): SQLite clean-proof database path.
        lock_file (pathlib.Path): Stable root-level cross-process mutation lock.
    """

    root: pathlib.Path
    version_dir: pathlib.Path
    database: pathlib.Path
    lock_file: pathlib.Path


@dataclasses.dataclass(frozen=True)
class CleanupResult:
    """Result of deleting only known pydocfmt-owned cache children.

    Attributes:
        root (pathlib.Path): Configured cache root that was inspected.
        removed_paths (tuple[pathlib.Path, ...]): Owned version directories removed.
    """

    root: pathlib.Path
    removed_paths: tuple[pathlib.Path, ...]


def cache_directory_for_profile(profile: settings_core.SettingsProfile[CheckSettings]) -> pathlib.Path:
    """Resolve the configured cache directory with default project-root semantics.

    Args:
        profile (settings_core.SettingsProfile[CheckSettings]): Current-working-directory settings profile controlling
            cache location.

    Returns:
        pathlib.Path: Normalized absolute cache root.
    """
    configured = profile.settings.cache_dir
    if os.path.isabs(configured):
        return pathlib.Path(os.path.abspath(os.path.normpath(configured)))
    base = profile.project_root if profile.priority_for_field("cache_dir") == settings_core.DEFAULT_SOURCE_PRIORITY else profile.base_for_field("cache_dir")
    return pathlib.Path(os.path.abspath(os.path.normpath(os.path.join(base, configured))))


def cache_layout(cache_dir: str | os.PathLike[str]) -> CacheLayout:
    """Return the fixed versioned layout below a configured cache directory.

    Args:
        cache_dir (str | os.PathLike[str]): Configured cache root.

    Returns:
        CacheLayout: Root, version directory, and database paths.
    """
    root = pathlib.Path(cache_dir)
    version_dir = root / _VERSION_DIRECTORY
    return CacheLayout(root=root, version_dir=version_dir, database=version_dir / _DATABASE_NAME, lock_file=root / _LOCK_NAME)


def validate_existing_layout_paths(layout: CacheLayout) -> None:
    """Reject symlinked cache roots, version directories, or database leaves.

    Args:
        layout (CacheLayout): Cache paths to validate without creating them.

    Raises:
        CacheDirectoryError: If an owned layout path is a symlink.
    """
    for label, path in (("cache root", layout.root), ("cache version directory", layout.version_dir), ("cache database", layout.database), ("cache lock", layout.lock_file)):
        if path.is_symlink():
            raise CacheDirectoryError(f"Refusing symlinked {label}: {path}")


def ensure_cache_layout(layout: CacheLayout) -> None:
    """Create the owned cache layout and marker files with restrictive directory modes.

    Args:
        layout (CacheLayout): Cache paths to create and claim.

    Raises:
        CacheDirectoryError: If the paths cannot be created or safely claimed.
    """
    prepare_cache_root_for_lock(layout)
    _write_marker_if_missing(layout.root / _CACHE_TAG_NAME, _CACHE_TAG_CONTENT)
    _write_marker_if_missing(layout.root / _GITIGNORE_NAME, _GITIGNORE_CONTENT)
    _verify_cache_tag(layout.root)
    _validate_regular_leaf_if_present(layout.lock_file, label="cache lock")
    _ensure_directory(layout.version_dir)


def prepare_cache_root_for_lock(layout: CacheLayout) -> None:
    """Create only the root needed for locking and reject unclaimable existing contents.

    Args:
        layout (CacheLayout): Cache paths whose root should be prepared.

    Raises:
        CacheDirectoryError: If the root cannot be created or safely claimed.
    """
    validate_existing_layout_paths(layout)
    if layout.root.exists() and not cache_root_is_owned(layout.root) and not _cache_root_is_claimable(layout):
        raise CacheDirectoryError(f"Refusing to claim non-empty cache directory without the expected pydocfmt ownership tag: {layout.root}")
    _ensure_directory(layout.root)
    _validate_regular_leaf_if_present(layout.lock_file, label="cache lock")


def cache_root_is_owned(root: pathlib.Path) -> bool:
    """Return whether a non-symlinked directory has the exact pydocfmt cache tag.

    Args:
        root (pathlib.Path): Candidate cache root.

    Returns:
        bool: Whether the directory carries the exact ownership marker.
    """
    if root.is_symlink() or not root.is_dir():
        return False
    tag = root / _CACHE_TAG_NAME
    try:
        tag_stat = tag.lstat()
        if not stat.S_ISREG(tag_stat.st_mode):
            return False
        return tag.read_text(encoding="utf-8") == _CACHE_TAG_CONTENT
    except (OSError, UnicodeError):
        return False


def mutation_lock(layout: CacheLayout, *, timeout: float, allow_claimable: bool = False) -> filelock.FileLock:
    """Return the stable native lock coordinating all cache mutations.

    Args:
        layout (CacheLayout): Owned cache layout containing the lock path.
        timeout (float): Maximum seconds to wait for the lock.
        allow_claimable (bool): Whether an empty or bootstrap-lock-only root may be locked before initial ownership.

    Returns:
        filelock.FileLock: Native lock configured to retain its regular lock file.
    """
    if not cache_root_is_owned(layout.root) and not (allow_claimable and _cache_root_is_claimable(layout)):
        _verify_cache_tag(layout.root)
    _validate_regular_leaf_if_present(layout.lock_file, label="cache lock")
    return filelock.FileLock(layout.lock_file, timeout=timeout, mode=0o600, fallback_to_soft=False, preserve_lock_file=True)


def clean_cache(cache_dir: str | os.PathLike[str], *, lock_timeout: float = 5) -> CleanupResult:
    """Remove only pydocfmt version directories from a tagged cache root.

    Args:
        cache_dir (str | os.PathLike[str]): Configured cache root to clean.
        lock_timeout (float): Maximum seconds to wait for another cache mutation.

    Returns:
        CleanupResult: Owned children removed from the retained root.

    Raises:
        CacheDirectoryError: If the root or an owned child cannot be verified safely.
    """
    layout = cache_layout(cache_dir)
    try:
        root_stat = layout.root.lstat()
    except FileNotFoundError:
        return CleanupResult(root=layout.root, removed_paths=())
    except OSError as error:
        raise CacheDirectoryError(f"Unable to inspect cache root {layout.root}: {error}") from error
    if stat.S_ISLNK(root_stat.st_mode):
        raise CacheDirectoryError(f"Refusing symlinked cache root: {layout.root}")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise CacheDirectoryError(f"Cache root is not a regular directory: {layout.root}")
    try:
        _verify_cache_tag(layout.root)
    except CacheDirectoryError as error:
        try:
            empty = not any(layout.root.iterdir())
        except OSError:
            empty = False
        if empty:
            raise CacheDirectoryError(f"Refusing to clean an untagged empty cache directory because cleanup requires exact pydocfmt ownership: {layout.root}") from error
        raise
    try:
        lock = mutation_lock(layout, timeout=lock_timeout)
        with lock:
            return _clean_owned_cache(layout)
    except filelock.Timeout as error:
        raise CacheDirectoryError(f"Timed out waiting for the pydocfmt cache lock: {layout.lock_file}") from error
    except OSError as error:
        raise CacheDirectoryError(f"Unable to lock pydocfmt cache {layout.root}: {error}") from error


def _clean_owned_cache(layout: CacheLayout) -> CleanupResult:
    """Remove verified version directories while the mutation lock is held."""
    _verify_cache_tag(layout.root)
    removed: list[pathlib.Path] = []
    try:
        children = sorted(layout.root.iterdir(), key=lambda path: path.name)
    except OSError as error:
        raise CacheDirectoryError(f"Unable to enumerate cache root {layout.root}: {error}") from error
    for child in children:
        if _OWNED_VERSION_RE.fullmatch(child.name):
            if child.is_symlink() or not child.is_dir():
                raise CacheDirectoryError(_cleanup_failure_message(f"Refusing unexpected owned-version path: {child}", removed))
            try:
                shutil.rmtree(child)
            except OSError as error:
                raise CacheDirectoryError(_cleanup_failure_message(f"Unable to remove owned cache directory {child}: {error}", removed)) from error
            removed.append(child)
    return CleanupResult(root=layout.root, removed_paths=tuple(removed))


def _cleanup_failure_message(message: str, removed: list[pathlib.Path]) -> str:
    """Add safe-retry context when cleanup already removed owned paths."""
    if not removed:
        return message
    return f"{message} Cleanup had already removed {len(removed)} owned path(s); rerunning the command is safe."


def prune_quarantine_files(layout: CacheLayout, *, now: float | None = None, max_count: int = 3, max_age_days: int = 30) -> None:
    """Bound known database quarantine files by age and count without touching unknown paths.

    Args:
        layout (CacheLayout): Cache paths containing version-specific quarantine files.
        now (float | None): Current Unix timestamp, or real wall-clock time by default.
        max_count (int): Maximum newest quarantine files to retain.
        max_age_days (int): Maximum quarantine age in days.
    """
    try:
        if not cache_root_is_owned(layout.root):
            return
        if not layout.version_dir.is_dir() or layout.version_dir.is_symlink():
            return
        if now is None:
            now = time.time()
        groups: dict[str, list[tuple[pathlib.Path, float]]] = {}
        for path in layout.version_dir.iterdir():
            match = _KNOWN_QUARANTINE_RE.fullmatch(path.name)
            if match is None:
                continue
            path_stat = path.lstat()
            if not stat.S_ISREG(path_stat.st_mode):
                continue
            groups.setdefault(match.group(1), []).append((path, path_stat.st_mtime))
        ordered_groups = sorted(((max(mtime for _, mtime in entries), tuple(path for path, _ in entries)) for entries in groups.values()), key=operator.itemgetter(0), reverse=True)
        cutoff = now - max_age_days * 86400
        for index, (newest_mtime, paths) in enumerate(ordered_groups):
            if index >= max_count or newest_mtime < cutoff:
                for path in paths:
                    path.unlink()
    except OSError:
        return


def quarantine_database(layout: CacheLayout, *, kind: str, now: float | None = None) -> pathlib.Path | None:
    """Move a malformed owned database to one bounded non-executable quarantine path.

    Args:
        layout (CacheLayout): Owned database layout.
        kind (str): Quarantine classification, either `corrupt` or `incompatible`.
        now (float | None): Current Unix timestamp used in the quarantine name.

    Returns:
        pathlib.Path | None: New quarantine path, or None if no safe move occurred.

    Raises:
        ValueError: If `kind` is unsupported.
    """
    if kind not in {"corrupt", "incompatible"}:
        raise ValueError(f"Unknown cache quarantine kind: {kind}")
    try:
        validate_existing_layout_paths(layout)
        _verify_cache_tag(layout.root)
        _validate_database_group(layout)
        if not layout.database.exists():
            return None
        if now is None:
            now = time.time()
        quarantine = layout.version_dir / f"{_DATABASE_NAME}.{kind}-{int(now)}-{os.getpid()}"
        moves = [(layout.database, quarantine)]
        for suffix in ("-wal", "-shm"):
            source = pathlib.Path(f"{layout.database}{suffix}")
            if source.exists():
                moves.append((source, pathlib.Path(f"{quarantine}{suffix}")))
        if any(destination.exists() or destination.is_symlink() for _, destination in moves):
            return None
        completed: list[tuple[pathlib.Path, pathlib.Path]] = []
        try:
            for source, destination in moves:
                source.replace(destination)
                completed.append((source, destination))
        except OSError:
            for source, destination in reversed(completed):
                with contextlib.suppress(OSError):
                    destination.replace(source)
            return None
        prune_quarantine_files(layout, now=now)
    except (OSError, ValueError):
        return None
    else:
        return quarantine


def _ensure_directory(path: pathlib.Path) -> None:
    """Create one directory with user-only mode or validate an existing directory."""
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        if path.is_symlink() or not path.is_dir():
            raise CacheDirectoryError(f"Cache path is not a regular directory: {path}") from None
    except OSError as error:
        raise CacheDirectoryError(str(error)) from error


def _write_marker_if_missing(path: pathlib.Path, content: str) -> None:
    """Create one fixed marker without replacing existing content."""
    if path.is_symlink():
        raise CacheDirectoryError(f"Refusing symlinked cache marker: {path}")
    try:
        with path.open("x", encoding="utf-8", newline="") as marker:
            marker.write(content)
    except FileExistsError:
        if not path.is_file():
            raise CacheDirectoryError(f"Cache marker is not a regular file: {path}") from None
    except OSError as error:
        raise CacheDirectoryError(str(error)) from error


def _verify_cache_tag(root: pathlib.Path) -> None:
    """Require the exact pydocfmt ownership tag before destructive owned-path work."""
    tag = root / _CACHE_TAG_NAME
    try:
        tag_stat = tag.lstat()
        if not stat.S_ISREG(tag_stat.st_mode):
            raise CacheDirectoryError(f"Cache tag is not a regular file: {tag}")
        content = tag.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CacheDirectoryError(f"Unable to read pydocfmt cache tag at {tag}: {error}") from error
    if content != _CACHE_TAG_CONTENT:
        raise CacheDirectoryError(f"Refusing cache directory without the expected pydocfmt ownership tag: {root}")


def _validate_regular_leaf_if_present(path: pathlib.Path, *, label: str) -> None:
    """Reject an existing leaf unless it is a non-symlinked regular file."""
    try:
        path_stat = path.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise CacheDirectoryError(f"Unable to inspect {label} {path}: {error}") from error
    if not stat.S_ISREG(path_stat.st_mode):
        raise CacheDirectoryError(f"Refusing non-regular {label}: {path}")


def _validate_database_group(layout: CacheLayout) -> None:
    """Require every existing live SQLite group member to be a regular file."""
    for path in (layout.database, pathlib.Path(f"{layout.database}-wal"), pathlib.Path(f"{layout.database}-shm")):
        _validate_regular_leaf_if_present(path, label="cache database file")


def _cache_root_is_claimable(layout: CacheLayout) -> bool:
    """Return whether an unowned root is empty apart from the regular bootstrap lock."""
    if layout.root.is_symlink() or not layout.root.is_dir():
        return False
    try:
        children = tuple(layout.root.iterdir())
    except OSError:
        return False
    if not children:
        return True
    return children == (layout.lock_file,) and layout.lock_file.is_file() and not layout.lock_file.is_symlink()
