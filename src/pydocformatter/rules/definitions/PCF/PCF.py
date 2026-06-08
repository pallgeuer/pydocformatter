from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.definition import RuleCategoryBase
from pydocformatter.rules.models import RuleCategoryMetadata


@rule_collection.register_rule_category
class PCF(RuleCategoryBase):
    meta = RuleCategoryMetadata(
        prefix="PCF",
        name="pydocformatter comment formatting",
        url="https://github.com/pallgeuer/pydocformatter",
    )
