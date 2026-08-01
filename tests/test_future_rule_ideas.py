"""Future-rule audit consistency tests."""

# Standard library imports
import re
import pathlib
import collections

# Third-party imports
import pytest

# First-party imports
import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.models import FixAvailability


ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "devel" / "future_rule_ideas.md"
RANGE_SEPARATOR = "\N{EN DASH}"
FIX_ABBREVIATIONS = {FixAvailability.ALWAYS: "A", FixAvailability.USUALLY: "U", FixAvailability.SOMETIMES: "S", FixAvailability.NEVER: "N"}


def test_current_coverage_audit_matches_registered_rule_fix_availability() -> None:
    """Require every registered rule to have one accurate fix classification."""
    audited = tuple((code, fix) for group, fix in _audit_fix_rows() for code in _expand_rule_group(group))
    counts = collections.Counter(code for code, _ in audited)
    expected = {rule_class.meta.code.tag: FIX_ABBREVIATIONS[rule_class.meta.fix_availability] for rule_class in rule_collection.RULE_COLLECTION.rules}

    assert not tuple(code for code, count in counts.items() if count != 1)
    assert set(counts) == set(expected)
    assert dict(audited) == expected


def test_current_coverage_summary_matches_registered_rule_counts() -> None:
    """Keep total, category, and fix-availability counts synchronized with metadata."""
    text = AUDIT_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"There are currently (?P<total>\d+) rules: (?P<pcf>\d+) PCF and (?P<pdf>\d+) PDF\. Fix availability is (?P<always>\d+) always, (?P<usually>\d+) usually, (?P<sometimes>\d+) sometimes, and (?P<never>\d+) never\.",
        text,
    )
    assert match is not None
    rules = rule_collection.RULE_COLLECTION.rules
    expected = {
        "total": len(rules),
        "pcf": sum(rule_class.meta.code.prefix == "PCF" for rule_class in rules),
        "pdf": sum(rule_class.meta.code.prefix == "PDF" for rule_class in rules),
        "always": sum(rule_class.meta.fix_availability is FixAvailability.ALWAYS for rule_class in rules),
        "usually": sum(rule_class.meta.fix_availability is FixAvailability.USUALLY for rule_class in rules),
        "sometimes": sum(rule_class.meta.fix_availability is FixAvailability.SOMETIMES for rule_class in rules),
        "never": sum(rule_class.meta.fix_availability is FixAvailability.NEVER for rule_class in rules),
    }

    assert {name: int(value) for name, value in match.groupdict().items()} == expected


@pytest.mark.parametrize(
    ("group", "expected"), [("PDF001", ("PDF001",)), (f"PDF102{RANGE_SEPARATOR}105", ("PDF102", "PDF103", "PDF104", "PDF105")), ("PDF306/307/312", ("PDF306", "PDF307", "PDF312"))]
)
def test_expand_rule_group(group: str, expected: tuple[str, ...]) -> None:
    """Expand every compact rule-code notation used by the audit."""
    assert _expand_rule_group(group) == expected


def _audit_fix_rows() -> tuple[tuple[str, str], ...]:
    """Return rule groups and fix abbreviations from the current-coverage tables."""
    text = AUDIT_PATH.read_text(encoding="utf-8")
    current_coverage = text.split("## Current coverage audit", 1)[1].split("## Proposed additions and extensions", 1)[0]
    rows: list[tuple[str, str]] = []
    for line in current_coverage.splitlines():
        if not line.startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if len(cells) == 3 and cells[0] not in {"Rule", "Rules"} and cells[2] in FIX_ABBREVIATIONS.values():
            rows.append((cells[0], cells[2]))
    return tuple(rows)


def _expand_rule_group(group: str) -> tuple[str, ...]:
    """Expand one audit code, slash group, or inclusive range."""
    match = re.fullmatch(r"(?P<prefix>[A-Z]+)(?P<body>\d+(?:(?:/|" + RANGE_SEPARATOR + r")\d+)*)", group)
    if match is None:
        raise ValueError(f"Invalid audit rule group: {group}")
    prefix = match.group("prefix")
    codes: list[str] = []
    for part in match.group("body").split("/"):
        start_text, separator, end_text = part.partition(RANGE_SEPARATOR)
        if not separator:
            codes.append(f"{prefix}{start_text}")
            continue
        width = len(start_text)
        codes.extend(f"{prefix}{number:0{width}d}" for number in range(int(start_text), int(end_text) + 1))
    return tuple(codes)
