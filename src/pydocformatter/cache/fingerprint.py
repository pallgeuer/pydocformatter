"""Deterministic cache fingerprints and source hashing."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import sys
import enum
import json
import math
import stat
import hashlib
import pathlib
import operator
import platform
import dataclasses
import importlib.metadata
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

# First-party imports
import pydocformatter
from pydocformatter.cache.models import CACHE_PROTOCOL_VERSION, CACHE_SCHEMA_VERSION, AnalysisFingerprint, EngineFingerprint


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules_selection import SelectedRule
    from pydocformatter.source_path import SourcePathContext


_PACKAGE_DIGEST_LABEL = b"pydocfmt-package-source-v2\0"
_PACKAGE_ARTIFACT_DIGEST_LABEL = b"pydocfmt-package-artifact-v1\0"
_CANONICAL_DIGEST_LABEL = b"pydocfmt-canonical-v1\0"
_ANALYSIS_ENCODING_VERSION = 1


class CacheFingerprintError(RuntimeError):
    """Raised when a required cache identity cannot be established safely."""


def canonical_primitive(value: Any, *, project_root: str | os.PathLike[str] | None = None) -> Any:
    """Convert supported cache input values to explicit deterministic JSON primitives.

    Args:
        value (Any): Cache identity value to encode.
        project_root (str | os.PathLike[str] | None): Root used to relativize contained paths.

    Returns:
        Any: Tagged JSON-compatible primitive representation.

    Raises:
        TypeError: If the value type has no canonical cache encoding.
        ValueError: If a float is non-finite.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Canonical cache floats must be finite")
        return ["float", value.hex()]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, enum.Enum):
        return canonical_primitive(value.value, project_root=project_root)
    if isinstance(value, os.PathLike):
        return canonical_path(value, project_root=project_root)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return [
            "dataclass",
            f"{type(value).__module__}.{type(value).__qualname__}",
            [[field.name, canonical_primitive(getattr(value, field.name), project_root=project_root)] for field in dataclasses.fields(value)],
        ]
    if isinstance(value, list):
        return ["list", [canonical_primitive(item, project_root=project_root) for item in value]]
    if isinstance(value, tuple):
        return ["tuple", [canonical_primitive(item, project_root=project_root) for item in value]]
    if isinstance(value, frozenset):
        encoded = [canonical_primitive(item, project_root=project_root) for item in value]
        return ["frozenset", sorted(encoded, key=_canonical_json)]
    if isinstance(value, Mapping):
        encoded_items = [[canonical_primitive(key, project_root=project_root), canonical_primitive(item, project_root=project_root)] for key, item in value.items()]
        return ["mapping", sorted(encoded_items, key=lambda item: _canonical_json(item[0]))]
    raise TypeError(f"Unsupported canonical cache value: {type(value).__name__}")


def canonical_path(path: str | os.PathLike[str], *, project_root: str | os.PathLike[str] | None) -> list[str]:
    """Return a tagged normalized path, relative to the project root when contained by it.

    Args:
        path (str | os.PathLike[str]): Path spelling to normalize.
        project_root (str | os.PathLike[str] | None): Root used to identify relocatable contained paths.

    Returns:
        list[str]: Tagged relative or absolute path representation.
    """
    path_string = os.fspath(path)
    if not os.path.isabs(path_string):
        return ["relative", _forward_path(os.path.normpath(path_string))]

    absolute = _normalize_absolute_path(path_string)
    if project_root is not None:
        root = _normalize_absolute_path(project_root)
        return list(_canonical_absolute_path(absolute, root))
    return ["absolute", _forward_path(absolute)]


def canonical_bytes(value: Any, *, project_root: str | os.PathLike[str] | None = None) -> bytes:
    """Serialize supported cache input as canonical UTF-8 JSON bytes.

    Args:
        value (Any): Cache identity value to serialize.
        project_root (str | os.PathLike[str] | None): Root used to relativize contained paths.

    Returns:
        bytes: Deterministic ASCII-compatible JSON bytes.
    """
    return _canonical_json(canonical_primitive(value, project_root=project_root)).encode("utf-8")


