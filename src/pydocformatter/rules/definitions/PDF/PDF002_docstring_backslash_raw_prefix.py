"""PDF002 docstring-backslash-raw-prefix rule."""

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
from pydocformatter.rules.definition_helpers import string_literals
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF002DocstringBackslashRawPrefix(RuleBase):
    """Rule implementation for PDF002.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF002"),
        name="docstring-backslash-raw-prefix",
        message="Docstring with backslashes should use a raw string prefix",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for non-raw docstrings containing source backslashes.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return tuple(violation for docstring in _candidate_docstrings(context) if (violation := _violation_for_docstring(docstring, context=context)) is not None)


def _candidate_docstrings(context: RuleContext) -> tuple[PDF_definition.DocstringInfo, ...]:
    """Return simple non-raw docstrings whose source body contains a backslash."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(docstring for docstring in data.docstrings if _needs_raw_prefix(docstring))


def _violation_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_violations.RuleViolation | None:
    """Return a fixable or non-fixable violation for one docstring."""
    del context
    if not _needs_raw_prefix(docstring):
        return None
    planned_change = _planned_change_for_docstring(docstring)
    if planned_change is not None:
        return rule_violations.violation_for_optional_planned_source_change(PDF002DocstringBackslashRawPrefix.meta, planned_change, line_numbers=_line_numbers(docstring))
    # Non-fixable violations point only to manually actionable backslash lines; fixable source changes still report the
    # whole docstring range.
    reportable_lines = reportable_backslash_line_numbers(docstring)
    if not reportable_lines:
        return None
    return rule_violations.diagnostic(PDF002DocstringBackslashRawPrefix.meta, reportable_lines)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo) -> rule_edits.PlannedSourceChange | None:
    """Return a source change for one safely raw-prefixable docstring."""
    rendered = _rendered_docstring(docstring)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered), line_numbers=_line_numbers(docstring), suppression_line_numbers=())


def _needs_raw_prefix(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a simple docstring should use a raw prefix."""
    if not isinstance(docstring.node, cst.SimpleString):
        return False
    if "r" in docstring.node.prefix.lower():
        return False
    body_source = string_literals.simple_string_body_source(docstring.node)
    return body_source is not None and "\\" in body_source


def _rendered_docstring(docstring: PDF_definition.DocstringInfo) -> str | None:
    """Return raw-prefixed source for one simple docstring when value-preserving."""
    if not isinstance(docstring.node, cst.SimpleString) or docstring.node.prefix:
        return None
    body_source = string_literals.simple_string_body_source(docstring.node)
    if body_source is None or "\\" not in body_source:
        return None
    return string_literals.render_simple_string_from_body_source("r", docstring.node.quote, body_source, expected_value=docstring.value)


def reportable_backslash_line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return lines with non-fixable backslashes other than non-ASCII character escapes.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring whose source spelling contains backslashes.

    Returns:
        tuple[int, ...]: One-based physical source lines containing reportable backslash escapes.
    """
    if not isinstance(docstring.node, cst.SimpleString):
        return _line_numbers(docstring)
    body_source = string_literals.simple_string_body_source(docstring.node)
    if body_source is None:
        return _line_numbers(docstring)
    reportable_lines: set[int] = set()
    line_number = docstring.physical_lines[0].line_number
    index = 0
    while index < len(body_source):
        char = body_source[index]
        if char == "\\":
            parsed = string_literals.parse_simple_string_escape(body_source, index)
            if parsed is None:
                reportable_lines.add(line_number)
                index += 1
                continue
            if not _is_non_ascii_character_escape(parsed):
                reportable_lines.add(line_number)
            line_number += _line_breaks(body_source[index : parsed.end])
            index = parsed.end
        elif char == "\r":
            line_number += 1
            index += 2 if index + 1 < len(body_source) and body_source[index + 1] == "\n" else 1
        elif char == "\n":
            line_number += 1
            index += 1
        else:
            index += 1
    return tuple(sorted(reportable_lines))


def _is_non_ascii_character_escape(parsed: string_literals.StringEscape) -> bool:
    """Return whether PDF002 should suppress this non-ASCII character escape."""
    return len(parsed.value) == 1 and ord(parsed.value) > 0x7F


def _line_breaks(text: str) -> int:
    """Return the number of physical line breaks in source text."""
    count = 0
    index = 0
    while index < len(text):
        if text[index] == "\r":
            count += 1
            index += 2 if index + 1 < len(text) and text[index + 1] == "\n" else 1
        elif text[index] == "\n":
            count += 1
            index += 1
        else:
            index += 1
    return count


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return source line numbers covered by a docstring expression."""
    return tuple(line.line_number for line in docstring.physical_lines)
