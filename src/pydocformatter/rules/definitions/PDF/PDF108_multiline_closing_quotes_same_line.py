from __future__ import annotations

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF108MultilineClosingQuotesSameLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF108"),
        name="multiline-closing-quotes-same-line",
        message="Multi-line docstring closing quotes should be on the same line as content",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED,
                        values=(DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST),
                    ),
                ),
            ),
        ),
        incompatible_with=(RuleCode("PDF109"),),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for closing quotes that should share the final content line."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Move closing quotes onto the final content line where safe."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_context_source_changes(context, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe closing-quote same-line changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring, require_multiline=True):
        return None
    content_indexes = PDF_definition.docstring_content_indexes(docstring)
    if not content_indexes:
        return None
    last_content = content_indexes[-1]
    if last_content == len(docstring.structure.lines) - 1 and not PDF_definition.docstring_value_ends_with_newline(docstring):
        return None
    output_lines = tuple(PDF_definition.DocstringOutputLine(original=line) for line in docstring.structure.lines[: last_content + 1])
    line_numbers = PDF_definition.docstring_value_line_numbers(docstring.structure.lines[last_content:])
    return PDF_definition.planned_simple_docstring_output_change(
        docstring,
        context=context,
        output_lines=output_lines,
        line_numbers=line_numbers,
        preserve_trailing_newline=False,
        separator_fallback=PDF_definition.DocstringOutputSeparatorFallback.CLOSING,
    )
