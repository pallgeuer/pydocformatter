"""PDF406 empty-section rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, rest_fields, section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF406EmptySection(RuleBase):
    """Rule implementation for PDF406.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF406"),
        name="empty-section",
        message="Docstring section should not be empty",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for recognized sections without body content.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _violations(context, rule=cls.meta)


def _violations(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for recognized sections or reST fields with no body content."""
    data = PDF.require_data(context)
    violations: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        for section in docstring.structure.sections:
            if not _section_has_content(docstring, section):
                line = docstring.structure.lines[section.header_line]
                violations.append(rule_violations.diagnostic(rule, section_edits.line_numbers(docstring, line), instance_message=f"Docstring section '{section.name}' should not be empty"))
        if docstring.structure.convention is DocstringConvention.REST:
            for entry in docstring.structure.entries:
                if entry.field_name is None or rest_fields.has_content(entry):
                    continue
                line = docstring.structure.lines[entry.start_line]
                violations.append(rule_violations.diagnostic(rule, section_edits.line_numbers(docstring, line), instance_message=f"Docstring field '{rest_fields.label(entry)}' should not be empty"))
    return tuple(violations)


def _section_has_content(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> bool:
    """Return whether a section body contains non-whitespace text."""
    return any(line.text.strip(" \t") for line in docstring.structure.lines[section.content_start_line : section.end_line])
