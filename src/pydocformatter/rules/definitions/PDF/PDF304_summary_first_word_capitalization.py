"""PDF304 summary-first-word-capitalization rule."""

from __future__ import annotations

import dataclasses

import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF304SummaryFirstWordCapitalization(RuleBase):
    """Rule implementation for PDF304.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF304"),
        name="summary-first-word-capitalization",
        message="Docstring summary first word should be capitalized",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for function summaries whose first word is not capitalized."""
        return tuple(result.finding for result in _results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Capitalize safely mapped summary first words."""
        changes = tuple(result.change for result in _results(context, rule=cls.meta) if result.change is not None)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_context_source_changes(context, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes, instance_fixable=True)
        return RuleFixResult(module=module, fixed_findings=findings)


@dataclasses.dataclass(frozen=True)
class _CapitalizationResult:
    """Finding plus optional source change for one capitalization target.

    Attributes:
        finding (RuleFinding): Diagnostic reported for the summary word.
        change (rule_edits.PlannedSourceChange | None): Safe source rewrite for the word, when the docstring can be
            mapped back to source.
    """

    finding: RuleFinding
    change: rule_edits.PlannedSourceChange | None


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[_CapitalizationResult, ...]:
    """Return findings and optional fixes for summary capitalization."""
    data = PDF.require_data(context)
    results: list[_CapitalizationResult] = []
    for target in data.summary_line_targets:
        if not summary_style.is_function_docstring(target.docstring):
            continue
        word = summary_style.first_word_target(target)
        if word is None or not _should_capitalize(word.word):
            continue
        capitalized_word = f"{word.word[0].upper()}{word.word[1:]}"
        change = _planned_change(word, replacement=capitalized_word, context=context)
        results.append(
            _CapitalizationResult(
                finding=RuleFinding(
                    rule=rule,
                    line_numbers=summary_style.line_numbers(word),
                    instance_fixable=change is not None,
                    instance_message=f"Docstring summary first word '{word.word}' should be capitalized",
                ),
                change=change,
            )
        )
    return tuple(results)


def _should_capitalize(word: str) -> bool:
    """Return whether a summary first word should be capitalized."""
    trimmed = word.rstrip(".!?")
    if not trimmed or trimmed == trimmed.upper():
        return False
    first = trimmed[0]
    if not first.isascii() or first == first.upper():
        return False
    return all(char.isascii() and (char.isalpha() or char == "'") for char in trimmed[1:])


def _planned_change(word: summary_style.SummaryWordTarget, *, replacement: str, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a safe replacement for one summary first word."""
    docstring = word.docstring
    line = word.line
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    start_offset = PDF_definition.value_offset_for_text_column(line, word.text_start_column, require_source_text=True)
    end_offset = PDF_definition.value_offset_for_text_column(line, word.text_end_column, require_source_text=True)
    if start_offset is None or end_offset is None:
        return None
    value_lines = [value_line.raw_text for value_line in docstring.structure.lines]
    raw_start_column = start_offset - line.start_offset
    raw_end_column = end_offset - line.start_offset
    value_lines[line.index] = f"{line.raw_text[:raw_start_column]}{replacement}{line.raw_text[raw_end_column:]}"
    replacement_edit = rule_edits.PlannedTextReplacement(start_offset=start_offset, end_offset=end_offset, text=replacement, line_numbers=summary_style.line_numbers(word))
    return PDF_definition.planned_simple_docstring_source_change(docstring, context=context, replacements=(replacement_edit,), value_lines=value_lines)
