from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check


def ignored_conventions_except(*allowed: settings_check.DocstringConvention) -> tuple[settings_check.DocstringConvention, ...]:
    """Return docstring conventions ignored by a convention-specific rule."""
    allowed_set = set(allowed)
    return tuple(convention for convention in settings_check.DocstringConvention if convention not in allowed_set)
