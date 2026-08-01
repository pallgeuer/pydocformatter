"""PDF304 summary-first-word-capitalization rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import first_word_capitalization, summary_style
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


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
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for summaries whose first word is not capitalized.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _violations(context, rule=cls.meta)


def _violations(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations and optional fixes for summary capitalization."""
    data = PDF.require_data(context)
    violations: list[rule_violations.RuleViolation] = []
    for target in data.summary_line_targets:
        word = summary_style.first_word_target(target)
        if word is None or not first_word_capitalization.should_capitalize(word.word):
            continue
        capitalized_word = f"{word.word[0].upper()}{word.word[1:]}"
        change = _planned_change(word, replacement=capitalized_word)
        violations.append(
            rule_violations.violation_for_optional_planned_source_change(
                rule, change, line_numbers=summary_style.line_numbers(word), instance_message=f"Docstring summary first word '{word.word}' should be capitalized"
            )
        )
    return tuple(violations)


def _planned_change(word: summary_style.SummaryWordTarget, *, replacement: str) -> rule_edits.PlannedSourceChange | None:
    """Return a safe replacement for one summary first word."""
    docstring = word.docstring
    line = word.line
    if not PDF_definition.can_canonically_rewrite_simple_docstring(docstring):
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
    return PDF_definition.planned_simple_docstring_source_change(docstring, replacements=(replacement_edit,), value_lines=value_lines)
