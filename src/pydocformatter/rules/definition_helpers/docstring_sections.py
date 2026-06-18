from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check

GOOGLE_SECTIONS = {
    "args",
    "arguments",
    "attention",
    "attributes",
    "caution",
    "danger",
    "error",
    "example",
    "examples",
    "hint",
    "important",
    "keyword args",
    "keyword arguments",
    "methods",
    "note",
    "notes",
    "other args",
    "other arguments",
    "raises",
    "references",
    "return",
    "returns",
    "see also",
    "tip",
    "todo",
    "warning",
    "warnings",
    "warns",
    "yield",
    "yields",
}
NUMPY_SECTIONS = {
    "attributes",
    "examples",
    "extended summary",
    "methods",
    "notes",
    "other parameters",
    "other params",
    "parameters",
    "raises",
    "receives",
    "references",
    "returns",
    "see also",
    "short summary",
    "warnings",
    "warns",
    "yields",
}
PARAMETER_SECTION_NAMES = {"args", "arguments", "keyword args", "keyword arguments", "other args", "other arguments", "parameters", "other parameters", "other params", "receives"}
REST_PARAMETER_VALUE_FIELDS = frozenset({"param", "parameter", "arg", "argument", "keyword", "kwarg"})
REST_PARAMETER_TYPE_FIELDS = frozenset({"type"})
REST_RETURN_VALUE_FIELDS = frozenset({"return", "returns"})
REST_RETURN_TYPE_FIELDS = frozenset({"rtype"})
REST_YIELD_VALUE_FIELDS = frozenset({"yield", "yields"})
REST_YIELD_TYPE_FIELDS = frozenset({"ytype"})
REST_EXCEPTION_FIELDS = frozenset({"raise", "raises", "except", "exception"})

# Google style defines entry-section ordering, but does not define a canonical order for narrative admonition sections.
GOOGLE_ORDER_RANKS = {
    "args": 0,
    "arguments": 0,
    "keyword args": 0,
    "keyword arguments": 0,
    "other args": 0,
    "other arguments": 0,
    "return": 1,
    "returns": 1,
    "yield": 1,
    "yields": 1,
    "raises": 2,
    "warns": 2,
}
NUMPY_ORDER_RANKS = {
    "short summary": 0,
    "extended summary": 1,
    "parameters": 2,
    "returns": 3,
    "yields": 4,
    "receives": 5,
    "other parameters": 6,
    "other params": 6,
    "raises": 7,
    "warns": 8,
    "warnings": 8,
    "see also": 9,
    "notes": 10,
    "references": 11,
    "examples": 12,
    "attributes": 13,
    "methods": 14,
}
GOOGLE_REPEATED_SECTION_KEYS = {
    "arguments": "args",
    "examples": "example",
    "keyword arguments": "keyword args",
    "notes": "note",
    "other arguments": "other args",
    "returns": "return",
    "warnings": "warning",
    "yields": "yield",
}
NUMPY_REPEATED_SECTION_KEYS = {
    "other params": "other parameters",
    "warnings": "warns",
}


def convention_parses_sections(convention: settings_check.DocstringConvention) -> bool:
    """Return whether a docstring convention recognizes named sections."""
    return convention in (settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY)


def canonical_section_name(convention: settings_check.DocstringConvention, name: str) -> str | None:
    """Return the canonical spelling for a recognized convention section."""
    normalized = name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE and normalized in GOOGLE_SECTIONS:
        return normalized.title()
    if convention == settings_check.DocstringConvention.NUMPY and normalized in NUMPY_SECTIONS:
        return normalized.title()
    return None


def section_order_rank(convention: settings_check.DocstringConvention, section_name: str) -> int | None:
    """Return the ordering rank for a convention section, if it is ordered."""
    normalized = section_name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_ORDER_RANKS.get(normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_ORDER_RANKS.get(normalized)
    return None


def repeated_section_key(convention: settings_check.DocstringConvention, section_name: str) -> str:
    """Return the repeated-section identity key for a convention section."""
    normalized = section_name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_REPEATED_SECTION_KEYS.get(normalized, normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_REPEATED_SECTION_KEYS.get(normalized, normalized)
    return normalized
