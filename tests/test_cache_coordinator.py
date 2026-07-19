"""Tests for cache probing and disk execution integration."""

# Future imports
from __future__ import annotations

# Standard library imports
import gc
import io
import os
import typing
import threading
import dataclasses
import concurrent.futures
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.cli.check as check_command
import pydocformatter.cache.store as cache_store
import pydocformatter.cache.directory as cache_directory
import pydocformatter.cache.coordinator as cache_coordinator
import pydocformatter.cache.fingerprint as cache_fingerprint
from pydocformatter import file_selection, formatter, rules_selection
from pydocformatter.cache.models import CacheStats, CleanProof
from pydocformatter.cli import settings_check
from pydocformatter.cli.settings_check import CheckSettings, OutputFormat
from pydocformatter.rules.models import RuleCacheBehavior
from pydocformatter.settings import ARGUMENT_SOURCE_PRIORITY, SettingsProfile
from pydocformatter.source_path import SourcePathContext, SourcePathContextBuilder
from tests import cli_helpers


if typing.TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


def _profile(settings: CheckSettings, root: Path) -> SettingsProfile[CheckSettings]:
    """Return a complete settings profile rooted at a test project."""
    fields = tuple(field.name for field in dataclasses.fields(settings))
    bases = {field: str(root) for field in fields}
    priorities = dict.fromkeys(fields, 0)
    if os.path.isabs(settings.cache_dir):
        priorities["cache_dir"] = ARGUMENT_SOURCE_PRIORITY
    return SettingsProfile(settings=settings, field_bases=bases, field_priorities=priorities, project_root=str(root))


def _proof_for(path: Path, *, digest: bytes | None = None, mtime_ns: int | None = None, day: int | None = None) -> CleanProof:
    """Return a proof aligned with one test path."""
    source = path.read_bytes()
    if day is None:
        day = cache_store.utc_day()
    if mtime_ns is None:
        mtime_ns = path.stat().st_mtime_ns
    return CleanProof(
        engine_key=b"e" * 32,
        analysis_key=b"a" * 32,
        path_key="module.py",
        path_context_key=b"p" * 32,
        source_digest=formatter.digest_source_bytes(source) if digest is None else digest,
        source_size=len(source),
        mtime_ns=mtime_ns,
        last_seen_day=day,
    )


def _request(path: Path, *, index: int = 0, path_key: str = "module.py", path_context_key: bytes = b"p" * 32, cacheable: bool = True) -> cache_coordinator.CacheRequest:
    """Return cache identities matching `_proof_for`."""
    identity = cache_coordinator.CacheIdentity(analysis_key=b"a" * 32, path_key=path_key, path_context_key=path_context_key) if cacheable else None
    return cache_coordinator.CacheRequest(index=index, path=str(path), identity=identity)


def _disk_request(path: Path, settings: CheckSettings, selection: rules_selection.RuleSelection, *, fix: bool, write: bool, collect_clean_snapshot: bool) -> formatter.DiskFormatRequest:
    """Return one fully resolved public disk formatting request."""
    return formatter.DiskFormatRequest(
        path=str(path),
        settings=settings,
        execution_plan=selection.execution_plan_for_path(str(path)),
        source_path=SourcePathContext.for_path(str(path)),
        fix=fix,
        write=write,
        collect_clean_snapshot=collect_clean_snapshot,
    )


def _probe_candidates(path: Path, count: int) -> tuple[tuple[cache_coordinator.CacheRequest, CleanProof], ...]:
    """Return ordered metadata-compatible candidates sharing one source file."""
    proof = _proof_for(path)
    return tuple((_request(path, index=index, path_key=f"module-{index}.py"), dataclasses.replace(proof, path_key=f"module-{index}.py")) for index in range(count))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("analysis_key", b"short", id="analysis-length"),
        pytest.param("analysis_key", bytearray(32), id="analysis-type"),
        pytest.param("path_key", "", id="empty-path"),
        pytest.param("path_key", Path("module.py"), id="path-type"),
        pytest.param("path_context_key", b"short", id="context-length"),
        pytest.param("path_context_key", bytearray(32), id="context-type"),
    ],
)
def test_cache_identity_rejects_malformed_fields(field: str, value: object) -> None:
    values: dict[str, object] = {"analysis_key": b"a" * 32, "path_key": "module.py", "path_context_key": b"p" * 32}
    values[field] = value

    with pytest.raises(ValueError, match="Cache"):
        cache_coordinator.CacheIdentity(**typing.cast("dict[str, typing.Any]", values))


