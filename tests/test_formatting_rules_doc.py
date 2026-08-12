# Future imports
from __future__ import annotations

# Standard library imports
import re
import pathlib
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import pydocformatter.rules.collection as rule_collection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.codes import RuleSelector
from tests import markdown_table_helpers


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.models as rule_models


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAT_RULES_PATH = ROOT / "docs" / "public" / "ruff_rule_links.md"
EXPECTED_PCF_HEADERS = ("Code", "Name", "Message", "Fixable", "Require explicit", "Since", "Ruff rules")
EXPECTED_PDF_HEADERS = ("Code", "Name", "Message", "Fixable", "Require explicit", "Convention effects", "Since", "Conflicts", "Ruff rules")
EXPECTED_RUFF_HEADERS = ("Code", "Name", "Message", "Fixable", "Since", "Support by pydocformatter")
PCF_HEADING = "### PCF: pydocformatter comment formatting"
PDF_HEADING = "### PDF: pydocformatter docstring formatting"
RUFF_HEADING = "## Ruff rules"
RULE_TABLE_WRAPPER = '<div class="pydocformatter-rule-table-wrapper" markdown="1">'
PDF_RULE_TABLE_WRAPPER = '<div class="pydocformatter-rule-table-wrapper pydocformatter-pdf-rule-table-wrapper" markdown="1">'
CONVENTION_NAMES = {DocstringConvention.NONE: "None", DocstringConvention.PEP257: "PEP257", DocstringConvention.GOOGLE: "Google", DocstringConvention.NUMPY: "NumPy", DocstringConvention.REST: "reST"}
PYDOCFORMATTER_MAPPING_LABELS = ("Disable", "Related to")
RUFF_MAPPING_LABELS = ("Replaced by", "Related to")
PYDOCFORMATTER_CODE_PATTERN = r"P[CD]F\d{3}"
RUFF_CODE_PATTERN = r"[A-Z]+\d{3,4}"


def _table_rows_after_heading(text: str, heading: str, headers: tuple[str, ...]) -> list[dict[str, str]]:
    """Return Markdown table rows owned by the expected heading."""
    wrapper = PDF_RULE_TABLE_WRAPPER if heading == PDF_HEADING else RULE_TABLE_WRAPPER
    table = markdown_table_helpers.table_after_heading(text, heading, label=FORMAT_RULES_PATH.as_posix(), expected_leading_lines=(wrapper,))
    assert markdown_table_helpers.table_headers(table, label=FORMAT_RULES_PATH.as_posix()) == headers
    rows = list(markdown_table_helpers.table_rows(table, label=FORMAT_RULES_PATH.as_posix()))
    for row in rows:
        if "Code" in row:
            row["Code"] = _plain_code_cell(row["Code"])
    return rows


def _plain_code_cell(cell: str) -> str:
    """Return the visible rule code from a linked or code-formatted table cell."""
    match = re.fullmatch(r"\[`([^`]+)`\]\([^)]+\)", cell)
    if match:
        code = match.group(1)
        assert isinstance(code, str)
        return code
    return cell.strip("`")


def _convention_effects(rule: rule_models.RuleMetadata) -> dict[DocstringConvention, rule_models.RuleSettingEffect]:
    """Return docstring convention effects for a rule."""
    return {convention: effect for convention in DocstringConvention if (effect := rule.setting_effect("docstring_convention", convention)) is not None}


def _convention_effects_cell(rule: rule_models.RuleMetadata) -> str:
    """Return the formatting rules table cell for convention effects."""
    effects = _convention_effects(rule)
    disabled = [CONVENTION_NAMES[convention] for convention in DocstringConvention if effects.get(convention) and effects[convention].value == "Disabled"]
    ignored = [CONVENTION_NAMES[convention] for convention in DocstringConvention if effects.get(convention) and effects[convention].value == "Ignored"]
    parts = []
    if disabled:
        parts.append(f"Disabled: {', '.join(disabled)}")
    if ignored:
        parts.append(f"Ignored: {', '.join(ignored)}")
    return "; ".join(parts) or "-"


