"""Narrow data models for persistent clean proofs.

Attributes:
    CACHE_PROTOCOL_VERSION (int): Version of cache fingerprint and coordination semantics.
    CACHE_SCHEMA_VERSION (int): Version of the persistent SQLite schema and cache layout.
    DIGEST_SIZE (int): Required byte length of SHA-256 cache keys and source digests.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses


CACHE_PROTOCOL_VERSION = 1
CACHE_SCHEMA_VERSION = 1
DIGEST_SIZE = 32


@dataclasses.dataclass(frozen=True)
class EngineFingerprint:
    """Analysis-engine identities that invalidate persistent proofs.

    Attributes:
        protocol_version (int): Internal cache protocol version.
        schema_version (int): Persistent database schema version.
        distribution_version (str): Installed pydocformatter distribution version.
        implementation_digest (bytes): Digest of the installed artifact manifest or complete implementation source tree.
        filelock_version (str): Installed filelock distribution version.
        libcst_version (str): Installed LibCST distribution version.
        python_implementation (str): Python implementation name.
        python_cache_tag (str | None): Python bytecode cache tag.
        python_version (tuple[int | str, ...]): Complete Python version identity including release level.
        os_name (str): Runtime operating-system family name.
        platform (str): Runtime platform identifier.
        byteorder (str): Runtime byte order.
        architecture (tuple[str, str]): Platform architecture and linkage identity.
        line_separator (str): Native platform line separator.
    """

    protocol_version: int
    schema_version: int
    distribution_version: str
    implementation_digest: bytes
    filelock_version: str
    libcst_version: str
    python_implementation: str
    python_cache_tag: str | None
    python_version: tuple[int | str, ...]
    os_name: str
    platform: str
    byteorder: str
    architecture: tuple[str, str]
    line_separator: str


@dataclasses.dataclass(frozen=True)
class AnalysisFingerprint:
    """Canonical direct-analysis settings and final-rule identities.

    Attributes:
        encoding_version (int): Version of the analysis-key encoding.
        analysis_settings_key (bytes): Effective direct-analysis settings digest.
        selected_rules_key (bytes): Final ordered path-specific rule-code digest.
    """

    encoding_version: int
    analysis_settings_key: bytes
    selected_rules_key: bytes


@dataclasses.dataclass(frozen=True)
class CleanProof:
    """One persisted proof that a precise on-disk source state was clean.

    Attributes:
        engine_key (bytes): Digest of the complete analysis-engine identity.
        analysis_key (bytes): Digest of effective direct-analysis settings and final ordered rule codes.
        path_key (str): Canonical project-relative or absolute lexical path identity.
        path_context_key (bytes): Digest of package, module, visibility, and resolved-path context.
        source_digest (bytes): SHA-256 digest of complete domain-separated raw source bytes.
        source_size (int): Exact raw source length in bytes.
        mtime_ns (int | None): Optional negative-only modification-time hint for the proven source size.
        last_seen_day (int): UTC day number when the proof was last inserted or reused.
    """

    engine_key: bytes
    analysis_key: bytes
    path_key: str
    path_context_key: bytes
    source_digest: bytes
    source_size: int
    mtime_ns: int | None
    last_seen_day: int

    def __post_init__(self) -> None:
        """Reject malformed proof fields at the construction boundary."""
        for label, digest in (("engine key", self.engine_key), ("analysis key", self.analysis_key), ("path context key", self.path_context_key), ("source digest", self.source_digest)):
            if type(digest) is not bytes or len(digest) != DIGEST_SIZE:
                raise ValueError(f"Clean proof {label} must be an exact digest")
        if type(self.path_key) is not str or not self.path_key:
            raise ValueError("Clean proof path key must be a non-empty string")
        if type(self.source_size) is not int or self.source_size < 0:
            raise ValueError("Clean proof source size must be a non-negative integer")
        if self.mtime_ns is not None and type(self.mtime_ns) is not int:
            raise ValueError("Clean proof modification time must be an integer or None")
        if type(self.last_seen_day) is not int or self.last_seen_day < 0:
            raise ValueError("Clean proof last-seen day must be a non-negative integer")


@dataclasses.dataclass(frozen=True)
class CacheStats:
    """Internal counters for cache probing and persistence.

    Attributes:
        candidates (int): Requests eligible for persistent lookup.
        hits (int): Proofs accepted after full source validation.
        metadata_rejected (int): Candidate proofs rejected by size or mtime hints.
        digest_rejected (int): Candidate proofs rejected after hashing raw bytes.
        misses (int): Cacheable requests sent to normal analysis.
        uncacheable (int): Requests bypassed by policy or engine failure.
        read_errors (int): Parent probe reads that failed and fell back to normal execution.
        writes (int): Clean proofs inserted or replaced in the store.
        store_errors (int): Best-effort store operations that failed.
    """

    candidates: int = 0
    hits: int = 0
    metadata_rejected: int = 0
    digest_rejected: int = 0
    misses: int = 0
    uncacheable: int = 0
    read_errors: int = 0
    writes: int = 0
    store_errors: int = 0

    def increment(self, **increments: int) -> CacheStats:
        """Return counters with the named non-negative increments applied.

        Args:
            **increments (int): Counter names and non-negative amounts to add.

        Returns:
            CacheStats: New immutable statistics with the increments applied.

        Raises:
            KeyError: If an increment names an unknown counter.
            ValueError: If an increment is negative.
        """
        values = {field.name: getattr(self, field.name) for field in dataclasses.fields(self)}
        for name, increment in increments.items():
            if name not in values:
                raise KeyError(name)
            if increment < 0:
                raise ValueError("Cache statistic increments must not be negative")
            values[name] += increment
        return CacheStats(**values)
