from __future__ import annotations

import pydocformatter.rules.definition_helpers.parameter_documentation as parameter_documentation
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF500MissingParameterDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF500"),
        name="missing-parameter-documentation",
        message="Function parameter is missing docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for signature parameters missing docstring documentation."""
        return parameter_documentation.missing_parameter_findings(context, rule=cls.meta)