def test_cache_probe_is_frozen_and_uses_immutable_hit_storage() -> None:
    probe = cache_coordinator.CacheProbe(hits=(), miss_indexes=(0,), requests=(cache_coordinator.CacheRequest(index=0, path="module.py", identity=None),), touches=(), stats=CacheStats(uncacheable=1))

    assert isinstance(probe.hits, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        probe.__setattr__("hits", ())


def test_metadata_mismatch_bypasses_parent_hashing(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    proof = _proof_for(target, mtime_ns=target.stat().st_mtime_ns + 1)
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=(proof,))
    digest = mocker.patch("pydocformatter.formatter.digest_source_file", side_effect=AssertionError("metadata mismatch must not hash"), autospec=True)

    probe = cache_coordinator.CacheCoordinator(store, engine_key=proof.engine_key, parallelism=4).probe((_request(target),))

    assert probe.hits == ()
    assert probe.miss_indexes == (0,)
    assert probe.stats.metadata_rejected == 1
    digest.assert_not_called()


def test_metadata_match_with_digest_mismatch_cannot_hit(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    proof = _proof_for(target, digest=b"x" * 32)
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=(proof,))

    probe = cache_coordinator.CacheCoordinator(store, engine_key=proof.engine_key, parallelism=4).probe((_request(target),))

    assert probe.hits == ()
    assert probe.miss_indexes == (0,)
    assert probe.stats.digest_rejected == 1


def test_valid_path_context_mismatch_is_a_normal_miss_without_store_error(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    proof = _proof_for(target)
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=(proof,))
    request = _request(target, path_context_key=b"q" * 32)

    probe = cache_coordinator.CacheCoordinator(store, engine_key=proof.engine_key, parallelism=1).probe((request,))

    assert probe.miss_indexes == (0,)
    assert probe.stats.store_errors == 0


def test_same_size_timestamp_preserving_edit_cannot_hit(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_bytes(b"value = 1\n")
    original_stat = target.stat()
    proof = _proof_for(target)
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=(proof,))
    target.write_bytes(b"value = 2\n")
    os.utime(target, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    probe = cache_coordinator.CacheCoordinator(store, engine_key=proof.engine_key, parallelism=1).probe((_request(target),))

    assert probe.hits == ()
    assert probe.stats.digest_rejected == 1


def test_current_coordinator_parallelism_controls_digest_probe_threads(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    base_proof = _proof_for(target)
    requests = tuple(_request(target, index=index, path_key=f"module-{index}.py") for index in range(3))
    proofs = tuple(dataclasses.replace(base_proof, path_key=request.identity.path_key) for request in requests if request.identity is not None)
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=proofs)
    created_workers = []

    class ImmediateThreadExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            created_workers.append(max_workers)
            self.submissions = 0

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def submit(self, fn: typing.Callable[..., typing.Any], *args: object) -> concurrent.futures.Future[typing.Any]:
            self.submissions += 1
            future: concurrent.futures.Future[typing.Any] = concurrent.futures.Future()
            future.set_result(fn(*args))
            return future

    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", new=ImmediateThreadExecutor)

    probe = cache_coordinator.CacheCoordinator(store, engine_key=base_proof.engine_key, parallelism=2).probe(requests)

    assert created_workers == [2]
    assert probe.stats.hits == len(requests)


def test_zero_probe_candidates_return_without_an_executor(tmp_path: Path, mocker: MockerFixture) -> None:
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=4)
    executor = mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", side_effect=AssertionError("zero candidates must not create an executor"), autospec=True)

    assert coordinator._validate_possible_hits(()) == ()
    executor.assert_not_called()


def test_one_probe_worker_retains_the_sequential_path(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 3)
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=1)
    executor = mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", side_effect=AssertionError("one worker must stay sequential"), autospec=True)
    validate = mocker.spy(cache_coordinator, "_validate_source")

    outcomes = coordinator._validate_possible_hits(candidates)

    assert tuple(request.index for request, _, _ in outcomes) == (0, 1, 2)
    assert all(outcome is cache_coordinator._ProbeOutcome.HIT for _, _, outcome in outcomes)
    assert validate.call_count == len(candidates)
    executor.assert_not_called()


def test_many_probe_candidates_bound_submissions_and_pending_futures_by_concurrency(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 1000)
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=4)
    submissions: list[concurrent.futures.Future[typing.Any]] = []
    created_workers: list[int | None] = []
    pending_sizes: list[int] = []

    class ImmediateExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            created_workers.append(max_workers)

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def submit(fn: typing.Callable[..., typing.Any], *args: object) -> concurrent.futures.Future[typing.Any]:
            future: concurrent.futures.Future[typing.Any] = concurrent.futures.Future()
            try:
                future.set_result(fn(*args))
            except BaseException as error:
                future.set_exception(error)
            submissions.append(future)
            return future

    original_wait = concurrent.futures.wait

    def tracking_wait(
        fs: typing.Iterable[concurrent.futures.Future[typing.Any]], timeout: float | None = None, return_when: str = concurrent.futures.ALL_COMPLETED
    ) -> tuple[set[concurrent.futures.Future[typing.Any]], set[concurrent.futures.Future[typing.Any]]]:
        futures = set(fs)
        pending_sizes.append(len(futures))
        return original_wait(futures, timeout=timeout, return_when=return_when)

    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", new=ImmediateExecutor)
    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.wait", side_effect=tracking_wait, autospec=True)
    validate = mocker.patch("pydocformatter.cache.coordinator._validate_source", return_value=cache_coordinator._ProbeOutcome.HIT, autospec=True)

    outcomes = coordinator._validate_possible_hits(candidates)

    assert created_workers == [4]
    assert len(submissions) > 1
    assert len(submissions) <= 4 * 8
    assert len(submissions) < len(candidates) // 10
    assert pending_sizes
    assert max(pending_sizes) <= 4 * 2
    assert validate.call_count == len(candidates)
    assert tuple(request.index for request, _, _ in outcomes) == tuple(range(len(candidates)))


def test_probe_batching_handles_fewer_candidates_than_the_target_task_count(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 3)
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=2)
    submissions = 0

    class ImmediateExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            assert max_workers == 2

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def submit(fn: typing.Callable[..., typing.Any], *args: object) -> concurrent.futures.Future[typing.Any]:
            nonlocal submissions
            submissions += 1
            future: concurrent.futures.Future[typing.Any] = concurrent.futures.Future()
            future.set_result(fn(*args))
            return future

    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", new=ImmediateExecutor)

    outcomes = coordinator._validate_possible_hits(candidates)

    assert 1 <= submissions <= len(candidates)
    assert tuple(request.index for request, _, _ in outcomes) == (0, 1, 2)


