from __future__ import annotations

import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF503ExtraneousReturnDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF503"),
        name="extraneous-return-documentation",
        message="Docstring has a return section for a function that does not return",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for return docs on functions without meaningful returns."""
        return value_documentation.extraneous_return_findings(context, rule=cls.meta)
