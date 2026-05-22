from __future__ import annotations

import dataclasses
import os
from collections.abc import Mapping

import pydocformatter.rules.collection as rule_collection
import pydocformatter.settings as settings_core
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.base import ALL_RULE_SELECTOR_TAG, RuleCode, RuleMetadata, RuleSelector
from pydocformatter.rules.collection import RuleCollection
from pydocformatter.utils.globs import GlobPatternSet


@dataclasses.dataclass(frozen=True)
class SelectedRule:
    """A rule selected for processing with its effective fixability."""

    rule: RuleMetadata
    fixable: bool
    enabled_specificity: int


@dataclasses.dataclass(frozen=True)
class PerFileRuleIgnore:
    """Rule ignore selectors resolved for one path pattern."""

    pattern: str
    base_path: str
    rule_codes: frozenset[RuleCode]
    rule_specificities: tuple[tuple[RuleCode, int], ...]
    matcher: GlobPatternSet = dataclasses.field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        """Compile the ignore matcher once for repeated per-path checks."""
        object.__setattr__(self, "matcher", GlobPatternSet.compile((self.pattern,), match_parent_segments_for_bare=False))

    def matches(self, path: str) -> bool:
        """Return whether this per-file ignore entry matches a normalized path."""
        return self.matcher.matches(_base_relative_posix_path(path, self.base_path))


@dataclasses.dataclass(frozen=True)
class RuleSelection:
    """Effective rule selection for a resolved settings object."""

    rules: tuple[SelectedRule, ...]
    per_file_ignores: tuple[PerFileRuleIgnore, ...]
    errors: tuple[str, ...]
    collection: RuleCollection

    def for_path(self, path: str) -> tuple[SelectedRule, ...]:
        """Return selected rules after applying per-file ignores to a path."""
        ignored_specificities: dict[RuleCode, int] = {}
        for ignore in self.per_file_ignores:
            if ignore.matches(path):
                for rule_code, specificity in ignore.rule_specificities:
                    ignored_specificities[rule_code] = max(ignored_specificities.get(rule_code, -1), specificity)
        if not ignored_specificities:
            return self.rules
        return tuple(rule for rule in self.rules if ignored_specificities.get(rule.rule.code, -1) < rule.enabled_specificity)


def select_rules(
    settings: CheckSettings, *, collection: RuleCollection | None = None, field_bases: Mapping[str, str] | None = None, profile: settings_core.SettingsProfile[CheckSettings] | None = None
) -> RuleSelection:
    """Resolve rule selection and fixability settings against collected rules."""
    if collection is None:
        collection = rule_collection.RULE_COLLECTION
    if profile is not None:
        settings = profile.settings
        field_bases = profile.field_bases

    errors: list[str] = []
    selected_specificities = _resolve_rule_specificities(
        settings.select + settings.extend_select,
        collection=collection,
        context="rule selection",
        errors=errors,
    )
    ignored_specificities = _resolve_rule_specificities(settings.ignore, collection=collection, context="ignored rules", errors=errors)
    enabled_specificities = _resolve_enabled_specificities(selected_specificities, ignored_specificities)

    fixable_specificities = _resolve_rule_specificities(
        settings.fixable + settings.extend_fixable,
        collection=collection,
        context="fixable rules",
        errors=errors,
        require_inherently_fixable=True,
    )
    unfixable_specificities = _resolve_rule_specificities(settings.unfixable, collection=collection, context="unfixable rules", errors=errors)
    effectively_fixable_codes = _resolve_enabled_specificities(fixable_specificities, unfixable_specificities)

    selected_rules = tuple(
        SelectedRule(rule=rule_class.meta, fixable=rule_class.meta.fixable and rule_class.meta.code in effectively_fixable_codes, enabled_specificity=enabled_specificities[rule_class.meta.code])
        for rule_class in collection.rules
        if rule_class.meta.code in enabled_specificities
    )
    per_file_ignores = _resolve_per_file_ignores(settings, collection=collection, errors=errors, field_bases=field_bases)
    return RuleSelection(rules=selected_rules, per_file_ignores=per_file_ignores, errors=tuple(errors), collection=collection)


def _resolve_per_file_ignores(settings: CheckSettings, *, collection: RuleCollection, errors: list[str], field_bases: Mapping[str, str] | None) -> tuple[PerFileRuleIgnore, ...]:
    """Resolve per-file rule ignore selectors."""
    ignores: list[PerFileRuleIgnore] = []
    for field in ("per_file_ignores", "extend_per_file_ignores"):
        base_path = os.getcwd() if field_bases is None else field_bases.get(field, os.getcwd())
        for pattern, selectors in getattr(settings, field):
            rule_specificities = _resolve_rule_specificities(selectors, collection=collection, context=f"per-file ignores for {pattern!r}", errors=errors)
            ignores.append(PerFileRuleIgnore(pattern=pattern, base_path=base_path, rule_codes=frozenset(rule_specificities), rule_specificities=tuple(sorted(rule_specificities.items()))))
    return tuple(ignores)


def _resolve_rule_specificities(selectors: tuple[str, ...], *, collection: RuleCollection, context: str, errors: list[str], require_inherently_fixable: bool = False) -> dict[RuleCode, int]:
    """Resolve selectors to rule-code specificities and append nonfatal errors for unusable selectors."""
    rule_specificities: dict[RuleCode, int] = {}
    for selector_tag in selectors:
        selector = _parse_selector(selector_tag, context=context, errors=errors)
        if selector is None:
            continue

        matching_rules = collection.matching_rules(selector)
        if not matching_rules:
            if selector_tag != ALL_RULE_SELECTOR_TAG:
                errors.append(f"{context} contains unknown selector: {selector_tag}")
            continue

        if require_inherently_fixable:
            fixable_rules = tuple(rule for rule in matching_rules if rule.meta.fixable)
            if not fixable_rules and selector_tag != ALL_RULE_SELECTOR_TAG:
                errors.append(f"{context} selector {selector_tag!r} only matches inherently unfixable rules")
            matching_rules = fixable_rules

        specificity = _selector_specificity(selector)
        for rule in matching_rules:
            rule_specificities[rule.meta.code] = max(rule_specificities.get(rule.meta.code, -1), specificity)
    return rule_specificities


def _resolve_enabled_specificities(enabled_specificities: dict[RuleCode, int], disabled_specificities: dict[RuleCode, int]) -> dict[RuleCode, int]:
    """Return enabled rules where the enabling selector is more specific than the disabling selector."""
    return {rule_code: enabled_specificity for rule_code, enabled_specificity in enabled_specificities.items() if enabled_specificity > disabled_specificities.get(rule_code, -1)}


def _selector_specificity(selector: RuleSelector) -> int:
    """Return the priority of a selector, where longer concrete selectors are more specific than shorter ones."""
    if selector.tag == ALL_RULE_SELECTOR_TAG:
        return 0
    return len(selector.tag)


def _parse_selector(selector: str, *, context: str, errors: list[str]) -> RuleSelector | None:
    """Parse one selector and append a nonfatal error if it is invalid."""
    if not RuleSelector.is_valid_tag(selector):
        errors.append(f"{context} contains invalid selector: {selector}")
        return None

    return RuleSelector(selector)


def _base_relative_posix_path(path: str, base_path: str) -> str:
    """Return a base-relative path using POSIX separators."""
    return os.path.relpath(os.path.abspath(path), os.path.abspath(base_path)).replace(os.sep, "/")
