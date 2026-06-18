from __future__ import annotations

import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF107MultilineOpeningQuotesSepLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF107"),
        name="multiline-opening-quotes-sep-line",
        message="Multi-line docstring opening quotes should be on a separate line",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED,
                        values=(DocstringConvention.NONE, DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST, DocstringConvention.PEP257),
                    ),
                ),
            ),
        ),
        incompatible_with=(RuleCode("PDF106"),),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for opening quotes that should be separate from content."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Move first content lines below opening quotes where safe."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe opening-quote separate-line changes."""
    data = PDF_definition.PDF.require_data(context)
    source_lines = source_text.source_lines_from_context(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: list[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring, require_multiline=True):
        return None
    content_indexes = PDF_definition.docstring_content_indexes(docstring)
    if not content_indexes or content_indexes[0] != 0:
        return None
    canonical_margin = PDF_definition.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
    first_line = docstring.structure.lines[0]
    moved_text = first_line.raw_text.lstrip(" \t")
    output_lines = (
        PDF_definition.DocstringOutputLine(source="", value=""),
        PDF_definition.DocstringOutputLine(source=f"{canonical_margin}{moved_text}", value=f"{canonical_margin}{moved_text}"),
        *(PDF_definition.DocstringOutputLine(original=line) for line in docstring.structure.lines[1:]),
    )
    line_numbers = PDF_definition.docstring_value_line_numbers((first_line,))
    return PDF_definition.planned_simple_docstring_output_change(docstring, context=context, output_lines=output_lines, line_numbers=line_numbers)