def test_probe_batches_can_complete_out_of_order_without_reordering_results(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 20)
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=2)
    completion_order: list[int] = []

    class DeferredFuture(concurrent.futures.Future[typing.Any]):
        def __init__(self, start_index: int, fn: typing.Callable[..., typing.Any], args: tuple[object, ...]) -> None:
            super().__init__()
            self.start_index = start_index
            self.fn = fn
            self.args = args

        def complete(self) -> None:
            if not self.done():
                completion_order.append(self.start_index)
                try:
                    self.set_result(self.fn(*self.args))
                except BaseException as error:
                    self.set_exception(error)

    class DeferredExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            assert max_workers == 2

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def submit(fn: typing.Callable[..., typing.Any], *args: object) -> concurrent.futures.Future[typing.Any]:
            if fn is cache_coordinator._validate_source_batch:
                batch = typing.cast("tuple[tuple[cache_coordinator.CacheRequest, CleanProof], ...]", args[0])
                start = batch[0][0].index
            else:
                proof = typing.cast("CleanProof", args[1])
                start = int(proof.path_key.removeprefix("module-").removesuffix(".py"))
            return DeferredFuture(start, fn, args)

    def complete_one(
        fs: typing.Iterable[concurrent.futures.Future[typing.Any]], timeout: float | None = None, return_when: str = concurrent.futures.ALL_COMPLETED
    ) -> tuple[set[concurrent.futures.Future[typing.Any]], set[concurrent.futures.Future[typing.Any]]]:
        del timeout, return_when
        futures = set(fs)
        chosen = max(futures, key=lambda future: typing.cast("DeferredFuture", future).start_index)
        typing.cast("DeferredFuture", chosen).complete()
        return {chosen}, futures - {chosen}

    def complete_all(fs: typing.Iterable[concurrent.futures.Future[typing.Any]]) -> typing.Iterator[concurrent.futures.Future[typing.Any]]:
        futures = sorted(fs, key=lambda future: typing.cast("DeferredFuture", future).start_index, reverse=True)
        for future in futures:
            typing.cast("DeferredFuture", future).complete()
            yield future

    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", new=DeferredExecutor)
    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.wait", side_effect=complete_one, autospec=True)
    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.as_completed", side_effect=complete_all, autospec=True)

    outcomes = coordinator._validate_possible_hits(candidates)

    assert completion_order != sorted(completion_order)
    assert tuple(request.index for request, _, _ in outcomes) == tuple(range(len(candidates)))


def test_validate_source_batch_preserves_mixed_outcomes_and_validates_every_candidate_once(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 6)
    expected = (
        cache_coordinator._ProbeOutcome.HIT,
        cache_coordinator._ProbeOutcome.DIGEST_REJECTED,
        cache_coordinator._ProbeOutcome.READ_ERROR,
        cache_coordinator._ProbeOutcome.HIT,
        cache_coordinator._ProbeOutcome.READ_ERROR,
        cache_coordinator._ProbeOutcome.DIGEST_REJECTED,
    )

    def validate(path: str, proof: CleanProof) -> cache_coordinator._ProbeOutcome:
        del path
        index = int(proof.path_key.removeprefix("module-").removesuffix(".py"))
        return expected[index]

    validate_source = mocker.patch("pydocformatter.cache.coordinator._validate_source", side_effect=validate, autospec=True)

    outcomes = cache_coordinator._validate_source_batch(candidates)

    assert tuple(outcome for _, _, outcome in outcomes) == expected
    assert validate_source.call_count == len(candidates)


def test_rolling_batches_preserve_mixed_outcomes_within_and_across_batches(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 20)
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=2)
    possible = (cache_coordinator._ProbeOutcome.HIT, cache_coordinator._ProbeOutcome.DIGEST_REJECTED, cache_coordinator._ProbeOutcome.READ_ERROR)

    def validate(path: str, proof: CleanProof) -> cache_coordinator._ProbeOutcome:
        del path
        index = int(proof.path_key.removeprefix("module-").removesuffix(".py"))
        return possible[index % len(possible)]

    class ImmediateExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            assert max_workers == 2

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def submit(fn: typing.Callable[..., typing.Any], *args: object) -> concurrent.futures.Future[typing.Any]:
            future: concurrent.futures.Future[typing.Any] = concurrent.futures.Future()
            future.set_result(fn(*args))
            return future

    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", new=ImmediateExecutor)
    validate_source = mocker.patch("pydocformatter.cache.coordinator._validate_source", side_effect=validate, autospec=True)

    outcomes = coordinator._validate_possible_hits(candidates)

    assert tuple(outcome for _, _, outcome in outcomes) == tuple(possible[index % len(possible)] for index in range(len(candidates)))
    assert validate_source.call_count == len(candidates)


def test_unexpected_batch_validation_exception_propagates(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 20)
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=2)

    def validate(path: str, proof: CleanProof) -> cache_coordinator._ProbeOutcome:
        del path
        if proof.path_key == "module-5.py":
            raise RuntimeError("unexpected validation failure")
        return cache_coordinator._ProbeOutcome.HIT

    mocker.patch("pydocformatter.cache.coordinator._validate_source", side_effect=validate, autospec=True)

    with pytest.raises(RuntimeError, match="unexpected validation failure"):
        coordinator._validate_possible_hits(candidates)


