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
import collections
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_sections, section_edits


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


@dataclasses.dataclass(frozen=True)
class RestFieldPart:
    """One reStructuredText value or type field occurrence used for pairing.

    Attributes:
        key (str | None): Normalized identity used to pair value and type fields.
        name (str | None): Parsed field argument spelling associated with this occurrence.
        entry (PDF_definition.DocstringEntry): Parsed reStructuredText field represented by this occurrence.
        order (int): Monotonic source-order index among considered entries.
    """

    key: str | None
    name: str | None
    entry: PDF_definition.DocstringEntry
    order: int


@dataclasses.dataclass(frozen=True)
class RestFieldPair:
    """One FIFO-associated reStructuredText value and type field occurrence.

    Attributes:
        value (RestFieldPart): Value or description field occurrence.
        type (RestFieldPart): Corresponding type field occurrence.
    """

    value: RestFieldPart
    type: RestFieldPart


@dataclasses.dataclass(frozen=True)
class RestFieldPairing:
    """Complete one-to-one pairing result for one reStructuredText entry kind.

    Attributes:
        value_parts (tuple[RestFieldPart, ...]): Value field occurrences in source order.
        pairs (tuple[RestFieldPair, ...]): FIFO pairs ordered by their value occurrences.
        orphan_types (tuple[RestFieldPart, ...]): Type occurrences without corresponding value fields.
    """

    value_parts: tuple[RestFieldPart, ...]
    pairs: tuple[RestFieldPair, ...]
    orphan_types: tuple[RestFieldPart, ...]


def pair_value_and_type_fields(entries: tuple[PDF_definition.DocstringEntry, ...], kind: PDF_definition.DocstringEntryKind) -> RestFieldPairing:
    """Pair reStructuredText value and type fields of one semantic kind.

    Args:
        entries (tuple[PDF_definition.DocstringEntry, ...]): Parsed entries from one docstring.
        kind (PDF_definition.DocstringEntryKind): Parameter, return, yield, or attribute kind to pair.

    Returns:
        RestFieldPairing: Ordered FIFO pairs and unmatched occurrences for the requested kind.

    Raises:
        ValueError: If the requested entry kind has no reStructuredText value/type pairing semantics.
    """
    return _pair_value_and_type_fields(entries, (kind,))[kind]


def pair_all_value_and_type_fields(entries: tuple[PDF_definition.DocstringEntry, ...]) -> dict[PDF_definition.DocstringEntryKind, RestFieldPairing]:
    """Pair every supported reStructuredText value/type field family in one entry scan.

    Args:
        entries (tuple[PDF_definition.DocstringEntry, ...]): Parsed entries from one docstring.

    Returns:
        dict[PDF_definition.DocstringEntryKind, RestFieldPairing]: Pairing results keyed by every pairable semantic
            kind.
    """
    kinds = tuple(PDF_definition.DocstringEntryKind(family.kind) for family in docstring_sections.REST_FIELD_FAMILIES if family.type_fields)
    return _pair_value_and_type_fields(entries, kinds)


def value_field_label(entry: PDF_definition.DocstringEntry) -> str:
    """Return the user-facing value-field family label for a standard reStructuredText entry.

    Args:
        entry (PDF_definition.DocstringEntry): Parsed standard reStructuredText entry.

    Returns:
        str: Value-field family label used in diagnostics.

    Raises:
        ValueError: If the entry is not a standard reStructuredText field.
    """
    metadata = docstring_sections.rest_field_metadata(entry.field_name)
    if metadata is None or metadata[0].kind != entry.kind.value:
        raise ValueError("A value-field label requires a standard reStructuredText entry")
    return metadata[0].label


