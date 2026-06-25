"""PDF400 section-name-capitalization rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definition_helpers.section_name_replacements as section_name_replacements
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF400SectionNameCapitalization(RuleBase):
    """Rule implementation for PDF400.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF400"),
        name="section-name-capitalization",
        message="Docstring section name should be properly capitalized",
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
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for non-canonical convention section capitalization."""
        return section_edits.findings_for_results(_results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Capitalize safely mapped convention section names."""
        return section_edits.fix_result_for_results(context, cls.meta, _results(context, rule=cls.meta))


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[section_edits.SectionEditResult, ...]:
    """Return findings and fixes for section name capitalization."""
    return section_name_replacements.results_for_mapped_names(
        context,
        rule=rule,
        section_name_mapper=docstring_sections.canonical_section_name,
        section_message_builder=_section_message,
        field_name_mapper=str.lower,
        field_message_builder=_field_message,
    )


def _section_message(name: str, replacement: str) -> str:
    """Return the diagnostic message for a section capitalization replacement."""
    return f"Docstring section name '{name}' should be capitalized as '{replacement}'"


def _field_message(name: str, replacement: str) -> str:
    """Return the diagnostic message for a reST field capitalization replacement."""
    return f"Docstring reStructuredText field name '{name}' should be lowercase as '{replacement}'"
