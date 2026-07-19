"""Bounded invocation-level preparation, probing, and persistence."""

# Future imports
from __future__ import annotations

# Standard library imports
import stat
import pathlib
import dataclasses

# First-party imports
import pydocformatter.settings as settings_core
import pydocformatter.cache.store as cache_store
import pydocformatter.cache.directory as cache_directory
import pydocformatter.cache.coordinator as cache_coordinator
import pydocformatter.cache.fingerprint as cache_fingerprint
from pydocformatter import formatter
from pydocformatter.cache.models import CacheStats
from pydocformatter.cli import settings_check
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.models import RuleCacheBehavior
from pydocformatter.rules_selection import RuleExecutionPlan
from pydocformatter.source_path import SourcePathContext


@dataclasses.dataclass(frozen=True)
class CacheCandidate:
    """Resolved parent-process inputs for one selected disk path.

    Attributes:
        index (int): Original selected-file result index.
        path (str): Display and filesystem path.
        profile (settings_core.SettingsProfile[CheckSettings]): Effective settings profile for direct analysis.
        execution_plan (RuleExecutionPlan): Final path-specific rule execution plan.
        source_path (SourcePathContext): Precomputed source-path semantics.
        selection_succeeded (bool): Whether rule selection completed without operational errors.
        fix (bool): Whether selected fixes should be applied.
        write (bool): Whether modified source should be written in place.
    """

    index: int
    path: str
    profile: settings_core.SettingsProfile[CheckSettings]
    execution_plan: RuleExecutionPlan
    source_path: SourcePathContext
    selection_succeeded: bool
    fix: bool
    write: bool


@dataclasses.dataclass(frozen=True)
class PreparedFile:
    """One cache request paired with its lean worker request.

    Attributes:
        index (int): Original selected-file result index.
        cache_request (cache_coordinator.CacheRequest): Persistent proof identities and eligibility.
        format_request (formatter.DiskFormatRequest): Lean request sent to normal execution on a miss.
    """

    index: int
    cache_request: cache_coordinator.CacheRequest
    format_request: formatter.DiskFormatRequest


@dataclasses.dataclass(frozen=True)
class PreparedCacheBatch:
    """Immutable prepared files and invocation-level preparation failures.

    Attributes:
        files (tuple[PreparedFile, ...]): Ordered prepared cache and formatter requests.
        preparation_errors (int): Explicitly counted engine, semantic-analysis, and path-identity failures.
    """

    files: tuple[PreparedFile, ...]
    preparation_errors: int


@dataclasses.dataclass(frozen=True)
class _CacheRuntime:
    """Lazily initialized coordinator and path identity builder."""

    coordinator: cache_coordinator.CacheCoordinator
    path_builder: cache_fingerprint.PathFingerprintBuilder


@dataclasses.dataclass(frozen=True)
class CachePersistence:
    """Final cache counters and invocation-level warnings.

    Attributes:
        stats (CacheStats): Counters after lookup, validation, and persistence.
        warnings (tuple[str, ...]): Run-level cache warnings to print once.
    """

    stats: CacheStats
    warnings: tuple[str, ...]


