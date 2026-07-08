"""PDF507 extraneous-exception-documentation rule."""

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
from pydocformatter.rules.definition_helpers import value_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF507ExtraneousExceptionDocumentation(RuleBase):
    """Rule implementation for PDF507.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF507"),
        name="extraneous-exception-documentation",
        message="Docstring documents an exception that is not explicitly raised",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST)
                    ),
                ),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for exception docs absent from direct raises.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        violations: list[rule_violations.RuleViolation] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            del definition
            violations.extend(
                rule_violations.diagnostic(cls.meta, entry.line_numbers, instance_message=f"Docstring documents exception '{entry.name}' that is not explicitly raised")
                for entry in value_documentation.documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False)
                if entry.name is not None and not any(value_documentation.exception_names_match(raised.name, entry.name) for raised in facts.raised_exceptions)
            )
        return tuple(violations)