def _conflicts_cell(rule: rule_models.RuleMetadata) -> str:
    """Return the formatting rules table cell for incompatible rules."""
    return ", ".join(str(code) for code in rule.incompatible_with) or "-"


def _explicit_cell(rule: rule_models.RuleMetadata) -> str:
    """Return the formatting rules table cell for explicit-selection requirements."""
    selectors = tuple(RuleSelector(selector) for selector in CheckSettings().require_explicit)
    return "Opt-in" if any(selector.selects_code(rule.code) for selector in selectors) else "-"


def _mapping_codes(cell: str, *, labels: tuple[str, ...], code_pattern: str) -> dict[str, list[str]]:
    """Return codes from canonical mapping clauses, rejecting unrecognized text."""
    if cell == "-":
        return {}
    clause_pattern = re.compile(rf"(?P<label>{'|'.join(re.escape(label) for label in labels)}) (?P<codes>{code_pattern}(?:, {code_pattern})*)")
    mappings: dict[str, list[str]] = {}
    for clause in cell.split(";"):
        stripped = clause.strip()
        match = clause_pattern.fullmatch(stripped)
        assert match is not None, f"Unexpected Ruff mapping clause: {stripped!r}"
        label = match.group("label")
        assert label not in mappings, f"Repeated Ruff mapping label: {label!r}"
        codes = re.findall(code_pattern, match.group("codes"))
        assert len(codes) == len(set(codes)), f"Repeated Ruff mapping code in clause: {stripped!r}"
        mappings[label] = codes
    return mappings


@pytest.mark.parametrize(
    "cell", ["Related RUF023", "related PDF527", "Related to RUF023 PLE0237", "Related to RUF023, PLE0237 trailing", "Related to RUF023; Related to PLE0237", "Related to RUF023, RUF023"]
)
def test_ruff_mapping_parser_rejects_noncanonical_clauses(cell: str) -> None:
    with pytest.raises(AssertionError):
        _mapping_codes(cell, labels=PYDOCFORMATTER_MAPPING_LABELS, code_pattern=RUFF_CODE_PATTERN)


def test_rule_list_table_headers_are_sentence_case() -> None:
    """Rule-list table headers must keep sentence-case wording."""
    text = FORMAT_RULES_PATH.read_text(encoding="utf-8")

    for heading, headers in ((PCF_HEADING, EXPECTED_PCF_HEADERS), (PDF_HEADING, EXPECTED_PDF_HEADERS), (RUFF_HEADING, EXPECTED_RUFF_HEADERS)):
        wrapper = PDF_RULE_TABLE_WRAPPER if heading == PDF_HEADING else RULE_TABLE_WRAPPER
        table = markdown_table_helpers.table_after_heading(text, heading, label=FORMAT_RULES_PATH.as_posix(), expected_leading_lines=(wrapper,))
        assert markdown_table_helpers.table_headers(table, label=FORMAT_RULES_PATH.as_posix()) == headers


def test_pydocformatter_rule_tables_match_rule_metadata() -> None:
    text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
    rows = _table_rows_after_heading(text, PCF_HEADING, EXPECTED_PCF_HEADERS) + _table_rows_after_heading(text, PDF_HEADING, EXPECTED_PDF_HEADERS)
    row_by_code = {row["Code"]: row for row in rows}
    expected_codes = tuple(str(rule_class.meta.code) for rule_class in rule_collection.RULE_COLLECTION.rules)

    assert tuple(row_by_code) == expected_codes
    for rule_class in rule_collection.RULE_COLLECTION.rules:
        rule = rule_class.meta
        row = row_by_code[str(rule.code)]
        assert row["Name"] == rule.name
        assert row["Message"] == rule.message
        assert row["Fixable"] == rule.fix_availability.value
        assert row["Require explicit"] == _explicit_cell(rule)
        assert row["Since"] == rule.stable_since

        if rule.code.prefix == "PDF":
            assert row["Convention effects"] == _convention_effects_cell(rule)
            assert row["Conflicts"] == _conflicts_cell(rule)


