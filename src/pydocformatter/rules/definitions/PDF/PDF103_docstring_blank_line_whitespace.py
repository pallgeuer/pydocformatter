"""PDF103 docstring-blank-line-whitespace rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from collections.abc import Sequence
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli import settings_check
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import text_layout
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF103DocstringBlankLineWhitespace(RuleBase):
    """Rule implementation for PDF103.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF103"),
        name="docstring-blank-line-whitespace",
        message="Blank docstring line has whitespace",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for blank docstring line whitespace.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe blank-line whitespace changes."""
    data = PDF_definition.PDF.require_data(context)
    source_lines = context.source_lines
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: Sequence[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    canonical_margin = PDF_definition.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
    targets = tuple(_line_target(docstring, line, canonical_margin=canonical_margin, context=context) for line in docstring.structure.lines)
    return PDF_definition.planned_simple_docstring_line_change(docstring, context=context, raw_line_targets=targets)


def _line_target(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine, *, canonical_margin: str, context: RuleContext) -> str | None:
    """Return the target raw text for one blank line, if it should change."""
    if docstring.value == "":
        return None
    if text_layout.has_space_tab_content(line.raw_text):
        return None
    if PDF_definition.is_same_line_closing_delimiter_prefix(docstring, line):
        return canonical_margin
    if context.settings.docstring_blank_line_style == settings_check.DocstringBlankLineStyle.ALIGNED:
        return canonical_margin
    return ""
