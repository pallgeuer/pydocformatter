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
    return tuple(result for docstring in data.docstrings if (result := result_for_docstring(docstring, context=context, rule=rule, policy=policy)) is not None)


def result_for_docstring(
    docstring: PDF_definition.DocstringInfo,
    *,
    context: RuleContext,
    rule: RuleMetadata,
    policy: SummaryPunctuationPolicy,
) -> SummaryPunctuationResult | None:
    """Return one summary-punctuation result for a docstring."""
    target = _target_line(docstring)
    if target is None:
        return None
    trimmed = target.text.rstrip(" \t")
    if not trimmed or trimmed.endswith("\\") or trimmed.endswith(tuple(policy.valid_endings)):
        return None
    change = None if trimmed.endswith(tuple(policy.nonfixable_endings)) else _planned_change(docstring, target, context=context)
    return SummaryPunctuationResult(
        finding=RuleFinding(rule=rule, line_numbers=_target_line_numbers(docstring, target), instance_fixable=change is not None),
        change=change,
    )


def _target_line(docstring: PDF_definition.DocstringInfo) -> PDF_definition.DocstringValueLine | None:
    """Return the summary line whose terminal punctuation should be checked."""
    first_block = next((block for block in docstring.structure.blocks if block.kind is not PDF_definition.DocstringBlockKind.BLANK), None)
    if first_block is None:
        return None
    if first_block.kind is PDF_definition.DocstringBlockKind.SUMMARY:
        return _final_non_empty_line(docstring, first_block.start_line, first_block.end_line)
    return None


def _final_non_empty_line(docstring: PDF_definition.DocstringInfo, start: int, end: int) -> PDF_definition.DocstringValueLine | None:
    """Return the final non-adornment logical line in a summary block."""
    for index in range(end - 1, start - 1, -1):
        line = docstring.structure.lines[index]
        if line.text.strip(" \t"):
            if PDF_definition.is_adornment(line.text):
                continue
            return line
    return None


def _planned_change(
    docstring: PDF_definition.DocstringInfo,
    target: PDF_definition.DocstringValueLine,
    *,
    context: RuleContext,
) -> rule_edits.PlannedSourceChange | None:
    """Return a safe insertion of a period at the end of a trimmed target line."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    insertion_offset = target.start_offset + len(target.raw_text.rstrip(" \t"))
    value_lines = [line.raw_text for line in docstring.structure.lines]
    value_lines[target.index] = f"{target.raw_text[: insertion_offset - target.start_offset]}.{target.raw_text[insertion_offset - target.start_offset :]}"
    replacement = rule_edits.PlannedTextReplacement(
        start_offset=insertion_offset,
        end_offset=insertion_offset,
        text=".",
        line_numbers=_target_line_numbers(docstring, target),
    )
    return PDF_definition.planned_simple_docstring_source_change(docstring, context=context, replacements=(replacement,), value_lines=value_lines)


def _target_line_numbers(docstring: PDF_definition.DocstringInfo, target: PDF_definition.DocstringValueLine) -> tuple[int, ...]:
    """Return concrete source lines for a punctuation target."""
    if target.source_line_number is not None:
        return PDF_definition.docstring_value_line_numbers((target,))
    return tuple(line.line_number for line in docstring.physical_lines)
