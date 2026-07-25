"""PDF104 opening-quotes-whitespace rule."""

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
from pydocformatter.rules.definition_helpers import text_layout
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF104OpeningQuotesWhitespace(RuleBase):
    """Rule implementation for PDF104.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF104"),
        name="opening-quotes-whitespace",
        message="Docstring has extra whitespace after opening quotes",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for extra whitespace after opening quotes.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe opening quote whitespace changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo) -> rule_edits.PlannedSourceChange | None:
    """Return one source replacement for opening quote whitespace."""
    if not PDF_definition.can_canonically_rewrite_simple_docstring(docstring):
        return None
    line = docstring.structure.lines[0]
    if not text_layout.has_space_tab_content(line.raw_text):
        return None
    whitespace_end = len(line.raw_text) - len(line.raw_text.lstrip(" \t"))
    if whitespace_end == 0:
        return None
    return _validated_change(docstring, line, whitespace_end=whitespace_end, replacement_text="") or _validated_change(docstring, line, whitespace_end=whitespace_end, replacement_text=" ")


def _validated_change(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine, *, whitespace_end: int, replacement_text: str) -> rule_edits.PlannedSourceChange | None:
    """Return a validated opening quote whitespace change."""
    if line.source_line_number is None:
        return None
    target_line = f"{replacement_text}{line.raw_text[whitespace_end:]}"
    if target_line == line.raw_text:
        return None
    value_lines = [value_line.raw_text for value_line in docstring.structure.lines]
    value_lines[line.index] = target_line
    return PDF_definition.planned_simple_docstring_source_change(
        docstring,
        replacements=(
            rule_edits.PlannedTextReplacement(start_offset=line.start_offset, end_offset=line.start_offset + whitespace_end, text=replacement_text, line_numbers=(line.source_line_number,)),
        ),
        value_lines=value_lines,
    )
