"""PDF001 docstring-quote-style rule."""

from __future__ import annotations

import libcst as cst

import pydocformatter.rules.definition_helpers.string_literals as string_literals
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleFinding, RuleMetadata

_TARGET_QUOTE = '"""'


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF001DocstringQuoteStyle(RuleBase):
    """Rule implementation for PDF001.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF001"),
        name="docstring-quote-style",
        message="Docstring should use triple double quotes",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for docstrings that do not use triple double quotes."""
        return tuple(finding for docstring in _candidate_docstrings(context) if (finding := _finding_for_docstring(docstring, context=context)) is not None)

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Replace safely renderable docstrings with triple double-quoted literals."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        return rule_edits.fix_result_for_planned_source_changes(context, cls.meta, changes, instance_fixable=True)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return replacements for all safely requotable docstrings."""
    return tuple(change for docstring in _candidate_docstrings(context) if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _candidate_docstrings(context: RuleContext) -> tuple[PDF_definition.DocstringInfo, ...]:
    """Return simple docstrings that may need quote-style normalization."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(docstring for docstring in data.docstrings if isinstance(docstring.node, cst.SimpleString) and docstring.node.quote != _TARGET_QUOTE)


def _finding_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> RuleFinding | None:
    """Return a fixable or non-fixable finding for one docstring."""
    if not isinstance(docstring.node, cst.SimpleString) or docstring.node.quote == _TARGET_QUOTE:
        return None
    planned_change = _planned_change_for_docstring(docstring, context=context)
    return RuleFinding(rule=PDF001DocstringQuoteStyle.meta, line_numbers=_line_numbers(docstring), instance_fixable=planned_change is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a source change for one safely requotable docstring."""
    rendered = _rendered_docstring(docstring, line_ending=context.line_ending)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=_line_numbers(docstring),
        suppression_line_numbers=(),
    )


def _rendered_docstring(docstring: PDF_definition.DocstringInfo, *, line_ending: str) -> str | None:
    """Return triple double-quoted source for one simple docstring."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    body_source = string_literals.simple_string_body_source(docstring.node)
    if body_source is not None:
        rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, _TARGET_QUOTE, body_source, expected_value=docstring.value)
        if rendered is not None:
            return rendered
        if "r" in docstring.node.prefix.lower():
            return None
    fragments = string_literals.value_fragments_for_simple_string(docstring.node, line_ending=line_ending)
    if fragments is None:
        return None
    retargeted = string_literals.retarget_fragments(fragments, quote=_TARGET_QUOTE, line_ending=line_ending)
    body_source = "".join(fragment.source for fragment in retargeted)
    return string_literals.render_simple_string_from_body_source(docstring.node.prefix, _TARGET_QUOTE, body_source, expected_value=docstring.value)


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return source line numbers covered by a docstring expression."""
    return tuple(line.line_number for line in docstring.physical_lines)
