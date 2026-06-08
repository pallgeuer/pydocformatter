from __future__ import annotations

import dataclasses
import os
from collections.abc import Mapping

import pydocformatter.rules.collection as rule_collection
import pydocformatter.settings as settings_core
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.collection import RuleCollection
from pydocformatter.rules.models import ALL_RULE_SELECTOR_TAG, FixAvailability, RuleCode, RuleMetadata, RuleSelector
from pydocformatter.utils.globs import GlobPatternSet


@dataclasses.dataclass(frozen=True)
class SelectedRule:
    """A rule selected for processing with its effective fixability."""

    rule: RuleMetadata
    fixable: bool
    enabled_priority: int
    enabled_specificity: int


@dataclasses.dataclass(frozen=True, order=True)
class _SelectorStrength:
    """Priority and specificity of one rule selector match."""

    priority: int
    specificity: int


@dataclasses.dataclass(frozen=True)
class _SelectorGroup:
    """Rule selectors that came from one configuration source."""

    selectors: tuple[str, ...]
    priority: int


@dataclasses.dataclass(frozen=True)
class PerFileRuleIgnore:
    """Rule ignore selectors resolved for one path pattern."""

    pattern: str
    base_path: str
    rule_codes: frozenset[RuleCode]
    rule_specificities: tuple[tuple[RuleCode, int], ...]
    negated: bool = dataclasses.field(init=False)
    matcher: GlobPatternSet = dataclasses.field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        """Compile the ignore matcher once for repeated per-path checks."""
        negated = self.pattern.startswith("!")
        object.__setattr__(self, "negated", negated)
        pattern = self.pattern[1:] if negated else self.pattern
        object.__setattr__(self, "matcher", GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False))

    def matches(self, path: str) -> bool:
        """Return whether this per-file ignore entry matches a normalized path."""
        matched = self.matcher.matches(_base_relative_posix_path(path, self.base_path))
        return not matched if self.negated else matched


@dataclasses.dataclass(frozen=True)
class RuleSelection:
    """Effective rule selection for a resolved settings object."""

    rules: tuple[SelectedRule, ...]
    per_file_ignores: tuple[PerFileRuleIgnore, ...]
    errors: tuple[str, ...]
    collection: RuleCollection

    def for_path(self, path: str) -> tuple[SelectedRule, ...]:
        """Return selected rules after applying per-file ignores to a path."""
        ignored_rule_codes: set[RuleCode] = set()
        for ignore in self.per_file_ignores:
            if ignore.matches(path):
                ignored_rule_codes.update(ignore.rule_codes)
        if not ignored_rule_codes:
            return self.rules
        return tuple(rule for rule in self.rules if rule.rule.code not in ignored_rule_codes)


def select_rules(
    settings: CheckSettings,
    *,
    collection: RuleCollection | None = None,
    field_bases: Mapping[str, str] | None = None,
    field_priorities: Mapping[str, int] | None = None,
    profile: settings_core.SettingsProfile[CheckSettings] | None = None,
) -> RuleSelection:
    """Resolve rule selection and fixability settings against collected rules."""
    if collection is None:
        collection = rule_collection.RULE_COLLECTION
    if profile is not None:
        settings = profile.settings
        field_bases = profile.field_bases
        field_priorities = profile.field_priorities

    errors: list[str] = []
    selected_strengths = _resolve_rule_strengths(
        _selector_groups(
            settings,
            primary_field="select",
            extension_field="extend_select",
            field_priorities=field_priorities,
        ),
        collection=collection,
        context="rule selection",
        errors=errors,
    )
    _resolve_rule_strengths(
        _skipped_selector_groups(
            settings,
            primary_field="select",
            extension_field="extend_select",
            field_priorities=field_priorities,
        ),
        collection=collection,
        context="rule selection",
        errors=errors,
    )
    ignored_strengths = _resolve_rule_strengths(
        _selector_groups(
            settings,
            primary_field="select",
            extension_field="ignore",
            field_priorities=field_priorities,
            include_primary=False,
        ),
        collection=collection,
        context="ignored rules",
        errors=errors,
    )
    _resolve_rule_strengths(
        _skipped_selector_groups(
            settings,
            primary_field="select",
            extension_field="ignore",
            field_priorities=field_priorities,
        ),
        collection=collection,
        context="ignored rules",
        errors=errors,
    )
    enabled_strengths = _resolve_enabled_strengths(selected_strengths, ignored_strengths)

    fixable_strengths = _resolve_rule_strengths(
        _selector_groups(
            settings,
            primary_field="fixable",
            extension_field="extend_fixable",
            field_priorities=field_priorities,
        ),
        collection=collection,
        context="fixable rules",
        errors=errors,
        require_available_fix=True,
    )
    _resolve_rule_strengths(
        _skipped_selector_groups(
            settings,
            primary_field="fixable",
            extension_field="extend_fixable",
            field_priorities=field_priorities,
        ),
        collection=collection,
        context="fixable rules",
        errors=errors,
        require_available_fix=True,
    )
    unfixable_strengths = _resolve_rule_strengths(
        _selector_groups(
            settings,
            primary_field="fixable",
            extension_field="unfixable",
            field_priorities=field_priorities,
            include_primary=False,
        ),
        collection=collection,
        context="unfixable rules",
        errors=errors,
    )
    _resolve_rule_strengths(
        _skipped_selector_groups(
            settings,
            primary_field="fixable",
            extension_field="unfixable",
            field_priorities=field_priorities,
        ),
        collection=collection,
        context="unfixable rules",
        errors=errors,
    )
    effectively_fixable_codes = _resolve_enabled_strengths(fixable_strengths, unfixable_strengths)

    selected_rules = tuple(
        SelectedRule(
            rule=rule_class.meta,
            fixable=rule_class.meta.fix_availability != FixAvailability.NEVER and rule_class.meta.code in effectively_fixable_codes,
            enabled_priority=enabled_strengths[rule_class.meta.code].priority,
            enabled_specificity=enabled_strengths[rule_class.meta.code].specificity,
        )
        for rule_class in collection.rules
        if rule_class.meta.code in enabled_strengths
    )
    per_file_ignores = _resolve_per_file_ignores(settings, collection=collection, errors=errors, field_bases=field_bases)
    return RuleSelection(rules=selected_rules, per_file_ignores=per_file_ignores, errors=tuple(errors), collection=collection)


