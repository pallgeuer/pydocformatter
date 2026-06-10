from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleMetadata


@rule_collection.register_rule_to(PDF)
class PDF001ReflowRequired(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF001"),
        name="reflow-required",
        message="Docstring chunk needs reflow",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
        setting_effects=(),
    )
