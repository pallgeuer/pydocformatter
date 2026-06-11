from __future__ import annotations

import dataclasses
import enum
import re

from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG, RuleCode

_RULE_PREFIX_RE = re.compile(r"^[A-Z]+$")


class FixAvailability(enum.StrEnum):
    """Rule-level automatic fix availability."""

    ALWAYS = "Always"
    USUALLY = "Usually"
    SOMETIMES = "Sometimes"
    NEVER = "Never"


class RuleSettingEffect(enum.StrEnum):
    """Effect of a resolved setting value on rule selection."""

    IGNORED = "Ignored"
    DISABLED = "Disabled"


@dataclasses.dataclass(frozen=True, order=True)
class RuleSettingEffectValues:
    """Triggering values for one setting effect."""

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
    """Selection effects associated with one resolved setting field."""

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
        stable_since (str): pydocformatter version in which the rule became stable.
        setting_effects (tuple[RuleSettingEffects, ...]): Selection effects driven by resolved setting values.
        incompatible_with (tuple[RuleCode, ...]): Rule codes that cannot be selected together with this rule.
    """

    code: RuleCode
    name: str
    message: str
    fix_availability: FixAvailability
    stable_since: str
    setting_effects: tuple[RuleSettingEffects, ...]
    incompatible_with: tuple[RuleCode, ...]

    def __post_init__(self) -> None:
        """Validate rule metadata fields."""
        if not isinstance(self.code, RuleCode):
            raise TypeError(f"Expected RuleCode, got {type(self.code).__name__}")
        if not isinstance(self.fix_availability, FixAvailability):
            raise TypeError(f"Expected FixAvailability, got {type(self.fix_availability).__name__}")
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
        instance_message (str | None): Optional message overriding the rule default for this instance.
        instance_fixable (bool | None): Optional fixability overriding the rule default for this instance.
    """

    @dataclasses.dataclass(frozen=True, order=True)
    class Key:
        """Key used to merge findings that differ only by line numbers."""

        rule: RuleMetadata
        message: str
        fixable: bool

    rule: RuleMetadata
    line_numbers: tuple[int, ...]
    instance_message: str | None = None
    instance_fixable: bool | None = None

    @property
    def message(self) -> str:
        """Return the instance-specific or default rule message."""
        return self.rule.message if self.instance_message is None else self.instance_message

    @property
    def fixable(self) -> bool:
        """Return whether this specific finding can be automatically fixed."""
        if self.instance_fixable is not None:
            return self.instance_fixable
        if self.rule.fix_availability == FixAvailability.ALWAYS:
            return True
        elif self.rule.fix_availability == FixAvailability.NEVER:
            return False
        elif self.rule.fix_availability in {FixAvailability.USUALLY, FixAvailability.SOMETIMES}:
            raise ValueError(f"{self.rule.code}: Findings for {self.rule.fix_availability.lower()}-fixable rules must specify instance_fixable")
        else:
            raise AssertionError(f"Unexpected fix availability: {self.rule.fix_availability}")

    @property
    def grouping_key(self) -> RuleFinding.Key:
        """Return the key used to merge findings that differ only by line numbers."""
        return RuleFinding.Key(rule=self.rule, message=self.message, fixable=self.fixable)

    def with_line_numbers(self, line_numbers: tuple[int, ...]) -> RuleFinding:
        """Return this finding with updated line numbers."""
        return dataclasses.replace(self, line_numbers=line_numbers)
