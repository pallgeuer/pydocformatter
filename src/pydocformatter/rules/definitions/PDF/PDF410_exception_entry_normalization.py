"""PDF410 exception-entry-normalization rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, section_edits, unicode_safety
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF410ExceptionEntryNormalization(RuleBase):
    """Rule implementation for PDF410.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF410"),
        name="exception-entry-normalization",
        message="Docstring exception or warning entry should use canonical spelling",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for non-canonical exception and warning entry spelling.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for exception and warning entry normalization."""
    data = PDF_definition.PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=rule)
        for entry in docstring.structure.entries:
            if not PDF_definition.is_exception_name_entry_kind(entry.kind) or entry.name_list_edit_slot is None:
                continue
            line = docstring.structure.lines[entry.name_list_edit_slot.line_index]
            replacement = _exception_or_warning_name_replacement(line.text, entry)
            if replacement is None:
                continue
            start_column, end_column, canonical = replacement
            subject = "warning" if entry.kind is PDF_definition.DocstringEntryKind.WARNING else "exception"
            original = line.text[start_column:end_column]
            message = f"Docstring {subject} entry spelling should be normalized from '{original}' to '{canonical}'"
            accumulator.add(line, start_column, end_column, canonical, instance_message=message)
        results.extend(accumulator.results())
    return tuple(results)


def _exception_or_warning_name_replacement(text: str, entry: PDF_definition.DocstringEntry) -> tuple[int, int, str] | None:
    """Return canonical exception or warning name-list replacement details."""
    slot = entry.name_list_edit_slot
    if not entry.names or slot is None or unicode_safety.has_nonstandard_whitespace_or_control(text):
        return None
    canonical = ", ".join(entry.names)
    if text[slot.start_column : slot.end_column] == canonical:
        return None
    return slot.start_column, slot.end_column, canonical
