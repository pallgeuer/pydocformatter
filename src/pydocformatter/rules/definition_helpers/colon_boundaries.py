"""Colon-ended prose boundary helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import re


_LABEL_LIKE_COLON_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*:$")


def is_colon_header_text(text: str, *, require_unindented: bool = False) -> bool:
    """Return whether text is a non-empty colon-ended boundary line.

    Args:
        text (str): Logical line content to classify.
        require_unindented (bool): Whether indented text should be excluded from colon-header classification.

    Returns:
        Whether the text should act as a colon-ended structure boundary.
    """
    stripped = text.strip()
    if not stripped or not text.rstrip().endswith(":"):
        return False
    return not require_unindented or not text[:1].isspace()


def allows_colon_continuation(previous_text: str, current_text: str) -> bool:
    """Return whether a colon-ended line may continue the previous prose line.

    Args:
        previous_text (str): Previous logical line content in the candidate prose region.
        current_text (str): Current logical line content ending with a colon.

    Returns:
        Whether current text can be joined to previous text as one prose continuation.
    """
    stripped_previous = _strip_closing_punctuation(previous_text.rstrip())
    stripped_current = current_text.strip()
    if not stripped_previous or stripped_previous.endswith((".", "?", "!")):
        return False
    if not is_colon_header_text(current_text) or not stripped_current:
        return False
    return not stripped_current[0].isupper() and not _LABEL_LIKE_COLON_RE.match(stripped_current)


def _strip_closing_punctuation(text: str) -> str:
    """Return text without trailing quote or closing bracket characters."""
    while text and text[-1] in "\"'`)]}":
        text = text[:-1].rstrip()
    return text
