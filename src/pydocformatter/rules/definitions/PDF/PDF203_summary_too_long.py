from __future__ import annotations

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF203SummaryTooLong(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF203"),
        name="summary-too-long",
        message="Docstring summary does not fit on one line",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for summaries that still span multiple logical lines."""
        data = PDF_definition.PDF.require_data(context)
        return tuple(finding for docstring in data.docstrings if (finding := _finding_for_docstring(docstring)) is not None)


def _finding_for_docstring(docstring: PDF_definition.DocstringInfo) -> RuleFinding | None:
    """Return one finding if a parsed top-level summary spans multiple lines."""
    summary = next((block for block in docstring.structure.blocks if block.kind is PDF_definition.DocstringBlockKind.SUMMARY), None)
    if summary is None or summary.end_line - summary.start_line <= 1:
        return None
    line_count = summary.end_line - summary.start_line
    return RuleFinding(
        rule=PDF203SummaryTooLong.meta,
        line_numbers=_summary_line_numbers(docstring, summary),
        instance_message=f"Docstring summary spans {line_count} lines and does not fit on one line",
    )


def _summary_line_numbers(docstring: PDF_definition.DocstringInfo, summary: PDF_definition.DocstringBlock) -> tuple[int, ...]:
    """Return concrete source lines for a summary block."""
    mapped = tuple(line.source_line_number for line in docstring.structure.lines[summary.start_line : summary.end_line] if line.source_line_number is not None)
    if mapped:
        return tuple(dict.fromkeys(mapped))
    return tuple(line.line_number for line in docstring.physical_lines[summary.start_line : summary.end_line])