def canonical_digest(value: Any, *, project_root: str | os.PathLike[str] | None = None) -> bytes:
    """Return a domain-separated SHA-256 digest of canonical cache input.

    Args:
        value (Any): Cache identity value to hash.
        project_root (str | os.PathLike[str] | None): Root used to relativize contained paths.

    Returns:
        bytes: Fixed-length canonical identity digest.
    """
    digest = hashlib.sha256()
    digest.update(_CANONICAL_DIGEST_LABEL)
    digest.update(canonical_bytes(value, project_root=project_root))
    return digest.digest()


def analysis_settings_key(identity: tuple[tuple[str, object], ...]) -> bytes:
    """Return the effective direct-analysis settings fingerprint.

    Args:
        identity (tuple[tuple[str, object], ...]): Schema-ordered effective setting names and normalized values that
            determine clean analysis.

    Returns:
        bytes: Canonical direct-analysis settings digest.
    """
    return canonical_digest(identity)


def selected_rules_key(selected_rules: tuple[SelectedRule, ...]) -> bytes:
    """Return the final path-specific selected-rule fingerprint.

    Args:
        selected_rules (tuple[SelectedRule, ...]): Rules after path-specific selection is fully resolved.

    Returns:
        bytes: Canonical selected-rule digest.
    """
    return canonical_digest(tuple(selected.rule.code.tag for selected in selected_rules))


def analysis_fingerprint(identity: tuple[tuple[str, object], ...], selected_rules: tuple[SelectedRule, ...]) -> tuple[AnalysisFingerprint, bytes]:
    """Return the semantic clean-analysis fingerprint model and digest.

    Args:
        identity (tuple[tuple[str, object], ...]): Effective direct-analysis settings identity.
        selected_rules (tuple[SelectedRule, ...]): Final ordered path-specific rules.

    Returns:
        tuple[AnalysisFingerprint, bytes]: Structured analysis identity and its canonical digest.
    """
    fingerprint = AnalysisFingerprint(encoding_version=_ANALYSIS_ENCODING_VERSION, analysis_settings_key=analysis_settings_key(identity), selected_rules_key=selected_rules_key(selected_rules))
    return fingerprint, canonical_digest(fingerprint)


class PathFingerprintBuilder:
    """Construct file path identities with invocation-local canonical-parent reuse."""

    def __init__(self, project_root: str | os.PathLike[str]) -> None:
        """Pre-normalize one project root and initialize an empty parent encoding memo.

        Args:
            project_root (str | os.PathLike[str]): Root used for relocatable path encoding.
        """
        self._project_root = _normalize_absolute_path(project_root)
        self._canonical_parents: dict[str, tuple[str, str]] = {}

    def fingerprints(self, context: SourcePathContext) -> tuple[str, bytes]:
        """Return the lexical path key and semantic path-context digest together.

        Args:
            context (SourcePathContext): Precomputed normalized absolute path semantics.

        Returns:
            tuple[str, bytes]: Canonical lexical path key and semantic path-context digest.
        """
        lexical_path = self._canonical_path(context.lexical_path)
        resolved_path = lexical_path if context.resolved_path == context.lexical_path else self._canonical_path(context.resolved_path)
        lexical_primitive = list(lexical_path)
        resolved_primitive = list(resolved_path)
        return _canonical_json(lexical_primitive), _path_context_key(context, lexical_path=lexical_primitive, resolved_path=resolved_primitive)

    def _canonical_path(self, path: str) -> tuple[str, str]:
        """Encode one normalized absolute context path through its memoized parent."""
        if not os.path.isabs(path):
            raise ValueError(f"Path fingerprint builder requires an absolute normalized path: {path}")
        if path == self._project_root:
            return "project-relative", "."
        parent, name = os.path.split(path)
        if not name or parent == path:
            return _canonical_absolute_path(path, self._project_root)
        parent_encoding = self._canonical_parents.get(parent)
        if parent_encoding is None:
            parent_encoding = _canonical_absolute_path(parent, self._project_root)
            self._canonical_parents[parent] = parent_encoding
        tag, encoded_parent = parent_encoding
        encoded_name = _forward_path(name)
        if tag == "project-relative":
            return tag, encoded_name if encoded_parent == "." else f"{encoded_parent}/{encoded_name}"
        return tag, _forward_path(os.path.join(encoded_parent, name))


