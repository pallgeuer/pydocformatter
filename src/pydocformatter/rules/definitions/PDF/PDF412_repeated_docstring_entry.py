"""PDF412 repeated-docstring-entry rule."""

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
from pydocformatter.rules.definition_helpers import docstring_conventions, parameter_documentation, rest_fields, section_edits
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF412RepeatedDocstringEntry(RuleBase):
    """Rule implementation for PDF412.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF412"),
        name="repeated-docstring-entry",
        message="Docstring entry should not be repeated",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for repeated docstring entries.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF_definition.PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for docstring in data.docstrings:
            seen_keys: set[tuple[str, str]] = set()
            for entry in docstring.structure.entries:
                repeated_keys: list[EntryKey] = []
                for entry_key in _entry_keys(entry):
                    if entry_key.comparison in seen_keys:
                        repeated_keys.append(entry_key)
                    else:
                        seen_keys.add(entry_key.comparison)
                if repeated_keys:
                    line = docstring.structure.lines[entry.start_line]
                    violations.append(rule_violations.diagnostic(cls.meta, section_edits.line_numbers(docstring, line), instance_message=_instance_message(repeated_keys)))
        return tuple(violations)


@dataclasses.dataclass(frozen=True)
class EntryKey:
    """Comparable and user-facing identity for one parsed entry name.

    Attributes:
        comparison (tuple[str, str]): Semantic identity used to detect repeated entries.
        label (str): Entry name shown in the diagnostic message.
        message_kind (str): User-facing semantic entry kind shown in the diagnostic message.
    """

    comparison: tuple[str, str]
    label: str
    message_kind: str


def _entry_keys(entry: PDF_definition.DocstringEntry) -> tuple[EntryKey, ...]:
    """Return comparable whole-docstring duplicate keys for a parsed entry."""
    if entry.field_name is not None:
        return _rest_entry_keys(entry)
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER:
        return tuple(
            EntryKey(("parameter", parameter_documentation.parameter_comparison_name(name)), parameter_documentation.parameter_comparison_name(name), "parameter") for name in entry.names if name
        )
    if entry.kind in {PDF_definition.DocstringEntryKind.ATTRIBUTE, PDF_definition.DocstringEntryKind.METHOD} or PDF_definition.is_exception_name_entry_kind(entry.kind):
        return tuple(EntryKey((entry.kind.value, name), name, entry.kind.value) for name in entry.names if name)
    if entry.kind is PDF_definition.DocstringEntryKind.FIELD:
        return tuple(EntryKey(("field", name), name, "field") for name in entry.names if name)
    return ()


def _rest_entry_keys(entry: PDF_definition.DocstringEntry) -> tuple[EntryKey, ...]:
    """Return duplicate keys for named reStructuredText entry fields."""
    return tuple(EntryKey(rest_key.comparison, rest_key.label, rest_key.message_kind) for rest_key in rest_fields.named_repetition_keys(entry))


def _instance_message(repeated_keys: list[EntryKey]) -> str:
    """Return a diagnostic message for one repeated entry."""
    repeated_labels = tuple(dict.fromkeys(entry_key.label for entry_key in repeated_keys))
    entry_kind = repeated_keys[0].message_kind
    if len(repeated_labels) == 1:
        return f"Docstring {entry_kind} entry '{repeated_labels[0]}' repeats earlier entry"
    labels = ", ".join(f"'{label}'" for label in repeated_labels)
    return f"Docstring {entry_kind} entry repeats earlier entries: {labels}"
