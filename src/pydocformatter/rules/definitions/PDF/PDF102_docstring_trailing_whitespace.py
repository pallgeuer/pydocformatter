"""PDF102 docstring-trailing-whitespace rule."""

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
from pydocformatter.rules.definition_helpers import ascii_whitespace, inline_markup, text_layout
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF102DocstringTrailingWhitespace(RuleBase):
    """Rule implementation for PDF102.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF102"),
        name="docstring-trailing-whitespace",
        message="Non-empty docstring line has trailing whitespace",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for trailing whitespace on non-empty docstring lines.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe trailing-whitespace changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if docstring.kind is not PDF_definition.DocstringKind.SIMPLE:
        return None
    source_map = docstring.source_map
    if source_map is None:
        return None
    fragments = source_map.fragments
    replacements: list[rule_edits.PlannedTextReplacement] = []
    value_lines = [line.raw_text for line in docstring.structure.lines]
    for line in docstring.structure.lines:
        if not text_layout.has_space_tab_content(line.raw_text) or not _has_following_evaluated_newline(docstring, line):
            continue
        trailing_start = len(line.raw_text.rstrip(ascii_whitespace.SPACE_AND_TAB))
        if trailing_start == len(line.raw_text):
            continue
        line_fragments = fragments[line.start_offset : line.end_offset]
        hard_break = inline_markup.terminal_hard_break(line_fragments, has_following_newline=True)
        if hard_break is not None and hard_break.kind is inline_markup.HardBreakKind.SPACES:
            preserved_start = hard_break.start
            removable_start = len(line.raw_text[:preserved_start].rstrip("\t"))
            if removable_start == preserved_start:
                continue
            target_value = f"{line.raw_text[:removable_start]}{line.raw_text[preserved_start:]}"
            deletion_start = line.start_offset + removable_start
            deletion_end = line.start_offset + preserved_start
        else:
            target_value = line.raw_text[:trailing_start]
            deletion_start = line.start_offset + trailing_start
            deletion_end = line.end_offset
        line_numbers = source_map.physical_line_numbers(deletion_start, deletion_end, first_line_number=docstring.range.start.line)
        value_lines[line.index] = target_value
        replacements.append(
            rule_edits.PlannedTextReplacement(
                start_offset=deletion_start, end_offset=deletion_end, text=source_map.preserved_source_for_value_deletion(deletion_start, deletion_end), line_numbers=line_numbers
            )
        )
    return PDF_definition.planned_simple_docstring_source_change(docstring, replacements=tuple(replacements), value_lines=value_lines, source_map=source_map)


def _has_following_evaluated_newline(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine) -> bool:
    """Return whether a logical line is followed by an evaluated newline separator."""
    return line.end_offset < len(docstring.value)