def test_probe_worker_count_retains_the_thread_cap(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    candidates = _probe_candidates(target, 40)
    coordinator = cache_coordinator.CacheCoordinator(cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache")), engine_key=b"e" * 32, parallelism=100)
    created_workers: list[int | None] = []

    class ImmediateExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            created_workers.append(max_workers)

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def submit(fn: typing.Callable[..., typing.Any], *args: object) -> concurrent.futures.Future[typing.Any]:
            future: concurrent.futures.Future[typing.Any] = concurrent.futures.Future()
            future.set_result(fn(*args))
            return future

    mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", new=ImmediateExecutor)

    coordinator._validate_possible_hits(candidates)

    assert created_workers == [32]


def test_real_probe_threads_validate_each_source_once_with_configured_concurrency(tmp_path: Path, mocker: MockerFixture) -> None:
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for index, target in enumerate(targets):
        target.write_text(f"value = {index}\n", encoding="utf-8")
    proofs = tuple(dataclasses.replace(_proof_for(target), path_key=f"module-{index}.py") for index, target in enumerate(targets))
    requests = tuple(_request(target, index=index, path_key=proof.path_key) for index, (target, proof) in enumerate(zip(targets, proofs, strict=True)))
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=proofs)
    barrier = threading.Barrier(2)
    thread_ids: set[int] = set()
    lock = threading.Lock()
    original_validate = cache_coordinator._validate_source

    def validate(path: str, proof: CleanProof) -> cache_coordinator._ProbeOutcome:
        with lock:
            thread_ids.add(threading.get_ident())
        barrier.wait(timeout=5)
        return original_validate(path, proof)

    mocker.patch("pydocformatter.cache.coordinator._validate_source", side_effect=validate, autospec=True)
    source_digest = mocker.spy(formatter, "digest_source_file")

    probe = cache_coordinator.CacheCoordinator(store, engine_key=proofs[0].engine_key, parallelism=2).probe(requests)

    assert probe.stats.hits == 2
    assert len(thread_ids) == 2
    assert source_digest.call_count == 2


def test_row_absences_create_no_digest_executor(tmp_path: Path, mocker: MockerFixture) -> None:
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text("value = 1\n", encoding="utf-8")
    requests = tuple(_request(target, index=index, path_key=f"module-{index}.py") for index, target in enumerate(targets))
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    executor = mocker.patch("pydocformatter.cache.coordinator.concurrent.futures.ThreadPoolExecutor", side_effect=AssertionError("row absences must not create digest tasks"), autospec=True)

    probe = cache_coordinator.CacheCoordinator(store, engine_key=b"e" * 32, parallelism=4).probe(requests)

    assert probe.stats.hits == 0
    assert probe.stats.misses == 2
    executor.assert_not_called()


def test_probe_read_failure_falls_back_to_normal_miss(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    proof = _proof_for(target)
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=(proof,))
    target.unlink()

    probe = cache_coordinator.CacheCoordinator(store, engine_key=proof.engine_key, parallelism=1).probe((_request(target),))

    assert probe.hits == ()
    assert probe.miss_indexes == (0,)
    assert probe.stats.read_errors == 1


def test_probe_aggregates_mixed_outcomes_with_one_statistics_update(tmp_path: Path, mocker: MockerFixture) -> None:
    targets = tuple(tmp_path / f"{name}.py" for name in ("hit", "metadata", "digest", "read", "absent", "uncacheable"))
    for target in targets:
        target.write_text("value = 1\n", encoding="utf-8")
    proofs = (
        dataclasses.replace(_proof_for(targets[0]), path_key="hit.py"),
        dataclasses.replace(_proof_for(targets[1]), path_key="metadata.py", mtime_ns=targets[1].stat().st_mtime_ns + 1),
        dataclasses.replace(_proof_for(targets[2], digest=b"x" * 32), path_key="digest.py"),
        dataclasses.replace(_proof_for(targets[3]), path_key="read.py"),
    )
    requests = tuple(_request(target, index=index, path_key=f"{name}.py") for index, (name, target) in enumerate(zip(("hit", "metadata", "digest", "read", "absent"), targets[:5], strict=True)))
    requests = (*requests, _request(targets[5], index=5, path_key="uncacheable.py", cacheable=False))
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=proofs)
    targets[3].unlink()
    increment = mocker.spy(CacheStats, "increment")

    probe = cache_coordinator.CacheCoordinator(store, engine_key=b"e" * 32, parallelism=1).probe(requests)

    assert probe.stats == CacheStats(candidates=5, hits=1, metadata_rejected=1, digest_rejected=1, misses=4, uncacheable=1, read_errors=1)
    assert probe.miss_indexes == (1, 2, 3, 4, 5)
    assert increment.call_count == 1


