"""Missing-documentation activation helpers."""

from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition import RuleContext

# Broad public-only PDF500/PDF502/PDF504/PDF506 checks treat only constructor/callable dunders as public; other protocol
# dunders stay quiet unless they have explicit relevant docs.
_PUBLIC_DUNDER_FUNCTIONS = {"__init__", "__new__", "__call__"}


def should_check_missing_documentation(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo, *, context: RuleContext, has_relevant_documentation: bool) -> bool:
    """Return whether a missing-documentation rule should inspect this docstring."""
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
    """Return whether a docstring has non-summary body content."""
    non_blank_blocks = tuple(block for block in docstring.structure.blocks if block.kind is not PDF_definition.DocstringBlockKind.BLANK)
    return bool(non_blank_blocks) and (len(non_blank_blocks) != 1 or non_blank_blocks[0].kind is not PDF_definition.DocstringBlockKind.SUMMARY)


def is_public_definition(definition: PDF_definition.DefinitionInfo) -> bool:
    """Return whether a definition is public for broad missing-documentation checks."""
    current: PDF_definition.DefinitionInfo | None = definition
    while current is not None and current.kind is not PDF_definition.DefinitionKind.MODULE:
        if _is_private_name(current.name):
            return False
        current = current.parent
    return True


def _is_private_name(name: str) -> bool:
    """Return whether a definition name is private for broad documentation checks."""
    if name in _PUBLIC_DUNDER_FUNCTIONS:
        return False
    return name.startswith("_")
