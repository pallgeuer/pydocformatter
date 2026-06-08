from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleCategoryBase, RuleCategoryMetadata


@rule_collection.register_rule_category
class PDF(RuleCategoryBase):
    """Docstring formatting rules."""

    meta = RuleCategoryMetadata(prefix="PDF", name="pydocformatter docstring formatting", url="https://github.com/pallgeuer/pydocformatter")
