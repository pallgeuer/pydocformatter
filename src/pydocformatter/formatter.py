"""File and stdin formatting orchestration.

Attributes:
    UTF8_BOM (str): Unicode byte order mark stripped from decoded UTF-8 source before LibCST parsing and rule execution.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import typing
import hashlib
import collections
import dataclasses

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.runner as rule_runner
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules import line_endings
from pydocformatter.rules.models import RuleFinding, RuleMetadata
from pydocformatter.rules_selection import RuleExecutionPlan
from pydocformatter.source_path import SourcePathContext


if typing.TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules_selection import RuleSelection


UTF8_BOM = "\ufeff"
_SOURCE_DIGEST_LABEL = b"pydocfmt-source-v1\0"
_READ_CHUNK_SIZE = 1024 * 1024


@dataclasses.dataclass(frozen=True)
class FormatterResult:
    """Formatter result for one display path.

    Attributes:
        path (str): Display path used for diagnostics and diff headers.
        old_source (str | None): Source text before formatting, or None when unavailable or intentionally not
            materialized for a cached clean result.
        new_source (str | None): Source text after formatting, or None when unavailable or intentionally not
            materialized for a cached clean result.
        modified (bool): Whether formatting changed the source and the result represents a successful source state.
        fixed_findings (collections.Counter[RuleMetadata]): Counts of fixed findings keyed by rule metadata.
        unfixed_findings (tuple[RuleFinding, ...]): Remaining rule findings after formatting, with line numbers aligned
            to new_source.
        errors (tuple[str, ...]): Operational errors that prevented normal formatting or writing.
    """

    path: str
    old_source: str | None
    new_source: str | None
    modified: bool
    fixed_findings: collections.Counter[RuleMetadata]
    unfixed_findings: tuple[RuleFinding, ...]
    errors: tuple[str, ...]

    @classmethod
    def cached_clean(cls, path: str) -> FormatterResult:
        """Return the explicit source-less result for a validated clean-proof hit.

        Args:
            path (str): Display path represented by the cached result.

        Returns:
            FormatterResult: Finding-free unchanged result without materialized source text.
        """
        return cls(path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())


@dataclasses.dataclass(frozen=True)
class DiskFormatRequest:
    """Fully resolved inputs for one disk-backed formatter execution.

    Attributes:
        path (str): Display and filesystem path to format.
        settings (CheckSettings): Effective settings for the source path.
        execution_plan (RuleExecutionPlan): Lean path-specific rule execution plan.
        source_path (SourcePathContext): Precomputed source-path semantics.
        fix (bool): Whether selected fixes should be applied.
        write (bool): Whether modified source should be written back to disk.
        collect_clean_snapshot (bool): Whether to return a clean source identity for cache persistence.
    """

    path: str
    settings: CheckSettings
    execution_plan: RuleExecutionPlan
    source_path: SourcePathContext
    fix: bool
    write: bool
    collect_clean_snapshot: bool


@dataclasses.dataclass(frozen=True)
class CleanSourceSnapshot:
    """Complete identity of a clean source state eligible for persistence.

    Attributes:
        source_digest (bytes): Digest of the final clean on-disk bytes.
        source_size (int): Exact length of the final clean on-disk bytes.
        mtime_ns (int | None): Optional negative-only modification-time hint retained only for matching source size.
    """

    source_digest: bytes
    source_size: int
    mtime_ns: int | None


@dataclasses.dataclass(frozen=True)
class DiskFormatResult:
    """Formatter result and optional cache evidence from one disk worker.

    Attributes:
        result (FormatterResult): User-visible formatting result.
        clean_snapshot (CleanSourceSnapshot | None): Complete eligible clean state, or None when persistence is not
            requested or the final disk state is not proven clean.
    """

    result: FormatterResult
    clean_snapshot: CleanSourceSnapshot | None


def format_stream(path: str, *, file: typing.TextIO, settings: CheckSettings, rule_selection: RuleSelection, fix: bool) -> FormatterResult:
    """Run the rule-based formatter for one open text stream.

    Args:
        path (str): Display path used for diagnostics and path-specific rule selection.
        file (typing.TextIO): Open text stream to read once without writing.
        settings (CheckSettings): Resolved formatter settings.
        rule_selection (RuleSelection): Precomputed rule selection for the settings profile.
        fix (bool): Whether fixes should be applied to the returned source.

    Returns:
        FormatterResult: Formatting result with source text, findings, and operational errors.

    Raises:
        AssertionError: If `format_source` returns an invalid result without source text.
    """
    try:
        source = file.read()
    except UnicodeDecodeError as error:
        return FormatterResult(
            path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(f"Failed to decode {path} as UTF-8: {error}",)
        )
    except OSError as error:
        return FormatterResult(path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(f"Failed to read file {path}: {error}",))

    result = format_source(source, path, settings=settings, rule_selection=rule_selection, fix=fix)
    if result.old_source is None or result.new_source is None:
        raise AssertionError("format_source() must return a valid source state")
    return result


def format_disk_file(request: DiskFormatRequest) -> DiskFormatResult:
    """Read, format, and optionally write one fully resolved disk request.

    Args:
        request (DiskFormatRequest): Path, settings, execution plan, source context, mode, and snapshot policy.

    Returns:
        DiskFormatResult: User-visible result and optional complete clean source snapshot.

    Raises:
        AssertionError: If the strict source formatter returns an invalid result without source text.
    """
    path = request.path
    try:
        with open(path, "rb") as path_file:
            original_mtime_ns = None
            original_stat_size = None
            if request.collect_clean_snapshot:
                try:
                    original_stat = os.fstat(path_file.fileno())
                except OSError:
                    pass
                else:
                    original_stat_size = original_stat.st_size
                    original_mtime_ns = original_stat.st_mtime_ns
            source_bytes = path_file.read()
    except OSError as error:
        result = FormatterResult(
            path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(f"Failed to read file {path}: {error}",)
        )
        return DiskFormatResult(result=result, clean_snapshot=None)

    original_size = len(source_bytes)
    original_digest = digest_source_bytes(source_bytes) if request.collect_clean_snapshot else None
    if original_stat_size != original_size:
        original_mtime_ns = None
    try:
        source = source_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        result = FormatterResult(
            path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(f"Failed to decode {path} as UTF-8: {error}",)
        )
        return DiskFormatResult(result=result, clean_snapshot=None)
    del source_bytes

    result = _format_source_plan(source, path, settings=request.settings, execution_plan=request.execution_plan, fix=request.fix, source_path=request.source_path)
    if result.old_source is None or result.new_source is None:
        raise AssertionError("format_source() must return a valid source state")

    wrote_source = False
    if request.fix and request.write and result.modified:
        try:
            with open(path, "w", encoding="utf-8", newline="") as path_file:
                written = path_file.write(result.new_source)
                _require_complete_write(written, expected=len(result.new_source))
            wrote_source = True
        except OSError as error:
            failed_result = FormatterResult(
                path=path,
                old_source=result.old_source,
                new_source=result.old_source,
                modified=False,
                fixed_findings=collections.Counter(),
                unfixed_findings=(),
                errors=(f"Failed to write file {path}: {error}",),
            )
            return DiskFormatResult(result=failed_result, clean_snapshot=None)

    clean_snapshot: CleanSourceSnapshot | None = None
    if request.collect_clean_snapshot and not result.errors and not result.unfixed_findings:
        if result.modified and wrote_source:
            new_bytes = result.new_source.encode("utf-8")
            written_size = len(new_bytes)
            try:
                written_stat = os.stat(path)
            except OSError:
                written_mtime_ns = None
            else:
                written_mtime_ns = written_stat.st_mtime_ns if written_stat.st_size == written_size else None
            clean_snapshot = CleanSourceSnapshot(source_digest=digest_source_bytes(new_bytes), source_size=written_size, mtime_ns=written_mtime_ns)
        elif not result.modified:
            if original_digest is None:
                raise AssertionError("Clean snapshot collection requires an original source digest")
            clean_snapshot = CleanSourceSnapshot(source_digest=original_digest, source_size=original_size, mtime_ns=original_mtime_ns)
    return DiskFormatResult(result=result, clean_snapshot=clean_snapshot)


def digest_source_bytes(source_bytes: bytes) -> bytes:
    """Return the domain-separated SHA-256 digest of complete raw source bytes.

    Args:
        source_bytes (bytes): Complete source contents in their original byte representation.

    Returns:
        bytes: Exact SHA-256 cache digest for the source contents.
    """
    digest = hashlib.sha256()
    digest.update(_SOURCE_DIGEST_LABEL)
    digest.update(source_bytes)
    return digest.digest()


def digest_source_file(file: typing.BinaryIO) -> tuple[bytes, int]:
    """Read a binary stream completely and return its source digest and length.

    Args:
        file (typing.BinaryIO): Binary source stream positioned at the beginning of the contents to hash.

    Returns:
        tuple[bytes, int]: Exact SHA-256 cache digest and byte count.

    Raises:
        TypeError: If the stream yields text rather than bytes.
    """
    digest = hashlib.sha256()
    digest.update(_SOURCE_DIGEST_LABEL)
    size = 0
    while True:
        chunk = file.read(_READ_CHUNK_SIZE)
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise TypeError("Source digest file must be opened in binary mode")
        digest.update(chunk)
        size += len(chunk)
    return digest.digest(), size


def _require_complete_write(written: int, *, expected: int) -> None:
    """Raise an output error when a text stream reports a partial write."""
    if written != expected:
        raise OSError(f"incomplete write: wrote {written} of {expected} characters")


def format_source(source: str, path: str, *, settings: CheckSettings, rule_selection: RuleSelection, fix: bool) -> FormatterResult:
    """Run the rule-based formatter for source text.

    Args:
        source (str): Python source text to format.
        path (str): Display path used for diagnostics.
        settings (CheckSettings): Resolved formatter settings.
        rule_selection (RuleSelection): Precomputed rule selection for the settings profile.
        fix (bool): Whether fixes should be applied to the returned source.

    Returns:
        FormatterResult: Formatting result for the supplied source text.
    """
    return _format_source_plan(source, path, settings=settings, execution_plan=rule_selection.execution_plan_for_path(path), fix=fix, source_path=SourcePathContext.for_path(path))


def _format_source_plan(source: str, path: str, *, settings: CheckSettings, execution_plan: RuleExecutionPlan, fix: bool, source_path: SourcePathContext) -> FormatterResult:
    """Format source through one fully resolved rule and source-path plan."""
    try:
        module = cst.parse_module(source)
    except Exception as error:
        return FormatterResult(
            path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(f"Failed to parse {path} with LibCST: {error}",)
        )

    line_ending = line_endings.resolve_line_ending(source, line_ending=settings.line_ending)
    run_result = rule_runner.run_rule_plan(module, path=path, settings=settings, line_ending=line_ending, execution_plan=execution_plan, fix=fix, source=source, source_path=source_path)
    fixed_findings = collections.Counter(finding.rule for finding in run_result.fixed_findings)
    errors = list(run_result.errors)

    if run_result.source_changed:
        try:
            new_source = run_result.module.code
            if source.startswith(UTF8_BOM) and not new_source.startswith(UTF8_BOM):
                new_source = UTF8_BOM + new_source
        except Exception as error:
            errors.append(f"Failed to generate formatted source for {path}: {error}")
            new_source = source
            fixed_findings.clear()
    else:
        new_source = source

    return FormatterResult(
        path=path, old_source=source, new_source=new_source, modified=(new_source != source), fixed_findings=fixed_findings, unfixed_findings=run_result.unfixed_findings, errors=tuple(errors)
    )
