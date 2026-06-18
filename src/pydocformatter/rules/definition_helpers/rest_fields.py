from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition


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
