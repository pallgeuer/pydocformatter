from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF103DocstringBlankLineWhitespace(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF103"),
        name="docstring-blank-line-whitespace",
        message="Blank docstring line has whitespace",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for blank docstring line whitespace."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Normalize whitespace on blank docstring lines."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe blank-line whitespace changes."""
    data = PDF_definition.PDF.require_data(context)
    source_lines = PDF_definition.source_lines_from_context(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: list[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    canonical_margin = PDF_definition.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
    targets = tuple(_line_target(docstring, line, canonical_margin=canonical_margin, context=context) for line in docstring.structure.lines)
    return PDF_definition.planned_simple_docstring_line_change(docstring, context=context, raw_line_targets=targets)


def _line_target(
    docstring: PDF_definition.DocstringInfo,
    line: PDF_definition.DocstringValueLine,
    *,
    canonical_margin: str,
    context: RuleContext,
) -> str | None:
    """Return the target raw text for one blank line, if it should change."""
    if docstring.value == "":
        return None
    if PDF_definition.has_space_tab_content(line.raw_text):
        return None
    if PDF_definition.is_same_line_closing_delimiter_prefix(docstring, line):
        return canonical_margin
    if context.settings.docstring_blank_line_style == settings_check.DocstringBlankLineStyle.ALIGNED:
        return canonical_margin
    return ""
