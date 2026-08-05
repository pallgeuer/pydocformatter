"""PDF417 numpy-return-entry-shape rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_source
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF417NumpyReturnEntryShape(RuleBase):
    """Rule implementation for PDF417.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF417"),
        name="numpy-return-entry-shape",
        message="NumPy Returns entries should match single-value or multiple-value structure",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.conventions_except(DocstringConvention.NUMPY)),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for invalid NumPy Returns entry structure.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for definition in data.definitions:
            if definition.kind is not PDF_definition.DefinitionKind.FUNCTION:
                continue
            docstring = data.docstring_for(definition)
            if docstring is None:
                continue
            for section in docstring.structure.sections:
                if section.name.lower() not in {"return", "returns"}:
                    continue
                entries = tuple(entry for entry in section.entries if entry.kind is PDF_definition.DocstringEntryKind.RETURN)
                for entry in entries:
                    message = _entry_message(entry, section_entry_count=len(entries))
                    if message is None:
                        continue
                    line_numbers = docstring_source.docstring_line_numbers(docstring, docstring.structure.lines[entry.start_line])
                    violations.append(rule_violations.diagnostic(cls.meta, line_numbers, instance_message=message))
        return tuple(violations)


def _entry_message(entry: PDF_definition.DocstringEntry, *, section_entry_count: int) -> str | None:
    """Return the shape diagnostic for one Returns entry, if invalid."""
    if len(entry.names) > 1:
        return "NumPy Returns entry should document each returned value in a separate entry"
    if section_entry_count == 1 and entry.names:
        return "Single-value NumPy Returns entry should contain only the type"
    return None
