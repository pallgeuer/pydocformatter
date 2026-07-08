"""PDF203 summary-too-long rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF203SummaryTooLong(RuleBase):
    """Rule implementation for PDF203.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF203"),
        name="summary-too-long",
        message="Docstring summary does not fit on one line",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for summaries that still span multiple logical lines.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF_definition.PDF.require_data(context)
        return tuple(violation for docstring in data.docstrings if (violation := _violation_for_docstring(docstring)) is not None)


def _violation_for_docstring(docstring: PDF_definition.DocstringInfo) -> rule_violations.RuleViolation | None:
    """Return one violation if a parsed top-level summary spans multiple lines."""
    summary = next((block for block in docstring.structure.blocks if block.kind is PDF_definition.DocstringBlockKind.SUMMARY), None)
    if summary is None or summary.end_line - summary.start_line <= 1:
        return None
    line_count = summary.end_line - summary.start_line
    return rule_violations.diagnostic(PDF203SummaryTooLong.meta, _summary_line_numbers(docstring, summary), instance_message=f"Docstring summary spans {line_count} lines and does not fit on one line")


def _summary_line_numbers(docstring: PDF_definition.DocstringInfo, summary: PDF_definition.DocstringBlock) -> tuple[int, ...]:
    """Return concrete source lines for a summary block."""
    mapped = tuple(line.source_line_number for line in docstring.structure.lines[summary.start_line : summary.end_line] if line.source_line_number is not None)
    if mapped:
        return tuple(dict.fromkeys(mapped))
    return tuple(line.line_number for line in docstring.physical_lines[summary.start_line : summary.end_line])
