"""Entry-description style targets and fixes."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import first_word_capitalization, terminal_punctuation


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.models import RuleMetadata


@dataclasses.dataclass(frozen=True)
class EntryDescriptionWordTarget:
    """One first word in a documentation entry description.

    Attributes:
        target (PDF_definition.EntryDescriptionLineTarget): Description fragment that contains the word.
        word (str): First whitespace-delimited word selected for capitalization.
        start_offset (int): Evaluated docstring value offset where the word starts.
        end_offset (int): Evaluated docstring value offset immediately after the word.
    """

    target: PDF_definition.EntryDescriptionLineTarget
    word: str
    start_offset: int
    end_offset: int


class _SourceSafeReplacementPlanner:
    """Plan source-local docstring replacements whose spelling equals their runtime value."""

    def __init__(self, context: RuleContext) -> None:
        """Store shared context for direct source replacements."""
        self.context = context
        self.line_bounds = PDF_definition.line_bounds_for_context(context)

    def planned_replacement(
        self, target: PDF_definition.EntryDescriptionLineTarget, *, start_offset: int, end_offset: int, replacement: str, expected_source: str | None
    ) -> rule_edits.PlannedSourceChange | None:
        """Return a direct source replacement for a source-safe evaluated replacement."""
        if not PDF_definition.simple_docstring_replacement_is_source_safe(target.docstring, replacement):
            return None
        source_map = target.docstring.source_map
        if source_map is None or start_offset < 0 or end_offset < start_offset or end_offset > len(source_map.value):
            return None
        if expected_source is not None and source_map.producing_source_for_value_slice(start_offset, end_offset) != expected_source:
            return None
        line_numbers = line_numbers_for_offsets(target, start_offset=start_offset, end_offset=end_offset)
        return rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(
                range=PDF_definition.simple_docstring_source_range(target.docstring, source_map=source_map, start_offset=start_offset, end_offset=end_offset, line_bounds=self.line_bounds),
                replacement=replacement,
            ),
            line_numbers=line_numbers,
            suppression_line_numbers=(),
        )


def first_line_targets(context: RuleContext) -> tuple[PDF_definition.EntryDescriptionLineTarget, ...]:
    """Return first non-empty parsed entry description fragments.

    Args:
        context (RuleContext): Current file context with prepared PDF data.

    Returns:
        Entry description targets pointing at first description fragments.
    """
    return PDF_definition.PDF.require_data(context).entry_description_first_line_targets()


def terminal_line_targets(context: RuleContext) -> tuple[PDF_definition.EntryDescriptionLineTarget, ...]:
    """Return final non-empty parsed entry description fragments.

    Args:
        context (RuleContext): Current file context with prepared PDF data.

    Returns:
        Entry description targets pointing at final description fragments.
    """
    return PDF_definition.PDF.require_data(context).entry_description_terminal_line_targets()


def punctuation_violations(context: RuleContext, *, rule: RuleMetadata, policy: terminal_punctuation.TerminalPunctuationPolicy) -> tuple[rule_violations.RuleViolation, ...]:
    """Return entry-description punctuation violations.

    Args:
        context (RuleContext): Current file context with prepared PDF data.
        rule (RuleMetadata): Rule metadata used for diagnostics and fixes.
        policy (terminal_punctuation.TerminalPunctuationPolicy): Valid, replaceable, and non-fixable terminal
            punctuation policy.

    Returns:
        Entry-description punctuation violations for eligible entries.
    """
    planner = _SourceSafeReplacementPlanner(context)
    return tuple(result for target in terminal_line_targets(context) if (result := _punctuation_violation(target, context=context, rule=rule, policy=policy, planner=planner)) is not None)


def capitalization_violations(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return entry-description first-word capitalization violations.

    Args:
        context (RuleContext): Current file context with prepared PDF data.
        rule (RuleMetadata): Rule metadata used for diagnostics and fixes.

    Returns:
        Entry-description first-word capitalization violations for eligible entries.
    """
    violations: list[rule_violations.RuleViolation] = []
    planner = _SourceSafeReplacementPlanner(context)
    for target in first_line_targets(context):
        word = first_word_target(target)
        if word is None or not first_word_capitalization.should_capitalize(word.word):
            continue
        replacement = word.word[0].upper()
        change = _planned_replacement(word.target, start_offset=word.start_offset, end_offset=word.start_offset + 1, replacement=replacement, context=context, planner=planner)
        violations.append(
            rule_violations.violation_for_optional_planned_source_change(
                rule, change, line_numbers=line_numbers(word.target), instance_message=f"Docstring entry description first word '{word.word}' should be capitalized"
            )
        )
    return tuple(violations)


