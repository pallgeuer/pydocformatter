"""PDF312 entry-description-too-generic rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import string
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_conventions, docstring_sections, docstring_source, unicode_safety
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

_ASCII_LOWER_TRANSLATION = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_ASCII_WORD_SEPARATOR = rf"[{re.escape(ascii_whitespace.SPACE_AND_TAB)}]+"
_ASCII_NAME_SEPARATOR = rf"[{re.escape(ascii_whitespace.SPACE_AND_TAB)}_.]+"
_NAME_TOKEN_RE = re.compile(r"[a-z0-9]+")


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
                if policy is None or docstring.owner.kind is not policy.owner_kind or not entry.description or docstring_sections.is_rest_type_field(entry.field_name):
                    continue
                if not all(_exact_description_fragment_is_safe(docstring.value[fragment.full_start_offset : fragment.full_end_offset]) for fragment in entry.description_lines):
                    continue
                matching_names = _generic_description_names(entry, policy=policy)
                if matching_names is None:
                    continue
                line = docstring.structure.lines[entry.start_line]
                results.append(rule_violations.diagnostic(cls.meta, docstring_source.docstring_line_numbers(docstring, line), instance_message=_instance_message(matching_names, policy=policy)))
        return tuple(results)


def _generic_description_names(entry: PDF_definition.DocstringEntry, *, policy: _DescriptionPolicy) -> tuple[str, ...] | None:
    """Return names implicated by an exact generic description, or None."""
    if _matches_exact_description(entry.description, policy.unnamed_patterns):
        return tuple(dict.fromkeys(entry.names))
    matching_names = tuple(dict.fromkeys(name for name in entry.names if _matches_exact_named_description(entry.description, name, policy.named_templates)))
    return matching_names or None


def _matches_exact_description(description: str, sequences: frozenset[tuple[str, ...]]) -> bool:
    """Return whether prose exactly matches one normalized word sequence."""
    normalized = _normalized_exact_description(description)
    if normalized is None:
        return False
    return any(re.fullmatch(_ASCII_WORD_SEPARATOR.join(map(re.escape, sequence)), normalized) is not None for sequence in sequences)


def _matches_exact_named_description(description: str, name: str, templates: frozenset[tuple[tuple[str, ...], tuple[str, ...]]]) -> bool:
    """Return whether prose exactly matches one name-bearing template."""
    normalized = _normalized_exact_description(description)
    if not name.isascii():
        return False
    name_tokens = _name_tokens(name)
    if normalized is None or not name_tokens:
        return False
    boundary_name = name.lstrip("*")
    leading_underscores = r"(?:_+)?" if boundary_name.startswith("_") else ""
    trailing_underscores = r"(?:_+)?" if boundary_name.endswith("_") else ""
    name_pattern = rf"\*{{0,2}}{leading_underscores}{_ASCII_NAME_SEPARATOR.join(map(re.escape, name_tokens))}{trailing_underscores}"
    for prefix, suffix in templates:
        parts = (*map(re.escape, prefix), name_pattern, *map(re.escape, suffix))
        if re.fullmatch(_ASCII_WORD_SEPARATOR.join(parts), normalized) is not None:
            return True
    return False


def _normalized_exact_description(description: str) -> str | None:
    """Return exact-matcher prose normalized at its outer boundary."""
    if unicode_safety.has_nonstandard_whitespace_or_control(description):
        return None
    normalized = description.strip(ascii_whitespace.SPACE_AND_TAB).translate(_ASCII_LOWER_TRANSLATION)
    normalized = normalized.rstrip(".?!").rstrip(ascii_whitespace.SPACE_AND_TAB)
    if not normalized or not normalized.isascii():
        return None
    return normalized


def _exact_description_fragment_is_safe(text: str) -> bool:
    """Return whether one full fragment obeys the exact ASCII layout policy."""
    return text.isascii() and not unicode_safety.has_nonstandard_whitespace_or_control(text)


def _name_tokens(name: str) -> tuple[str, ...]:
    """Return comparison tokens for a documented name."""
    stripped = name.strip("*")
    return tuple(token for token in _NAME_TOKEN_RE.findall(stripped.replace("_", " ").lower()) if token)


def _instance_message(names: tuple[str, ...], *, policy: _DescriptionPolicy) -> str:
    """Return the concrete generic-description diagnostic for an entry."""
    if not names:
        return f"{policy.message_subject} documentation is too generic"
    displayed_names = ", ".join(f"'{name}'" for name in names)
    return f"{policy.message_subject} documentation for {displayed_names} is too generic"
