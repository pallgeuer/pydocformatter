from __future__ import annotations

import dataclasses
import enum
import re

_RULE_CODE_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
_RULE_PREFIX_RE = re.compile(r"^[A-Z]+$")
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
    url: str | None = None

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
        elif self.rule.fix_availability == FixAvailability.SOMETIMES:
            raise ValueError(f"{self.rule.code}: Findings for sometimes-fixable rules must specify instance_fixable")
        else:
            raise AssertionError(f"Unexpected fix availability: {self.rule.fix_availability}")

    @property
    def grouping_key(self) -> RuleFinding.Key:
        """Return the key used to merge findings that differ only by line numbers."""
        return RuleFinding.Key(rule=self.rule, message=self.message, fixable=self.fixable)

    def with_line_numbers(self, line_numbers: tuple[int, ...]) -> RuleFinding:
        """Return this finding with updated line numbers."""
        return dataclasses.replace(self, line_numbers=line_numbers)
