from __future__ import annotations

import dataclasses
import os

import pydocformatter.rules.collection as rule_collection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.base import ALL_RULE_SELECTOR_TAG, RuleBase, RuleCode, RuleMetadata, RuleSelector
from pydocformatter.rules.collection import RuleCollection
from pydocformatter.utils.globs import GlobPatternSet


@dataclasses.dataclass(frozen=True)
class SelectedRule:
    """A rule selected for processing with its effective fixability."""

    rule: RuleMetadata
    fixable: bool


@dataclasses.dataclass(frozen=True)
class PerFileRuleIgnore:
    """Rule ignore selectors resolved for one path pattern."""

    pattern: str
    rule_codes: frozenset[RuleCode]

    def matches(self, path: str) -> bool:
        """Return whether this per-file ignore entry matches a normalized path."""
        matcher = GlobPatternSet.compile((self.pattern,), match_parent_segments_for_bare=False)
        return matcher.matches(path)


@dataclasses.dataclass(frozen=True)
class RuleSelection:
    """Effective rule selection for a resolved settings object."""

    rules: tuple[SelectedRule, ...]
    per_file_ignores: tuple[PerFileRuleIgnore, ...]
    errors: tuple[str, ...]
    collection: RuleCollection

    def for_path(self, path: str) -> tuple[SelectedRule, ...]:
        """Return selected rules after applying per-file ignores to a path."""
        normalized_path = _normalize_path(path)
        ignored_codes: set[RuleCode] = set()
        for ignore in self.per_file_ignores:
            if ignore.matches(normalized_path):
                ignored_codes.update(ignore.rule_codes)
        if not ignored_codes:
            return self.rules
        return tuple(rule for rule in self.rules if rule.rule.code not in ignored_codes)


def select_rules(settings: CheckSettings, *, collection: RuleCollection | None = None) -> RuleSelection:
    """Resolve rule selection and fixability settings against collected rules."""
    if collection is None:
        collection = rule_collection.RULE_COLLECTION

    errors: list[str] = []
    selected_codes = _resolve_rule_code_set(
        settings.select + settings.extend_select,
        collection=collection,
        context="rule selection",
        errors=errors,
    )
    ignored_codes = _resolve_rule_code_set(settings.ignore, collection=collection, context="ignored rules", errors=errors)
    enabled_codes = selected_codes - ignored_codes

    fixable_codes = _resolve_rule_code_set(
        settings.fixable + settings.extend_fixable,
        collection=collection,
        context="fixable rules",
        errors=errors,
        require_inherently_fixable=True,
    )
    unfixable_codes = _resolve_rule_code_set(settings.unfixable, collection=collection, context="unfixable rules", errors=errors)
    effectively_fixable_codes = fixable_codes - unfixable_codes

    selected_rules = tuple(
        SelectedRule(rule=rule_class.meta, fixable=rule_class.meta.fixable and rule_class.meta.code in effectively_fixable_codes)
        for rule_class in collection.rules
        if rule_class.meta.code in enabled_codes
    )
    per_file_ignores = _resolve_per_file_ignores(settings, collection=collection, errors=errors)
    return RuleSelection(rules=selected_rules, per_file_ignores=per_file_ignores, errors=tuple(errors), collection=collection)


def _resolve_per_file_ignores(settings: CheckSettings, *, collection: RuleCollection, errors: list[str]) -> tuple[PerFileRuleIgnore, ...]:
    """Resolve per-file rule ignore selectors."""
    ignores: list[PerFileRuleIgnore] = []
    for pattern, selectors in settings.per_file_ignores + settings.extend_per_file_ignores:
        rule_codes = _resolve_rule_code_set(selectors, collection=collection, context=f"per-file ignores for {pattern!r}", errors=errors)
        ignores.append(PerFileRuleIgnore(pattern=pattern, rule_codes=frozenset(rule_codes)))
    return tuple(ignores)


def _resolve_rule_code_set(
    selectors: tuple[str, ...],
    *,
    collection: RuleCollection,
    context: str,
    errors: list[str],
    require_inherently_fixable: bool = False,
) -> set[RuleCode]:
    """Resolve selectors to rule codes and append nonfatal errors for unusable selectors."""
    rule_codes: set[RuleCode] = set()
    for selector in selectors:
        matching_rules = _matching_rules(selector, collection=collection, context=context, errors=errors)
        if not matching_rules:
            continue

        if require_inherently_fixable:
            fixable_rules = tuple(rule for rule in matching_rules if rule.meta.fixable)
            if not fixable_rules and selector != ALL_RULE_SELECTOR_TAG:
                errors.append(f"{context} selector {selector!r} only matches inherently unfixable rules")
            matching_rules = fixable_rules

        rule_codes.update(rule.meta.code for rule in matching_rules)
    return rule_codes


def _matching_rules(selector: str, *, collection: RuleCollection, context: str, errors: list[str]) -> tuple[type[RuleBase], ...]:
    """Resolve one selector against a collection."""
    if not RuleSelector.is_valid_tag(selector):
        errors.append(f"{context} contains invalid selector: {selector}")
        return ()

    rule_selector = RuleSelector(selector)
    matching_rules = collection.matching_rules(rule_selector)
    if not matching_rules and selector != ALL_RULE_SELECTOR_TAG:
        errors.append(f"{context} contains unknown selector: {selector}")
    return matching_rules


def _normalize_path(path: str) -> str:
    """Return a POSIX-style path suitable for per-file rule matching."""
    candidate = os.path.normpath(path)
    if os.path.isabs(candidate):
        try:
            candidate = os.path.relpath(candidate)
        except ValueError:
            pass
    return candidate.replace(os.sep, "/")
