"""Missing-documentation activation helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli import settings_check


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.source_path import SourcePathContext


# Broad public-only PDF500/PDF502/PDF504/PDF506 checks treat only constructor/callable dunders as public; other protocol
# dunders stay quiet unless they have explicit relevant docs.
_PUBLIC_DUNDER_FUNCTIONS = {"__init__", "__new__", "__call__"}


def should_check_missing_documentation(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo, *, context: RuleContext, has_relevant_documentation: bool) -> bool:
    """Return whether a missing-documentation rule should inspect this docstring.

    Args:
        definition (PDF_definition.DefinitionInfo): Definition that owns the docstring being considered.
        docstring (PDF_definition.DocstringInfo): Parsed docstring whose body and structures drive policy checks.
        context (RuleContext): Current file context with resolved missing-documentation settings.
        has_relevant_documentation (bool): Whether the docstring already contains the section or field kind targeted by
            the rule.

    Returns:
        bool: Whether the rule should report missing documentation for this definition and docstring.

    Raises:
        AssertionError: If settings contain an unexpected missing-documentation policy value.
    """
    if has_relevant_documentation:
        return True
    policy = context.settings.docstring_missing_documentation
    if policy is settings_check.DocstringMissingDocumentation.HAS_SECTION:
        return False
    if context.settings.docstring_missing_documentation_public_only and not is_public_definition(definition):
        return False
    if policy is settings_check.DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS:
        return has_more_than_summary(docstring)
    if policy is settings_check.DocstringMissingDocumentation.ALL_DOCSTRINGS:
        return True
    raise AssertionError(f"Unexpected missing-documentation policy: {policy}")


def has_more_than_summary(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a docstring has non-summary body content.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to inspect for body structures beyond a summary.

    Returns:
        bool: Whether the docstring contains any non-blank block other than a lone summary block.
    """
    non_blank_blocks = tuple(block for block in docstring.structure.blocks if block.kind is not PDF_definition.DocstringBlockKind.BLANK)
    return bool(non_blank_blocks) and (len(non_blank_blocks) != 1 or non_blank_blocks[0].kind is not PDF_definition.DocstringBlockKind.SUMMARY)


def is_public_definition(definition: PDF_definition.DefinitionInfo) -> bool:
    """Return whether a definition is public for broad missing-documentation checks.

    Args:
        definition (PDF_definition.DefinitionInfo): Definition whose name and owning chain should be inspected.

    Returns:
        bool: Whether the definition and all non-module ancestors are public under the missing-documentation policy.
    """
    current: PDF_definition.DefinitionInfo | None = definition
    while current is not None and current.kind is not PDF_definition.DefinitionKind.MODULE:
        if _is_private_name(current.name):
            return False
        current = current.parent
    return True


def is_public_module_path(context: SourcePathContext) -> bool:
    """Return whether a source path names a public module or package.

    Args:
        context (SourcePathContext): Precomputed source path to classify.

    Returns:
        Whether no discovered module path component starts with an underscore.
    """
    return context.public


def _is_private_name(name: str) -> bool:
    """Return whether a definition name is private for broad documentation checks."""
    if name in _PUBLIC_DUNDER_FUNCTIONS:
        return False
    return name.startswith("_")