def test_validated_hit_is_source_less_and_touch_is_not_rewritten_same_day(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    proof = _proof_for(target)
    store = cache_store.CacheStore(cache_directory.cache_layout(tmp_path / "cache"))
    store.commit(touches=(), proofs=(proof,))
    coordinator = cache_coordinator.CacheCoordinator(store, engine_key=proof.engine_key, parallelism=1)

    probe = coordinator.probe((_request(target),))
    stats = coordinator.persist(probe, {})
    result = probe.hits[0].result

    assert result == formatter.FormatterResult.cached_clean(str(target))
    assert result.old_source is None
    assert result.new_source is None
    assert not result.modified
    assert stats.hits == 1
    assert stats.writes == 0


def test_cached_clean_result_remains_compatible_with_summary_and_diff_output() -> None:
    result = formatter.FormatterResult.cached_clean("module.py")
    summary = io.StringIO()
    diff = io.StringIO()

    check_command.print_results([], [result], output_format=OutputFormat.GROUPED, output=summary)
    check_command.print_diff_results([result], output=diff)

    assert summary.getvalue() == "All checks passed!\n"
    assert diff.getvalue() == ""


def test_cold_clean_disk_execution_reads_once_and_returns_original_snapshot(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(select=("PDF300",))
    selection = rules_selection.select_rules(settings)
    real_open = typing.cast("typing.Callable[..., typing.IO[typing.Any]]", open)
    binary_opens = 0

    def counting_open(path: str, mode: str = "r", **kwargs: object) -> typing.IO[typing.Any]:
        nonlocal binary_opens
        if os.fspath(path) == str(target) and mode == "rb":
            binary_opens += 1
        return real_open(path, mode, **kwargs)

    mocker.patch("pydocformatter.formatter.open", side_effect=counting_open)
    execution = formatter.format_disk_file(_disk_request(target, settings, selection, fix=False, write=True, collect_clean_snapshot=True))

    assert execution.clean_snapshot is not None
    assert execution.clean_snapshot.source_digest == formatter.digest_source_bytes(target.read_bytes())
    assert binary_opens == 1


@pytest.mark.parametrize("collect_clean_snapshot", [False, True])
def test_disk_execution_only_reads_metadata_for_clean_snapshots(tmp_path: Path, mocker: MockerFixture, collect_clean_snapshot: bool) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(select=("PDF300",))
    selection = rules_selection.select_rules(settings)
    fstat = mocker.spy(formatter.os, "fstat")

    execution = formatter.format_disk_file(_disk_request(target, settings, selection, fix=False, write=True, collect_clean_snapshot=collect_clean_snapshot))

    assert not execution.result.errors
    assert fstat.call_count == int(collect_clean_snapshot)


def test_disk_execution_releases_raw_bytes_before_parsing(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(select=("PDF300",))
    selection = rules_selection.select_rules(settings)
    real_parse_module = formatter.cst.parse_module

    class TrackedBytes(bytes):
        released = False

        def __del__(self) -> None:
            type(self).released = True

    class BinaryReader:
        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return TrackedBytes(b'"""Module."""\n')

    def asserting_parse_module(source: str) -> object:
        gc.collect()
        assert TrackedBytes.released
        return real_parse_module(source)

    mocker.patch("pydocformatter.formatter.open", return_value=BinaryReader())
    mocker.patch("pydocformatter.formatter.cst.parse_module", side_effect=asserting_parse_module)

    execution = formatter.format_disk_file(_disk_request(target, settings, selection, fix=False, write=True, collect_clean_snapshot=False))

    assert not execution.result.errors


def test_dirty_check_and_diff_execution_never_populate(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    settings = CheckSettings(select=("PDF300",))
    selection = rules_selection.select_rules(settings)
    checked = formatter.format_disk_file(_disk_request(target, settings, selection, fix=False, write=True, collect_clean_snapshot=True))
    diffed = formatter.format_disk_file(_disk_request(target, settings, selection, fix=True, write=False, collect_clean_snapshot=True))

    assert checked.clean_snapshot is None
    assert diffed.clean_snapshot is None
    assert target.read_text(encoding="utf-8") == '"""Summary"""\n'


def test_successful_clean_fix_records_post_write_bytes(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    settings = CheckSettings(select=("PDF300",))
    selection = rules_selection.select_rules(settings)

    execution = formatter.format_disk_file(_disk_request(target, settings, selection, fix=True, write=True, collect_clean_snapshot=True))

    assert execution.result.modified
    assert target.read_text(encoding="utf-8") == '"""Summary."""\n'
    assert execution.clean_snapshot is not None
    assert execution.clean_snapshot.source_digest == formatter.digest_source_bytes(target.read_bytes())
    assert execution.clean_snapshot.source_size == target.stat().st_size
    assert execution.clean_snapshot.mtime_ns == target.stat().st_mtime_ns


def test_partial_write_never_populates_cache(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    settings = CheckSettings(select=("PDF300",))
    selection = rules_selection.select_rules(settings)
    real_open = typing.cast("typing.Callable[..., typing.IO[typing.Any]]", open)

    class PartialWriter:
        def __init__(self) -> None:
            self.calls = 0

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def write(self, source: str) -> int:
            self.calls += 1
            return len(source) - 1

    def partial_open(path: str, mode: str = "r", **kwargs: object) -> typing.IO[typing.Any] | PartialWriter:
        if os.fspath(path) == str(target) and mode == "w":
            return PartialWriter()
        return real_open(path, mode, **kwargs)

    mocker.patch("pydocformatter.formatter.open", side_effect=partial_open)
    execution = formatter.format_disk_file(_disk_request(target, settings, selection, fix=True, write=True, collect_clean_snapshot=True))

    assert execution.result.errors
    assert not execution.result.modified
    assert execution.clean_snapshot is None
    assert target.read_text(encoding="utf-8") == '"""Summary"""\n'


def test_post_write_stat_failure_keeps_clean_snapshot_without_mtime(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    settings = CheckSettings(select=("PDF300",))
    selection = rules_selection.select_rules(settings)
    mocker.patch("pydocformatter.formatter.os.stat", side_effect=OSError("stat failed"), autospec=True)

    execution = formatter.format_disk_file(_disk_request(target, settings, selection, fix=True, write=True, collect_clean_snapshot=True))

    assert execution.clean_snapshot is not None
    assert execution.clean_snapshot.mtime_ns is None


def test_first_clean_cli_run_analyzes_and_second_run_skips_parsing(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    argv = ["pydocfmt", "check", "--cache-dir", str(cache), "--parallelism", "1", str(target)]

    cold = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)
    parse = mocker.patch("pydocformatter.formatter.cst.parse_module", side_effect=AssertionError("warm hit must not parse"), autospec=True)
    warm = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)

    assert cold == warm
    assert warm.exit_code == 0
    assert warm.stdout == "All checks passed!\n"
    parse.assert_not_called()


def test_all_hit_cli_run_does_not_instantiate_process_pool(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    targets = (tmp_path / "a.py", tmp_path / "b.py")
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    argv = ["pydocfmt", "check", "--cache-dir", str(cache), "--parallelism", "2", *(str(target) for target in targets)]
    cold = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)
    executor = mocker.patch("pydocformatter.cli.check.concurrent.futures.ProcessPoolExecutor", side_effect=AssertionError("all-hit run must not create workers"), autospec=True)

    warm = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)

    assert cold == warm
    executor.assert_not_called()


def test_mixed_hit_miss_pool_is_sized_from_misses_and_preserves_order(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    settings = CheckSettings(cache_dir=str(cache), parallelism=3.0)
    profile = _profile(settings, tmp_path)
    targets = tuple(tmp_path / f"{name}.py" for name in ("a", "b", "c"))
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=profile) for target in targets)
    selection = rules_selection.select_rules(settings, profile=profile)
    selections = {profile.key(): selection}
    check_command.format_selected_files(selected_files, rule_selections=selections, use_stdin=False, fix=False, write=True, parallelism=3.0, cache_profile=profile)
    targets[0].write_text('"""Changed module."""\n', encoding="utf-8")
    targets[2].write_text('"""Another changed module."""\n', encoding="utf-8")
    created_workers = []

    class ImmediateExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            created_workers.append(max_workers)
            self.submissions = 0

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def submit(self, fn: typing.Callable[[formatter.DiskFormatRequest], formatter.DiskFormatResult], request: formatter.DiskFormatRequest) -> concurrent.futures.Future[formatter.DiskFormatResult]:
            self.submissions += 1
            future: concurrent.futures.Future[formatter.DiskFormatResult] = concurrent.futures.Future()
            future.set_result(fn(request))
            return future

    batch = check_command.format_selected_files(
        selected_files,
        rule_selections=selections,
        use_stdin=False,
        fix=False,
        write=True,
        parallelism=3.0,
        cache_profile=profile,
        executor_factory=typing.cast("check_command._ExecutorFactory", ImmediateExecutor),
    )

    assert created_workers == [2]
    assert [result.path for result in batch.results] == [str(target) for target in targets]
    assert batch.results[1] == formatter.FormatterResult.cached_clean(str(targets[1]))


def test_one_miss_after_warm_population_stays_sequential(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    settings = CheckSettings(cache_dir=str(cache), parallelism=4.0)
    profile = _profile(settings, tmp_path)
    targets = (tmp_path / "a.py", tmp_path / "b.py")
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=profile) for target in targets)
    selection = rules_selection.select_rules(settings, profile=profile)
    selections = {profile.key(): selection}
    check_command.format_selected_files(selected_files, rule_selections=selections, use_stdin=False, fix=False, write=True, parallelism=4.0, cache_profile=profile)
    targets[0].write_text('"""Changed module."""\n', encoding="utf-8")

    def fail_executor(*args: object, **kwargs: object) -> typing.NoReturn:
        del args, kwargs
        raise AssertionError("One miss must not create an executor")

    batch = check_command.format_selected_files(
        selected_files,
        rule_selections=selections,
        use_stdin=False,
        fix=False,
        write=True,
        parallelism=4.0,
        cache_profile=profile,
        executor_factory=typing.cast("check_command._ExecutorFactory", fail_executor),
    )

    assert batch.results[0].old_source == '"""Changed module."""\n'
    assert batch.results[1] == formatter.FormatterResult.cached_clean(str(targets[1]))


def test_homogeneous_files_share_one_analysis_fingerprint_but_keep_file_identities_independent(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    targets = tuple(tmp_path / f"{name}.py" for name in ("a", "b", "c"))
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=profile) for target in targets)
    selection = rules_selection.select_rules(settings, profile=profile)
    analysis_fingerprint = mocker.spy(cache_fingerprint, "analysis_fingerprint")
    path_fingerprints = mocker.spy(cache_fingerprint.PathFingerprintBuilder, "fingerprints")
    source_context = mocker.spy(SourcePathContextBuilder, "for_path")
    source_digest = mocker.spy(formatter, "digest_source_bytes")

    check_command.format_selected_files(selected_files, rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert analysis_fingerprint.call_count == 1
    assert path_fingerprints.call_count == len(targets)
    assert source_context.call_count == len(targets)
    assert source_digest.call_count == len(targets)


def test_distinct_semantic_pairs_each_construct_one_shared_analysis_fingerprint(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    first_settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), line_length=88, parallelism=1.0)
    second_settings = dataclasses.replace(first_settings, line_length=100)
    first_profile = _profile(first_settings, tmp_path)
    second_profile = _profile(second_settings, tmp_path)
    targets = tuple(tmp_path / f"{name}.py" for name in ("a", "b", "c", "d"))
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=first_profile if index < 2 else second_profile) for index, target in enumerate(targets))
    selections = {first_profile.key(): rules_selection.select_rules(first_settings, profile=first_profile), second_profile.key(): rules_selection.select_rules(second_settings, profile=second_profile)}
    analysis_fingerprint = mocker.spy(cache_fingerprint, "analysis_fingerprint")
    path_fingerprints = mocker.spy(cache_fingerprint.PathFingerprintBuilder, "fingerprints")

    check_command.format_selected_files(selected_files, rule_selections=selections, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=first_profile)

    assert analysis_fingerprint.call_count == 2
    assert path_fingerprints.call_count == len(targets)


