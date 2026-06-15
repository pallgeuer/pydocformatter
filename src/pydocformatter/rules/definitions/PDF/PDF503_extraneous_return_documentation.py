from __future__ import annotations

import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF503ExtraneousReturnDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF503"),
        name="extraneous-return-documentation",
        message="Docstring has a return section for a function that does not return",
        fix_availability=FixAvailability.NEVER,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )
