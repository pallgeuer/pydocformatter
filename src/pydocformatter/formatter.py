"""File and stdin formatting orchestration.

Attributes:
    UTF8_BOM (str): Unicode byte order mark stripped from decoded UTF-8 source before LibCST parsing and rule execution.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import re
import typing
import hashlib
import collections
import dataclasses

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.markdown as markdown_source
import pydocformatter.rules.runner as rule_runner
from pydocformatter.cli import settings_check
from pydocformatter.cli.settings_check import CheckSettings, SourceLanguage
from pydocformatter.rules import line_endings
from pydocformatter.rules.models import RuleFinding, RuleMetadata
from pydocformatter.rules_selection import RuleExecutionPlan
from pydocformatter.source_path import SourcePathContext
from pydocformatter.utils import text


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
class _PythonParseFailure:
    """Structured Python parse failure before host-source rendering."""

    detail: str
    line: int | None
    column: int | None
    context_line: int | None
    context_column: int | None
    context_source: str | None


@dataclasses.dataclass(frozen=True)
class _PythonFormatOutcome:
    """Python formatting result with original findings and structured errors."""

    result: FormatterResult
    initial_findings: tuple[RuleFinding, ...]
    rule_errors: tuple[rule_runner.RuleOperationalError, ...]


@dataclasses.dataclass(frozen=True)
class DiskFormatRequest:
    """Fully resolved inputs for one disk-backed formatter execution.

    Attributes:
        path (str): Display and filesystem path to format.
        settings (CheckSettings): Effective settings for the source path.
        source_language (SourceLanguage | None): Resolved source language, or None when the filename is unmapped.
        execution_plan (RuleExecutionPlan): Lean path-specific rule execution plan.
        source_path (SourcePathContext): Precomputed source-path semantics.
        fix (bool): Whether selected fixes should be applied.
        write (bool): Whether modified source should be written back to disk.
        collect_clean_snapshot (bool): Whether to return a clean source identity for cache persistence.
    """

    path: str
    settings: CheckSettings
    source_language: SourceLanguage | None
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


def format_stream(path: str, *, file: typing.TextIO, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, apply_language_defaults: bool = True) -> FormatterResult:
    """Run the rule-based formatter for one open text stream.

    Args:
        path (str): Display path used for diagnostics and path-specific rule selection.
        file (typing.TextIO): Open text stream to read once without writing.
        settings (CheckSettings): Caller-supplied formatter settings.
        rule_selection (RuleSelection): Precomputed rule selection for the settings profile.
        fix (bool): Whether fixes should be applied to the returned source.
        apply_language_defaults (bool): Whether to apply automatic defaults for the filename's resolved source language.

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

    result = format_source(source, path, settings=settings, rule_selection=rule_selection, fix=fix, apply_language_defaults=apply_language_defaults)
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
    if request.source_language is None:
        return DiskFormatResult(result=_unknown_language_result(path, source=None), clean_snapshot=None)
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

    result = _format_source_plan(
        source, path, settings=request.settings, source_language=request.source_language, execution_plan=request.execution_plan, fix=request.fix, source_path=request.source_path
    )
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


def format_source(source: str, path: str, *, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, apply_language_defaults: bool = True) -> FormatterResult:
    """Run the rule-based formatter for source text.

    Args:
        source (str): Python or Markdown source text to format.
        path (str): Display path used for diagnostics.
        settings (CheckSettings): Caller-supplied formatter settings.
        rule_selection (RuleSelection): Precomputed rule selection for the settings profile.
        fix (bool): Whether fixes should be applied to the returned source.
        apply_language_defaults (bool): Whether to apply automatic defaults for the filename's resolved source language.

    Returns:
        FormatterResult: Formatting result for the supplied source text.
    """
    source_language = settings_check.source_language_for_path(path, settings.extension)
    if source_language is None:
        return _unknown_language_result(path, source=source)
    effective_settings = settings_check.apply_language_defaults(settings, source_language) if apply_language_defaults else settings
    return _format_source_plan(
        source,
        path,
        settings=effective_settings,
        source_language=source_language,
        execution_plan=rule_selection.execution_plan_for_path(path, source_context=effective_settings.source_context),
        fix=fix,
        source_path=SourcePathContext.for_path(path),
    )


def _format_source_plan(
    source: str, path: str, *, settings: CheckSettings, source_language: SourceLanguage, execution_plan: RuleExecutionPlan, fix: bool, source_path: SourcePathContext
) -> FormatterResult:
    """Format Python or Markdown source through one fully resolved rule and source-path plan."""
    if source_language is SourceLanguage.MARKDOWN:
        return _format_markdown_source_plan(source, path, settings=settings, execution_plan=execution_plan, fix=fix, source_path=source_path)
    return _format_python_source_plan(source, path, settings=settings, execution_plan=execution_plan, fix=fix, source_path=source_path)


