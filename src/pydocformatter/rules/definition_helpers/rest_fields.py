from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits

PLURAL_FIELD_NAMES = {
    "raise": "raises",
    "returns": "return",
    "yields": "yield",
}
TERM_FIELD_NAMES = {
    "arg": "param",
    "argument": "param",
    "except": "raises",
    "exception": "raises",
    "key": "param",
    "keyword": "param",
    "kwarg": "param",
    "parameter": "param",
}


def label(entry: PDF_definition.DocstringEntry) -> str:
    """Return the user-facing spelling of a reStructuredText field."""
    field_name = entry.field_name or ""
    if entry.field_argument:
        return f":{field_name} {entry.field_argument}:"
    return f":{field_name}:"


def has_content(entry: PDF_definition.DocstringEntry) -> bool:
    """Return whether a reStructuredText field has inline or continuation content."""
    # A protected continuation body counts as content even when it has no reflowable description text.
    return bool(entry.description or entry.end_line > entry.start_line + 1)


def order_rank(entry: PDF_definition.DocstringEntry) -> int | None:
    """Return the canonical order rank for a comparable reStructuredText field."""
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER:
        return 0
    if entry.kind in (PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD):
        return 1
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION:
        return 2
    return None


def repetition_key(entry: PDF_definition.DocstringEntry) -> tuple[str, str, str] | None:
    """Return the comparable repetition key for a reStructuredText field."""
    field_name = entry.field_name or ""
    argument = entry.field_argument or ""
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and field_name in docstring_sections.REST_PARAMETER_VALUE_FIELDS:
        if not entry.names:
            return None
        return ("parameter", ",".join(entry.names), "")
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and field_name in docstring_sections.REST_PARAMETER_TYPE_FIELDS:
        if not argument:
            return None
        return ("parameter-type", argument, "")
    if entry.kind is PDF_definition.DocstringEntryKind.RETURN and field_name in docstring_sections.REST_RETURN_VALUE_FIELDS:
        return ("return", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.RETURN and field_name in docstring_sections.REST_RETURN_TYPE_FIELDS:
        return ("return-type", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.YIELD and field_name in docstring_sections.REST_YIELD_VALUE_FIELDS:
        return ("yield", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.YIELD and field_name in docstring_sections.REST_YIELD_TYPE_FIELDS:
        return ("yield-type", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION and field_name in docstring_sections.REST_EXCEPTION_FIELDS:
        if not entry.names:
            return None
        return ("exception", ",".join(entry.names), "")
    return ("field", field_name, argument)


def original_field_name(line: PDF_definition.DocstringValueLine) -> str | None:
    """Return the field name spelling from a parsed reStructuredText field line."""
    start_column, end_column = field_name_span(line)
    return line.text[start_column:end_column] or None


def plural_field_name(name: str) -> str | None:
    """Return the preferred singular or plural spelling for a reStructuredText field name."""
    return PLURAL_FIELD_NAMES.get(name.lower())


def term_normalized_field_name(name: str) -> str | None:
    """Return the preferred equivalent term for a reStructuredText field name."""
    return TERM_FIELD_NAMES.get(name.lower())


def replacement_for_field_name(line: PDF_definition.DocstringValueLine, new_name: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a replacement for a reStructuredText field name span."""
    start_column, end_column = field_name_span(line)
    return section_edits.text_replacement(line, start_column, end_column, new_name)


def field_name_span(line: PDF_definition.DocstringValueLine) -> tuple[int, int]:
    """Return the text column span for a reStructuredText field name."""
    start_column = field_name_start_column(line)
    end_column = start_column
    while end_column < len(line.text) and line.text[end_column] not in " \t:":
        end_column += 1
    return start_column, end_column


def field_name_start_column(line: PDF_definition.DocstringValueLine) -> int:
    """Return the text column where a reStructuredText field name starts."""
    # Parsed reStructuredText field lines start with a colon after indentation.
    return len(line.text) - len(line.text.lstrip(" \t")) + 1
