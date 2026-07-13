"""Docstring convention policy helpers.

Attributes:
    UNPARSED_CONVENTIONS (tuple[settings_check.DocstringConvention, ...]): Conventions that do not parse Google
        sections, NumPy sections, or reStructuredText fields.
    PARSED_CONVENTIONS (tuple[settings_check.DocstringConvention, ...]): Conventions that parse at least one supported
        section or field syntax.
"""

# Future imports
from __future__ import annotations

# First-party imports
from pydocformatter.cli import settings_check
from pydocformatter.rules.models import RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


UNPARSED_CONVENTIONS = (settings_check.DocstringConvention.NONE, settings_check.DocstringConvention.PEP257)
PARSED_CONVENTIONS = (settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY, settings_check.DocstringConvention.REST)


def conventions_except(*allowed: settings_check.DocstringConvention) -> tuple[settings_check.DocstringConvention, ...]:
    """Return docstring conventions not included in the allowed set.

    Args:
        *allowed (settings_check.DocstringConvention): Conventions to exclude from the returned tuple.

    Returns:
        tuple[settings_check.DocstringConvention, ...]: Conventions not listed in `allowed`.
    """
    allowed_set = set(allowed)
    return tuple(convention for convention in settings_check.DocstringConvention if convention not in allowed_set)


def ignored_conventions_except(*allowed: settings_check.DocstringConvention) -> tuple[settings_check.DocstringConvention, ...]:
    """Return docstring conventions ignored by a convention-specific rule.

    Args:
        *allowed (settings_check.DocstringConvention): Conventions where the rule should remain selectable by broad
            selectors.

    Returns:
        tuple[settings_check.DocstringConvention, ...]: Conventions that should trigger a metadata ignored effect.
    """
    return conventions_except(*allowed)


def convention_setting_effects(*, disabled: tuple[settings_check.DocstringConvention, ...] = (), ignored: tuple[settings_check.DocstringConvention, ...] = ()) -> tuple[RuleSettingEffects, ...]:
    """Return docstring-convention setting effects for rule metadata.

    Args:
        disabled (tuple[settings_check.DocstringConvention, ...]): Conventions that should always remove the rule from
            active selection.
        ignored (tuple[settings_check.DocstringConvention, ...]): Conventions that should remove broad rule selections
            while allowing exact rule-code selection to restore the rule.

    Returns:
        tuple[RuleSettingEffects, ...]: Metadata setting effects for `docstring_convention`.
    """
    effects = (
        *((RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=disabled),) if disabled else ()),
        *((RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=ignored),) if ignored else ()),
    )
    return (RuleSettingEffects(setting="docstring_convention", effects=effects),) if effects else ()


def missing_documentation_is_inert(convention: settings_check.DocstringConvention) -> bool:
    """Return whether missing-documentation rules stay inert because convention-specific documentation is not parsed.

    Args:
        convention (settings_check.DocstringConvention): Active docstring convention.

    Returns:
        bool: Whether missing-documentation checks should avoid reporting convention-targeted findings.
    """
    return convention in {settings_check.DocstringConvention.NONE, settings_check.DocstringConvention.PEP257}
