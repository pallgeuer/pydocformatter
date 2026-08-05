"""PDF106 multiline-opening-quotes-same-line rule."""

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
from pydocformatter.rules.definition_helpers import docstring_rendering, docstring_source
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF106MultilineOpeningQuotesSameLine(RuleBase):
    """Rule implementation for PDF106.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF106"),
        name="multiline-opening-quotes-same-line",
        message="Multi-line docstring opening quotes should be on the same line as content",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NUMPY, DocstringConvention.PEP257)),)),
        ),
        incompatible_with=(RuleCode("PDF107"),),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for opening quotes that should share the first content line.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe opening-quote same-line changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not docstring_source.can_canonically_rewrite_simple_docstring(docstring, require_multiline=True):
        return None
    content_indexes = docstring_source.docstring_content_indexes(docstring)
    if not content_indexes:
        return None
    first_content = content_indexes[0]
    if first_content == 0:
        return None
    output_lines = (
        docstring_rendering.DocstringOutputLine(original=docstring.structure.lines[first_content], strip_docstring_margin=True, source=None, value=None),
        *(docstring_rendering.DocstringOutputLine(original=line, source=None, value=None) for line in docstring.structure.lines[first_content + 1 :]),
    )
    line_numbers = docstring_source.docstring_value_line_numbers(docstring.structure.lines[: first_content + 1])
    return docstring_rendering.planned_simple_docstring_output_change(
        docstring, context=context, output_lines=output_lines, line_numbers=line_numbers, separator_fallback=docstring_rendering.DocstringOutputSeparatorFallback.OPENING
    )