def _pair_value_and_type_fields(entries: tuple[PDF_definition.DocstringEntry, ...], kinds: tuple[PDF_definition.DocstringEntryKind, ...]) -> dict[PDF_definition.DocstringEntryKind, RestFieldPairing]:
    """Pair selected reStructuredText value/type field families in one entry scan."""
    families: dict[PDF_definition.DocstringEntryKind, docstring_sections.RestFieldFamily] = {}
    value_parts_by_kind: dict[PDF_definition.DocstringEntryKind, list[RestFieldPart]] = {}
    type_parts_by_kind: dict[PDF_definition.DocstringEntryKind, list[RestFieldPart]] = {}
    for kind in kinds:
        family = docstring_sections.rest_field_family_for_kind(kind.value)
        if family is None or not family.type_fields:
            raise ValueError(f"Unsupported reStructuredText value/type pairing kind: {kind.value}")
        families[kind] = family
        value_parts_by_kind[kind] = []
        type_parts_by_kind[kind] = []
    part_order = 0
    for entry in entries:
        names = entry.names or (None,)
        metadata = docstring_sections.rest_field_metadata(entry.field_name)
        family = families.get(entry.kind)
        if metadata is not None and family is not None and metadata[0] is family:
            target = type_parts_by_kind[entry.kind] if metadata[1] is docstring_sections.RestFieldRole.TYPE else value_parts_by_kind[entry.kind]
            target.extend(RestFieldPart(key=family.pairing_key(name), name=name, entry=entry, order=part_order + offset) for offset, name in enumerate(names))
        part_order += len(names)
    return {kind: _pair_field_parts(value_parts_by_kind[kind], type_parts_by_kind[kind]) for kind in kinds}


def _pair_field_parts(value_parts: list[RestFieldPart], type_parts: list[RestFieldPart]) -> RestFieldPairing:
    """Return FIFO pairs and orphan types for one semantic field family."""
    type_parts_by_key: dict[str | None, collections.deque[RestFieldPart]] = {}
    for type_part in type_parts:
        type_parts_by_key.setdefault(type_part.key, collections.deque()).append(type_part)
    pairs: list[RestFieldPair] = []
    used_type_orders: set[int] = set()
    for value_part in value_parts:
        queued_type_parts = type_parts_by_key.get(value_part.key)
        if not queued_type_parts:
            continue
        type_part = queued_type_parts.popleft()
        used_type_orders.add(type_part.order)
        pairs.append(RestFieldPair(value=value_part, type=type_part))
    return RestFieldPairing(value_parts=tuple(value_parts), pairs=tuple(pairs), orphan_types=tuple(type_part for type_part in type_parts if type_part.order not in used_type_orders))


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
    metadata = docstring_sections.rest_field_metadata(field_name)
    if metadata is not None and metadata[0].kind == entry.kind.value:
        family, role = metadata
        if entry.kind in {PDF_definition.DocstringEntryKind.PARAMETER, PDF_definition.DocstringEntryKind.EXCEPTION, PDF_definition.DocstringEntryKind.ATTRIBUTE}:
            return None
        if entry.kind in {PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD}:
            suffix = "-type" if role is docstring_sections.RestFieldRole.TYPE else ""
            return (f"{family.kind}{suffix}", "", "")
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
    metadata = docstring_sections.rest_field_metadata(field_name)
    if metadata is None or metadata[0].kind != entry.kind.value:
        return ()
    family, role = metadata
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER:
        if role is docstring_sections.RestFieldRole.VALUE:
            return tuple(
                NamedRepetitionKey(("rest-parameter", comparison_name), comparison_name, "reST parameter")
                for name in entry.names
                if name
                for comparison_name in (family.pairing_key(name),)
                if comparison_name is not None
            )
        comparison_name = family.pairing_key(argument)
        return (NamedRepetitionKey(("rest-parameter-type", comparison_name), comparison_name, "reST parameter type"),) if comparison_name else ()
    if entry.kind is PDF_definition.DocstringEntryKind.ATTRIBUTE:
        if role is docstring_sections.RestFieldRole.VALUE:
            return tuple(NamedRepetitionKey(("rest-attribute", name), name, "reST attribute") for name in entry.names if name)
        return (NamedRepetitionKey(("rest-attribute-type", argument), argument, "reST attribute type"),) if argument else ()
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION:
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
    return len(line.text) - len(line.text.lstrip(ascii_whitespace.SPACE_AND_TAB)) + 1