class CacheSession:
    """Own bounded cache preparation and parent-only coordinator state for one invocation."""

    def __init__(self, *, profile: settings_core.SettingsProfile[CheckSettings] | None, parallelism: int, cache_root: pathlib.Path | None, warnings: tuple[str, ...], preparation_errors: int) -> None:
        """Initialize a session from resolved cache components.

        Args:
            profile (settings_core.SettingsProfile[CheckSettings] | None): Enabled cache profile eligible for lazy
                initialization, or None when storage is disabled or unavailable.
            parallelism (int): Resolved source-validation concurrency for lazy coordinator construction.
            cache_root (pathlib.Path | None): Configured cache root retained for final availability checks.
            warnings (tuple[str, ...]): Preparation warnings already established for the invocation.
            preparation_errors (int): Preparation failures already counted before file-specific work.
        """
        self._profile = profile
        self._parallelism = parallelism
        self._cache_root = cache_root
        self._warnings = warnings
        self._preparation_errors = preparation_errors
        self._runtime: _CacheRuntime | None = None
        self._runtime_attempted = False

    @classmethod
    def from_profile(cls, profile: settings_core.SettingsProfile[CheckSettings] | None, *, parallelism: int) -> CacheSession:
        """Build the invocation cache components from the command-level profile.

        Args:
            profile (settings_core.SettingsProfile[CheckSettings] | None): Run-level profile, or None to disable caching
                for a direct caller.
            parallelism (int): Resolved parent-side source validation concurrency.

        Returns:
            CacheSession: Available or safely degraded invocation session.
        """
        if profile is None or not profile.settings.cache:
            return cls(profile=None, parallelism=parallelism, cache_root=None, warnings=(), preparation_errors=0)
        cache_root = cache_directory.cache_directory_for_profile(profile)
        unavailable_parent = _unavailable_cache_parent(cache_root)
        if unavailable_parent is not None:
            return cls(profile=None, parallelism=parallelism, cache_root=cache_root, warnings=(_missing_cache_parent_warning(unavailable_parent),), preparation_errors=1)
        return cls(profile=profile, parallelism=parallelism, cache_root=cache_root, warnings=(), preparation_errors=0)

    def prepare(self, candidates: tuple[CacheCandidate, ...]) -> PreparedCacheBatch:
        """Prepare cache identities and lean formatter requests with memoized semantic analysis keys.

        Args:
            candidates (tuple[CacheCandidate, ...]): Ordered fully resolved selected-file inputs.

        Returns:
            PreparedCacheBatch: Immutable requests and explicit preparation failure count.
        """
        preparation_errors = self._preparation_errors
        if self._profile is None:
            policy_eligible = (False,) * len(candidates)
        else:
            policy_eligible = tuple(
                candidate.selection_succeeded and all(selected.rule.cache_behavior is RuleCacheBehavior.FILE_LOCAL for selected in candidate.execution_plan.selected_rules) for candidate in candidates
            )
        if self._profile is not None and any(policy_eligible):
            preparation_errors += self._initialize_runtime()
        runtime = self._runtime
        analysis_keys: dict[tuple[tuple[tuple[str, object], ...], tuple[str, ...]], bytes | None] = {}
        prepared: list[PreparedFile] = []
        for candidate, eligible in zip(candidates, policy_eligible, strict=True):
            identity: cache_coordinator.CacheIdentity | None = None
            if eligible and runtime is not None:
                try:
                    settings_identity = settings_check.analysis_settings_identity(candidate.profile)
                    rule_identity = tuple(selected.rule.code.tag for selected in candidate.execution_plan.selected_rules)
                    semantic_identity = (settings_identity, rule_identity)
                except (OSError, UnicodeError, TypeError, ValueError):
                    preparation_errors += 1
                else:
                    if semantic_identity not in analysis_keys:
                        try:
                            _, shared_analysis_key = cache_fingerprint.analysis_fingerprint(settings_identity, candidate.execution_plan.selected_rules)
                        except (OSError, UnicodeError, TypeError, ValueError, OverflowError):
                            shared_analysis_key = None
                            preparation_errors += 1
                        analysis_keys[semantic_identity] = shared_analysis_key
                    analysis_key = analysis_keys[semantic_identity]
                    if analysis_key is not None:
                        try:
                            path_key, path_context_key = runtime.path_builder.fingerprints(candidate.source_path)
                            identity = cache_coordinator.CacheIdentity(analysis_key=analysis_key, path_key=path_key, path_context_key=path_context_key)
                        except (OSError, UnicodeError, TypeError, ValueError, OverflowError):
                            preparation_errors += 1
            request = cache_coordinator.CacheRequest(index=candidate.index, path=candidate.path, identity=identity)
            format_request = formatter.DiskFormatRequest(
                path=candidate.path,
                settings=candidate.profile.settings,
                execution_plan=candidate.execution_plan,
                source_path=candidate.source_path,
                fix=candidate.fix,
                write=candidate.write,
                collect_clean_snapshot=identity is not None,
            )
            prepared.append(PreparedFile(index=candidate.index, cache_request=request, format_request=format_request))
        return PreparedCacheBatch(files=tuple(prepared), preparation_errors=preparation_errors)

    def probe(self, batch: PreparedCacheBatch) -> cache_coordinator.CacheProbe:
        """Probe one prepared batch and return all state required for persistence.

        Args:
            batch (PreparedCacheBatch): Immutable requests to probe.

        Returns:
            cache_coordinator.CacheProbe: Explicit hits, misses, touches, requests, and counters.
        """
        requests = tuple(prepared.cache_request for prepared in batch.files)
        if self._runtime is None:
            stats = CacheStats(uncacheable=len(batch.files), store_errors=batch.preparation_errors)
            return cache_coordinator.CacheProbe(hits=(), miss_indexes=tuple(prepared.index for prepared in batch.files), requests=requests, touches=(), stats=stats)
        probe = self._runtime.coordinator.probe(requests)
        return dataclasses.replace(probe, stats=probe.stats.increment(store_errors=batch.preparation_errors))

    def persist(self, probe: cache_coordinator.CacheProbe, executions: dict[int, formatter.DiskFormatResult]) -> CachePersistence:
        """Persist exactly one probe's touches and clean executions and finalize warnings.

        Args:
            probe (cache_coordinator.CacheProbe): Exact probe whose misses produced the executions.
            executions (dict[int, formatter.DiskFormatResult]): Miss executions keyed by selected-file index.

        Returns:
            CachePersistence: Final counters and invocation warnings.
        """
        stats = probe.stats if self._runtime is None else self._runtime.coordinator.persist(probe, executions)
        warnings = list(self._warnings)
        if self._cache_root is not None and not warnings:
            unavailable_parent = _unavailable_cache_parent(self._cache_root)
            if unavailable_parent is not None:
                warnings.append(_missing_cache_parent_warning(unavailable_parent))
                if stats.store_errors == 0:
                    stats = stats.increment(store_errors=1)
        return CachePersistence(stats=stats, warnings=tuple(warnings))

    def _initialize_runtime(self) -> int:
        """Initialize cache-only engine and path state once, returning its failure count."""
        if self._runtime_attempted:
            return 0
        self._runtime_attempted = True
        profile = self._profile
        cache_root = self._cache_root
        if profile is None or cache_root is None:
            return 0
        try:
            _, engine_key = cache_fingerprint.engine_fingerprint()
            path_builder = cache_fingerprint.PathFingerprintBuilder(profile.project_root)
            coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(cache_root)), engine_key=engine_key, parallelism=self._parallelism)
        except cache_fingerprint.CacheFingerprintError:
            return 1
        except (OSError, UnicodeError, TypeError, ValueError):
            return 1
        self._runtime = _CacheRuntime(coordinator=coordinator, path_builder=path_builder)
        return 0


def _unavailable_cache_parent(cache_root: pathlib.Path) -> pathlib.Path | None:
    """Return an unavailable immediate parent only when the absent root can be classified reliably."""
    try:
        cache_root.lstat()
    except FileNotFoundError:
        pass
    except NotADirectoryError:
        return cache_root.parent
    except OSError:
        return None
    else:
        return None
    try:
        parent_stat = cache_root.parent.stat()
    except (FileNotFoundError, NotADirectoryError):
        return cache_root.parent
    except OSError:
        return None
    return None if stat.S_ISDIR(parent_stat.st_mode) else cache_root.parent


def _missing_cache_parent_warning(parent: pathlib.Path) -> str:
    """Return the fixed user-facing warning for an unavailable cache parent."""
    return f"pydocfmt check: Cache warning: Cache directory parent does not exist or is not a directory; running without persistent cache: {parent}"
