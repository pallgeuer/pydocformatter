from __future__ import annotations

import libcst as cst

import pydocformatter.rules.definition_helpers.string_literals as string_literals
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF000ConcatenatedDocstringLiteral(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF000"),
        name="concatenated-docstring-literal",
        message="Docstring should use a single string literal",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for concatenated docstring expressions."""
        return tuple(_finding_for_docstring(docstring, context=context) for docstring in _concatenated_docstrings(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Replace concatenated docstrings with equivalent simple literals."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes, instance_fixable=True)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return replacements for all concatenated docstrings."""
    return tuple(change for docstring in _concatenated_docstrings(context) if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _concatenated_docstrings(context: RuleContext) -> tuple[PDF_definition.DocstringInfo, ...]:
    """Return concatenated docstrings in the current context."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(docstring for docstring in data.docstrings if docstring.kind == PDF_definition.DocstringKind.CONCATENATED)


def _finding_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> RuleFinding:
    """Return a fixable or non-fixable finding for one concatenated docstring."""
    return RuleFinding(rule=PDF000ConcatenatedDocstringLiteral.meta, line_numbers=_line_numbers(docstring), instance_fixable=_planned_change_for_docstring(docstring, context=context) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a source change for one renderable concatenated docstring."""
    if not isinstance(docstring.node, cst.ConcatenatedString):
        return None
    fragments = string_literals.fragments_for_concatenated_string(docstring.node, target_quote='"""', line_ending=context.line_ending)
    if fragments is None:
        return None
    rendered = string_literals.render_simple_string_from_fragments(cst.SimpleString('""""""'), fragments, expected_value=docstring.value)
    if rendered is None:
        rendered = string_literals.render_value_as_simple_string(docstring.value, line_ending=context.line_ending, escape_non_ascii=docstring.source.isascii())
    if rendered is None:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=_line_numbers(docstring),
    )


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return source line numbers covered by a docstring expression."""
    return tuple(line.line_number for line in docstring.physical_lines)
