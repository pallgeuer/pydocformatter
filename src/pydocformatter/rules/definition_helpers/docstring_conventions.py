"""Docstring convention policy helpers."""

from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check


def ignored_conventions_except(*allowed: settings_check.DocstringConvention) -> tuple[settings_check.DocstringConvention, ...]:
    """Return docstring conventions ignored by a convention-specific rule.

    Args:
        *allowed (settings_check.DocstringConvention): Conventions where the rule should remain selectable by broad
            selectors.

    Returns:
        tuple[settings_check.DocstringConvention, ...]: Conventions that should trigger a metadata ignored effect.
    """
    allowed_set = set(allowed)
    return tuple(convention for convention in settings_check.DocstringConvention if convention not in allowed_set)


def missing_documentation_is_inert(convention: settings_check.DocstringConvention) -> bool:
    """Return whether missing-documentation rules stay inert because convention-specific documentation is not parsed.

    Args:
        convention (settings_check.DocstringConvention): Active docstring convention.

    Returns:
        bool: Whether missing-documentation checks should avoid reporting convention-targeted findings.
    """
    return convention in (settings_check.DocstringConvention.NONE, settings_check.DocstringConvention.PEP257)
