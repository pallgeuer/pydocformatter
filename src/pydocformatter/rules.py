import re

ALL_RULE_CODE = "ALL"

# TODO: In future, the rule codes and prefixes should be automatically collected from the available defined rules in
#       code (e.g. collected via decorator)
RULE_CODES = frozenset(
    {
        "PDF001",
        "PDF002",
        "PDF003",
        "PDF004",
        "PDF005",
        "PDF006",
        "PDF100",
        "PDF101",
        "PDF102",
        "PDF103",
        "PDF104",
        "PDF105",
        "PDF106",
        "PCF001",
        "PCF002",
    }
)
RULE_PREFIXES = frozenset({"PDF", "PCF"})

_SELECTOR_RE = re.compile(r"^([A-Z]+)([0-9]*)$")


def selector_matches_known_rule(selector: str) -> bool:
    """Return whether a selector matches a known rule.

    Args:
        selector (str): Rule selector to validate, such as `ALL`, `PDF`, or `PDF001`.

    Returns:
        bool: True if the selector targets the full rule set, a known rule prefix, or at least one known concrete rule.
    """
    if selector == ALL_RULE_CODE:
        return True

    match = _SELECTOR_RE.fullmatch(selector)
    if match is None:
        return False

    prefix, digits = match.groups()
    if prefix not in RULE_PREFIXES:
        return False

    if not digits:
        return True

    return any(code.startswith(selector) for code in RULE_CODES)
