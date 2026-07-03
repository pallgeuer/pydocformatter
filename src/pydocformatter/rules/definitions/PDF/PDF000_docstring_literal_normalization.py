"""PDF000 docstring-literal-normalization rule."""

from __future__ import annotations

import libcst as cst

import pydocformatter.rules.definition_helpers.string_literals as string_literals
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF000DocstringLiteralNormalization(RuleBase):
    """Rule implementation for PDF000.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF000"),
        name="docstring-literal-normalization",
        message="Docstring literal should be normalized",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for non-normal docstring literals.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return tuple(violation for docstring in _candidate_docstrings(context) if (violation := _violation_for_docstring(docstring, context=context)) is not None)


def _candidate_docstrings(context: RuleContext) -> tuple[PDF_definition.DocstringInfo, ...]:
    """Return docstrings that may need literal source normalization."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(docstring for docstring in data.docstrings if docstring.kind in {PDF_definition.DocstringKind.CONCATENATED, PDF_definition.DocstringKind.SIMPLE})


def _violation_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_violations.RuleViolation | None:
    """Return a fixable or non-fixable violation for one concatenated docstring."""
    planned_change = _planned_change_for_docstring(docstring, context=context)
    if planned_change is None and docstring.kind != PDF_definition.DocstringKind.CONCATENATED:
        return None
    return rule_violations.violation_for_optional_planned_source_change(PDF000DocstringLiteralNormalization.meta, planned_change, line_numbers=_line_numbers(docstring))


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a source change for one renderable docstring."""
    rendered = _rendered_docstring(docstring, line_ending=context.line_ending)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=_line_numbers(docstring),
        suppression_line_numbers=(),
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
    prefix = _normalized_simple_docstring_prefix(node)
    literalized = string_literals.literalized_whitespace_fragments(fragments, line_ending=line_ending)
    if literalized == fragments and prefix == node.prefix:
        return None
    rendered = string_literals.render_simple_string_from_fragments(node, literalized, expected_value=expected_value, prefix=prefix)
    if rendered is not None:
        return rendered
    retargeted = string_literals.retarget_fragments(literalized, quote='"""', line_ending=line_ending)
    rendered = string_literals.render_simple_string_from_fragments(cst.SimpleString('""""""'), retargeted, expected_value=expected_value)
    if rendered is not None:
        return rendered
    return string_literals.render_value_as_simple_string(expected_value, line_ending=line_ending, escape_non_ascii=escape_non_ascii)


def _normalized_simple_docstring_prefix(node: cst.SimpleString) -> str:
    """Return the PDF000-normalized prefix for a simple docstring."""
    return "" if node.prefix.lower() == "u" else node.prefix


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return source line numbers covered by a docstring expression."""
    return tuple(line.line_number for line in docstring.physical_lines)
