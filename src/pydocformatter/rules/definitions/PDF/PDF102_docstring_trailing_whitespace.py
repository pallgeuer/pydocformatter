from __future__ import annotations

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF102DocstringTrailingWhitespace(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF102"),
        name="docstring-trailing-whitespace",
        message="Non-empty docstring line has trailing whitespace",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for trailing whitespace on non-empty docstring lines."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Remove trailing whitespace from non-empty docstring lines."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe trailing-whitespace changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    targets: list[str | None] = []
    for line in docstring.structure.lines:
        target = None
        if PDF_definition.has_space_tab_content(line.raw_text) and _has_following_evaluated_newline(docstring, line):
            stripped = line.raw_text.rstrip(" \t")
            if stripped != line.raw_text:
                target = stripped
        targets.append(target)
    return PDF_definition.planned_simple_docstring_line_change(docstring, context=context, raw_line_targets=tuple(targets))


def _has_following_evaluated_newline(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine) -> bool:
    """Return whether a logical line is followed by an evaluated newline separator."""
    return line.end_offset < len(docstring.value)
