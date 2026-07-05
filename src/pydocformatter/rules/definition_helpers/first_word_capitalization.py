"""First-word capitalization safety checks."""

from __future__ import annotations


def should_capitalize(word: str) -> bool:
    """Return whether a first word can be safely capitalized.

    Args:
        word (str): First word selected from summary or entry-description text.

    Returns:
        Whether the word is lowercase ASCII prose whose first character can be uppercased safely.
    """
    trimmed = word.rstrip(".!?")
    if not trimmed or trimmed == trimmed.upper():
        return False
    first = trimmed[0]
    if not first.isascii() or not first.isalpha() or not first.islower():
        return False
    return all(char.isascii() and (char.islower() or char == "'") for char in trimmed[1:])
