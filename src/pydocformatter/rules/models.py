"""Shared rule metadata and diagnostic models."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import enum
import dataclasses

# First-party imports
from pydocformatter.rules import line_targets
from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG, RuleCode


_RULE_PREFIX_RE = re.compile(r"^[A-Z]+$")


class FixAvailability(enum.StrEnum):
    """Rule-level automatic fix availability.

    Attributes:
        ALWAYS: Every reported finding has an automatic fix.
        USUALLY: Every semantic violation kind has a correction, but instance-specific safety can prevent a fix.
        SOMETIMES: At least one semantic violation kind is intentionally diagnostic-only while others have fixes.
        NEVER: The rule is diagnostic-only.
    """

    ALWAYS = "Always"
    USUALLY = "Usually"
    SOMETIMES = "Sometimes"
    NEVER = "Never"


class RuleCheckKind(enum.StrEnum):
    """How a rule participates in check passes.

    Attributes:
        STANDARD: Rule checks source directly and returns findings for its own code.
        SUPPRESSION_AUDIT: Rule reports unused or invalid source suppressions after standard checks run.
    """

    STANDARD = "standard"
    SUPPRESSION_AUDIT = "suppression-audit"


class RuleCacheBehavior(enum.StrEnum):
    """Rule dependency behavior for persistent clean-proof caching.

    Attributes:
        FILE_LOCAL: Findings and fixes depend only on fingerprinted file-local inputs.
        UNCACHEABLE: Selecting the rule bypasses persistent lookup and population.
    """

    FILE_LOCAL = "file-local"
    UNCACHEABLE = "uncacheable"


class RuleSettingEffect(enum.StrEnum):
    """Effect of a resolved setting value on rule selection.

    Attributes:
        IGNORED: Matching values remove the rule unless it was selected exactly.
        DISABLED: Matching values always remove the rule from the active selection.
    """

    IGNORED = "Ignored"
    DISABLED = "Disabled"


@dataclasses.dataclass(frozen=True, order=True)
class RuleSettingEffectValues:
    """Triggering values for one setting effect.

    Attributes:
        effect (RuleSettingEffect): Selection effect to apply when the resolved setting matches.
        values (tuple[object, ...]): Hashable setting values that trigger the effect.
    """

    effect: RuleSettingEffect
    values: tuple[object, ...]

    def __post_init__(self) -> None:
        """Validate the effect and its triggering values."""
        if not isinstance(self.effect, RuleSettingEffect):
            raise TypeError(f"Expected RuleSettingEffect, got {type(self.effect).__name__}")
        if not isinstance(self.values, tuple):
            raise TypeError("Rule setting effect triggering values must be a tuple")
        if not self.values:
            raise ValueError("Rule setting effect triggering values must not be empty")
        try:
            hash(self.values)
        except TypeError:
            raise TypeError("Rule setting effect triggering values must be hashable") from None


@dataclasses.dataclass(frozen=True, order=True)
class RuleSettingEffects:
    """Selection effects associated with one resolved setting field.

    Attributes:
        setting (str): Name of the resolved settings field that controls the effects.
        effects (tuple[RuleSettingEffectValues, ...]): Effects available for specific values of that field.
    """

    setting: str
    effects: tuple[RuleSettingEffectValues, ...]

    def __post_init__(self) -> None:
        """Validate the setting name and effect records."""
        if not self.setting:
            raise ValueError("Rule setting name must not be empty")
        if not isinstance(self.effects, tuple):
            raise TypeError("Rule setting effects must be a tuple")
        if not all(isinstance(effect, RuleSettingEffectValues) for effect in self.effects):
            raise TypeError("Rule setting effects must contain RuleSettingEffectValues instances")


@dataclasses.dataclass(frozen=True, order=True)
class RuleMetadata:
    """Metadata for a pydocformatter rule.

    Attributes:
        code (RuleCode): Rule code.
        name (str): Rule name.
        message (str): Default diagnostic message.
        fix_availability (FixAvailability): Rule-level automatic fix availability.
        stable_since (str): Version of pydocformatter in which the rule became stable.
        setting_effects (tuple[RuleSettingEffects, ...]): Selection effects driven by resolved setting values.
        incompatible_with (tuple[RuleCode, ...]): Rule codes that cannot be selected together with this rule.
        check_kind (RuleCheckKind): Check-pass phase used to run the rule.
        cache_behavior (RuleCacheBehavior): Declared dependency behavior for persistent caching.
    """

    code: RuleCode
    name: str
    message: str
    fix_availability: FixAvailability
    stable_since: str
    setting_effects: tuple[RuleSettingEffects, ...]
    incompatible_with: tuple[RuleCode, ...]
    check_kind: RuleCheckKind = dataclasses.field(kw_only=True)
    cache_behavior: RuleCacheBehavior = dataclasses.field(default=RuleCacheBehavior.UNCACHEABLE, kw_only=True)

    def __post_init__(self) -> None:
        """Validate rule metadata fields."""
        if not isinstance(self.code, RuleCode):
            raise TypeError(f"Expected RuleCode, got {type(self.code).__name__}")
        if not isinstance(self.fix_availability, FixAvailability):
            raise TypeError(f"Expected FixAvailability, got {type(self.fix_availability).__name__}")
        if not isinstance(self.check_kind, RuleCheckKind):
            raise TypeError(f"Expected RuleCheckKind, got {type(self.check_kind).__name__}")
        if not isinstance(self.cache_behavior, RuleCacheBehavior):
            raise TypeError(f"Expected RuleCacheBehavior, got {type(self.cache_behavior).__name__}")
        if not self.name:
            raise ValueError(f"{self.code}: Rule name must not be empty")
        if not self.message:
            raise ValueError(f"{self.code}: Rule message must not be empty")
        if not self.stable_since:
            raise ValueError(f"{self.code}: Stable version must not be empty")
        if not isinstance(self.setting_effects, tuple):
            raise TypeError(f"{self.code}: Rule setting effects must be a tuple")
        if not all(isinstance(setting_effects, RuleSettingEffects) for setting_effects in self.setting_effects):
            raise TypeError(f"{self.code}: Rule setting effects must contain RuleSettingEffects instances")
        if not isinstance(self.incompatible_with, tuple):
            raise TypeError(f"{self.code}: Incompatible rule codes must be a tuple")
        if not all(isinstance(rule_code, RuleCode) for rule_code in self.incompatible_with):
            raise TypeError(f"{self.code}: Incompatible rule codes must contain RuleCode instances")
        if len(set(self.incompatible_with)) != len(self.incompatible_with):
            raise ValueError(f"{self.code}: Incompatible rule codes must not contain duplicates")

    def setting_effect(self, setting: str, value: object) -> RuleSettingEffect | None:
        """Return the effective selection effect for one resolved setting value.

        Args:
            setting (str): Resolved settings field to query.
            value (object): Resolved field value to match against declared effects.

        Returns:
            RuleSettingEffect | None: Matching effect with disabled precedence, or none when no effect applies.
        """
        triggered_effects = {
            effect_values.effect for setting_effects in self.setting_effects if setting_effects.setting == setting for effect_values in setting_effects.effects if value in effect_values.values
        }
        if RuleSettingEffect.DISABLED in triggered_effects:
            return RuleSettingEffect.DISABLED
        if RuleSettingEffect.IGNORED in triggered_effects:
            return RuleSettingEffect.IGNORED
        return None


@dataclasses.dataclass(frozen=True, order=True)
class RuleCategoryMetadata:
    """Metadata for one pydocformatter rule category.

    Attributes:
        prefix (str): Rule-code prefix for the category.
        name (str): User-facing category name.
        url (str | None): Optional project or documentation URL for the category.
    """

    prefix: str
    name: str
    url: str | None

    def __post_init__(self) -> None:
        """Validate category metadata fields."""
        if _RULE_PREFIX_RE.fullmatch(self.prefix) is None or self.prefix.startswith(ALL_RULE_SELECTOR_TAG):
            raise ValueError(f"Invalid rule category prefix: {self.prefix}")
        if self.name == "":
            raise ValueError(f"{self.prefix}: Rule category name must not be empty")


@dataclasses.dataclass(frozen=True)
class RuleFinding:
    """A remaining or fixed instance of a rule issue.

    Attributes:
        rule (RuleMetadata): Rule metadata for the finding.
        line_numbers (tuple[int, ...]): One-based source line numbers associated with the finding.
        suppression_line_numbers (tuple[tuple[int, ...], ...]): Additional line-number targets used only for source
            suppression matching.
        instance_message (str | None): Optional message overriding the rule default for this instance.
        instance_fixable (bool | None): Optional fixability overriding the rule default for this instance.
    """

    @dataclasses.dataclass(frozen=True, order=True)
    class Key:
        """Key used to merge findings that differ only by line numbers.

        Attributes:
            rule (RuleMetadata): Rule metadata shared by merge-compatible findings.
            message (str): Effective diagnostic message after instance-specific overrides.
            fixable (bool): Effective fixability for the merged finding group.
        """

        rule: RuleMetadata
        message: str
        fixable: bool

    rule: RuleMetadata
    line_numbers: tuple[int, ...]
    suppression_line_numbers: tuple[tuple[int, ...], ...] = ()
    instance_message: str | None = None
    instance_fixable: bool | None = dataclasses.field(kw_only=True)

    def __post_init__(self) -> None:
        """Validate finding target lines."""
        object.__setattr__(self, "line_numbers", line_targets.normalize_line_numbers(self.line_numbers, "Finding line numbers"))
        object.__setattr__(
            self,
            "suppression_line_numbers",
            line_targets.normalize_line_number_targets(self.suppression_line_numbers, "Finding suppression line-number targets", "Finding suppression line-number target"),
        )

    @property
    def message(self) -> str:
        """Instance-specific or default rule message.

        Returns:
            str: Diagnostic text that should be displayed for this finding.
        """
        return self.rule.message if self.instance_message is None else self.instance_message

    @property
    def fixable(self) -> bool:
        """Whether this specific finding can be automatically fixed.

        Returns:
            bool: Whether this finding has an enabled source fix.

        Raises:
            ValueError: If a conditionally fixable rule did not specify per-instance fixability.
            AssertionError: If rule metadata contains an unknown fix-availability value.
        """
        if self.instance_fixable is not None:
            return self.instance_fixable
        if self.rule.fix_availability == FixAvailability.ALWAYS:
            return True
        if self.rule.fix_availability == FixAvailability.NEVER:
            return False
        if self.rule.fix_availability in {FixAvailability.USUALLY, FixAvailability.SOMETIMES}:
            raise ValueError(f"{self.rule.code}: Findings for {self.rule.fix_availability.lower()}-fixable rules must specify instance_fixable")
        raise AssertionError(f"Unexpected fix availability: {self.rule.fix_availability}")

    @property
    def grouping_key(self) -> RuleFinding.Key:
        """Key used to merge findings that differ only by line numbers.

        Returns:
            RuleFinding.Key: Merge key that excludes line targets but preserves rule, message, and fixability.
        """
        return RuleFinding.Key(rule=self.rule, message=self.message, fixable=self.fixable)

    @property
    def suppression_targets(self) -> tuple[tuple[int, ...], ...]:
        """Line-number targets that can suppress this finding.

        Returns:
            tuple[tuple[int, ...], ...]: Primary and alternate one-based line groups accepted by suppression directives.
        """
        return (self.line_numbers, *self.suppression_line_numbers)

    def with_line_numbers(self, line_numbers: tuple[int, ...]) -> RuleFinding:
        """Return this finding with updated line numbers.

        Args:
            line_numbers (tuple[int, ...]): Replacement primary diagnostic target lines.

        Returns:
            RuleFinding: Copy of this finding with normalized line numbers.
        """
        return dataclasses.replace(self, line_numbers=line_numbers)
