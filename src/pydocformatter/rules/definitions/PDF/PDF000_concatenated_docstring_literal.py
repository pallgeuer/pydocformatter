from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_collection.register_rule_to(PDF_definition.PDF)
class PDF000ConcatenatedDocstringLiteral(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF000"),
        name="concatenated-docstring-literal",
        message="Docstring should use a single string literal",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
        setting_effects=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for concatenated docstring expressions."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Replace concatenated docstrings with equivalent simple literals."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return replacements for all concatenated docstrings."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(range=docstring.range, replacement=PDF_definition.serialize_simple_docstring(docstring.value).replace("\n", context.line_ending)),
            line_numbers=tuple(line.line_number for line in docstring.physical_lines),
        )
        for docstring in data.docstrings
        if docstring.kind == PDF_definition.DocstringKind.CONCATENATED
    )
