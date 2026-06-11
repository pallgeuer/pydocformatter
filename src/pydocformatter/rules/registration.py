from __future__ import annotations

import dataclasses
from typing import Callable

from pydocformatter.rules.definition import RuleBase, RuleCategoryBase


class RuleError(ValueError):
    """Rule registration, collection, or definition import error."""


@dataclasses.dataclass(frozen=True)
class RuleRegistry:
    """Registry of rule category classes."""

    category_classes: set[type[RuleCategoryBase]] = dataclasses.field(default_factory=set)

    def register(self, category_class: type[RuleCategoryBase]) -> type[RuleCategoryBase]:
        """Register a rule category class for collection."""
        if not isinstance(category_class, type) or not issubclass(category_class, RuleCategoryBase):
            raise RuleError(f"Registered rule category must inherit RuleCategoryBase: {category_class!r}")
        self.category_classes.add(category_class)
        return category_class


DEFAULT_RULE_REGISTRY = RuleRegistry()


def register_rule_category(category_class: type[RuleCategoryBase]) -> type[RuleCategoryBase]:
    """Register a rule category class for collection."""
    return DEFAULT_RULE_REGISTRY.register(category_class)


def register_rule_category_to(registry: RuleRegistry) -> Callable[[type[RuleCategoryBase]], type[RuleCategoryBase]]:
    """Return a category decorator that registers category classes to a registry."""

    def decorator(category_class: type[RuleCategoryBase]) -> type[RuleCategoryBase]:
        """Register a category class to the bound registry."""
        return registry.register(category_class)

    return decorator


def register_rule_to(category: type[RuleCategoryBase]) -> Callable[[type[RuleBase]], type[RuleBase]]:
    """Return a rule decorator that registers rule classes to a category."""
    if not isinstance(category, type) or not issubclass(category, RuleCategoryBase):
        raise RuleError(f"Rule category must inherit RuleCategoryBase: {category!r}")

    def decorator(rule_class: type[RuleBase]) -> type[RuleBase]:
        """Register a rule class to the bound category."""
        if not isinstance(rule_class, type) or not issubclass(rule_class, RuleBase):
            raise RuleError(f"Registered rule must inherit RuleBase: {rule_class!r}")
        if rule_class.meta.code.prefix != category.meta.prefix:
            raise RuleError(f"Rule code prefix {rule_class.meta.code.prefix!r} does not match rule category prefix {category.meta.prefix!r}")
        existing = category.code_class_map.get(rule_class.meta.code)
        if existing is not None and existing is not rule_class:
            raise RuleError(f"Duplicate rule code in category {category.meta.prefix}: {rule_class.meta.code}")
        category.code_class_map[rule_class.meta.code] = rule_class
        return rule_class

    return decorator