def _unknown_language_result(path: str, *, source: str | None) -> FormatterResult:
    """Return an unchanged operational-error result for an unmapped filename."""
    return FormatterResult(
        path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(settings_check.unknown_source_language_error(path),)
    )


def _format_python_source_plan(source: str, path: str, *, settings: CheckSettings, execution_plan: RuleExecutionPlan, fix: bool, source_path: SourcePathContext) -> FormatterResult:
    """Format strict Python source through one fully resolved rule and source-path plan."""
    parsed = _parse_python_source(source)
    if isinstance(parsed, _PythonParseFailure):
        return FormatterResult(
            path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(_render_parse_failure(parsed, path=path),)
        )
    return _format_parsed_python_source_plan(source, path, module=parsed, settings=settings, execution_plan=execution_plan, fix=fix, source_path=source_path).result


def _format_parsed_python_source_plan(
    source: str, path: str, *, module: cst.Module, settings: CheckSettings, execution_plan: RuleExecutionPlan, fix: bool, source_path: SourcePathContext
) -> _PythonFormatOutcome:
    """Format already parsed Python source and retain its initial findings."""
    line_ending = line_endings.resolve_line_ending(source, line_ending=settings.line_ending)
    run_result = rule_runner.run_rule_plan(module, path=path, settings=settings, line_ending=line_ending, execution_plan=execution_plan, fix=fix, source=source, source_path=source_path)
    fixed_findings = collections.Counter(finding.rule for finding in run_result.fixed_findings)

    if run_result.source_changed:
        new_source = run_result.source
        if source.startswith(UTF8_BOM) and not new_source.startswith(UTF8_BOM):
            new_source = UTF8_BOM + new_source
    else:
        new_source = source

    return _PythonFormatOutcome(
        result=FormatterResult(
            path=path,
            old_source=source,
            new_source=new_source,
            modified=(new_source != source),
            fixed_findings=fixed_findings,
            unfixed_findings=run_result.unfixed_findings,
            errors=tuple(error.render() for error in run_result.errors),
        ),
        initial_findings=run_result.initial_findings,
        rule_errors=run_result.errors,
    )


