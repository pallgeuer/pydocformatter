"""PDF104 opening-quotes-whitespace rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF104OpeningQuotesWhitespace(RuleBase):
    """Rule implementation for PDF104.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF104"),
        name="opening-quotes-whitespace",
        message="Docstring has extra whitespace after opening quotes",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for extra whitespace after opening quotes."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Remove extra whitespace after opening quotes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_context_source_changes(context, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe opening quote whitespace changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one source replacement for opening quote whitespace."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    line = docstring.structure.lines[0]
    if not text_layout.has_space_tab_content(line.raw_text):
        return None
    whitespace_end = len(line.raw_text) - len(line.raw_text.lstrip(" \t"))
    if whitespace_end == 0:
        return None
    return _validated_change(docstring, line, whitespace_end=whitespace_end, replacement_text="", context=context) or _validated_change(
        docstring,
        line,
        whitespace_end=whitespace_end,
        replacement_text=" ",
        context=context,
    )


def _validated_change(
    docstring: PDF_definition.DocstringInfo,
    line: PDF_definition.DocstringValueLine,
    *,
    whitespace_end: int,
    replacement_text: str,
    context: RuleContext,
) -> rule_edits.PlannedSourceChange | None:
    """Return a validated opening quote whitespace change."""
    if line.source_line_number is None:
        return None
    target_line = f"{replacement_text}{line.raw_text[whitespace_end:]}"
    if target_line == line.raw_text:
        return None
    value_lines = [value_line.raw_text for value_line in docstring.structure.lines]
    value_lines[line.index] = target_line
    return PDF_definition.planned_simple_docstring_source_change(
        docstring,
        context=context,
        replacements=(
            rule_edits.PlannedTextReplacement(
                start_offset=line.start_offset,
                end_offset=line.start_offset + whitespace_end,
                text=replacement_text,
                line_numbers=(line.source_line_number,),
            ),
        ),
        value_lines=value_lines,
    )