def first_word_target(target: PDF_definition.EntryDescriptionLineTarget) -> EntryDescriptionWordTarget | None:
    """Return the first whitespace-delimited word in an entry description fragment.

    Args:
        target (PDF_definition.EntryDescriptionLineTarget): Entry description fragment whose first word should be
            selected.

    Returns:
        First word target and evaluated-value offsets, or None for an empty fragment.
    """
    match = re.search(r"\S+", target.fragment.text)
    if match is None:
        return None
    return EntryDescriptionWordTarget(target=target, word=match.group(0), start_offset=target.fragment.start_offset + match.start(), end_offset=target.fragment.start_offset + match.end())


def line_numbers(target: PDF_definition.EntryDescriptionLineTarget) -> tuple[int, ...]:
    """Return concrete source lines for an entry description target.

    Args:
        target (PDF_definition.EntryDescriptionLineTarget): Entry description fragment to map back to source lines.

    Returns:
        Concrete one-based source lines occupied by the target fragment.
    """
    return PDF_definition.docstring_line_numbers(target.docstring, target.line)


def line_numbers_for_offsets(target: PDF_definition.EntryDescriptionLineTarget, *, start_offset: int, end_offset: int) -> tuple[int, ...]:
    """Return source lines covered by an evaluated-offset replacement.

    Args:
        target (PDF_definition.EntryDescriptionLineTarget): Entry description fragment whose owning docstring supplies
            logical source-line mappings.
        start_offset (int): Evaluated docstring value offset where the replacement starts.
        end_offset (int): Evaluated docstring value offset immediately after the replacement target.

    Returns:
        Concrete one-based source lines occupied by the replacement span, falling back to the target fragment line.
    """
    if start_offset == end_offset:
        return line_numbers(target)
    lines = tuple(line for line in target.docstring.structure.lines if line.source_line_number is not None and line.start_offset <= start_offset and end_offset <= line.end_offset)
    if lines:
        return PDF_definition.docstring_value_line_numbers(lines)
    return line_numbers(target)


def _punctuation_violation(
    target: PDF_definition.EntryDescriptionLineTarget, *, context: RuleContext, rule: RuleMetadata, policy: terminal_punctuation.TerminalPunctuationPolicy, planner: _SourceSafeReplacementPlanner
) -> rule_violations.RuleViolation | None:
    """Return one entry-description punctuation violation."""
    return terminal_punctuation.violation(
        text=target.fragment.text,
        policy=policy,
        rule=rule,
        line_numbers=line_numbers(target),
        planned_change=lambda expected_terminal, replacement: (
            None
            if expected_terminal == "," and any(terminal_punctuation.comma_may_introduce_block(kind) for kind in target.following_block_kinds)
            else _planned_replacement(
                target,
                start_offset=target.fragment.end_offset if expected_terminal is None else target.fragment.end_offset - 1,
                end_offset=target.fragment.end_offset,
                replacement=replacement,
                context=context,
                planner=planner,
            )
        ),
    )


def _planned_replacement(
    target: PDF_definition.EntryDescriptionLineTarget, *, start_offset: int, end_offset: int, replacement: str, context: RuleContext, planner: _SourceSafeReplacementPlanner
) -> rule_edits.PlannedSourceChange | None:
    """Return a safe source change for one entry description fragment replacement."""
    docstring = target.docstring
    line = target.line
    if start_offset < line.start_offset or end_offset < start_offset or end_offset > line.end_offset:
        return None
    fragment_start = start_offset - target.fragment.start_offset
    fragment_end = end_offset - target.fragment.start_offset
    expected_source = target.fragment.text[fragment_start:fragment_end] if start_offset != end_offset else None
    direct_change = planner.planned_replacement(target, start_offset=start_offset, end_offset=end_offset, replacement=replacement, expected_source=expected_source)
    if direct_change is not None:
        return direct_change
    line_start = start_offset - line.start_offset
    line_end = end_offset - line.start_offset
    value_lines = [structure_line.raw_text for structure_line in docstring.structure.lines]
    value_lines[line.index] = f"{line.raw_text[:line_start]}{replacement}{line.raw_text[line_end:]}"
    replacement_edit = rule_edits.PlannedTextReplacement(start_offset=start_offset, end_offset=end_offset, text=replacement, line_numbers=line_numbers(target))
    return PDF_definition.planned_simple_docstring_text_change(
        docstring, context=context, replacement=replacement_edit, expected_value=PDF_definition.join_docstring_value_lines(docstring, value_lines), expected_source=expected_source
    )
