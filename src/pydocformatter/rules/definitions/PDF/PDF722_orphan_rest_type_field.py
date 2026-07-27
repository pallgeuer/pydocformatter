"""PDF722 orphan-rest-type-field rule."""

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
from pydocformatter.rules.definition_helpers import docstring_conventions, rest_fields
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF722OrphanRestTypeField(RuleBase):
    """Rule implementation for PDF722.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF722"),
        name="orphan-rest-type-field",
        message="reST type field has no corresponding value field",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.conventions_except(DocstringConvention.REST)),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for reStructuredText type fields without value fields.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for docstring in data.docstrings:
            pairings = rest_fields.pair_all_value_and_type_fields(docstring.structure.entries)
            for type_part in (type_part for pairing in pairings.values() for type_part in pairing.orphan_types):
                entry = type_part.entry
                line_numbers = PDF_definition.docstring_line_numbers(docstring, docstring.structure.lines[entry.start_line])
                violations.append(
                    rule_violations.diagnostic(
                        cls.meta, line_numbers, instance_message=f"reST type field '{rest_fields.label(entry)}' has no corresponding {rest_fields.value_field_label(entry)} value field"
                    )
                )
        return tuple(sorted(violations, key=lambda violation: violation.finding.line_numbers))
