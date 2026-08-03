"""reStructuredText directive introducer recognition."""

# Future imports
from __future__ import annotations

# Standard library imports
import re


_DIRECTIVE_NAME_PATTERN = r"(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*"
_DIRECTIVE_RE = re.compile(rf"^(?P<indent>[ \t]*)\.\.[ \t]+(?P<name>{_DIRECTIVE_NAME_PATTERN})[ ]?::(?=[ \t]|$)(?P<argument>.*)$")
_MALFORMED_DIRECTIVE_RE = re.compile(rf"^(?P<indent>[ \t]*)\.\.[ \t]+(?P<name>{_DIRECTIVE_NAME_PATTERN})[ ]?:(?=[ \t]|$)(?P<argument>.*)$")


def directive_match(text: str) -> re.Match[str] | None:
    """Match a complete reStructuredText directive opener.

    Args:
        text (str): Logical line to inspect.

    Returns:
        Match data for a valid opener, or `None`.
    """
    return _DIRECTIVE_RE.match(text)


def malformed_directive_match(text: str) -> re.Match[str] | None:
    """Match a directive opener with exactly one trailing colon.

    Args:
        text (str): Logical line to inspect.

    Returns:
        Match data for a malformed opener, or `None`.
    """
    return _MALFORMED_DIRECTIVE_RE.match(text)