def _path_context_key(context: SourcePathContext, *, lexical_path: list[str], resolved_path: list[str]) -> bytes:
    """Return the path-context digest from completed canonical path primitives."""
    semantic_context = (
        ("display-path", lexical_path),
        ("resolved-path", resolved_path),
        ("module-parts", context.module_parts),
        ("package-parts", context.package_parts),
        ("filename-stem", context.filename_stem),
        ("package-initializer", context.package_initializer),
        ("existing", context.existing),
        ("public", context.public),
    )
    return canonical_digest(semantic_context)


def implementation_source_digest(package_root: pathlib.Path | None = None) -> bytes | None:
    """Return a digest of sorted installed pydocformatter Python paths and bytes, or None on failure.

    Args:
        package_root (pathlib.Path | None): Package tree to hash, or the installed pydocformatter package by default.

    Returns:
        bytes | None: Complete package source digest, or None when identity cannot be established.
    """
    if package_root is None:
        package_file = getattr(pydocformatter, "__file__", None)
        if package_file is None:
            return None
        package_root = pathlib.Path(package_file).parent
    try:
        package_root = pathlib.Path(os.path.abspath(os.path.normpath(package_root)))
        root_links: tuple[tuple[str, str, str], ...] = ()
        if package_root.is_symlink():
            root_links = (_implementation_link_identity(package_root, logical_path="."),)
        root_stat = package_root.stat()
        if not stat.S_ISDIR(root_stat.st_mode):
            return None
        sources: list[tuple[str, tuple[tuple[str, str, str], ...], pathlib.Path]] = []
        _collect_implementation_sources(package_root, package_root=package_root, links=root_links, ancestor_directories=frozenset(), sources=sources)
        if not sources:
            return None
        digest = hashlib.sha256()
        digest.update(_PACKAGE_DIGEST_LABEL)
        for logical_path, links, path in sorted(sources, key=operator.itemgetter(0)):
            _update_length_prefixed(digest, os.fsencode(logical_path))
            digest.update(len(links).to_bytes(8, "big"))
            for link_path, target, resolved_target in links:
                _update_length_prefixed(digest, os.fsencode(link_path))
                _update_length_prefixed(digest, os.fsencode(target))
                _update_length_prefixed(digest, os.fsencode(resolved_target))
            content = path.read_bytes()
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
        return digest.digest()
    except (OSError, ValueError):
        return None


def _installed_artifact_identity() -> tuple[bytes, str] | None:
    """Return a trusted non-editable distribution-manifest identity and version."""
    try:
        distribution = importlib.metadata.distribution("pydocformatter")
        if not _distribution_matches_imported_package(distribution):
            return None
        direct_url_text = distribution.read_text("direct_url.json")
        return _artifact_identity_from_distribution(distribution, direct_url_text=direct_url_text)
    except (OSError, UnicodeError, importlib.metadata.PackageNotFoundError):
        return None


def _distribution_matches_imported_package(distribution: importlib.metadata.Distribution) -> bool:
    """Return whether distribution metadata belongs to the imported package tree."""
    package_file = getattr(pydocformatter, "__file__", None)
    if package_file is None:
        return False
    imported_root = pathlib.Path(package_file).parent
    distribution_root = pathlib.Path(str(distribution.locate_file("pydocformatter")))
    try:
        return imported_root.samefile(distribution_root)
    except OSError:
        return False


