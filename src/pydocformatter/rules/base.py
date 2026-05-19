from __future__ import annotations

import dataclasses
import operator
import re
from typing import Any, ClassVar

from pydocformatter.utils.misc import classproperty

RULE_CODE_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
RULE_SELECTOR_RE = re.compile(r"^([A-Z]+)([0-9]*)$")


def rule_code_is_valid(code: str) -> bool:
    """Return whether a string is a valid full rule code."""
    return RULE_CODE_RE.fullmatch(code) is not None


def rule_selector_is_valid(selector: str) -> bool:
    """Return whether a string is a valid rule selector."""
    return RULE_SELECTOR_RE.fullmatch(selector) is not None


def split_rule_code(code: str) -> tuple[str, str]:
    """Return the prefix and number string parts of a full rule code."""
    match = RULE_CODE_RE.fullmatch(code)
    if match is None:
        raise ValueError(f"Invalid rule code: {code}")
    prefix, number_str = match.groups()
    return prefix, number_str


def split_rule_selector(selector: str) -> tuple[str, str]:
    """Return the prefix and number string parts of a rule selector."""
    match = RULE_SELECTOR_RE.fullmatch(selector)
    if match is None:
        raise ValueError(f"Invalid rule selector: {selector}")
    prefix, number_str = match.groups()
    return prefix, number_str


@dataclasses.dataclass(frozen=True, order=True)
class RuleMetadata:
    """Metadata for a pydocformatter rule."""

    code: str
    prefix: str = dataclasses.field(init=False)
    number_str: str = dataclasses.field(init=False)
    number: int = dataclasses.field(init=False)
    name: str
    message: str
    fixable: bool

    def __post_init__(self) -> None:
        """Derive rule selector metadata from the full rule code."""
        prefix, number_str = split_rule_code(self.code)
        object.__setattr__(self, "prefix", prefix)
        object.__setattr__(self, "number_str", number_str)
        object.__setattr__(self, "number", int(number_str))

    def matches_selector(self, selector: str) -> bool:
        """Return whether this rule is matched by a rule selector."""
        try:
            prefix, number_str = split_rule_selector(selector)
        except ValueError:
            return False
        return self.matches_selector_parts(prefix, number_str)

    def matches_selector_parts(self, prefix: str, number_str: str) -> bool:
        """Return whether this rule is matched by selector parts."""
        return prefix == "ALL" or (prefix == self.prefix and (not number_str or self.number_str.startswith(number_str)))


def _alias_meta_field(name: str) -> classproperty[Any]:
    """Create a classproperty that delegates to meta.<name>."""
    return classproperty(operator.attrgetter(f"meta.{name}"))


class RuleBase:
    """Base class for implemented pydocformatter rules."""

    meta: ClassVar[RuleMetadata]

    code = _alias_meta_field("code")
    prefix = _alias_meta_field("prefix")
    number_str = _alias_meta_field("number_str")
    number = _alias_meta_field("number")
    name = _alias_meta_field("name")
    message = _alias_meta_field("message")
    fixable = _alias_meta_field("fixable")
