"""File and stdin formatting orchestration.

Attributes:
    UTF8_BOM (str): Unicode byte order mark stripped from decoded UTF-8 source before LibCST parsing and rule execution.
"""

from __future__ import annotations

import collections
import dataclasses
import typing

import libcst as cst

import pydocformatter.rules.line_endings as line_endings
import pydocformatter.rules.runner as rule_runner
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.models import RuleFinding, RuleMetadata
from pydocformatter.rules_selection import RuleSelection

UTF8_BOM = "\ufeff"


@dataclasses.dataclass(frozen=True)
class FormatterResult:
    """Formatter result for one display path.

    Attributes:
        path (str): Display path used for diagnostics and diff headers.
        old_source (str | None): Source text before formatting, or None if source text could not be read or decoded.
        new_source (str | None): Source text after formatting, or None if no valid source state is available.
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


def format_file(path: str, *, file: typing.TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
    """Run the rule-based formatter for one file.

    Args:
        path (str): Display path and filesystem path for the source file.
        file (typing.TextIO | None): Optional already-open text stream to read instead of opening `path`.
        settings (CheckSettings): Resolved formatter settings.
        rule_selection (RuleSelection): Precomputed rule selection for the settings profile.
        fix (bool): Whether fixes should be applied to the returned source.
        write (bool): Whether modified source should be written back to disk when reading from `path`.

    Returns:
        FormatterResult: Formatting result with source text, findings, and operational errors.

    Raises:
        AssertionError: If `format_source` returns an invalid result without source text.
    """
    try:
        if file is None:
            with open(path, encoding="utf-8", newline="") as path_file:
                source = path_file.read()
        else:
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

    if file is None and fix and write and result.modified:
        try:
            with open(path, "w", encoding="utf-8", newline="") as path_file:
                path_file.write(result.new_source)
        except OSError as error:
            return FormatterResult(
                path=path,
                old_source=result.old_source,
                new_source=result.old_source,
                modified=False,
                fixed_findings=collections.Counter(),
                unfixed_findings=(),
                errors=(f"Failed to write file {path}: {error}",),
            )

    return result


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
    try:
        module = cst.parse_module(source)
    except Exception as error:
        return FormatterResult(
            path=path,
            old_source=source,
            new_source=source,
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(),
            errors=(f"Failed to parse {path} with LibCST: {error}",),
        )

    line_ending = line_endings.resolve_line_ending(source, line_ending=settings.line_ending)
    run_result = rule_runner.run_rules(module, path=path, settings=settings, line_ending=line_ending, rule_selection=rule_selection, fix=fix, source=source)
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
        path=path,
        old_source=source,
        new_source=new_source,
        modified=(new_source != source),
        fixed_findings=fixed_findings,
        unfixed_findings=run_result.unfixed_findings,
        errors=tuple(errors),
    )
