import re

from pydocformatter.types import ToolName

ALL_RULE_CODE = "ALL"

RULE_CODES = frozenset(
    {
        "RD200",
        "RD205",
        "RD207",
        "RD208",
        "PDF000",
        "PDF001",
        "PCF001",
        "PCF002",
    }
)
RULE_PREFIX_TO_TOOL: dict[str, ToolName] = {
    "RD": "pydocfmt",
    "PDF": "pydocfmt",
    "PCF": "pycommentfmt",
}

_SELECTOR_RE = re.compile(r"^([A-Z]+)([0-9]*)$")


def selector_matches_known_rule(selector: str, *, tool_name: ToolName | None) -> bool:
    """Return whether a selector matches a known rule in the requested scope."""
    if selector == ALL_RULE_CODE:
        return True

    match = _SELECTOR_RE.fullmatch(selector)
    if match is None:
        return False

    prefix, digits = match.groups()
    owner_tool = RULE_PREFIX_TO_TOOL.get(prefix)
    if owner_tool is None or (tool_name is not None and owner_tool != tool_name):
        return False

    if not digits:
        return True

    return any(code.startswith(selector) for code in RULE_CODES)
