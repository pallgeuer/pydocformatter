from __future__ import annotations

import dataclasses
import importlib
import operator
import pkgutil
from types import ModuleType
from typing import Callable, Iterable

import pydocformatter.rules.definitions as rule_definitions
from pydocformatter.rules.base import RuleBase, RuleCode, RuleSelector


@dataclasses.dataclass(frozen=True, init=False)
class RuleCollection:
    """Collected pydocformatter rule classes."""

    rules: tuple[type[RuleBase], ...]
    rule_class: dict[RuleCode, type[RuleBase]]

    def __init__(self, rules: Iterable[type[RuleBase]]) -> None:
        """Create a deterministically ordered rule collection from rule classes."""
        rule_class_by_code: dict[RuleCode, type[RuleBase]] = {}
        for rule in rules:
            if not issubclass(rule, RuleBase):
                raise TypeError(f"Collected rule must inherit RuleBase: {rule!r}")
            existing = rule_class_by_code.get(rule.meta.code)
            if existing is not None and existing is not rule:
                raise ValueError(f"Duplicate rule code: {rule.meta.code}")
            rule_class_by_code[rule.meta.code] = rule

        sorted_rule_class = dict(sorted(rule_class_by_code.items(), key=operator.itemgetter(0)))
        object.__setattr__(self, "rules", tuple(sorted_rule_class.values()))
        object.__setattr__(self, "rule_class", sorted_rule_class)

    def matching_rules_exist(self, selector: RuleSelector) -> bool:
        """Return whether a selector matches at least one collected rule."""
        return any(selector.selects_code(rule.meta.code) for rule in self.rules)

    def matching_rules(self, selector: RuleSelector) -> tuple[type[RuleBase], ...]:
        """Return collected rules matched by a selector."""
        return tuple(rule for rule in self.rules if selector.selects_code(rule.meta.code))


@dataclasses.dataclass(frozen=True)
class RuleRegistry:
    """Registry of rule implementation classes."""

    rule_classes: set[type[RuleBase]] = dataclasses.field(default_factory=set)

    def register(self, rule_class: type[RuleBase]) -> type[RuleBase]:
        """Register a rule implementation class for collection."""
        if not issubclass(rule_class, RuleBase):
            raise TypeError(f"Registered rule must inherit RuleBase: {rule_class!r}")
        self.rule_classes.add(rule_class)
        return rule_class

    def collection(self) -> RuleCollection:
        """Return a deterministically ordered rule collection from registered rules."""
        return RuleCollection(self.rule_classes)


def register_rule(rule_class: type[RuleBase]) -> type[RuleBase]:
    """Register a rule implementation class for collection."""
    return DEFAULT_RULE_REGISTRY.register(rule_class)


def register_rule_to(registry: RuleRegistry) -> Callable[[type[RuleBase]], type[RuleBase]]:
    """Return a rule decorator that registers rule classes to a specific registry."""

    def decorator(rule_class: type[RuleBase]) -> type[RuleBase]:
        """Register a rule class to the bound registry."""
        return registry.register(rule_class)

    return decorator


def import_package_rules(*, package: ModuleType) -> None:
    """Import rule definition modules from a package."""
    if not hasattr(package, "__path__"):
        raise TypeError(f"Rule definitions package has no __path__: {package.__name__}")
    for module in pkgutil.walk_packages(path=package.__path__, prefix=f"{package.__name__}."):
        importlib.import_module(module.name)


DEFAULT_RULE_REGISTRY = RuleRegistry()
import_package_rules(package=rule_definitions)
RULE_COLLECTION = DEFAULT_RULE_REGISTRY.collection()
