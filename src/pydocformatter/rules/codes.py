from __future__ import annotations

import dataclasses
import re

_RULE_CODE_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
_RULE_SELECTOR_RE = re.compile(r"^([A-Z]+)([0-9]*)$")
ALL_RULE_SELECTOR_TAG = "ALL"


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
