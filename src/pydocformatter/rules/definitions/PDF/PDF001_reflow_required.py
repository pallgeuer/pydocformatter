from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_collection.register_rule_to(PDF)
class PDF001ReflowRequired(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")
