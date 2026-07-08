"""Function decorator policy helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import static_names


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.cli import settings_check
    from pydocformatter.rules.definition import RuleContext


def matched_function_decorator(definition: PDF_definition.DefinitionInfo, decorator_names: tuple[str, ...], *, context: RuleContext) -> str | None:
    """Return the first configured function decorator name found on a definition.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition whose decorators should be inspected.
        decorator_names (tuple[str, ...]): Decorator expression names accepted as matches after call unwrapping.
        context (RuleContext): Current source context used for import-aware matching.

    Returns:
        Matched source decorator name, or None when the definition is not a function or has no matching decorator.
    """
    if definition.kind is not PDF_definition.DefinitionKind.FUNCTION:
        return None
    for decorator in definition.decorators:
        decorator_name = static_names.configured_expression_name(decorator.decorator, decorator_names, context=context, unwrap_call=True)
        if decorator_name is not None:
            return decorator_name
    return None


def forbidden_docstring_decorator(definition: PDF_definition.DefinitionInfo, *, context: RuleContext, settings: settings_check.CheckSettings) -> str | None:
    """Return the matched decorator that forbids a function docstring.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition whose decorators should be inspected.
        context (RuleContext): Current source context used for import-aware matching.
        settings (settings_check.CheckSettings): Resolved settings containing forbidden function decorator names.

    Returns:
        Matched forbidden decorator name, or None when no configured forbidden decorator is present.
    """
    return matched_function_decorator(definition, settings.docstring_forbidden_function_decorators, context=context)


def optional_docstring_decorator(definition: PDF_definition.DefinitionInfo, *, context: RuleContext, settings: settings_check.CheckSettings) -> str | None:
    """Return the matched decorator that makes a function docstring optional.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition whose decorators should be inspected.
        context (RuleContext): Current source context used for import-aware matching.
        settings (settings_check.CheckSettings): Resolved settings containing optional function decorator names.

    Returns:
        Matched optional decorator name, or None when no configured optional decorator is present.
    """
    return matched_function_decorator(definition, settings.docstring_optional_function_decorators, context=context)


def function_missing_docstring_is_exempt(definition: PDF_definition.DefinitionInfo, *, context: RuleContext, settings: settings_check.CheckSettings) -> bool:
    """Return whether missing-docstring rules should skip a function.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition whose decorators should be inspected.
        context (RuleContext): Current source context used for import-aware matching.
        settings (settings_check.CheckSettings): Resolved settings containing optional and forbidden function decorator
            names.

    Returns:
        Whether the definition has a configured optional or forbidden function decorator.
    """
    return optional_docstring_decorator(definition, context=context, settings=settings) is not None or forbidden_docstring_decorator(definition, context=context, settings=settings) is not None
