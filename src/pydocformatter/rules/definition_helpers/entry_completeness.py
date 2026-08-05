"""Description completeness helpers for parsed docstring entries."""

# Future imports
from __future__ import annotations

# Standard library imports
import typing

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import docstring_source


if typing.TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.models import RuleMetadata


class DescribedEntry(typing.Protocol):
    """Parsed entry shape needed for prose completeness checks."""

    @property
    def description(self) -> str:
        """Parsed prose after excluding protected structures.

        Returns:
            str: Parsed prose available to completeness checks.
        """
        ...


def has_prose_description(entry: DescribedEntry) -> bool:
    """Return whether an entry has non-blank parsed prose.

    Args:
        entry (DescribedEntry): Parsed entry whose description should be checked.

    Returns:
        bool: Whether the parsed description contains non-whitespace prose.
    """
    return bool(entry.description.strip())


def missing_raw_entry_description_violations(
    context: RuleContext, *, meta: RuleMetadata, kind: PDF_definition.DocstringEntryKind, label: str, owner_kind: PDF_definition.DefinitionKind | None = None
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return diagnostics for named raw entries without parsed prose.

    Args:
        context (RuleContext): Current rule context with prepared PDF data.
        meta (RuleMetadata): Metadata for the concrete completeness rule.
        kind (PDF_definition.DocstringEntryKind): Semantic entry kind to inspect.
        label (str): Human-readable entry label used in diagnostic messages.
        owner_kind (PDF_definition.DefinitionKind | None): Optional docstring owner kind required for matching entries.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for matching named entries without parsed prose.
    """
    data = PDF_definition.PDF.require_data(context)
    return tuple(
        rule_violations.diagnostic(
            meta,
            docstring_source.docstring_line_numbers(docstring, docstring.structure.lines[entry.start_line]),
            instance_message=f"{label} '{', '.join(entry.names)}' docstring entry is missing a description",
        )
        for docstring in data.docstrings
        for entry in docstring.structure.entries
        if (owner_kind is None or docstring.owner.kind is owner_kind) and entry.kind is kind and entry.names and not has_prose_description(entry)
    )
