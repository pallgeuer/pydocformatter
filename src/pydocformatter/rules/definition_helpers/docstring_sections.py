"""Docstring section name metadata and matching."""

from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check

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
GOOGLE_SECTION_TERM_NAMES = {
    "arguments": "Args",
    "keyword arguments": "Keyword Args",
    "other arguments": "Other Args",
}
NUMPY_SECTION_TERM_NAMES = {
    "other params": "Other Parameters",
}
REST_PARAMETER_VALUE_FIELDS = frozenset({"param", "parameter", "arg", "argument", "key", "keyword", "kwarg"})
REST_PARAMETER_TYPE_FIELDS = frozenset({"type"})
REST_RETURN_VALUE_FIELDS = frozenset({"return", "returns"})
REST_RETURN_TYPE_FIELDS = frozenset({"rtype"})
REST_YIELD_VALUE_FIELDS = frozenset({"yield", "yields"})
REST_YIELD_TYPE_FIELDS = frozenset({"ytype"})
REST_EXCEPTION_FIELDS = frozenset({"raise", "raises", "except", "exception"})
REST_ATTRIBUTE_VALUE_FIELDS = frozenset({"ivar", "cvar", "var"})
REST_ATTRIBUTE_TYPE_FIELDS = frozenset({"vartype"})

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


def plural_section_name(convention: settings_check.DocstringConvention, name: str) -> str | None:
    """Return the preferred plural spelling for a convention section."""
    normalized = name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_SECTION_PLURAL_NAMES.get(normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_SECTION_PLURAL_NAMES.get(normalized)
    return None


def term_normalized_section_name(convention: settings_check.DocstringConvention, name: str) -> str | None:
    """Return the preferred equivalent section term for a convention section."""
    normalized = name.lower()
    if convention == settings_check.DocstringConvention.GOOGLE:
        return GOOGLE_SECTION_TERM_NAMES.get(normalized)
    if convention == settings_check.DocstringConvention.NUMPY:
        return NUMPY_SECTION_TERM_NAMES.get(normalized)
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
