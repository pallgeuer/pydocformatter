from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleCategoryBase, RuleCategoryMetadata


@rule_collection.register_rule_category
class PCF(RuleCategoryBase):
    """Comment formatting rules."""

    meta = RuleCategoryMetadata(prefix="PCF", name="pydocformatter comment formatting", url="https://github.com/pallgeuer/pydocformatter")
