from __future__ import annotations

import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF505ExtraneousYieldDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF505"),
        name="extraneous-yield-documentation",
        message="Docstring has a yield section for a function that does not yield a meaningful value",
        fix_availability=FixAvailability.NEVER,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for yield docs on functions without meaningful yields."""
        return value_documentation.extraneous_yield_findings(context, rule=cls.meta)
