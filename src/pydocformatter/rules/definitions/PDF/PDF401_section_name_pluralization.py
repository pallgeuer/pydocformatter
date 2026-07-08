"""PDF401 section-name-pluralization rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_sections, rest_fields, section_name_replacements
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF401SectionNamePluralization(RuleBase):
    """Rule implementation for PDF401.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF401"),
        name="section-name-pluralization",
        message="Docstring section name should use the preferred plural or canonical form",
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
        """Return violations for singular convention section names.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for section name pluralization."""
    return section_name_replacements.results_for_mapped_names(
        context,
        rule=rule,
        section_name_mapper=docstring_sections.plural_section_name,
        section_message_builder=_section_message,
        field_name_mapper=rest_fields.plural_field_name,
        field_message_builder=_field_message,
    )


def _section_message(name: str, replacement: str) -> str:
    """Return the diagnostic message for a section pluralization replacement."""
    return f"Docstring section name '{name}' should use plural form '{replacement}'"


def _field_message(name: str, replacement: str) -> str:
    """Return the diagnostic message for a reST field spelling replacement."""
    return f"Docstring reST field name '{name}' should use preferred spelling '{replacement}'"
