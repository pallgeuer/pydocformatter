"""Summary punctuation violation helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import terminal_punctuation


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.models import RuleMetadata


def results(context: RuleContext, *, rule: RuleMetadata, policy: terminal_punctuation.TerminalPunctuationPolicy) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for summary punctuation.

    Args:
        context (RuleContext): Current file context with prepared PDF summary targets.
        rule (RuleMetadata): Rule metadata used for diagnostics and fixes.
        policy (terminal_punctuation.TerminalPunctuationPolicy): Valid and non-fixable terminal punctuation policy.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Summary punctuation violations for eligible docstrings.
    """
    data = PDF_definition.PDF.require_data(context)
    return tuple(result for target in data.summary_terminal_line_targets if (result := result_for_target(target, rule=rule, policy=policy)) is not None)


def result_for_target(target: PDF_definition.SummaryLineTarget, *, rule: RuleMetadata, policy: terminal_punctuation.TerminalPunctuationPolicy) -> rule_violations.RuleViolation | None:
    """Return one summary-punctuation violation for a summary target.

    Args:
        target (PDF_definition.SummaryLineTarget): Summary line to inspect.
        rule (RuleMetadata): Rule metadata used for diagnostics and fixes.
        policy (terminal_punctuation.TerminalPunctuationPolicy): Valid and non-fixable terminal punctuation policy.

    Returns:
        rule_violations.RuleViolation | None: Violation for a bad ending, or None when the summary already complies.
    """
    line_numbers = PDF_definition.docstring_line_numbers(target.docstring, target.line)
    return terminal_punctuation.violation(text=target.line.text, policy=policy, rule=rule, line_numbers=line_numbers, planned_change=lambda: _planned_change(target))


def _planned_change(target: PDF_definition.SummaryLineTarget) -> rule_edits.PlannedSourceChange | None:
    """Return a safe insertion of a period at the end of a trimmed target line."""
    docstring = target.docstring
    line = target.line
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    insertion_offset = line.start_offset + len(line.raw_text.rstrip(" \t"))
    value_lines = [line.raw_text for line in docstring.structure.lines]
    value_lines[line.index] = f"{line.raw_text[: insertion_offset - line.start_offset]}.{line.raw_text[insertion_offset - line.start_offset :]}"
    replacement = rule_edits.PlannedTextReplacement(
        start_offset=insertion_offset, end_offset=insertion_offset, text=".", line_numbers=PDF_definition.docstring_line_numbers(target.docstring, target.line)
    )
    return PDF_definition.planned_simple_docstring_source_change(docstring, replacements=(replacement,), value_lines=value_lines)
