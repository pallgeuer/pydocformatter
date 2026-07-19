"""PDF105 closing-quotes-whitespace rule."""

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
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import text_layout
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF105ClosingQuotesWhitespace(RuleBase):
    """Rule implementation for PDF105.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF105"),
        name="closing-quotes-whitespace",
        message="Docstring has extra whitespace before closing quotes",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for extra whitespace before closing quotes.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe closing quote whitespace changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one source replacement for closing quote whitespace."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    line = docstring.structure.lines[-1]
    if not PDF_definition.is_same_line_closing_delimiter_prefix(docstring, line) or not text_layout.has_space_tab_content(line.raw_text):
        return None
    content_end = len(line.raw_text.rstrip(" \t"))
    if content_end == len(line.raw_text):
        return None
    return (
        _validated_change(docstring, line, content_end=content_end, replacement_text="", context=context)
        or _escaped_quote_change(docstring, line, content_end=content_end, context=context)
        or _validated_change(docstring, line, content_end=content_end, replacement_text=" ", context=context)
    )


def _escaped_quote_change(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine, *, content_end: int, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a value-preserving closing quote escape change."""
    if line.source_line_number is None or not isinstance(docstring.node, cst.SimpleString):
        return None
    target_value_line = line.raw_text[:content_end]
    target_source_line = PDF_definition.escaped_closing_quote_body_source(docstring.node, target_value_line)
    if target_source_line is None or target_source_line == target_value_line:
        return None
    replacement_start = _common_prefix_length(target_value_line, target_source_line)
    value_lines = [value_line.raw_text for value_line in docstring.structure.lines]
    value_lines[line.index] = target_value_line
    return PDF_definition.planned_simple_docstring_source_change(
        docstring,
        context=context,
        replacements=(
            rule_edits.PlannedTextReplacement(
                start_offset=line.start_offset + replacement_start, end_offset=line.end_offset, text=target_source_line[replacement_start:], line_numbers=(line.source_line_number,)
            ),
        ),
        value_lines=value_lines,
    )


def _validated_change(
    docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine, *, content_end: int, replacement_text: str, context: RuleContext
) -> rule_edits.PlannedSourceChange | None:
    """Return a validated closing quote whitespace change."""
    if line.source_line_number is None:
        return None
    target_line = f"{line.raw_text[:content_end]}{replacement_text}"
    if target_line == line.raw_text:
        return None
    value_lines = [value_line.raw_text for value_line in docstring.structure.lines]
    value_lines[line.index] = target_line
    return PDF_definition.planned_simple_docstring_source_change(
        docstring,
        context=context,
        replacements=(rule_edits.PlannedTextReplacement(start_offset=line.start_offset + content_end, end_offset=line.end_offset, text=replacement_text, line_numbers=(line.source_line_number,)),),
        value_lines=value_lines,
    )


def _common_prefix_length(first: str, second: str) -> int:
    """Return the shared character-prefix length for two strings."""
    return next((index for index, (left, right) in enumerate(zip(first, second, strict=False)) if left != right), min(len(first), len(second)))
