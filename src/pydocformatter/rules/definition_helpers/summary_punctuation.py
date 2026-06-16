from __future__ import annotations

import dataclasses

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
from pydocformatter.rules.definition import RuleContext
from pydocformatter.rules.models import RuleFinding, RuleMetadata


@dataclasses.dataclass(frozen=True)
class SummaryPunctuationResult:
    """Finding and optional fix for one summary-punctuation issue."""

    finding: RuleFinding
    change: rule_edits.PlannedSourceChange | None


@dataclasses.dataclass(frozen=True)
class SummaryPunctuationPolicy:
    """Policy for one summary-punctuation rule."""

    valid_endings: str
    nonfixable_endings: str


def results(context: RuleContext, *, rule: RuleMetadata, policy: SummaryPunctuationPolicy) -> tuple[SummaryPunctuationResult, ...]:
    """Return findings and optional fixes for summary punctuation."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(result for target in data.summary_terminal_line_targets if (result := result_for_target(target, context=context, rule=rule, policy=policy)) is not None)


def result_for_target(
    target: PDF_definition.SummaryLineTarget,
    *,
    context: RuleContext,
    rule: RuleMetadata,
    policy: SummaryPunctuationPolicy,
) -> SummaryPunctuationResult | None:
    """Return one summary-punctuation result for a summary target."""
    trimmed = target.line.text.rstrip(" \t")
    if not trimmed or trimmed.endswith("\\") or trimmed.endswith(tuple(policy.valid_endings)):
        return None
    change = None if trimmed.endswith(tuple(policy.nonfixable_endings)) else _planned_change(target, context=context)
    return SummaryPunctuationResult(
        finding=RuleFinding(rule=rule, line_numbers=PDF_definition.docstring_line_numbers(target.docstring, target.line), instance_fixable=change is not None),
        change=change,
    )


def _planned_change(
    target: PDF_definition.SummaryLineTarget,
    *,
    context: RuleContext,
) -> rule_edits.PlannedSourceChange | None:
    """Return a safe insertion of a period at the end of a trimmed target line."""
    docstring = target.docstring
    line = target.line
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    insertion_offset = line.start_offset + len(line.raw_text.rstrip(" \t"))
    value_lines = [line.raw_text for line in docstring.structure.lines]
    value_lines[line.index] = f"{line.raw_text[: insertion_offset - line.start_offset]}.{line.raw_text[insertion_offset - line.start_offset :]}"
    replacement = rule_edits.PlannedTextReplacement(
        start_offset=insertion_offset,
        end_offset=insertion_offset,
        text=".",
        line_numbers=PDF_definition.docstring_line_numbers(target.docstring, target.line),
    )
    return PDF_definition.planned_simple_docstring_source_change(docstring, context=context, replacements=(replacement,), value_lines=value_lines)