def test_distinct_profile_objects_with_equal_semantic_identities_share_one_analysis_fingerprint(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    first_profile = _profile(settings, tmp_path)
    second_profile = dataclasses.replace(first_profile, field_priorities={field: priority + 1 for field, priority in first_profile.field_priorities.items()})
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = (file_selection.SelectedFile(path=str(targets[0]), profile=first_profile), file_selection.SelectedFile(path=str(targets[1]), profile=second_profile))
    selections = {
        first_profile.key(): rules_selection.select_rules(first_profile.settings, profile=first_profile),
        second_profile.key(): rules_selection.select_rules(second_profile.settings, profile=second_profile),
    }
    analysis_fingerprint = mocker.spy(cache_fingerprint, "analysis_fingerprint")

    check_command.format_selected_files(selected_files, rule_selections=selections, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=first_profile)

    assert first_profile is not second_profile
    assert settings_check.analysis_settings_identity(first_profile) == settings_check.analysis_settings_identity(second_profile)
    assert analysis_fingerprint.call_count == 1


def test_shared_analysis_fingerprint_failure_fails_closed_for_every_matching_request(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    targets = tuple(tmp_path / f"{name}.py" for name in ("a", "b", "c"))
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=profile) for target in targets)
    selection = rules_selection.select_rules(settings, profile=profile)
    analysis_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.analysis_fingerprint", side_effect=ValueError("encoding failure"), autospec=True)
    path_fingerprints = mocker.spy(cache_fingerprint.PathFingerprintBuilder, "fingerprints")
    batch = check_command.format_selected_files(selected_files, rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert all(result.errors == () for result in batch.results)
    assert analysis_fingerprint.call_count == 1
    assert path_fingerprints.call_count == 0
    assert batch.cache_stats.uncacheable == len(targets)
    assert batch.cache_stats.store_errors == 1
    assert not cache.exists()


def test_analysis_fingerprint_failure_is_independent_for_a_different_semantic_pair(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    first_settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), line_length=88, parallelism=1.0)
    second_settings = dataclasses.replace(first_settings, line_length=100)
    first_profile = _profile(first_settings, tmp_path)
    second_profile = _profile(second_settings, tmp_path)
    targets = tuple(tmp_path / f"{name}.py" for name in ("a", "b", "c", "d"))
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=first_profile if index < 2 else second_profile) for index, target in enumerate(targets))
    selections = {first_profile.key(): rules_selection.select_rules(first_settings, profile=first_profile), second_profile.key(): rules_selection.select_rules(second_settings, profile=second_profile)}
    first_identity = settings_check.analysis_settings_identity(first_profile)
    original_analysis_fingerprint = cache_fingerprint.analysis_fingerprint

    def construct(identity: tuple[tuple[str, object], ...], selected_rules: tuple[rules_selection.SelectedRule, ...]) -> tuple[object, bytes]:
        if identity == first_identity:
            raise ValueError("first pair cannot be encoded")
        return original_analysis_fingerprint(identity, selected_rules)

    analysis_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.analysis_fingerprint", side_effect=construct, autospec=True)
    path_fingerprints = mocker.spy(cache_fingerprint.PathFingerprintBuilder, "fingerprints")
    batch = check_command.format_selected_files(selected_files, rule_selections=selections, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=first_profile)

    assert all(result.errors == () for result in batch.results)
    assert analysis_fingerprint.call_count == 2
    assert path_fingerprints.call_count == 2
    assert batch.cache_stats.candidates == 2
    assert batch.cache_stats.uncacheable == 2
    assert batch.cache_stats.writes == 2
    assert batch.cache_stats.store_errors == 1


