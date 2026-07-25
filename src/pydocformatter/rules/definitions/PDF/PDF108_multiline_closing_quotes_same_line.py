"""PDF108 multiline-closing-quotes-same-line rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF108MultilineClosingQuotesSameLine(RuleBase):
    """Rule implementation for PDF108.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

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
                        effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST)
                    ),
                ),
            ),
        ),
        incompatible_with=(RuleCode("PDF109"),),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for closing quotes that should share the final content line.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe closing-quote same-line changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.can_canonically_rewrite_simple_docstring(docstring, require_multiline=True):
        return None
    content_indexes = PDF_definition.docstring_content_indexes(docstring)
    if not content_indexes:
        return None
    last_content = content_indexes[-1]
    if last_content == len(docstring.structure.lines) - 1 and not PDF_definition.docstring_value_ends_with_newline(docstring):
        return None
    output_lines = tuple(PDF_definition.DocstringOutputLine(original=line, source=None, value=None) for line in docstring.structure.lines[: last_content + 1])
    line_numbers = PDF_definition.docstring_value_line_numbers(docstring.structure.lines[last_content:])
    return PDF_definition.planned_simple_docstring_output_change(
        docstring, context=context, output_lines=output_lines, line_numbers=line_numbers, preserve_trailing_newline=False, separator_fallback=PDF_definition.DocstringOutputSeparatorFallback.CLOSING
    )
