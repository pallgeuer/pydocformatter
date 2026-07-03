"""Rule selection, fixability, and per-file ignores."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Mapping

import pydocformatter.rules.collection as rule_collection
import pydocformatter.settings as settings_core
import pydocformatter.utils.misc as misc
from pydocformatter.cli.settings_check import DEFAULT_REQUIRE_EXPLICIT, CheckSettings
from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG, RuleCode, RuleSelector
from pydocformatter.rules.collection import RuleCollection
from pydocformatter.rules.models import FixAvailability, RuleMetadata, RuleSettingEffect
from pydocformatter.utils.globs import GlobPatternSet


@dataclasses.dataclass(frozen=True)
class SelectedRule:
    """A rule selected for processing with its effective fixability.

    Attributes:
        rule (RuleMetadata): Rule metadata selected for processing.
        fixable (bool): Whether fixes are enabled for this rule after fixability settings.
        enabled_priority (int): Source-priority level of the selector that enabled the rule.
        enabled_specificity (int): Specificity of the selector that enabled the rule.
    """

    rule: RuleMetadata
    fixable: bool
    enabled_priority: int
    enabled_specificity: int


@dataclasses.dataclass(frozen=True, order=True)
class _SelectorStrength:
    """Priority and specificity of one rule selector match."""

    priority: int
    specificity: int
    exact_match: bool = dataclasses.field(default=False, compare=False)


@dataclasses.dataclass(frozen=True)
class _SelectorGroup:
    """Rule selectors that came from one configuration source."""

    selectors: tuple[str, ...]
    priority: int


@dataclasses.dataclass(frozen=True)
class PerFileRuleIgnore:
    """Rule ignore selectors resolved for one path pattern.

    Attributes:
        pattern (str): Configured glob pattern, optionally prefixed with `!` for negation.
        base_path (str): Absolute directory relative to which `pattern` is evaluated.
        rule_codes (frozenset[RuleCode]): Rules ignored when this pattern matches.
        rule_specificities (tuple[tuple[RuleCode, int], ...]): Ignored rules paired with the selector specificity that
            selected them.
        negated (bool): Whether the pattern is a negated per-file-ignore entry.
        matcher (GlobPatternSet): Compiled matcher reused for per-path checks.
    """

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
        """Return whether this per-file ignore entry matches a normalized path.

        Args:
            path (str): Filesystem path to compare against the configured pattern base.

        Returns:
            bool: Whether the path is covered by the ignore entry after applying negation.
        """
        matched = self.matcher.matches(_base_relative_posix_path(path, self.base_path))
        return not matched if self.negated else matched


@dataclasses.dataclass(frozen=True)
class RuleSelection:
    """Effective rule selection for a resolved settings object.

    Attributes:
        rules (tuple[SelectedRule, ...]): Globally selected rules before per-file ignores are applied.
        per_file_ignores (tuple[PerFileRuleIgnore, ...]): Path-specific ignore entries resolved from settings.
        errors (tuple[str, ...]): Non-fatal rule-selection errors to report to the caller.
        collection (RuleCollection): Rule collection that supplied the selectable rule metadata.
    """

    rules: tuple[SelectedRule, ...]
    per_file_ignores: tuple[PerFileRuleIgnore, ...]
    errors: tuple[str, ...]
    collection: RuleCollection

    def for_path(self, path: str) -> tuple[SelectedRule, ...]:
        """Return selected rules after applying per-file ignores to a path.

        Args:
            path (str): Source path whose per-file ignore patterns should be evaluated.

        Returns:
            tuple[SelectedRule, ...]: Globally selected rules with path-specific ignored rules removed.
        """
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
    """Resolve rule selection and fixability settings against collected rules.

    Args:
        settings (CheckSettings): Resolved check settings to use when no profile override is supplied.
        collection (RuleCollection | None): Rule collection to select from, or the built-in collection by default.
        field_bases (Mapping[str, str] | None): Source-base directories for path-like rule settings.
        field_priorities (Mapping[str, int] | None): Source priorities used to break ties between selector groups.
        profile (settings_core.SettingsProfile[CheckSettings] | None): Complete settings profile that overrides the
            separate settings and metadata arguments.

    Returns:
        RuleSelection: Effective rule set, fixability flags, per-file ignores, and non-fatal selector errors.
    """
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
    enabled_strengths = _apply_setting_effects(settings, enabled_strengths=enabled_strengths, collection=collection)
    require_explicit_codes = _resolve_require_explicit_codes(settings, collection=collection, errors=errors, field_priorities=field_priorities)
    enabled_strengths = _apply_require_explicit(enabled_strengths, require_explicit_codes=require_explicit_codes)
    enabled_strengths = _resolve_rule_incompatibilities(enabled_strengths, collection=collection, errors=errors)

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


def _apply_setting_effects(settings: CheckSettings, *, enabled_strengths: dict[RuleCode, _SelectorStrength], collection: RuleCollection) -> dict[RuleCode, _SelectorStrength]:
    """Apply rule metadata effects triggered by resolved setting values."""
    effective_strengths = enabled_strengths.copy()
    for rule_class in collection.rules:
        rule = rule_class.meta
        if rule.code not in effective_strengths:
            continue
        triggered_effects: set[RuleSettingEffect] = set()
        for setting_effects in rule.setting_effects:
            try:
                setting_value = getattr(settings, setting_effects.setting)
            except AttributeError:
                raise ValueError(f"{rule.code}: Unknown rule setting effect field: {setting_effects.setting}") from None
            for effect_values in setting_effects.effects:
                if setting_value in effect_values.values:
                    triggered_effects.add(effect_values.effect)
        enabled_strength = effective_strengths[rule.code]
        if RuleSettingEffect.DISABLED in triggered_effects or (RuleSettingEffect.IGNORED in triggered_effects and not enabled_strength.exact_match):
            del effective_strengths[rule.code]
    return effective_strengths


def _resolve_require_explicit_codes(
    settings: CheckSettings,
    *,
    collection: RuleCollection,
    errors: list[str],
    field_priorities: Mapping[str, int] | None,
) -> frozenset[RuleCode]:
    """Return rules that broad selectors cannot enable without exact rule-code selection."""
    report_unknown = settings.require_explicit != DEFAULT_REQUIRE_EXPLICIT or _field_priority("require_explicit", field_priorities) > settings_core.DEFAULT_SOURCE_PRIORITY
    return frozenset(
        _resolve_rule_specificities(
            settings.require_explicit,
            collection=collection,
            context="require-explicit rules",
            errors=errors,
            report_unknown=report_unknown,
        )
    )


def _apply_require_explicit(enabled_strengths: dict[RuleCode, _SelectorStrength], *, require_explicit_codes: frozenset[RuleCode]) -> dict[RuleCode, _SelectorStrength]:
    """Remove require-explicit rules that were only selected through broad selectors."""
    return {rule_code: strength for rule_code, strength in enabled_strengths.items() if rule_code not in require_explicit_codes or strength.exact_match}


def _resolve_rule_incompatibilities(enabled_strengths: dict[RuleCode, _SelectorStrength], *, collection: RuleCollection, errors: list[str]) -> dict[RuleCode, _SelectorStrength]:
    """Keep the first selected rule from each incompatible set and report discarded rules."""
    effective_strengths: dict[RuleCode, _SelectorStrength] = {}
    for rule_class in collection.rules:
        rule = rule_class.meta
        if rule.code not in enabled_strengths:
            continue
        incompatible_codes = set(rule.incompatible_with)
        earlier_conflicts = tuple(code for code in effective_strengths if code in incompatible_codes)
        if earlier_conflicts:
            conflicts = ", ".join(map(str, earlier_conflicts))
            errors.append(f"Selected rule {rule.code} is incompatible with earlier selected {misc.auto_plural(len(earlier_conflicts), 'rule')} {conflicts}; {rule.code} has been disabled")
        else:
            effective_strengths[rule.code] = enabled_strengths[rule.code]
    return effective_strengths


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


def _resolve_rule_specificities(
    selectors: tuple[str, ...],
    *,
    collection: RuleCollection,
    context: str,
    errors: list[str],
    require_available_fix: bool = False,
    report_unknown: bool = True,
) -> dict[RuleCode, int]:
    """Resolve selectors to rule-code specificities and append nonfatal errors for unusable selectors."""
    strengths = _resolve_rule_strengths(
        (_SelectorGroup(selectors=selectors, priority=settings_core.DEFAULT_SOURCE_PRIORITY),),
        collection=collection,
        context=context,
        errors=errors,
        require_available_fix=require_available_fix,
        report_unknown=report_unknown,
    )
    return {rule_code: strength.specificity for rule_code, strength in strengths.items()}


def _resolve_rule_strengths(
    selector_groups: tuple[_SelectorGroup, ...],
    *,
    collection: RuleCollection,
    context: str,
    errors: list[str],
    require_available_fix: bool = False,
    report_unknown: bool = True,
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
                if report_unknown and selector_tag != ALL_RULE_SELECTOR_TAG:
                    errors.append(f"{context} contains unknown selector: {selector_tag}")
                continue

            if require_available_fix:
                fixable_rules = tuple(rule for rule in matching_rules if rule.meta.fix_availability != FixAvailability.NEVER)
                if not fixable_rules and selector_tag != ALL_RULE_SELECTOR_TAG:
                    errors.append(f"{context} selector {selector_tag!r} only matches rules with no available fixes")
                matching_rules = fixable_rules

            selector_specificity = _selector_specificity(selector)
            for rule in matching_rules:
                strength = _SelectorStrength(priority=selector_group.priority, specificity=selector_specificity, exact_match=selector.tag == rule.meta.code.tag)
                previous_strength = rule_strengths.get(rule.meta.code, _SelectorStrength(priority=-1, specificity=-1))
                strongest = max(previous_strength, strength)
                rule_strengths[rule.meta.code] = dataclasses.replace(strongest, exact_match=previous_strength.exact_match or strength.exact_match)
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
