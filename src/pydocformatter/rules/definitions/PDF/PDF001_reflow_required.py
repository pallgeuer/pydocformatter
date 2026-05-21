from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF001ReflowRequired(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fixable=True, stable_since="0.3.0")