def test_cache_disabled_run_uses_source_context_builder_but_skips_all_persistent_fingerprint_construction(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(cache=False, cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    selection = rules_selection.select_rules(settings, profile=profile)
    selected_file = file_selection.SelectedFile(path=str(target), profile=profile)
    engine_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.engine_fingerprint", side_effect=AssertionError("disabled cache must not construct an engine key"), autospec=True)
    analysis_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.analysis_fingerprint", side_effect=AssertionError("disabled cache must not construct an analysis key"), autospec=True)
    path_builder = mocker.patch("pydocformatter.cache.fingerprint.PathFingerprintBuilder", side_effect=AssertionError("disabled cache must not construct path fingerprints"), autospec=True)
    source_context = mocker.spy(SourcePathContextBuilder, "for_path")
    batch = check_command.format_selected_files((selected_file,), rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert batch.results[0].errors == ()
    assert batch.cache_stats.uncacheable == 1
    assert not cache.exists()
    engine_fingerprint.assert_not_called()
    analysis_fingerprint.assert_not_called()
    path_builder.assert_not_called()
    assert source_context.call_count == 1


def test_missing_parent_preflight_returns_batch_warning_and_skips_all_cache_identity_work(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    cache = tmp_path / "missing" / "cache"
    settings = CheckSettings(cache_dir=str(cache), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    selection = rules_selection.select_rules(settings, profile=profile)
    selected_file = file_selection.SelectedFile(path=str(target), profile=profile)
    engine_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.engine_fingerprint", side_effect=AssertionError("missing parent must skip engine identity"), autospec=True)
    analysis_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.analysis_fingerprint", side_effect=AssertionError("missing parent must skip analysis identity"), autospec=True)
    path_builder = mocker.patch("pydocformatter.cache.fingerprint.PathFingerprintBuilder", side_effect=AssertionError("missing parent must skip path identity"), autospec=True)
    store = mocker.patch("pydocformatter.cache.session.cache_store.CacheStore", side_effect=AssertionError("missing parent must skip cache lookup and persistence"), autospec=True)

    batch = check_command.format_selected_files((selected_file,), rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert isinstance(batch, check_command.FormatBatchResult)
    assert len(batch.results) == 1
    assert batch.cache_stats == CacheStats(uncacheable=1, store_errors=1)
    assert batch.warnings == (f"pydocfmt check: Cache warning: Cache directory parent does not exist or is not a directory; running without persistent cache: {cache.parent}",)
    assert not cache.parent.exists()
    engine_fingerprint.assert_not_called()
    analysis_fingerprint.assert_not_called()
    path_builder.assert_not_called()
    store.assert_not_called()


def test_parent_becoming_unavailable_after_preflight_surfaces_the_same_warning(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    cache = tmp_path / "state" / "cache"
    cache.parent.mkdir()
    settings = CheckSettings(cache_dir=str(cache), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    selected_file = file_selection.SelectedFile(path=str(target), profile=profile)

    def remove_parent() -> None:
        cache.parent.rmdir()

    mocker.patch("pydocformatter.cache.fingerprint.engine_fingerprint", side_effect=remove_parent, autospec=True)

    batch = check_command.format_selected_files(
        (selected_file,), rule_selections={profile.key(): rules_selection.select_rules(settings, profile=profile)}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile
    )

    assert batch.cache_stats == CacheStats(uncacheable=1, store_errors=1)
    assert batch.warnings == (f"pydocfmt check: Cache warning: Cache directory parent does not exist or is not a directory; running without persistent cache: {cache.parent}",)


def test_format_batch_result_is_frozen_for_empty_and_normal_disk_batches(tmp_path: Path) -> None:
    empty = check_command.format_selected_files((), rule_selections={}, use_stdin=False, fix=False, write=True, parallelism=1.0)
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(parallelism=1.0)
    profile = _profile(settings, tmp_path)
    selected_file = file_selection.SelectedFile(path=str(target), profile=profile)
    normal = check_command.format_selected_files(
        (selected_file,), rule_selections={profile.key(): rules_selection.select_rules(settings, profile=profile)}, use_stdin=False, fix=False, write=True, parallelism=1.0
    )

    assert empty == check_command.FormatBatchResult(results=(), cache_stats=CacheStats(), warnings=())
    assert isinstance(normal.results, tuple)
    assert normal.cache_stats == CacheStats(uncacheable=1)
    assert normal.warnings == ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        normal.__setattr__("warnings", ("changed",))


def test_process_pool_receives_only_lean_worker_requests(tmp_path: Path) -> None:
    settings = CheckSettings(parallelism=2.0)
    profile = _profile(settings, tmp_path)
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=profile) for target in targets)
    selection = rules_selection.select_rules(settings, profile=profile)
    received: list[formatter.DiskFormatRequest] = []

    class ImmediateExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            assert max_workers == 2

        def __enter__(self) -> typing.Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def submit(fn: typing.Callable[[formatter.DiskFormatRequest], formatter.DiskFormatResult], request: formatter.DiskFormatRequest) -> concurrent.futures.Future[formatter.DiskFormatResult]:
            received.append(request)
            future: concurrent.futures.Future[formatter.DiskFormatResult] = concurrent.futures.Future()
            future.set_result(fn(request))
            return future

    batch = check_command.format_selected_files(
        selected_files,
        rule_selections={profile.key(): selection},
        use_stdin=False,
        fix=False,
        write=True,
        parallelism=2.0,
        executor_factory=typing.cast("check_command._ExecutorFactory", ImmediateExecutor),
    )

    assert tuple(field.name for field in dataclasses.fields(formatter.DiskFormatRequest)) == ("path", "settings", "execution_plan", "source_path", "fix", "write", "collect_clean_snapshot")
    assert tuple(request.path for request in received) == tuple(str(target) for target in targets)
    assert all(request.settings is settings for request in received)
    assert all(not request.collect_clean_snapshot for request in received)
    assert all(not request.execution_plan.collection.categories or request.execution_plan.collection is selection.collection for request in received)
    assert tuple(result.path for result in batch.results) == tuple(str(target) for target in targets)


def test_uncacheable_selected_rule_bypasses_lookup_population_and_cache_only_fingerprints(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    selection = rules_selection.select_rules(settings, profile=profile)
    uncacheable_rule = dataclasses.replace(selection.rules[0].rule, cache_behavior=RuleCacheBehavior.UNCACHEABLE)
    uncacheable_selection = dataclasses.replace(selection, rules=(dataclasses.replace(selection.rules[0], rule=uncacheable_rule),))
    selected_file = file_selection.SelectedFile(path=str(target), profile=profile)
    engine_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.engine_fingerprint", side_effect=AssertionError("fully uncacheable runs must not construct an engine key"), autospec=True)
    analysis_fingerprint = mocker.patch("pydocformatter.cache.fingerprint.analysis_fingerprint", side_effect=AssertionError("uncacheable files must not construct an analysis key"), autospec=True)
    path_fingerprints = mocker.patch.object(
        cache_fingerprint.PathFingerprintBuilder, "fingerprints", side_effect=AssertionError("uncacheable files must not construct path fingerprints"), autospec=True
    )
    source_context = mocker.spy(SourcePathContextBuilder, "for_path")
    batch = check_command.format_selected_files(
        (selected_file,), rule_selections={profile.key(): uncacheable_selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile
    )

    assert batch.results[0].errors == ()
    assert batch.cache_stats.uncacheable == 1
    assert not cache.exists()
    engine_fingerprint.assert_not_called()
    analysis_fingerprint.assert_not_called()
    path_fingerprints.assert_not_called()
    assert source_context.call_count == 1


def test_cache_key_failure_degrades_to_uncached_execution(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    selection = rules_selection.select_rules(settings, profile=profile)
    selected_file = file_selection.SelectedFile(path=str(target), profile=profile)
    mocker.patch("pydocformatter.cache.fingerprint.analysis_fingerprint", side_effect=ValueError("encoding failure"), autospec=True)

    batch = check_command.format_selected_files((selected_file,), rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert batch.results[0].errors == ()
    assert batch.cache_stats.uncacheable == 1
    assert batch.cache_stats.store_errors == 1
    assert not cache.exists()


def test_path_fingerprint_failure_degrades_each_affected_request_to_uncached_execution(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=profile) for target in targets)
    selection = rules_selection.select_rules(settings, profile=profile)
    path_fingerprints = mocker.patch.object(cache_fingerprint.PathFingerprintBuilder, "fingerprints", side_effect=ValueError("path encoding failure"), autospec=True)
    batch = check_command.format_selected_files(selected_files, rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert all(result.errors == () for result in batch.results)
    assert path_fingerprints.call_count == len(targets)
    assert batch.cache_stats.uncacheable == len(targets)
    assert batch.cache_stats.store_errors == len(targets)
    assert not cache.exists()


def test_path_fingerprint_builder_construction_failure_disables_caching_for_the_invocation(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    selection = rules_selection.select_rules(settings, profile=profile)
    selected_file = file_selection.SelectedFile(path=str(target), profile=profile)
    mocker.patch("pydocformatter.cache.fingerprint.PathFingerprintBuilder", side_effect=ValueError("root encoding failure"), autospec=True)
    analysis_fingerprint = mocker.spy(cache_fingerprint, "analysis_fingerprint")
    batch = check_command.format_selected_files((selected_file,), rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert batch.results[0].errors == ()
    analysis_fingerprint.assert_not_called()
    assert batch.cache_stats.uncacheable == 1
    assert batch.cache_stats.store_errors == 1
    assert not cache.exists()


def test_engine_fingerprint_failure_is_counted_once_and_makes_every_file_uncacheable(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    settings = CheckSettings(cache_dir=str(cache), select=("PDF300",), parallelism=1.0)
    profile = _profile(settings, tmp_path)
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text('"""Module."""\n', encoding="utf-8")
    selected_files = tuple(file_selection.SelectedFile(path=str(target), profile=profile) for target in targets)
    selection = rules_selection.select_rules(settings, profile=profile)
    mocker.patch("pydocformatter.cache.fingerprint.engine_fingerprint", side_effect=cache_fingerprint.CacheFingerprintError("engine unavailable"), autospec=True)
    analysis_fingerprint = mocker.spy(cache_fingerprint, "analysis_fingerprint")

    batch = check_command.format_selected_files(selected_files, rule_selections={profile.key(): selection}, use_stdin=False, fix=False, write=True, parallelism=1.0, cache_profile=profile)

    assert batch.cache_stats.uncacheable == len(targets)
    assert batch.cache_stats.store_errors == 1
    assert all(result.errors == () for result in batch.results)
    analysis_fingerprint.assert_not_called()


def test_package_context_change_invalidates_a_clean_proof(tmp_path: Path) -> None:
    private_package = tmp_path / "_private"
    private_package.mkdir()
    target = private_package / "module.py"
    cache = tmp_path / "cache"
    target.write_text("", encoding="utf-8")
    argv = ["pydocfmt", "check", "--cache-dir", str(cache), "--select", "PDF603", str(target)]

    first = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)
    (private_package / "__init__.py").write_text("", encoding="utf-8")
    second = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)

    assert first.exit_code == 0
    assert second.exit_code == 1
    assert "PDF603" in second.stdout


def test_cache_stats_are_opt_in_and_do_not_change_status(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    base_argv = ["pydocfmt", "check", "--cache-dir", str(cache), str(target)]
    cold = cli_helpers.run_cli(pydocfmt_cli.main, base_argv, cwd=tmp_path)
    warm = cli_helpers.run_cli(pydocfmt_cli.main, [*base_argv, "--cache-stats"], cwd=tmp_path)

    assert warm.exit_code == cold.exit_code
    assert warm.stdout == cold.stdout
    assert warm.stderr == "Cache: candidates=1 hits=1 metadata-rejected=0 digest-rejected=0 misses=0 uncacheable=0 read-errors=0 writes=0 store-errors=0\n"