def _artifact_identity_from_distribution(distribution: importlib.metadata.Distribution, *, direct_url_text: str | None) -> tuple[bytes, str] | None:
    """Build a trusted artifact identity from one non-editable distribution manifest."""
    try:
        if not _direct_url_allows_artifact_identity(direct_url_text):
            return None
        entries = _package_manifest_entries(distribution.files)
        if entries is None:
            return None
        version = distribution.version
        if not isinstance(version, str) or not version:
            return None
        return _package_manifest_digest(entries), version
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def _direct_url_allows_artifact_identity(direct_url_text: str | None) -> bool:
    """Return whether direct-URL metadata identifies a non-editable install."""
    if direct_url_text is None:
        return True
    direct_url = json.loads(direct_url_text)
    if not isinstance(direct_url, dict) or not isinstance(direct_url.get("url"), str) or not direct_url["url"]:
        return False
    directory_info = direct_url.get("dir_info")
    if directory_info is None:
        return True
    if not isinstance(directory_info, dict):
        return False
    editable = directory_info.get("editable", False)
    return isinstance(editable, bool) and not editable


def _package_manifest_entries(files: Any) -> dict[str, tuple[str, str, int]] | None:
    """Return complete canonical package manifest entries, or None if unusable."""
    if files is None:
        return None
    entries: dict[str, tuple[str, str, int]] = {}
    for file in files:
        logical_path = _normalized_package_manifest_path(str(file))
        if logical_path is None:
            continue
        file_hash = file.hash
        size = file.size
        if file_hash is None or not isinstance(file_hash.mode, str) or not file_hash.mode or not isinstance(file_hash.value, str) or not file_hash.value or type(size) is not int or size < 0:
            return None
        file_hash.mode.encode("ascii")
        file_hash.value.encode("ascii")
        if logical_path in entries:
            return None
        entries[logical_path] = (file_hash.mode, file_hash.value, size)
    return entries or None


def _package_manifest_digest(entries: Mapping[str, tuple[str, str, int]]) -> bytes:
    """Return the identity digest for validated package manifest entries."""
    digest = hashlib.sha256()
    digest.update(_PACKAGE_ARTIFACT_DIGEST_LABEL)
    for logical_path, (algorithm, encoded_hash, size) in sorted(entries.items()):
        _update_length_prefixed(digest, logical_path.encode("utf-8"))
        _update_length_prefixed(digest, algorithm.encode("ascii"))
        _update_length_prefixed(digest, encoded_hash.encode("ascii"))
        digest.update(size.to_bytes(8, "big"))
    return digest.digest()


def _normalized_package_manifest_path(path: str) -> str | None:
    """Return one normalized package Python path from a distribution manifest."""
    normalized = path.replace("\\", "/")
    pure_path = pathlib.PurePosixPath(normalized)
    if pure_path.is_absolute() or not pure_path.parts or pure_path.parts[0] != "pydocformatter":
        return None
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        raise ValueError(f"Malformed pydocformatter manifest path: {path}")
    if pure_path.suffix != ".py":
        return None
    return pure_path.as_posix()


def _collect_implementation_sources(
    directory: pathlib.Path,
    *,
    package_root: pathlib.Path,
    links: tuple[tuple[str, str, str], ...],
    ancestor_directories: frozenset[tuple[int, int]],
    sources: list[tuple[str, tuple[tuple[str, str, str], ...], pathlib.Path]],
) -> None:
    """Collect logical Python sources while safely following directory symlinks."""
    directory_stat = directory.stat()
    directory_identity = (directory_stat.st_dev, directory_stat.st_ino)
    if directory_identity in ancestor_directories:
        raise ValueError(f"Symlink cycle in implementation source tree: {directory}")
    child_ancestors = ancestor_directories | {directory_identity}

    for path in sorted(directory.iterdir(), key=lambda child: child.name):
        logical_path = path.relative_to(package_root).as_posix()
        path_links = links
        if path.is_symlink():
            try:
                target_stat = path.stat()
            except (FileNotFoundError, NotADirectoryError):
                if path.suffix == ".py":
                    raise
                continue
            path_links = (*links, _implementation_link_identity(path, logical_path=logical_path))
        else:
            target_stat = path.stat(follow_symlinks=False)

        if stat.S_ISDIR(target_stat.st_mode):
            _collect_implementation_sources(path, package_root=package_root, links=path_links, ancestor_directories=child_ancestors, sources=sources)
        elif path.suffix == ".py":
            if not stat.S_ISREG(target_stat.st_mode):
                raise ValueError(f"Implementation source is not a regular file: {path}")
            sources.append((logical_path, path_links, path))