def test_rule_list_ruff_mapping_clauses_are_canonical_and_reference_known_codes() -> None:
    text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
    pydocformatter_rows = _table_rows_after_heading(text, PCF_HEADING, EXPECTED_PCF_HEADERS) + _table_rows_after_heading(text, PDF_HEADING, EXPECTED_PDF_HEADERS)
    ruff_rows = _table_rows_after_heading(text, RUFF_HEADING, EXPECTED_RUFF_HEADERS)
    pydocformatter_codes = {row["Code"] for row in pydocformatter_rows}
    ruff_codes = {row["Code"] for row in ruff_rows}

    for row in pydocformatter_rows:
        mappings = _mapping_codes(row.get("Ruff rules", "-"), labels=PYDOCFORMATTER_MAPPING_LABELS, code_pattern=RUFF_CODE_PATTERN)
        assert {code for codes in mappings.values() for code in codes} <= ruff_codes
    for row in ruff_rows:
        mappings = _mapping_codes(row["Support by pydocformatter"], labels=RUFF_MAPPING_LABELS, code_pattern=PYDOCFORMATTER_CODE_PATTERN)
        assert {code for codes in mappings.values() for code in codes} <= pydocformatter_codes


def test_rule_list_ruff_replacement_mappings_are_bidirectional() -> None:
    text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
    pydocformatter_rows = _table_rows_after_heading(text, PCF_HEADING, EXPECTED_PCF_HEADERS) + _table_rows_after_heading(text, PDF_HEADING, EXPECTED_PDF_HEADERS)
    ruff_rows = _table_rows_after_heading(text, RUFF_HEADING, EXPECTED_RUFF_HEADERS)
    disabled_by_ruff_rule: dict[str, list[str]] = {}
    replaced_by_ruff_rule: dict[str, list[str]] = {}

    for row in pydocformatter_rows:
        mappings = _mapping_codes(row.get("Ruff rules", "-"), labels=PYDOCFORMATTER_MAPPING_LABELS, code_pattern=RUFF_CODE_PATTERN)
        for ruff_code in mappings.get("Disable", ()):
            disabled_by_ruff_rule.setdefault(ruff_code, []).append(row["Code"])

    for row in ruff_rows:
        replacements = _mapping_codes(row["Support by pydocformatter"], labels=RUFF_MAPPING_LABELS, code_pattern=PYDOCFORMATTER_CODE_PATTERN).get("Replaced by", ())
        if replacements:
            replaced_by_ruff_rule[row["Code"]] = replacements

    assert _sorted_mapping_values(disabled_by_ruff_rule) == _sorted_mapping_values(replaced_by_ruff_rule)


def test_rule_list_ruff_related_mappings_are_bidirectional() -> None:
    text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
    pydocformatter_rows = _table_rows_after_heading(text, PCF_HEADING, EXPECTED_PCF_HEADERS) + _table_rows_after_heading(text, PDF_HEADING, EXPECTED_PDF_HEADERS)
    ruff_rows = _table_rows_after_heading(text, RUFF_HEADING, EXPECTED_RUFF_HEADERS)
    related_by_ruff_rule: dict[str, list[str]] = {}
    related_by_pydocformatter_rule: dict[str, list[str]] = {}

    for row in pydocformatter_rows:
        mappings = _mapping_codes(row.get("Ruff rules", "-"), labels=PYDOCFORMATTER_MAPPING_LABELS, code_pattern=RUFF_CODE_PATTERN)
        for ruff_code in mappings.get("Related to", ()):
            related_by_ruff_rule.setdefault(ruff_code, []).append(row["Code"])

    for row in ruff_rows:
        related_rules = _mapping_codes(row["Support by pydocformatter"], labels=RUFF_MAPPING_LABELS, code_pattern=PYDOCFORMATTER_CODE_PATTERN).get("Related to", ())
        if related_rules:
            related_by_pydocformatter_rule[row["Code"]] = related_rules

    assert _sorted_mapping_values(related_by_ruff_rule) == _sorted_mapping_values(related_by_pydocformatter_rule)


def _sorted_mapping_values(mapping: dict[str, list[str]]) -> dict[str, list[str]]:
    """Return mapping values sorted for order-insensitive code comparisons."""
    return {key: sorted(values) for key, values in mapping.items()}
