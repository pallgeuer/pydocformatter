"""PDF312 entry-description-too-generic rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_sections, documentation_style
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@dataclasses.dataclass(frozen=True)
class _DescriptionPolicy:
    """Exact generic-description policy for one semantic entry kind."""

    owner_kind: PDF_definition.DefinitionKind
    unnamed_patterns: frozenset[tuple[str, ...]]
    named_templates: frozenset[tuple[tuple[str, ...], tuple[str, ...]]]
    message_subject: str


_POLICIES = {
    PDF_definition.DocstringEntryKind.RETURN: _DescriptionPolicy(
        owner_kind=PDF_definition.DefinitionKind.FUNCTION,
        unnamed_patterns=frozenset({("the", "return", "value"), ("the", "returned", "value")}),
        named_templates=frozenset({(("the",), ("value",)), (("the",), ("return", "value")), (("the",), ("returned", "value"))}),
        message_subject="Return",
    ),
    PDF_definition.DocstringEntryKind.YIELD: _DescriptionPolicy(
        owner_kind=PDF_definition.DefinitionKind.FUNCTION,
        unnamed_patterns=frozenset({("the", "yielded", "value")}),
        named_templates=frozenset({(("the",), ("value",)), (("the",), ("yielded", "value"))}),
        message_subject="Yield",
    ),
    PDF_definition.DocstringEntryKind.EXCEPTION: _DescriptionPolicy(
        owner_kind=PDF_definition.DefinitionKind.FUNCTION,
        unnamed_patterns=frozenset({("the", "exception"), ("the", "error")}),
        named_templates=frozenset({(("the",), ("exception",)), (("the",), ("error",))}),
        message_subject="Exception",
    ),
    PDF_definition.DocstringEntryKind.WARNING: _DescriptionPolicy(
        owner_kind=PDF_definition.DefinitionKind.FUNCTION, unnamed_patterns=frozenset({("the", "warning")}), named_templates=frozenset({(("the",), ("warning",))}), message_subject="Warning"
    ),
    PDF_definition.DocstringEntryKind.METHOD: _DescriptionPolicy(
        owner_kind=PDF_definition.DefinitionKind.CLASS, unnamed_patterns=frozenset({("the", "method")}), named_templates=frozenset({(("the",), ("method",))}), message_subject="Method"
    ),
}


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF312EntryDescriptionTooGeneric(RuleBase):
    """Rule implementation for PDF312.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF312"),
        name="entry-description-too-generic",
        message="Docstring entry description is too generic",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for content-free parsed entry descriptions.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF_definition.PDF.require_data(context)
        results: list[rule_violations.RuleViolation] = []
        for docstring in data.docstrings:
            if not isinstance(docstring.owner, PDF_definition.DefinitionInfo):
                continue
            for entry in docstring.structure.entries:
                policy = _POLICIES.get(entry.kind)
                if (
                    policy is None
                    or docstring.owner.kind is not policy.owner_kind
                    or not entry.description
                    or docstring_sections.is_rest_type_field(entry.field_name)
                    or not all(documentation_style.exact_description_fragment_is_safe(docstring.value[fragment.full_start_offset : fragment.full_end_offset]) for fragment in entry.description_lines)
                    or not _is_too_generic(entry, policy=policy)
                ):
                    continue
                line = docstring.structure.lines[entry.start_line]
                results.append(rule_violations.diagnostic(cls.meta, PDF_definition.docstring_line_numbers(docstring, line), instance_message=f"{policy.message_subject} documentation is too generic"))
        return tuple(results)


def _is_too_generic(entry: PDF_definition.DocstringEntry, *, policy: _DescriptionPolicy) -> bool:
    """Return whether one parsed entry description matches an exact generic pattern."""
    if documentation_style.matches_exact_description(entry.description, policy.unnamed_patterns):
        return True
    return any(documentation_style.matches_exact_named_description(entry.description, name, policy.named_templates) for name in entry.names)
