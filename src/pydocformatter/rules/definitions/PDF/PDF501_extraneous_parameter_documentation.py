from __future__ import annotations

import pydocformatter.rules.definition_helpers.parameter_documentation as parameter_documentation
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF501ExtraneousParameterDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF501"),
        name="extraneous-parameter-documentation",
        message="Docstring documents a parameter that is not in the function signature",
        fix_availability=FixAvailability.NEVER,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for documented parameters absent from the signature."""
        return parameter_documentation.extraneous_parameter_findings(context, rule=cls.meta)
