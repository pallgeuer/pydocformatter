"""Directive comment syntax shared by comment rules and suppression parsing.

Attributes:
    NOQA_RE (re.Pattern[str]): Generic `noqa` parser that keeps selector payloads and trailing rationale comments
        separate.
    PYDOCFMT_NOQA_RE (re.Pattern[str]): Pydocfmt line-suppression parser for optional rule selectors and preserved
        rationale text.
    PYDOCFMT_BRACKET_RE (re.Pattern[str]): Pydocfmt bracket-directive parser used by normalization and suppression
        handling.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re


NOQA_RE = re.compile(r"^noqa(?:\s*:\s*(?P<selectors>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
PYDOCFMT_NOQA_RE = re.compile(r"^pydocfmt\s*:\s*noqa(?:\s*:\s*(?P<selectors>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
PYDOCFMT_BRACKET_RE = re.compile(r"^pydocfmt\s*:\s*(?P<action>ignore|file-ignore|disable|enable)\s*(?P<codes>\[(?P<selectors>[^\]]*)\])(?P<rest>.*)$", re.IGNORECASE)
