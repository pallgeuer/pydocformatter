"""Shared data models for PDF7xx typed-entry documentation rules."""

from __future__ import annotations

import dataclasses
import enum
import typing

if typing.TYPE_CHECKING:
    import pydocformatter.rules.definitions.PDF.PDF as PDF_definition


class TypedDocumentationSubject(enum.Enum):
    """Documented subject groups dispatched by PDF7xx rules.

    Attributes:
        PARAMETER: Function parameter docstring entries.
        RETURN: Function return docstring entries.
        YIELD: Function yield docstring entries.
        CLASS_ATTRIBUTE: Owner-docstring class attribute entries.
        MODULE_ATTRIBUTE: Owner-docstring module attribute entries.
    """

    PARAMETER = "parameter"
    RETURN = "return"
    YIELD = "yield"
    CLASS_ATTRIBUTE = "class attribute"
    MODULE_ATTRIBUTE = "module attribute"


@dataclasses.dataclass(frozen=True)
class TypedDocstringTypeSource:
    """One docstring type spelling and its source location.

    Attributes:
        text (str): Parsed docstring type text.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the type spelling.
    """

    text: str
    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class TypedDocstringEntry:
    """One logical owning-docstring entry with optional type and description text.

    Attributes:
        name (str | None): Documented item name, when the subject has named entries.
        type_sources (tuple[TypedDocstringTypeSource, ...]): Parsed type spellings associated with the entry.
        description (str): Description prose from value documentation, excluding type-only reST fields.
        line_numbers (tuple[int, ...]): Source lines occupied by the value entry, or type-only entry when no value entry
            is present.
    """

    name: str | None
    type_sources: tuple[TypedDocstringTypeSource, ...]
    description: str
    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class TypedDocumentationTarget:
    """One code/documentation pair inspected by PDF7xx rules.

    Attributes:
        name (str): User-facing target name used in diagnostics.
        entry (TypedDocstringEntry): Logical docstring entry for the target.
        annotation_text (str | None): Source annotation text from code, if present.
        owner (PDF_definition.DefinitionInfo | None): Definition that owns the docstring entry.
    """

    name: str
    entry: TypedDocstringEntry
    annotation_text: str | None
    owner: PDF_definition.DefinitionInfo | None = None
