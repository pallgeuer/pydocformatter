"""Function decorator policy helpers."""

from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definition_helpers.decorators as decorator_helpers
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition


def matched_function_decorator(definition: PDF_definition.DefinitionInfo, decorator_names: tuple[str, ...]) -> str | None:
    """Return the first exact configured function decorator name found on a definition.

    Args:
        definition: Function definition whose decorators should be inspected.
        decorator_names: Exact decorator expression names accepted as matches after call unwrapping.

    Returns:
        Matched decorator name from `decorator_names`, or None when the definition is not a function or has no matching decorator.
    """
    if definition.kind is not PDF_definition.DefinitionKind.FUNCTION:
        return None
    configured_names = frozenset(decorator_names)
    for decorator in definition.decorators:
        decorator_name = decorator_helpers.decorator_qualified_name(decorator.decorator)
        if decorator_name in configured_names:
            return decorator_name
    return None


def forbidden_docstring_decorator(definition: PDF_definition.DefinitionInfo, *, settings: settings_check.CheckSettings) -> str | None:
    """Return the matched decorator that forbids a function docstring.

    Args:
        definition: Function definition whose decorators should be inspected.
        settings: Resolved settings containing forbidden function decorator names.

    Returns:
        Matched forbidden decorator name, or None when no configured forbidden decorator is present.
    """
    return matched_function_decorator(definition, settings.docstring_forbidden_function_decorators)


def optional_docstring_decorator(definition: PDF_definition.DefinitionInfo, *, settings: settings_check.CheckSettings) -> str | None:
    """Return the matched decorator that makes a function docstring optional.

    Args:
        definition: Function definition whose decorators should be inspected.
        settings: Resolved settings containing optional function decorator names.

    Returns:
        Matched optional decorator name, or None when no configured optional decorator is present.
    """
    return matched_function_decorator(definition, settings.docstring_optional_function_decorators)


def function_missing_docstring_is_exempt(definition: PDF_definition.DefinitionInfo, *, settings: settings_check.CheckSettings) -> bool:
    """Return whether missing-docstring rules should skip a function.

    Args:
        definition: Function definition whose decorators should be inspected.
        settings: Resolved settings containing optional and forbidden function decorator names.

    Returns:
        Whether the definition has a configured optional or forbidden function decorator.
    """
    return optional_docstring_decorator(definition, settings=settings) is not None or forbidden_docstring_decorator(definition, settings=settings) is not None
