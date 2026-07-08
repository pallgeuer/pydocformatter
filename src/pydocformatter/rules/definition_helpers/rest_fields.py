"""The reStructuredText field parsing helpers.

Attributes:
    PLURAL_FIELD_NAMES (dict[str, str]): ReStructuredText field spellings that should collapse to the singular canonical
        value-documentation form.
    TERM_FIELD_NAMES (dict[str, str]): ReStructuredText field aliases that should normalize to the preferred parameter
        or exception field term.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import docstring_sections, parameter_documentation, section_edits


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits


PLURAL_FIELD_NAMES = {"raise": "raises", "returns": "return", "yields": "yield"}
TERM_FIELD_NAMES = {"arg": "param", "argument": "param", "except": "raises", "exception": "raises", "key": "param", "keyword": "param", "kwarg": "param", "parameter": "param"}


@dataclasses.dataclass(frozen=True)
class NamedRepetitionKey:
    """Comparable and user-facing identity for one named reStructuredText entry.

    Attributes:
        comparison (tuple[str, str]): Semantic identity used to detect repeated entries.
        label (str): Entry name shown in the diagnostic message.
        message_kind (str): User-facing semantic entry kind shown in the diagnostic message.
    """

    comparison: tuple[str, str]
    label: str
    message_kind: str


def label(entry: PDF_definition.DocstringEntry) -> str:
    """Return the user-facing spelling of a reStructuredText field.

    Args:
        entry (PDF_definition.DocstringEntry): Parsed field entry to render.

    Returns:
        str: Field label including surrounding colons and any field argument.
    """
    field_name = entry.field_name or ""
    if entry.field_argument:
        return f":{field_name} {entry.field_argument}:"
    return f":{field_name}:"


def has_content(entry: PDF_definition.DocstringEntry) -> bool:
    """Return whether a reStructuredText field has inline or continuation content.

    Args:
        entry (PDF_definition.DocstringEntry): Parsed field entry to inspect.

    Returns:
        bool: Whether the field has a description or protected continuation body.
    """
    # A protected continuation body counts as content even when it has no reflowable description text.
    return bool(entry.description or entry.end_line > entry.start_line + 1)


def order_rank(entry: PDF_definition.DocstringEntry) -> int | None:
    """Return the canonical order rank for a comparable reStructuredText field.

    Args:
        entry (PDF_definition.DocstringEntry): Parsed field entry to rank by semantic kind.

    Returns:
        int | None: Relative order rank for comparable value-documentation fields, or None for unordered fields.
    """
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER:
        return 0
    if entry.kind in {PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD}:
        return 1
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION:
        return 2
    return None


def repetition_key(entry: PDF_definition.DocstringEntry) -> tuple[str, str, str] | None:
    """Return the comparable repetition key for a reStructuredText field.

    Args:
        entry (PDF_definition.DocstringEntry): Parsed field entry to compare for duplicate detection.

    Returns:
        tuple[str, str, str] | None: Semantic field identity, or None when the field lacks a comparable argument or is a
            named field handled by PDF412.
    """
    field_name = entry.field_name or ""
    argument = entry.field_argument or ""
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and field_name in docstring_sections.REST_PARAMETER_VALUE_FIELDS | docstring_sections.REST_PARAMETER_TYPE_FIELDS:
        return None
    if entry.kind is PDF_definition.DocstringEntryKind.RETURN and field_name in docstring_sections.REST_RETURN_VALUE_FIELDS:
        return ("return", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.RETURN and field_name in docstring_sections.REST_RETURN_TYPE_FIELDS:
        return ("return-type", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.YIELD and field_name in docstring_sections.REST_YIELD_VALUE_FIELDS:
        return ("yield", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.YIELD and field_name in docstring_sections.REST_YIELD_TYPE_FIELDS:
        return ("yield-type", "", "")
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION and field_name in docstring_sections.REST_EXCEPTION_FIELDS:
        return None
    if entry.kind is PDF_definition.DocstringEntryKind.ATTRIBUTE and field_name in docstring_sections.REST_ATTRIBUTE_VALUE_FIELDS | docstring_sections.REST_ATTRIBUTE_TYPE_FIELDS:
        return None
    return ("field", field_name, argument)


def named_repetition_keys(entry: PDF_definition.DocstringEntry) -> tuple[NamedRepetitionKey, ...]:
    """Return PDF412 duplicate keys for named reStructuredText entry fields.

    Args:
        entry (PDF_definition.DocstringEntry): Parsed reStructuredText field entry to compare for repeated named
            documentation.

    Returns:
        tuple[NamedRepetitionKey, ...]: Comparable identities and diagnostic labels for named fields owned by PDF412.
    """
    field_name = entry.field_name or ""
    argument = entry.field_argument or ""
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and field_name in docstring_sections.REST_PARAMETER_VALUE_FIELDS:
        return tuple(
            NamedRepetitionKey(("rest-parameter", parameter_documentation.parameter_comparison_name(name)), parameter_documentation.parameter_comparison_name(name), "reST parameter")
            for name in entry.names
            if name
        )
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and field_name in docstring_sections.REST_PARAMETER_TYPE_FIELDS:
        return (
            (
                NamedRepetitionKey(
                    ("rest-parameter-type", parameter_documentation.parameter_comparison_name(argument)), parameter_documentation.parameter_comparison_name(argument), "reST parameter type"
                ),
            )
            if argument
            else ()
        )
    if entry.kind is PDF_definition.DocstringEntryKind.ATTRIBUTE and field_name in docstring_sections.REST_ATTRIBUTE_VALUE_FIELDS:
        return tuple(NamedRepetitionKey(("rest-attribute", name), name, "reST attribute") for name in entry.names if name)
    if entry.kind is PDF_definition.DocstringEntryKind.ATTRIBUTE and field_name in docstring_sections.REST_ATTRIBUTE_TYPE_FIELDS:
        return (NamedRepetitionKey(("rest-attribute-type", argument), argument, "reST attribute type"),) if argument else ()
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION and field_name in docstring_sections.REST_EXCEPTION_FIELDS:
        return tuple(NamedRepetitionKey(("rest-exception", name), name, "reST exception") for name in entry.names if name)
    return ()


def original_field_name(line: PDF_definition.DocstringValueLine) -> str | None:
    """Return the field name spelling from a parsed reStructuredText field line.

    Args:
        line (PDF_definition.DocstringValueLine): Parsed docstring line containing a reStructuredText field.

    Returns:
        str | None: Field name as written in source, or None if the span is empty.
    """
    start_column, end_column = field_name_span(line)
    return line.text[start_column:end_column] or None


def plural_field_name(name: str) -> str | None:
    """Return the preferred singular or plural spelling for a reStructuredText field name.

    Args:
        name (str): Field name spelling to normalize.

    Returns:
        str | None: Preferred spelling for pluralization checks, or None when no replacement is configured.
    """
    return PLURAL_FIELD_NAMES.get(name.lower())


def term_normalized_field_name(name: str) -> str | None:
    """Return the preferred equivalent term for a reStructuredText field name.

    Args:
        name (str): Field name spelling to normalize.

    Returns:
        str | None: Preferred field term, or None when no replacement is configured.
    """
    return TERM_FIELD_NAMES.get(name.lower())


def replacement_for_field_name(line: PDF_definition.DocstringValueLine, new_name: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a replacement for a reStructuredText field name span.

    Args:
        line (PDF_definition.DocstringValueLine): Parsed docstring line containing a reStructuredText field.
        new_name (str): Replacement field name without surrounding colons.

    Returns:
        rule_edits.PlannedTextReplacement | None: Planned text replacement, or None if the span cannot be mapped safely.
    """
    start_column, end_column = field_name_span(line)
    return section_edits.text_replacement(line, start_column, end_column, new_name)


def field_name_span(line: PDF_definition.DocstringValueLine) -> tuple[int, int]:
    """Return the text column span for a reStructuredText field name.

    Args:
        line (PDF_definition.DocstringValueLine): Parsed docstring line containing a reStructuredText field.

    Returns:
        tuple[int, int]: Start and end text columns of the field name without colons or arguments.
    """
    start_column = field_name_start_column(line)
    end_column = start_column
    while end_column < len(line.text) and line.text[end_column] not in " \t:":
        end_column += 1
    return start_column, end_column


def field_name_start_column(line: PDF_definition.DocstringValueLine) -> int:
    """Return the text column where a reStructuredText field name starts.

    Args:
        line (PDF_definition.DocstringValueLine): Parsed docstring line containing a reStructuredText field.

    Returns:
        int: Text column immediately after the opening field colon.
    """
    # Parsed reStructuredText field lines start with a colon after indentation.
    return len(line.text) - len(line.text.lstrip(" \t")) + 1
