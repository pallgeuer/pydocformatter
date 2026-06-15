from __future__ import annotations

import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF405SectionNameColon(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF405"),
        name="section-name-colon",
        message="Docstring section name should end with a colon",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )
