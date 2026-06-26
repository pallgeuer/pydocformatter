"""Directive comment syntax shared by comment rules and suppression parsing."""

from __future__ import annotations

import re

NOQA_RE = re.compile(r"^noqa(?:\s*:\s*(?P<selectors>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
PYDOCFMT_NOQA_RE = re.compile(r"^pydocfmt\s*:\s*noqa(?:\s*:\s*(?P<selectors>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
PYDOCFMT_BRACKET_RE = re.compile(r"^pydocfmt\s*:\s*(?P<action>ignore|file-ignore|disable|enable)\s*(?P<codes>\[(?P<selectors>[^\]]*)\])(?P<rest>.*)$", re.IGNORECASE)
