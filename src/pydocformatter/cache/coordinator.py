"""Parent-process cache probing, result synthesis, and batched persistence."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import enum
import dataclasses
import concurrent.futures

# First-party imports
import pydocformatter.cache.store as cache_store
from pydocformatter import formatter
from pydocformatter.cache.models import DIGEST_SIZE, CacheStats, CleanProof


_MAX_PROBE_THREADS = 32
_PROBE_BATCHES_PER_WORKER = 8
_MAX_IN_FLIGHT_BATCHES_PER_WORKER = 2


@dataclasses.dataclass(frozen=True)
class CacheIdentity:
    """Validated persistent identities for one cacheable disk request.

    Attributes:
        analysis_key (bytes): Effective direct-analysis settings and final ordered rule-code digest.
        path_key (str): Canonical lexical path identity.
        path_context_key (bytes): Package, module, visibility, and physical-path digest.
    """

    analysis_key: bytes
    path_key: str
    path_context_key: bytes

    def __post_init__(self) -> None:
        """Reject malformed identity fields at their construction boundary."""
        if type(self.analysis_key) is not bytes or len(self.analysis_key) != DIGEST_SIZE:
            raise ValueError("Cache analysis identity must be an exact digest")
        if type(self.path_key) is not str or not self.path_key:
            raise ValueError("Cache lexical path identity must be a non-empty string")
        if type(self.path_context_key) is not bytes or len(self.path_context_key) != DIGEST_SIZE:
            raise ValueError("Cache path context identity must be an exact digest")


@dataclasses.dataclass(frozen=True)
class CacheRequest:
    """Optional cache identity for one ordered disk formatting request.

    Attributes:
        index (int): Original selected-file result index.
        path (str): Display and filesystem path to validate.
        identity (CacheIdentity | None): Complete persistent identity, or None when the request bypasses caching.
    """

    index: int
    path: str
    identity: CacheIdentity | None


@dataclasses.dataclass(frozen=True)
class CacheHit:
    """One immutable synthetic result accepted from persistent storage.

    Attributes:
        index (int): Original selected-file result index.
        result (formatter.FormatterResult): Source-less clean result synthesized for the display path.
    """

    index: int
    result: formatter.FormatterResult


@dataclasses.dataclass(frozen=True)
class CacheProbe:
    """Ordered-index hits and misses returned by one cache probe.

    Attributes:
        hits (tuple[CacheHit, ...]): Synthetic clean results in request order.
        miss_indexes (tuple[int, ...]): Original indexes requiring normal formatter execution.
        requests (tuple[CacheRequest, ...]): Exact prepared requests represented by this probe.
        touches (tuple[tuple[bytes, bytes, str, int], ...]): Validated proof retention updates for persistence.
        stats (CacheStats): Counters after lookup and raw-source validation.
    """

    hits: tuple[CacheHit, ...]
    miss_indexes: tuple[int, ...]
    requests: tuple[CacheRequest, ...]
    touches: tuple[tuple[bytes, bytes, str, int], ...]
    stats: CacheStats


class _ProbeOutcome(enum.StrEnum):
    """Internal result of validating one possible positive hit."""

    HIT = "hit"
    DIGEST_REJECTED = "digest-rejected"
    READ_ERROR = "read-error"


class CacheCoordinator:
    """Coordinate cache work around worker execution in the parent process.

    Attributes:
        store (cache_store.CacheStore): Parent-owned persistent proof store.
        engine_key (bytes): Analysis-engine identity used for cache lookups and updates.
        parallelism (int): Concurrency limit for source validation.
    """

    def __init__(self, store: cache_store.CacheStore, *, engine_key: bytes, parallelism: int) -> None:
        """Initialize one invocation coordinator with no open SQLite connection.

        Args:
            store (cache_store.CacheStore): Parent-owned persistent proof store.
            engine_key (bytes): Current analysis-engine identity digest.
            parallelism (int): Resolved concurrency limit for source validation.
        """
        self.store = store
        self.engine_key = engine_key
        self.parallelism = parallelism

    def probe(self, requests: tuple[CacheRequest, ...]) -> CacheProbe:
        """Load candidate rows, validate complete raw bytes, and synthesize clean hits.

        Args:
            requests (tuple[CacheRequest, ...]): Ordered disk requests with cache identities and eligibility.

        Returns:
            CacheProbe: Validated source-less hits, miss indexes, and lookup counters.

        Raises:
            AssertionError: If an internal probe outcome is unknown.
        """
        cacheable = tuple((request, request.identity) for request in requests if request.identity is not None)
        candidates = len(cacheable)
        uncacheable = len(requests) - candidates
        metadata_rejected = 0
        digest_rejected = 0
        read_errors = 0
        hits = 0
        lookup = self.store.lookup((self.engine_key, identity.analysis_key, identity.path_key) for _, identity in cacheable)
        proofs = lookup.proofs
        store_errors = len(lookup.failures)

        hit_results: list[CacheHit] = []
        possible: list[tuple[CacheRequest, CleanProof]] = []
        for request, identity in cacheable:
            proof = proofs.get((self.engine_key, identity.analysis_key, identity.path_key))
            if proof is None or proof.path_context_key != identity.path_context_key:
                continue
            try:
                stat_result = os.stat(request.path)
            except OSError:
                read_errors += 1
                continue
            if stat_result.st_size != proof.source_size or (proof.mtime_ns is not None and stat_result.st_mtime_ns != proof.mtime_ns):
                metadata_rejected += 1
                continue
            possible.append((request, proof))

        outcomes = self._validate_possible_hits(tuple(possible))
        touches: list[tuple[bytes, bytes, str, int]] = []
        today = cache_store.utc_day()
        for request, proof, outcome in outcomes:
            if outcome is _ProbeOutcome.HIT:
                hit_results.append(CacheHit(index=request.index, result=formatter.FormatterResult.cached_clean(request.path)))
                hits += 1
                if proof.last_seen_day != today:
                    touches.append((proof.engine_key, proof.analysis_key, proof.path_key, today))
            elif outcome is _ProbeOutcome.DIGEST_REJECTED:
                digest_rejected += 1
            elif outcome is _ProbeOutcome.READ_ERROR:
                read_errors += 1
            else:
                raise AssertionError(f"Unknown cache probe outcome: {outcome}")

        hit_indexes = frozenset(hit.index for hit in hit_results)
        miss_indexes = tuple(request.index for request in requests if request.index not in hit_indexes)
        stats = CacheStats().increment(
            candidates=candidates,
            hits=hits,
            metadata_rejected=metadata_rejected,
            digest_rejected=digest_rejected,
            misses=candidates - hits,
            uncacheable=uncacheable,
            read_errors=read_errors,
            store_errors=store_errors,
        )
        return CacheProbe(hits=tuple(hit_results), miss_indexes=miss_indexes, requests=requests, touches=tuple(touches), stats=stats)

    def persist(self, probe: CacheProbe, executions: dict[int, formatter.DiskFormatResult]) -> CacheStats:
        """Batch touches and eligible clean proofs after all normal execution succeeds.

        Args:
            probe (CacheProbe): Exact probe whose misses produced `executions`.
            executions (dict[int, formatter.DiskFormatResult]): Miss executions keyed by original selected-file index.

        Returns:
            CacheStats: Final lookup and persistence counters.

        Raises:
            AssertionError: If a bypassed request unexpectedly carries cache persistence evidence.
        """
        today = cache_store.utc_day()
        requests_by_index = {request.index: request for request in probe.requests}
        proofs: list[CleanProof] = []
        for index, execution in executions.items():
            request = requests_by_index[index]
            snapshot = execution.clean_snapshot
            if snapshot is None:
                continue
            identity = request.identity
            if identity is None:
                raise AssertionError("A bypassed cache request returned a clean persistence snapshot")
            proofs.append(
                CleanProof(
                    engine_key=self.engine_key,
                    analysis_key=identity.analysis_key,
                    path_key=identity.path_key,
                    path_context_key=identity.path_context_key,
                    source_digest=snapshot.source_digest,
                    source_size=snapshot.source_size,
                    mtime_ns=snapshot.mtime_ns,
                    last_seen_day=today,
                )
            )

        commit = self.store.commit(touches=probe.touches, proofs=proofs)
        return probe.stats.increment(writes=commit.writes, store_errors=len(commit.failures))

    def _validate_possible_hits(self, candidates: tuple[tuple[CacheRequest, CleanProof], ...]) -> tuple[tuple[CacheRequest, CleanProof, _ProbeOutcome], ...]:
        """Hash possible hits sequentially or through bounded rolling batches.

        Both thread count and in-flight batch count are bounded independently of candidate count.

        Args:
            candidates (tuple[tuple[CacheRequest, CleanProof], ...]): Metadata-compatible requests and stored proofs.

        Returns:
            tuple[tuple[CacheRequest, CleanProof, _ProbeOutcome], ...]: Candidates paired with content-validation
                outcomes in input order.
        """
        if not candidates:
            return ()
        workers = min(len(candidates), self.parallelism, _MAX_PROBE_THREADS)
        if workers <= 1:
            return tuple((request, proof, _validate_source(request.path, proof)) for request, proof in candidates)
        target_batches = min(len(candidates), workers * _PROBE_BATCHES_PER_WORKER)
        batch_size = (len(candidates) + target_batches - 1) // target_batches
        max_in_flight = min(target_batches, workers * _MAX_IN_FLIGHT_BATCHES_PER_WORKER)
        ordered: list[tuple[CacheRequest, CleanProof, _ProbeOutcome] | None] = [None] * len(candidates)
        batches = ((start, candidates[start : start + batch_size]) for start in range(0, len(candidates), batch_size))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            pending: dict[concurrent.futures.Future[tuple[tuple[CacheRequest, CleanProof, _ProbeOutcome], ...]], int] = {}

            def submit_next_batch() -> bool:
                try:
                    start, batch = next(batches)
                except StopIteration:
                    return False
                pending[executor.submit(_validate_source_batch, batch)] = start
                return True

            for _ in range(max_in_flight):
                if not submit_next_batch():
                    break
            while pending:
                completed, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
                if not completed:
                    raise AssertionError("Cache probing waited without a completed batch")
                for future in completed:
                    start = pending.pop(future)
                    outcomes = future.result()
                    for offset, outcome in enumerate(outcomes):
                        index = start + offset
                        if index >= len(candidates) or outcome[:2] != candidates[index]:
                            raise AssertionError("Cache probe batch returned misaligned candidate outcomes")
                        ordered[index] = outcome
                while len(pending) < max_in_flight and submit_next_batch():
                    pass
        if any(outcome is None for outcome in ordered):
            raise AssertionError("Cache probing completed without an outcome for every candidate")
        return tuple(outcome for outcome in ordered if outcome is not None)


def _validate_source_batch(candidates: tuple[tuple[CacheRequest, CleanProof], ...]) -> tuple[tuple[CacheRequest, CleanProof, _ProbeOutcome], ...]:
    """Validate one ordered candidate batch with one complete source check per file."""
    return tuple((request, proof, _validate_source(request.path, proof)) for request, proof in candidates)


def _validate_source(path: str, proof: CleanProof) -> _ProbeOutcome:
    """Read and hash complete current raw bytes for one possible positive hit."""
    try:
        with open(path, "rb") as source_file:
            digest, size = formatter.digest_source_file(source_file)
    except OSError:
        return _ProbeOutcome.READ_ERROR
    if size != proof.source_size or digest != proof.source_digest:
        return _ProbeOutcome.DIGEST_REJECTED
    return _ProbeOutcome.HIT
