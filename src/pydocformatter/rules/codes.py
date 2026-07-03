"""Rule code and selector parsing.

Attributes:
    ALL_RULE_SELECTOR_TAG (str): Reserved selector spelling that expands to every registered rule without being a valid
        concrete rule code.
"""

from __future__ import annotations

import dataclasses
import re

_RULE_CODE_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
_RULE_SELECTOR_RE = re.compile(r"^([A-Z]+)([0-9]*)$")
ALL_RULE_SELECTOR_TAG = "ALL"


@dataclasses.dataclass(frozen=True, order=True)
class RuleCode:
    """Parsed pydocformatter rule code.

    Attributes:
        tag (str): Full rule code such as `PDF101`.
        prefix (str): Alphabetic rule category prefix parsed from `tag`.
        number_str (str): Numeric rule suffix preserved with any leading zeros.
        number (int): Integer value of the numeric rule suffix.
    """

    tag: str
    prefix: str = dataclasses.field(init=False)
    number_str: str = dataclasses.field(init=False)
    number: int = dataclasses.field(init=False)

    @staticmethod
    def is_valid_tag(tag: str) -> bool:
        """Return whether a string is a valid rule code tag.

        Args:
            tag (str): Candidate concrete rule code such as `PDF101`.

        Returns:
            bool: Whether the tag has a prefix and numeric suffix and is not the reserved `ALL` selector.
        """
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
    """Parsed pydocformatter rule selector.

    Attributes:
        tag (str): Selector text such as `PDF`, `PDF10`, `PDF101`, or `ALL`.
        prefix (str): Alphabetic selector prefix, or `ALL`.
        number_str (str): Optional numeric selector prefix matched against rule-code numbers.
    """

    tag: str
    prefix: str = dataclasses.field(init=False)
    number_str: str = dataclasses.field(init=False)

    @staticmethod
    def is_valid_tag(tag: str) -> bool:
        """Return whether a string is a valid rule selector tag.

        Args:
            tag (str): Candidate selector such as `PDF`, `PDF10`, `PDF101`, or `ALL`.

        Returns:
            bool: Whether the tag can be parsed as a broad or exact rule selector.
        """
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
        """Return whether this selector selects a rule code.

        Args:
            code (RuleCode): Concrete rule code to compare against this selector.

        Returns:
            bool: Whether the selector covers the rule code by `ALL`, category prefix, numeric prefix, or exact match.
        """
        return self.prefix == ALL_RULE_SELECTOR_TAG or (self.prefix == code.prefix and (not self.number_str or code.number_str.startswith(self.number_str)))

    def __str__(self) -> str:
        """Return the full rule selector tag."""
        return self.tag

    def __format__(self, format_spec: str) -> str:
        """Format the full rule selector tag."""
        return self.tag.__format__(format_spec)
