from __future__ import annotations

import dataclasses
import enum
import re
from typing import ClassVar

import pydocformatter.utils.misc as misc

_RULE_CODE_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
_RULE_SELECTOR_RE = re.compile(r"^([A-Z]+)([0-9]*)$")
ALL_RULE_SELECTOR_TAG = "ALL"


class FixAvailability(enum.StrEnum):
    """Rule-level automatic fix availability."""

    ALWAYS = "Always"
    SOMETIMES = "Sometimes"
    NEVER = "Never"


@dataclasses.dataclass(frozen=True, order=True)
class RuleCode:
    """Parsed pydocformatter rule code."""

    tag: str
    prefix: str = dataclasses.field(init=False)
    number_str: str = dataclasses.field(init=False)
    number: int = dataclasses.field(init=False)

    @staticmethod
    def is_valid_tag(tag: str) -> bool:
        """Return whether a string is a valid rule code tag."""
        return _RULE_CODE_RE.fullmatch(tag) is not None and not tag.startswith(ALL_RULE_SELECTOR_TAG)

    def __post_init__(self) -> None:
        """Derive rule code parts from the full tag."""
        match = _RULE_CODE_RE.fullmatch(self.tag)
        if match is None or self.tag.startswith(ALL_RULE_SELECTOR_TAG):
            raise ValueError(f"Invalid rule code: {self.tag}")
        prefix, number_str = match.groups()
        object.__setattr__(self, "prefix", prefix)
        object.__setattr__(self, "number_str", number_str)
        object.__setattr__(self, "number", int(number_str))

    def __str__(self) -> str:
        """Return the full rule code tag."""
        return self.tag

    def __format__(self, format_spec: str) -> str:
        """Format the full rule code tag."""
        return self.tag.__format__(format_spec)


@dataclasses.dataclass(frozen=True, order=True)
class RuleSelector:
    """Parsed pydocformatter rule selector."""

    tag: str
    prefix: str = dataclasses.field(init=False)
    number_str: str = dataclasses.field(init=False)

    @staticmethod
    def is_valid_tag(tag: str) -> bool:
        """Return whether a string is a valid rule selector tag."""
        return tag == ALL_RULE_SELECTOR_TAG or (_RULE_SELECTOR_RE.fullmatch(tag) is not None and not tag.startswith(ALL_RULE_SELECTOR_TAG))

    def __post_init__(self) -> None:
        """Derive selector parts from the full tag."""
        if self.tag == ALL_RULE_SELECTOR_TAG:
            prefix, number_str = ALL_RULE_SELECTOR_TAG, ""
        else:
            match = _RULE_SELECTOR_RE.fullmatch(self.tag)
            if match is None or self.tag.startswith(ALL_RULE_SELECTOR_TAG):
                raise ValueError(f"Invalid rule selector: {self.tag}")
            prefix, number_str = match.groups()
            if prefix is None or number_str is None:
                raise ValueError(f"Invalid rule selector: {self.tag}")
        object.__setattr__(self, "prefix", prefix)
        object.__setattr__(self, "number_str", number_str)

    def selects_code(self, code: RuleCode) -> bool:
        """Return whether this selector selects a rule code."""
        return self.prefix == ALL_RULE_SELECTOR_TAG or (self.prefix == code.prefix and (not self.number_str or code.number_str.startswith(self.number_str)))

    def __str__(self) -> str:
        """Return the full rule selector tag."""
        return self.tag

    def __format__(self, format_spec: str) -> str:
        """Format the full rule selector tag."""
        return self.tag.__format__(format_spec)


@dataclasses.dataclass(frozen=True, order=True)
class RuleMetadata:
    """Metadata for a pydocformatter rule.

    Attributes:
        code (RuleCode): Rule code.
        name (str): Rule name.
        message (str): Default diagnostic message.
        fix_availability (FixAvailability): Rule-level automatic fix availability.
        stable_since (str): pydocformatter version in which the rule became stable.
    """

    code: RuleCode
    name: str
    message: str
    fix_availability: FixAvailability
    stable_since: str

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


def rule_fix_text(rule: RuleMetadata) -> str:
    """Return user-facing fix availability text for one rule."""
    if rule.fix_availability == FixAvailability.ALWAYS:
        return "Fix is always available."
    elif rule.fix_availability == FixAvailability.SOMETIMES:
        return "Fix is sometimes available."
    elif rule.fix_availability == FixAvailability.NEVER:
        return "Fix is not available."
    else:
        raise AssertionError(f"Unexpected fix availability: {rule.fix_availability}")


class RuleBase:
    """Base class for implemented pydocformatter rules."""

    meta: ClassVar[RuleMetadata]

    code = misc.alias_to_class_field("meta.code.tag")
    prefix = misc.alias_to_class_field("meta.code.prefix")
    number_str = misc.alias_to_class_field("meta.code.number_str")
    number = misc.alias_to_class_field("meta.code.number")
    name = misc.alias_to_class_field("meta.name")
    message = misc.alias_to_class_field("meta.message")
    fix_availability = misc.alias_to_class_field("meta.fix_availability")
    stable_since = misc.alias_to_class_field("meta.stable_since")

    def __init_subclass__(cls) -> None:
        """Require implemented rule classes to define metadata."""
        super().__init_subclass__()
        if "meta" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define RuleMetadata as 'meta'")
        if not isinstance(cls.meta, RuleMetadata):
            raise TypeError(f"{cls.__name__}.meta must be a RuleMetadata instance")