def _format_markdown_source_plan(source: str, path: str, *, settings: CheckSettings, execution_plan: RuleExecutionPlan, fix: bool, source_path: SourcePathContext) -> FormatterResult:
    """Format each selected fenced Python block in one Markdown source."""
    document_fences = markdown_source.markdown_fences(source)
    targets = tuple((index, fence) for index, fence in enumerate(document_fences) if fence.is_python and not fence.skipped)
    if not targets:
        return FormatterResult(path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

    parsed = tuple((index, fence, _parse_python_source(fence.source)) for index, fence in targets)
    if any(isinstance(module, _PythonParseFailure) for _, _, module in parsed):
        findings: list[RuleFinding] = []
        errors: list[str] = []
        for _, fence, module in parsed:
            if isinstance(module, _PythonParseFailure):
                errors.append(_render_parse_failure(module, path=path, line_offset=fence.body_start_line - 1, fence=fence))
            else:
                outcome = _format_parsed_python_source_plan(fence.source, path, module=module, settings=settings, execution_plan=execution_plan, fix=False, source_path=source_path)
                findings.extend(_offset_markdown_findings(outcome.result.unfixed_findings, fence=fence))
                errors.extend(_render_markdown_rule_errors(outcome.rule_errors, fence=fence))
        return FormatterResult(path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=tuple(findings), errors=tuple(errors))

    outcomes = tuple(
        (
            index,
            fence,
            _format_parsed_python_source_plan(fence.source, path, module=typing.cast("cst.Module", module), settings=settings, execution_plan=execution_plan, fix=fix, source_path=source_path),
        )
        for index, fence, module in parsed
    )
    if not fix:
        return FormatterResult(
            path=path,
            old_source=source,
            new_source=source,
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=tuple(finding for _, fence, outcome in outcomes for finding in _offset_markdown_findings(outcome.result.unfixed_findings, fence=fence)),
            errors=tuple(error for _, fence, outcome in outcomes for error in _render_markdown_rule_errors(outcome.rule_errors, fence=fence)),
        )

    errors = tuple(error for _, fence, outcome in outcomes for error in _render_markdown_rule_errors(outcome.rule_errors, fence=fence))
    if errors:
        return _markdown_rollback_result(source, path=path, outcomes=outcomes, errors=errors)

    replacements: list[tuple[markdown_source.MarkdownFence, str]] = []
    expected_sources: dict[int, str] = {}
    for index, fence, outcome in outcomes:
        if outcome.result.new_source is None:
            raise AssertionError("Markdown block formatting must retain source text")
        replacements.append((fence, outcome.result.new_source))
        expected_sources[index] = outcome.result.new_source
    new_source = markdown_source.replace_fence_bodies(source, tuple(replacements))
    rewrite_validation = markdown_source.validate_rewrite(document_fences, new_source, expected_sources=expected_sources)
    if rewrite_validation.error is not None:
        error = f"Unsafe Markdown rewrite for {path}: {rewrite_validation.error}; no fixes were applied"
        return _markdown_rollback_result(source, path=path, outcomes=outcomes, errors=(error,))

    fixed_findings: collections.Counter[RuleMetadata] = collections.Counter()
    unfixed_findings: list[RuleFinding] = []
    for index, _, outcome in outcomes:
        fixed_findings.update(outcome.result.fixed_findings)
        unfixed_findings.extend(_offset_markdown_findings(outcome.result.unfixed_findings, fence=rewrite_validation.fences[index]))
    return FormatterResult(path=path, old_source=source, new_source=new_source, modified=new_source != source, fixed_findings=fixed_findings, unfixed_findings=tuple(unfixed_findings), errors=())


def _parse_python_source(source: str) -> cst.Module | _PythonParseFailure:
    """Parse Python source or return a structured failure."""
    try:
        return cst.parse_module(source)
    except cst.ParserSyntaxError as error:
        detail = re.sub(r"^parser error: error at [0-9]+:[0-9]+: ", "parser error: ", error.message)
        context_line = error.editor_line
        source_lines = text.split_physical_lines(source)
        while context_line >= 1 and (context_line > len(source_lines) or not source_lines[context_line - 1].strip()):
            context_line -= 1
        if context_line >= 1:
            context_source = source_lines[context_line - 1]
            context_column = error.editor_column if context_line == error.editor_line else len(context_source.expandtabs()) + 1
        else:
            context_source = None
            context_column = None
            context_line = None
        return _PythonParseFailure(detail=detail, line=error.editor_line, column=error.editor_column, context_line=context_line, context_column=context_column, context_source=context_source)
    except Exception as error:
        return _PythonParseFailure(detail=str(error), line=None, column=None, context_line=None, context_column=None, context_source=None)


def _render_parse_failure(failure: _PythonParseFailure, *, path: str, line_offset: int = 0, fence: markdown_source.MarkdownFence | None = None) -> str:
    """Render a structured parse failure against its host source."""
    if failure.line is None or failure.column is None:
        return f"Failed to parse {path} with LibCST: {failure.detail}"
    column_prefix = fence.prefix_for_line(failure.line) if fence is not None else ""
    rendered = f"Failed to parse {path} with LibCST: Syntax Error @ {failure.line + line_offset}:{failure.column + len(column_prefix)}.\n{failure.detail}"
    if failure.context_source is not None and failure.context_line is not None and failure.context_column is not None:
        context_prefix = fence.prefix_for_line(failure.context_line) if fence is not None else ""
        rendered = f"{rendered}\n\n{context_prefix}{failure.context_source.expandtabs()}\n{' ' * (len(context_prefix) + failure.context_column - 1)}^"
    return rendered


def _offset_markdown_findings(findings: tuple[RuleFinding, ...], *, fence: markdown_source.MarkdownFence) -> tuple[RuleFinding, ...]:
    """Map block-relative findings to Markdown host lines."""
    line_offset = fence.body_start_line - 1
    return tuple(
        dataclasses.replace(
            finding,
            line_numbers=tuple(line + line_offset for line in finding.line_numbers),
            suppression_line_numbers=tuple(tuple(line + line_offset for line in lines) for lines in finding.suppression_line_numbers),
        )
        for finding in findings
    )


def _render_markdown_rule_errors(errors: tuple[rule_runner.RuleOperationalError, ...], *, fence: markdown_source.MarkdownFence) -> tuple[str, ...]:
    """Render block-relative rule errors in Markdown host coordinates."""
    line_offset = fence.body_start_line - 1
    return tuple(error.render(line_offset=line_offset) for error in errors)


def _markdown_rollback_result(source: str, *, path: str, outcomes: tuple[tuple[int, markdown_source.MarkdownFence, _PythonFormatOutcome], ...], errors: tuple[str, ...]) -> FormatterResult:
    """Return an unchanged Markdown result with original findings after an unsafe fix."""
    findings = tuple(finding for _, fence, outcome in outcomes for finding in _offset_markdown_findings(outcome.initial_findings, fence=fence))
    return FormatterResult(path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=findings, errors=errors)
