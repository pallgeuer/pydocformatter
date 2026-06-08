from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.definition import RuleCategoryBase
from pydocformatter.rules.models import RuleCategoryMetadata


@rule_collection.register_rule_category
class PDF(RuleCategoryBase):
    meta = RuleCategoryMetadata(
        prefix="PDF",
        name="pydocformatter docstring formatting",
        url="https://github.com/pallgeuer/pydocformatter",
    )
