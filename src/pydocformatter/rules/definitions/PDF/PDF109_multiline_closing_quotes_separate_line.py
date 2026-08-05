"""PDF109 multiline-closing-quotes-separate-line rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from collections.abc import Sequence
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_rendering, docstring_source
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF109MultilineClosingQuotesSeparateLine(RuleBase):
    """Rule implementation for PDF109.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF109"),
        name="multiline-closing-quotes-separate-line",
        message="Multi-line docstring closing quotes should be on a separate line",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(RuleCode("PDF108"),),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for closing quotes that should be separate from content.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe closing-quote separate-line changes."""
    data = PDF_definition.PDF.require_data(context)
    source_lines = context.source_lines
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: Sequence[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not docstring_source.can_canonically_rewrite_simple_docstring(docstring, require_multiline=True):
        return None
    content_indexes = docstring_source.docstring_content_indexes(docstring)
    if not content_indexes:
        return None
    last_content = content_indexes[-1]
    if last_content < len(docstring.structure.lines) - 1 or docstring_source.docstring_value_ends_with_newline(docstring):
        return None
    canonical_margin = docstring_source.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
    final_line = docstring.structure.lines[last_content]
    output_lines = (
        *(docstring_rendering.DocstringOutputLine(original=line, source=None, value=None) for line in docstring.structure.lines),
        docstring_rendering.DocstringOutputLine(source=canonical_margin, value=canonical_margin),
    )
    line_numbers = docstring_source.docstring_value_line_numbers((final_line,))
    return docstring_rendering.planned_simple_docstring_output_change(docstring, context=context, output_lines=output_lines, line_numbers=line_numbers, preserve_trailing_newline=False)
