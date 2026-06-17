from __future__ import annotations

import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF507ExtraneousExceptionDocumentation(RuleBase):
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
                        effect=RuleSettingEffect.IGNORED,
                        values=(DocstringConvention.NONE, DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.PEP257),
                    ),
                ),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for exception docs absent from direct raises."""
        return value_documentation.extraneous_exception_findings(context, rule=cls.meta)