def _implementation_link_identity(path: pathlib.Path, *, logical_path: str) -> tuple[str, str, str]:
    """Return one logical symlink path, exact target spelling, and final target identity."""
    target = _forward_path(os.readlink(path))
    resolved_target = _forward_path(os.path.normcase(os.path.realpath(path)))
    return logical_path, target, resolved_target


def _update_length_prefixed(digest: Any, value: bytes) -> None:
    """Add one unambiguous byte string to a package-source digest."""
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def engine_fingerprint(package_root: pathlib.Path | None = None) -> tuple[EngineFingerprint, bytes]:
    """Return the current engine identity and digest.

    Args:
        package_root (pathlib.Path | None): Explicit package tree to hash, or the installed pydocformatter
            implementation by default.

    Returns:
        tuple[EngineFingerprint, bytes]: Structured engine identity and digest.

    Raises:
        CacheFingerprintError: If any required engine identity cannot be established.
    """
    try:
        artifact_identity = _installed_artifact_identity() if package_root is None else None
        if artifact_identity is None:
            implementation_key = implementation_source_digest(package_root)
            distribution_version = importlib.metadata.version("pydocformatter")
        else:
            implementation_key, distribution_version = artifact_identity
    except CacheFingerprintError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, importlib.metadata.PackageNotFoundError) as error:
        raise CacheFingerprintError(f"Unable to establish the cache engine identity: {error}") from error
    if implementation_key is None:
        raise CacheFingerprintError("Unable to establish the pydocformatter implementation identity")
    try:
        version_info = sys.version_info
        fingerprint = EngineFingerprint(
            protocol_version=CACHE_PROTOCOL_VERSION,
            schema_version=CACHE_SCHEMA_VERSION,
            distribution_version=distribution_version,
            implementation_digest=implementation_key,
            filelock_version=importlib.metadata.version("filelock"),
            libcst_version=importlib.metadata.version("libcst"),
            python_implementation=sys.implementation.name,
            python_cache_tag=sys.implementation.cache_tag,
            python_version=(version_info.major, version_info.minor, version_info.micro, version_info.releaselevel, version_info.serial),
            os_name=os.name,
            platform=sys.platform,
            byteorder=sys.byteorder,
            architecture=platform.architecture(),
            line_separator=os.linesep,
        )
        return fingerprint, canonical_digest(fingerprint)
    except CacheFingerprintError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, importlib.metadata.PackageNotFoundError) as error:
        raise CacheFingerprintError(f"Unable to establish the cache engine identity: {error}") from error


def _forward_path(path: str) -> str:
    """Return a normalized path spelling with forward slashes."""
    if os.sep != "/":
        path = path.replace(os.sep, "/")
    if os.altsep is not None:
        path = path.replace(os.altsep, "/")
    return path


def _normalize_absolute_path(path: str | os.PathLike[str]) -> str:
    """Return the existing normalized absolute cache-path spelling."""
    return os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(path))))


def _canonical_absolute_path(absolute: str, project_root: str) -> tuple[str, str]:
    """Encode a normalized absolute path against a normalized project root."""
    try:
        common = os.path.commonpath((absolute, project_root))
    except ValueError:
        common = ""
    if common == project_root:
        return "project-relative", _forward_path(os.path.relpath(absolute, project_root))
    return "absolute", _forward_path(absolute)


def _canonical_json(value: Any) -> str:
    """Return compact deterministic JSON for an already canonical primitive."""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=False)
