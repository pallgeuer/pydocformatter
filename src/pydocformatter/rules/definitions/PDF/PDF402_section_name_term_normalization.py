"""PDF402 section-name-term-normalization rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.rest_fields as rest_fields
import pydocformatter.rules.definition_helpers.section_name_replacements as section_name_replacements
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF402SectionNameTermNormalization(RuleBase):
    """Rule implementation for PDF402.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF402"),
        name="section-name-term-normalization",
        message="Docstring section name should use the preferred equivalent term",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST)
                    ),
                ),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for non-preferred equivalent convention section terms.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for section name term normalization."""
    return section_name_replacements.results_for_mapped_names(
        context,
        rule=rule,
        section_name_mapper=docstring_sections.term_normalized_section_name,
        section_message_builder=_section_message,
        field_name_mapper=rest_fields.term_normalized_field_name,
        field_message_builder=_field_message,
    )


def _section_message(name: str, replacement: str) -> str:
    """Return the diagnostic message for a section term replacement."""
    return f"Docstring section name '{name}' should use equivalent term '{replacement}'"


def _field_message(name: str, replacement: str) -> str:
    """Return the diagnostic message for a reST field term replacement."""
    return f"Docstring reST field name '{name}' should use equivalent term '{replacement}'"
