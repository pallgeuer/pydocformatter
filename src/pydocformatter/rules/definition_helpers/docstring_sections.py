"""Docstring section name metadata and matching.

Attributes:
    GOOGLE_SECTIONS (set[str]): Lowercase Google-style section headings recognized by convention-aware parsing rules.
    NUMPY_SECTIONS (set[str]): Lowercase NumPy-style section headings recognized before underline validation and entry
        parsing.
    PARAMETER_SECTION_NAMES (set[str]): Section headings whose entries document callable parameters across supported
        docstring conventions.
    GOOGLE_SECTION_PLURAL_NAMES (dict[str, str]): Google headings that should use plural or canonical display spelling
        when PDF401 is selected.
    NUMPY_SECTION_PLURAL_NAMES (dict[str, str]): NumPy headings that should use plural or canonical display spelling
        when PDF401 is selected.
    GOOGLE_SECTION_TERM_NAMES (dict[str, str]): Google heading synonyms that should normalize to the preferred
        terminology when PDF402 is selected.
    NUMPY_SECTION_TERM_NAMES (dict[str, str]): NumPy heading synonyms that should normalize to the preferred terminology
        when PDF402 is selected.
    REST_FIELD_FAMILIES (tuple[RestFieldFamily, ...]): Standard semantic reStructuredText field families and their
        parsing, pairing, and diagnostic metadata.
    GOOGLE_ORDER_RANKS (dict[str, int]): Relative Google entry-section ordering used by PDF407 while leaving narrative
        sections unordered.
    NUMPY_ORDER_RANKS (dict[str, int]): Relative NumPy section ordering used by PDF407.
    GOOGLE_REPEATED_SECTION_KEYS (dict[str, str]): Google section-equivalence keys used to detect repeated sections
        across singular, plural, and synonym spellings.
    NUMPY_REPEATED_SECTION_KEYS (dict[str, str]): NumPy section-equivalence keys used to detect repeated sections across
        singular, plural, and synonym spellings.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import enum
import dataclasses

# First-party imports
from pydocformatter.cli import settings_check


class RestFieldRole(enum.Enum):
    """Semantic role of one standard reStructuredText field spelling.

    Attributes:
        VALUE: A field that provides value or description documentation.
        TYPE: A field that provides separate type documentation.
    """

    VALUE = "value"
    TYPE = "type"


class RestFieldArgumentPolicy(enum.Enum):
    """Argument arity accepted by one standard reStructuredText field family.

    Attributes:
        REQUIRED: Every field in the family requires an argument.
        OPTIONAL: Fields in the family accept either named or owner-wide forms.
        FORBIDDEN: Fields in the family must use owner-wide forms without arguments.
    """

    REQUIRED = "required"
    OPTIONAL = "optional"
    FORBIDDEN = "forbidden"


@dataclasses.dataclass(frozen=True)
class RestFieldFamily:
    """One semantic family of standard reStructuredText field spellings.

    Attributes:
        kind (str): Semantic docstring-entry kind value used by the PDF parser.
        label (str): User-facing value-field family label used in diagnostics.
        value_fields (frozenset[str]): Field spellings that provide value or description documentation.
        type_fields (frozenset[str]): Field spellings that provide separate type documentation.
        argument_policy (RestFieldArgumentPolicy): Whether fields in the family require, allow, or forbid arguments.
        strip_name_prefix_stars (bool): Whether pairing keys ignore leading variadic marker stars.
    """

    kind: str
    label: str
    value_fields: frozenset[str]
    type_fields: frozenset[str]
    argument_policy: RestFieldArgumentPolicy
    strip_name_prefix_stars: bool = False

    def pairing_key(self, name: str | None) -> str | None:
        """Return the normalized value/type pairing key for a field occurrence.

        Args:
            name (str | None): Parsed field name, or None for an owner-wide field.

        Returns:
            str | None: Name used for value/type pairing.
        """
        if name is not None and self.strip_name_prefix_stars:
            return name.lstrip("*")
        return name


GOOGLE_SECTIONS = {
    "arg",
    "args",
    "argument",
    "arguments",
    "attribute",
    "attention",
    "attributes",
    "caution",
    "danger",
    "error",
    "example",
    "examples",
    "hint",
    "important",
    "keyword arg",
    "keyword args",
    "keyword argument",
    "keyword arguments",
    "method",
    "methods",
    "note",
    "notes",
    "other arg",
    "other args",
    "other argument",
    "other arguments",
    "raise",
    "raises",
    "reference",
    "references",
    "return",
    "returns",
    "see also",
    "tip",
    "todo",
    "warning",
    "warnings",
    "warn",
    "warns",
    "yield",
    "yields",
}
NUMPY_SECTIONS = {
    "attribute",
    "attributes",
    "example",
    "examples",
    "extended summary",
    "method",
    "methods",
    "note",
    "notes",
    "other parameter",
    "other parameters",
    "other param",
    "other params",
    "parameter",
    "parameters",
    "raise",
    "raises",
    "receive",
    "receives",
    "reference",
    "references",
    "return",
    "returns",
    "see also",
    "short summary",
    "warning",
    "warnings",
    "warn",
    "warns",
    "yield",
    "yields",
}
PARAMETER_SECTION_NAMES = {
    "arg",
    "args",
    "argument",
    "arguments",
    "keyword arg",
    "keyword args",
    "keyword argument",
    "keyword arguments",
    "other arg",
    "other args",
    "other argument",
    "other arguments",
    "parameter",
    "parameters",
    "other parameter",
    "other parameters",
    "other param",
    "other params",
    "receive",
    "receives",
}
GOOGLE_SECTION_PLURAL_NAMES = {
    "arg": "Args",
    "argument": "Arguments",
    "attribute": "Attributes",
    "example": "Examples",
    "keyword arg": "Keyword Args",
    "keyword argument": "Keyword Arguments",
    "method": "Methods",
    "note": "Notes",
    "other arg": "Other Args",
    "other argument": "Other Arguments",
    "raise": "Raises",
    "reference": "References",
    "return": "Returns",
    "warning": "Warnings",
    "warn": "Warns",
    "yield": "Yields",
}
NUMPY_SECTION_PLURAL_NAMES = {
    "attribute": "Attributes",
    "example": "Examples",
    "method": "Methods",
    "note": "Notes",
    "other parameter": "Other Parameters",
    "other param": "Other Params",
    "parameter": "Parameters",
    "raise": "Raises",
    "receive": "Receives",
    "reference": "References",
    "return": "Returns",
    "warning": "Warnings",
    "warn": "Warns",
    "yield": "Yields",
}
GOOGLE_SECTION_TERM_NAMES = {"arguments": "Args", "keyword arguments": "Keyword Args", "other arguments": "Other Args"}
NUMPY_SECTION_TERM_NAMES = {"other params": "Other Parameters"}
REST_FIELD_FAMILIES = (
    RestFieldFamily(
        kind="parameter",
        label="parameter",
        value_fields=frozenset({"param", "parameter", "arg", "argument", "key", "keyword", "kwarg"}),
        type_fields=frozenset({"type"}),
        argument_policy=RestFieldArgumentPolicy.REQUIRED,
        strip_name_prefix_stars=True,
    ),
    RestFieldFamily(kind="return", label="return", value_fields=frozenset({"return", "returns"}), type_fields=frozenset({"rtype"}), argument_policy=RestFieldArgumentPolicy.FORBIDDEN),
    RestFieldFamily(kind="yield", label="yield", value_fields=frozenset({"yield", "yields"}), type_fields=frozenset({"ytype"}), argument_policy=RestFieldArgumentPolicy.OPTIONAL),
    RestFieldFamily(kind="exception", label="exception", value_fields=frozenset({"raise", "raises", "except", "exception"}), type_fields=frozenset(), argument_policy=RestFieldArgumentPolicy.REQUIRED),
    RestFieldFamily(kind="attribute", label="attribute", value_fields=frozenset({"ivar", "cvar", "var"}), type_fields=frozenset({"vartype"}), argument_policy=RestFieldArgumentPolicy.REQUIRED),
)
_REST_FIELD_FAMILY_BY_KIND = {family.kind: family for family in REST_FIELD_FAMILIES}
_REST_FIELD_METADATA_BY_NAME = {
    field_name: (family, role)
    for family in REST_FIELD_FAMILIES
    for role, field_names in ((RestFieldRole.VALUE, family.value_fields), (RestFieldRole.TYPE, family.type_fields))
    for field_name in field_names
}


def rest_field_family_for_kind(kind: str) -> RestFieldFamily | None:
    """Return standard reStructuredText field-family metadata for a semantic kind.

    Args:
        kind (str): Semantic docstring-entry kind value.

    Returns:
        RestFieldFamily | None: Matching family metadata, or None for a nonstandard kind.
    """
    return _REST_FIELD_FAMILY_BY_KIND.get(kind)


def rest_field_metadata(field_name: str | None) -> tuple[RestFieldFamily, RestFieldRole] | None:
    """Return standard reStructuredText family and role metadata for a field spelling.

    Args:
        field_name (str | None): Parsed field spelling without surrounding colons.

    Returns:
        tuple[RestFieldFamily, RestFieldRole] | None: Matching family and role, or None for a nonstandard field.
    """
    if field_name is None:
        return None
    return _REST_FIELD_METADATA_BY_NAME.get(field_name)


def is_rest_type_field(field_name: str | None) -> bool:
    """Return whether a field spelling provides separate reStructuredText type documentation.

    Args:
        field_name (str | None): Parsed field spelling without surrounding colons.

    Returns:
        bool: Whether the field belongs to the type role of a standard family.
    """
    metadata = rest_field_metadata(field_name)
    return metadata is not None and metadata[1] is RestFieldRole.TYPE


# Google style defines entry-section ordering, but does not define a canonical order for narrative admonition sections.
GOOGLE_ORDER_RANKS = {
    "arg": 0,
    "args": 0,
    "argument": 0,
    "arguments": 0,
    "keyword arg": 0,
    "keyword args": 0,
    "keyword argument": 0,
    "keyword arguments": 0,
    "other arg": 0,
    "other args": 0,
    "other argument": 0,
    "other arguments": 0,
    "return": 1,
    "returns": 1,
    "yield": 1,
    "yields": 1,
    "raise": 2,
    "raises": 2,
    "warn": 2,
    "warns": 2,
}
NUMPY_ORDER_RANKS = {
    "short summary": 0,
    "extended summary": 1,
    "parameter": 2,
    "parameters": 2,
    "return": 3,
    "returns": 3,
    "yield": 4,
    "yields": 4,
    "receive": 5,
    "receives": 5,
    "other parameter": 6,
    "other parameters": 6,
    "other param": 6,
    "other params": 6,
    "raise": 7,
    "raises": 7,
    "warn": 8,
    "warns": 8,
    "warning": 8,
    "warnings": 8,
    "see also": 9,
    "note": 10,
    "notes": 10,
    "reference": 11,
    "references": 11,
    "example": 12,
    "examples": 12,
    "attribute": 13,
    "attributes": 13,
    "method": 14,
    "methods": 14,
}
GOOGLE_REPEATED_SECTION_KEYS = {
    "arg": "args",
    "argument": "args",
    "arguments": "args",
    "attribute": "attributes",
    "examples": "example",
    "keyword arg": "keyword args",
    "keyword argument": "keyword args",
    "keyword arguments": "keyword args",
    "method": "methods",
    "notes": "note",
    "other arg": "other args",
    "other argument": "other args",
    "other arguments": "other args",
    "raise": "raises",
    "reference": "references",
    "return": "returns",
    "warnings": "warning",
    "warn": "warns",
    "yield": "yields",
}
NUMPY_REPEATED_SECTION_KEYS = {
    "attribute": "attributes",
    "example": "examples",
    "method": "methods",
    "note": "notes",
    "other parameter": "other parameters",
    "other params": "other parameters",
    "other param": "other parameters",
    "parameter": "parameters",
    "raise": "raises",
    "receive": "receives",
    "reference": "references",
    "return": "returns",
    "warning": "warnings",
    "warn": "warns",
    "yield": "yields",
}


def convention_parses_sections(convention: settings_check.DocstringConvention) -> bool:
    """Return whether a docstring convention recognizes named sections.

    Args:
        convention (settings_check.DocstringConvention): Active docstring convention.

    Returns:
        bool: Whether section-heading parsing is enabled for the convention.
    """
    return convention in {settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY}


def canonical_section_name(convention: settings_check.DocstringConvention, name: str) -> str | None:
    """Return the canonical spelling for a recognized convention section.

    Args:
        convention (settings_check.DocstringConvention): Active convention whose section names should be considered.
        name (str): Section heading text as parsed from a docstring.

    Returns:
        str | None: Title-cased canonical heading, or None when the convention does not recognize `name`.
    """
    normalized = name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE and normalized in GOOGLE_SECTIONS:
        return normalized.title()
    if convention == settings_check.DocstringConvention.NUMPY and normalized in NUMPY_SECTIONS:
        return normalized.title()
    return None


def plural_section_name(convention: settings_check.DocstringConvention, name: str) -> str | None:
    """Return the preferred plural spelling for a convention section.

    Args:
        convention (settings_check.DocstringConvention): Active convention whose pluralization policy should be used.
        name (str): Section heading text as parsed from a docstring.

    Returns:
        str | None: Preferred plural or canonical heading, or None when no plural replacement is configured.
    """
    normalized = name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_SECTION_PLURAL_NAMES.get(normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_SECTION_PLURAL_NAMES.get(normalized)
    return None


def term_normalized_section_name(convention: settings_check.DocstringConvention, name: str) -> str | None:
    """Return the preferred equivalent section term for a convention section.

    Args:
        convention (settings_check.DocstringConvention): Active convention whose terminology policy should be used.
        name (str): Section heading text as parsed from a docstring.

    Returns:
        str | None: Preferred equivalent heading, or None when no terminology replacement is configured.
    """
    normalized = name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_SECTION_TERM_NAMES.get(normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_SECTION_TERM_NAMES.get(normalized)
    return None


def section_order_rank(convention: settings_check.DocstringConvention, section_name: str) -> int | None:
    """Return the ordering rank for a convention section, if it is ordered.

    Args:
        convention (settings_check.DocstringConvention): Active convention whose ordering policy should be used.
        section_name (str): Section heading text as parsed from a docstring.

    Returns:
        int | None: Relative order rank, or None for sections with no enforced order.
    """
    normalized = section_name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_ORDER_RANKS.get(normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_ORDER_RANKS.get(normalized)
    return None


def repeated_section_key(convention: settings_check.DocstringConvention, section_name: str) -> str:
    """Return the repeated-section identity key for a convention section.

    Args:
        convention (settings_check.DocstringConvention): Active convention whose repeat-equivalence policy should be
            used.
        section_name (str): Section heading text as parsed from a docstring.

    Returns:
        str: Normalized key used to compare headings for duplicate-section detection.
    """
    normalized = section_name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_REPEATED_SECTION_KEYS.get(normalized, normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_REPEATED_SECTION_KEYS.get(normalized, normalized)
    return normalized
