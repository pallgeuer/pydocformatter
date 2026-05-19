from __future__ import annotations

import dataclasses
import importlib
import pkgutil
from types import ModuleType

import pydocformatter.rules.base as rule_base
import pydocformatter.rules.definitions as rule_definitions
from pydocformatter.rules.base import RuleBase, RuleMetadata

ALL_RULE_CODE = "ALL"
_REGISTERED_RULES: dict[str, type[RuleBase]] = {}


@dataclasses.dataclass(frozen=True)
class RuleCollection:
    """Collected pydocformatter rule metadata."""

    rules: tuple[RuleMetadata, ...]

    @classmethod
    def from_metadata(cls, rules: tuple[RuleMetadata, ...]) -> RuleCollection:
        """Return a deterministically ordered rule collection."""
        metadata_by_rule_code: dict[str, RuleMetadata] = {}
        for rule in rules:
            _validate_rule_metadata(rule)
            if rule.code in metadata_by_rule_code:
                raise ValueError(f"Duplicate rule code: {rule.code}")
            metadata_by_rule_code[rule.code] = rule
        return cls(rules=tuple(sorted(metadata_by_rule_code.values(), key=lambda rule: rule.code)))

    @classmethod
    def from_rule_classes(cls, rule_classes: tuple[type[RuleBase], ...]) -> RuleCollection:
        """Return a rule collection from registered rule classes."""
        return cls.from_metadata(tuple(rule_class.meta for rule_class in rule_classes))

    def selector_matches_some_rule(self, selector: str) -> bool:
        """Return whether a selector matches at least one collected rule."""
        if selector == ALL_RULE_CODE:
            return bool(self.rules)

        try:
            prefix, number_str = rule_base.split_rule_selector(selector)
        except ValueError:
            return False
        return any(rule.matches_selector_parts(prefix, number_str) for rule in self.rules)

    def matching_rules(self, selector: str) -> tuple[RuleMetadata, ...]:
        """Return collected rules matched by a selector."""
        if selector == ALL_RULE_CODE:
            return self.rules

        try:
            prefix, number_str = rule_base.split_rule_selector(selector)
        except ValueError:
            return ()
        return tuple(rule for rule in self.rules if rule.matches_selector_parts(prefix, number_str))


def register_rule(rule_class: type[RuleBase]) -> type[RuleBase]:
    """Register a rule implementation class for collection."""
    if not issubclass(rule_class, RuleBase):
        raise TypeError(f"Registered rule must inherit RuleBase: {rule_class!r}")

    metadata = rule_class.meta
    _validate_rule_metadata(metadata)
    existing = _REGISTERED_RULES.get(metadata.code)
    if existing is not None and existing is not rule_class:
        raise ValueError(f"Duplicate rule code: {metadata.code}")
    _REGISTERED_RULES[metadata.code] = rule_class
    return rule_class


def collect_rules(*, definitions_package: ModuleType = rule_definitions) -> RuleCollection:
    """Import rule definition modules and return the registered rule collection."""
    if not hasattr(definitions_package, "__path__"):
        raise TypeError(f"Rule definitions package has no __path__: {definitions_package.__name__}")

    package_prefix = f"{definitions_package.__name__}."
    for module in pkgutil.walk_packages(definitions_package.__path__, package_prefix):
        importlib.import_module(module.name)

    return RuleCollection.from_rule_classes(tuple(_REGISTERED_RULES[rule_code] for rule_code in sorted(_REGISTERED_RULES)))


def _validate_rule_metadata(rule: RuleMetadata) -> None:
    """Validate rule metadata supplied by rule definitions."""
    if not rule_base.rule_code_is_valid(rule.code):
        raise ValueError(f"{rule.code}: Rule code must match {rule_base.RULE_CODE_RE.pattern!r}")
    if not rule.name:
        raise ValueError(f"{rule.code}: Rule name must not be empty")
    if not rule.message:
        raise ValueError(f"{rule.code}: Rule message must not be empty")
