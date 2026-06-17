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
class PDF000DocstringLiteralNormalization(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF000"),
        name="docstring-literal-normalization",
        message="Docstring literal should be normalized",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for non-normal docstring literals."""
        return tuple(finding for docstring in _candidate_docstrings(context) if (finding := _finding_for_docstring(docstring, context=context)) is not None)

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Replace non-normal docstrings with equivalent simple literals."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes, instance_fixable=True)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return replacements for all non-normal docstrings."""
    return tuple(change for docstring in _candidate_docstrings(context) if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _candidate_docstrings(context: RuleContext) -> tuple[PDF_definition.DocstringInfo, ...]:
    """Return docstrings that may need literal source normalization."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(docstring for docstring in data.docstrings if docstring.kind in {PDF_definition.DocstringKind.CONCATENATED, PDF_definition.DocstringKind.SIMPLE})


def _finding_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> RuleFinding | None:
    """Return a fixable or non-fixable finding for one concatenated docstring."""
    planned_change = _planned_change_for_docstring(docstring, context=context)
    if planned_change is None and docstring.kind != PDF_definition.DocstringKind.CONCATENATED:
        return None
    return RuleFinding(rule=PDF000DocstringLiteralNormalization.meta, line_numbers=_line_numbers(docstring), instance_fixable=planned_change is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a source change for one renderable docstring."""
    rendered = _rendered_docstring(docstring, line_ending=context.line_ending)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=_line_numbers(docstring),
    )


def _rendered_docstring(docstring: PDF_definition.DocstringInfo, *, line_ending: str) -> str | None:
    """Return normalized source for a docstring literal."""
    if isinstance(docstring.node, cst.ConcatenatedString):
        return _rendered_concatenated_docstring(docstring, line_ending=line_ending)
    if isinstance(docstring.node, cst.SimpleString):
        return _rendered_simple_docstring(docstring.node, expected_value=docstring.value, line_ending=line_ending, escape_non_ascii=docstring.source.isascii())
    return None


def _rendered_concatenated_docstring(docstring: PDF_definition.DocstringInfo, *, line_ending: str) -> str | None:
    """Return normalized source for a concatenated docstring."""
    if not isinstance(docstring.node, cst.ConcatenatedString):
        return None
    fragments = string_literals.fragments_for_concatenated_string(docstring.node, target_quote='"""', line_ending=line_ending)
    if fragments is None:
        return None
    fragments = string_literals.literalized_whitespace_fragments(fragments, line_ending=line_ending)
    rendered = string_literals.render_simple_string_from_fragments(cst.SimpleString('""""""'), fragments, expected_value=docstring.value)
    if rendered is None:
        rendered = string_literals.render_value_as_simple_string(docstring.value, line_ending=line_ending, escape_non_ascii=docstring.source.isascii())
    return rendered


def _rendered_simple_docstring(node: cst.SimpleString, *, expected_value: str, line_ending: str, escape_non_ascii: bool) -> str | None:
    """Return normalized source for a simple docstring."""
    fragments = string_literals.value_fragments_for_simple_string(node, line_ending=line_ending)
    if fragments is None:
        return None
    literalized = string_literals.literalized_whitespace_fragments(fragments, line_ending=line_ending)
    if literalized == fragments:
        return None
    rendered = string_literals.render_simple_string_from_fragments(node, literalized, expected_value=expected_value)
    if rendered is not None:
        return rendered
    retargeted = string_literals.retarget_fragments(literalized, quote='"""', line_ending=line_ending)
    rendered = string_literals.render_simple_string_from_fragments(cst.SimpleString('""""""'), retargeted, expected_value=expected_value)
    if rendered is not None:
        return rendered
    return string_literals.render_value_as_simple_string(expected_value, line_ending=line_ending, escape_non_ascii=escape_non_ascii)


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return source line numbers covered by a docstring expression."""
    return tuple(line.line_number for line in docstring.physical_lines)
