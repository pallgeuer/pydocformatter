"""Suspicious Unicode classification for docstrings and comments.

Attributes:
    INDENTATION_ONLY_CODE_POINTS (frozenset[int]): Nonbreaking spaces reported only in logical-line indentation.
    EVERYWHERE_CODE_POINTS (frozenset[int]): Explicit controls, separators, bidi controls, and invisible formats
        reported in every position.
    CODE_POINT_LABELS (dict[int, str]): Stable diagnostic labels independent of the runtime Unicode database.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from collections.abc import Iterator


_C0_CONTROL_LABELS = (
    "NULL",
    "START OF HEADING",
    "START OF TEXT",
    "END OF TEXT",
    "END OF TRANSMISSION",
    "ENQUIRY",
    "ACKNOWLEDGE",
    "ALERT",
    "BACKSPACE",
    "CHARACTER TABULATION",
    "LINE FEED",
    "LINE TABULATION",
    "FORM FEED",
    "CARRIAGE RETURN",
    "SHIFT OUT",
    "SHIFT IN",
    "DATA LINK ESCAPE",
    "DEVICE CONTROL ONE",
    "DEVICE CONTROL TWO",
    "DEVICE CONTROL THREE",
    "DEVICE CONTROL FOUR",
    "NEGATIVE ACKNOWLEDGE",
    "SYNCHRONOUS IDLE",
    "END OF TRANSMISSION BLOCK",
    "CANCEL",
    "END OF MEDIUM",
    "SUBSTITUTE",
    "ESCAPE",
    "INFORMATION SEPARATOR FOUR",
    "INFORMATION SEPARATOR THREE",
    "INFORMATION SEPARATOR TWO",
    "INFORMATION SEPARATOR ONE",
)
_C1_CONTROL_LABELS = (
    "PADDING CHARACTER",
    "HIGH OCTET PRESET",
    "BREAK PERMITTED HERE",
    "NO BREAK HERE",
    "INDEX",
    "NEXT LINE",
    "START OF SELECTED AREA",
    "END OF SELECTED AREA",
    "CHARACTER TABULATION SET",
    "CHARACTER TABULATION WITH JUSTIFICATION",
    "LINE TABULATION SET",
    "PARTIAL LINE FORWARD",
    "PARTIAL LINE BACKWARD",
    "REVERSE LINE FEED",
    "SINGLE SHIFT TWO",
    "SINGLE SHIFT THREE",
    "DEVICE CONTROL STRING",
    "PRIVATE USE ONE",
    "PRIVATE USE TWO",
    "SET TRANSMIT STATE",
    "CANCEL CHARACTER",
    "MESSAGE WAITING",
    "START OF GUARDED AREA",
    "END OF GUARDED AREA",
    "START OF STRING",
    "SINGLE GRAPHIC CHARACTER INTRODUCER",
    "SINGLE CHARACTER INTRODUCER",
    "CONTROL SEQUENCE INTRODUCER",
    "STRING TERMINATOR",
    "OPERATING SYSTEM COMMAND",
    "PRIVACY MESSAGE",
    "APPLICATION PROGRAM COMMAND",
)

_CONTROL_AND_SEPARATOR_LABELS = {
    **{code_point: _C0_CONTROL_LABELS[code_point] for code_point in (*range(0x0009), *range(0x000B, 0x0020))},
    0x007F: "DELETE",
    **{code_point: _C1_CONTROL_LABELS[code_point - 0x0080] for code_point in range(0x0080, 0x00A0)},
    0x2028: "LINE SEPARATOR",
    0x2029: "PARAGRAPH SEPARATOR",
}
_INDENTATION_ONLY_LABELS = {0x00A0: "NO-BREAK SPACE", 0x2007: "FIGURE SPACE", 0x202F: "NARROW NO-BREAK SPACE"}
_BIDI_LABELS = {
    0x061C: "ARABIC LETTER MARK",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
    0x202A: "LEFT-TO-RIGHT EMBEDDING",
    0x202B: "RIGHT-TO-LEFT EMBEDDING",
    0x202C: "POP DIRECTIONAL FORMATTING",
    0x202D: "LEFT-TO-RIGHT OVERRIDE",
    0x202E: "RIGHT-TO-LEFT OVERRIDE",
    0x2066: "LEFT-TO-RIGHT ISOLATE",
    0x2067: "RIGHT-TO-LEFT ISOLATE",
    0x2068: "FIRST STRONG ISOLATE",
    0x2069: "POP DIRECTIONAL ISOLATE",
}
_INVISIBLE_FORMAT_LABELS = {
    0x00AD: "SOFT HYPHEN",
    0x180E: "MONGOLIAN VOWEL SEPARATOR",
    0x200B: "ZERO WIDTH SPACE",
    0x2060: "WORD JOINER",
    0x206A: "INHIBIT SYMMETRIC SWAPPING",
    0x206B: "ACTIVATE SYMMETRIC SWAPPING",
    0x206C: "INHIBIT ARABIC FORM SHAPING",
    0x206D: "ACTIVATE ARABIC FORM SHAPING",
    0x206E: "NATIONAL DIGIT SHAPES",
    0x206F: "NOMINAL DIGIT SHAPES",
    0xFEFF: "ZERO WIDTH NO-BREAK SPACE",
}
INDENTATION_ONLY_CODE_POINTS = frozenset(_INDENTATION_ONLY_LABELS)
EVERYWHERE_CODE_POINTS = frozenset({**_CONTROL_AND_SEPARATOR_LABELS, **_BIDI_LABELS, **_INVISIBLE_FORMAT_LABELS})
CODE_POINT_LABELS = {**_CONTROL_AND_SEPARATOR_LABELS, **_INDENTATION_ONLY_LABELS, **_BIDI_LABELS, **_INVISIBLE_FORMAT_LABELS}


@dataclasses.dataclass(frozen=True)
class SuspiciousUnicodeOccurrence:
    """One reportable character in evaluated or literal text.

    Attributes:
        offset (int): Zero-based character offset in the scanned text.
        code_point (int): Unicode scalar value of the character.
        label (str): Stable display name for diagnostics.
        indentation (bool): Whether an indentation-only character occurs in a logical-line prefix.
    """

    offset: int
    code_point: int
    label: str
    indentation: bool

    @property
    def can_fix(self) -> bool:
        """Whether replacing this occurrence with ASCII space is safe.

        Returns:
            bool: Whether the occurrence is a fixable indentation character.
        """
        return self.indentation and self.code_point in INDENTATION_ONLY_CODE_POINTS

    @property
    def code_point_text(self) -> str:
        """Stable uppercase code-point and label display.

        Returns:
            str: Code point and hard-coded diagnostic label.
        """
        return f"U+{self.code_point:04X} {self.label}"


def suspicious_unicode_occurrences(text: str) -> tuple[SuspiciousUnicodeOccurrence, ...]:
    """Return reportable characters from text in source order.

    Args:
        text (str): Evaluated or literal payload to scan.

    Returns:
        tuple[SuspiciousUnicodeOccurrence, ...]: Classified occurrences in input order.
    """
    return tuple(_suspicious_unicode_occurrences(text))


def _suspicious_unicode_occurrences(text: str) -> Iterator[SuspiciousUnicodeOccurrence]:
    """Yield reportable characters from text in source order."""
    in_indentation = True
    for offset, char in enumerate(text):
        code_point = ord(char)
        indentation = in_indentation and code_point in INDENTATION_ONLY_CODE_POINTS
        if code_point in EVERYWHERE_CODE_POINTS or indentation:
            yield SuspiciousUnicodeOccurrence(offset=offset, code_point=code_point, label=CODE_POINT_LABELS[code_point], indentation=indentation)
        if char in "\r\n":
            in_indentation = True
        elif in_indentation and not char.isspace():
            in_indentation = False


def is_nonbreaking_space(char: str) -> bool:
    """Return whether char is an accepted nonbreaking prose space.

    Args:
        char (str): Candidate single character.

    Returns:
        bool: Whether the character has nonbreaking prose semantics.
    """
    return len(char) == 1 and ord(char) in INDENTATION_ONLY_CODE_POINTS


def is_layout_separator(char: str) -> bool:
    """Return whether char separates wrapping tokens.

    Args:
        char (str): Candidate single character.

    Returns:
        bool: Whether wrapping may split and normalize at the character.
    """
    return char.isspace() and ord(char) not in EVERYWHERE_CODE_POINTS and not is_nonbreaking_space(char)
