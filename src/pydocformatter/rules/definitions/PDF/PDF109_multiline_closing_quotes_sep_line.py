from __future__ import annotations

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF109MultilineClosingQuotesSepLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF109"),
        name="multiline-closing-quotes-sep-line",
        message="Multi-line docstring closing quotes should be on a separate line",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(RuleCode("PDF108"),),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for closing quotes that should be separate from content."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Move closing quotes below the final content line where safe."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe closing-quote separate-line changes."""
    data = PDF_definition.PDF.require_data(context)
    source_lines = PDF_definition.source_lines_from_context(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: list[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring, require_multiline=True):
        return None
    content_indexes = PDF_definition.docstring_content_indexes(docstring)
    if not content_indexes:
        return None
    last_content = content_indexes[-1]
    if last_content < len(docstring.structure.lines) - 1 or PDF_definition.docstring_value_ends_with_newline(docstring):
        return None
    canonical_margin = PDF_definition.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
    final_line = docstring.structure.lines[last_content]
    output_lines = (
        *(PDF_definition.DocstringOutputLine(original=line) for line in docstring.structure.lines),
        PDF_definition.DocstringOutputLine(source=canonical_margin, value=canonical_margin),
    )
    line_numbers = PDF_definition.docstring_value_line_numbers((final_line,))
    return PDF_definition.planned_simple_docstring_output_change(docstring, context=context, output_lines=output_lines, line_numbers=line_numbers, preserve_trailing_newline=False)