def _selector_groups(
    settings: CheckSettings,
    *,
    primary_field: str,
    extension_field: str,
    field_priorities: Mapping[str, int] | None,
    include_primary: bool = True,
) -> tuple[_SelectorGroup, ...]:
    """Return selector groups that participate in Ruff-style source-priority resolution."""
    primary_priority = _field_priority(primary_field, field_priorities)
    groups: list[_SelectorGroup] = []
    if include_primary:
        groups.append(_SelectorGroup(selectors=getattr(settings, primary_field), priority=primary_priority))

    extension_priority = _field_priority(extension_field, field_priorities)
    if extension_priority >= primary_priority:
        groups.append(_SelectorGroup(selectors=getattr(settings, extension_field), priority=extension_priority))
    return tuple(groups)


def _field_priority(field: str, field_priorities: Mapping[str, int] | None) -> int:
    """Return the resolved source priority for a settings field."""
    if field_priorities is None:
        return settings_core.DEFAULT_SOURCE_PRIORITY
    return field_priorities.get(field, settings_core.DEFAULT_SOURCE_PRIORITY)


def _skipped_selector_groups(settings: CheckSettings, *, primary_field: str, extension_field: str, field_priorities: Mapping[str, int] | None) -> tuple[_SelectorGroup, ...]:
    """Return lower-priority selector groups that should be validated without participating."""
    primary_priority = _field_priority(primary_field, field_priorities)
    extension_priority = _field_priority(extension_field, field_priorities)
    if extension_priority >= primary_priority:
        return ()
    return (_SelectorGroup(selectors=getattr(settings, extension_field), priority=extension_priority),)


def _resolve_per_file_ignores(settings: CheckSettings, *, collection: RuleCollection, errors: list[str], field_bases: Mapping[str, str] | None) -> tuple[PerFileRuleIgnore, ...]:
    """Resolve per-file rule ignore selectors."""
    ignores: list[PerFileRuleIgnore] = []
    for field in ("per_file_ignores", "extend_per_file_ignores"):
        base_path = os.getcwd() if field_bases is None else field_bases.get(field, os.getcwd())
        for pattern, selectors in getattr(settings, field):
            rule_specificities = _resolve_rule_specificities(selectors, collection=collection, context=f"per-file ignores for {pattern!r}", errors=errors)
            ignores.append(PerFileRuleIgnore(pattern=pattern, base_path=base_path, rule_codes=frozenset(rule_specificities), rule_specificities=tuple(sorted(rule_specificities.items()))))
    return tuple(ignores)


def _resolve_rule_specificities(selectors: tuple[str, ...], *, collection: RuleCollection, context: str, errors: list[str], require_available_fix: bool = False) -> dict[RuleCode, int]:
    """Resolve selectors to rule-code specificities and append nonfatal errors for unusable selectors."""
    strengths = _resolve_rule_strengths(
        (_SelectorGroup(selectors=selectors, priority=settings_core.DEFAULT_SOURCE_PRIORITY),),
        collection=collection,
        context=context,
        errors=errors,
        require_available_fix=require_available_fix,
    )
    return {rule_code: strength.specificity for rule_code, strength in strengths.items()}


def _resolve_rule_strengths(
    selector_groups: tuple[_SelectorGroup, ...], *, collection: RuleCollection, context: str, errors: list[str], require_available_fix: bool = False
) -> dict[RuleCode, _SelectorStrength]:
    """Resolve selectors to rule-code source strengths and append nonfatal errors for unusable selectors."""
    rule_strengths: dict[RuleCode, _SelectorStrength] = {}
    for selector_group in selector_groups:
        for selector_tag in selector_group.selectors:
            selector = _parse_selector(selector_tag, context=context, errors=errors)
            if selector is None:
                continue

            matching_rules = collection.matching_rules(selector)
            if not matching_rules:
                if selector_tag != ALL_RULE_SELECTOR_TAG:
                    errors.append(f"{context} contains unknown selector: {selector_tag}")
                continue

            if require_available_fix:
                fixable_rules = tuple(rule for rule in matching_rules if rule.meta.fix_availability != FixAvailability.NEVER)
                if not fixable_rules and selector_tag != ALL_RULE_SELECTOR_TAG:
                    errors.append(f"{context} selector {selector_tag!r} only matches rules with no available fixes")
                matching_rules = fixable_rules

            strength = _SelectorStrength(priority=selector_group.priority, specificity=_selector_specificity(selector))
            for rule in matching_rules:
                rule_strengths[rule.meta.code] = max(rule_strengths.get(rule.meta.code, _SelectorStrength(priority=-1, specificity=-1)), strength)
    return rule_strengths


def _resolve_enabled_strengths(enabled_strengths: dict[RuleCode, _SelectorStrength], disabled_strengths: dict[RuleCode, _SelectorStrength]) -> dict[RuleCode, _SelectorStrength]:
    """Return enabled rules where the enabling selector has greater priority and specificity strength."""
    return {
        rule_code: enabled_strength for rule_code, enabled_strength in enabled_strengths.items() if enabled_strength > disabled_strengths.get(rule_code, _SelectorStrength(priority=-1, specificity=-1))
    }


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
