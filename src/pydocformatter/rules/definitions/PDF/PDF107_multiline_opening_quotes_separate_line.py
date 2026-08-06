"""PDF107 multiline-opening-quotes-separate-line rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_rendering, docstring_source, string_literals
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF107MultilineOpeningQuotesSeparateLine(RuleBase):
    """Rule implementation for PDF107.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF107"),
        name="multiline-opening-quotes-separate-line",
        message="Multi-line docstring opening quotes should be on a separate line",
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
        incompatible_with=(RuleCode("PDF106"),),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for opening quotes that should be separate from content.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe opening-quote separate-line changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not docstring_source.can_canonically_rewrite_simple_docstring(docstring, require_multiline=True):
        return None
    content_indexes = docstring_source.docstring_content_indexes(docstring)
    if not content_indexes or content_indexes[0] != 0:
        return None
    canonical_margin = docstring_source.docstring_canonical_margin(docstring, context=context)
    first_line = docstring.structure.lines[0]
    moved_text = first_line.raw_text.lstrip(ascii_whitespace.SPACE_AND_TAB)
    output_lines = (
        docstring_rendering.DocstringOutputLine(source="", value=""),
        docstring_rendering.DocstringOutputLine(source=f"{canonical_margin}{moved_text}", value=f"{canonical_margin}{moved_text}"),
        *(docstring_rendering.DocstringOutputLine(original=line, source=None, value=None) for line in docstring.structure.lines[1:]),
    )
    line_numbers = docstring_source.docstring_value_line_numbers((first_line,))
    return _planned_fast_body_change(docstring, context=context, output_lines=output_lines, line_numbers=line_numbers) or docstring_rendering.planned_simple_docstring_output_change(
        docstring, context=context, output_lines=output_lines, line_numbers=line_numbers
    )


def _planned_fast_body_change(
    docstring: PDF_definition.DocstringInfo, *, context: RuleContext, output_lines: tuple[docstring_rendering.DocstringOutputLine, ...], line_numbers: tuple[int, ...]
) -> rule_edits.PlannedSourceChange | None:
    """Return a validated replacement without decomposing the whole literal into value fragments."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    body_source = string_literals.simple_string_body_source(docstring.node)
    if body_source is None:
        return None
    first_line_source, rest_source = _split_first_body_line(body_source)
    if first_line_source is None:
        return None
    moved_text = first_line_source.lstrip(ascii_whitespace.SPACE_AND_TAB)
    moved_source = f"{docstring_source.docstring_canonical_margin(docstring, context=context)}{moved_text}"
    replacement_body = f"{context.line_ending}{moved_source}{context.line_ending}{rest_source}"
    expected_value = docstring_rendering.docstring_output_expected_value(output_lines, preserve_trailing_newline=docstring_source.docstring_value_ends_with_newline(docstring))
    rendered = docstring_rendering.render_docstring_output_with_separator_fallback(docstring, body_source=replacement_body, expected_value=expected_value, separator_fallback=None)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered), line_numbers=line_numbers, suppression_line_numbers=())


def _split_first_body_line(body_source: str) -> tuple[str | None, str]:
    """Return the first physical body line and remaining source after its line ending."""
    for index, char in enumerate(body_source):
        if char == "\r":
            end = index + 2 if index + 1 < len(body_source) and body_source[index + 1] == "\n" else index + 1
            return body_source[:index], body_source[end:]
        if char == "\n":
            return body_source[:index], body_source[index + 1 :]
    return None, ""
