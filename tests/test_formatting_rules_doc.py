# Future imports
from __future__ import annotations

# Standard library imports
import re
import pathlib
import unittest
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.collection as rule_collection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.codes import RuleSelector


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.models as rule_models


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAT_RULES_PATH = ROOT / "docs" / "rule_list.md"


def _table_rows_after_heading(text: str, heading: str) -> list[dict[str, str]]:
    """Return Markdown table rows immediately following a heading."""
    lines = text.splitlines()
    heading_index = lines.index(heading)
    table_lines: list[str] = []
    for line in lines[heading_index + 1 :]:
        if not line.strip():
            if table_lines:
                break
            continue
        if table_lines and not line.startswith("|"):
            break
        if line.startswith("|"):
            table_lines.append(line)

    if len(table_lines) < 2:
        raise AssertionError(f"No Markdown table found after {heading}")

    headers = _split_markdown_row(table_lines[0])
    return [dict(zip(headers, cells, strict=True)) for cells in (_split_markdown_row(line) for line in table_lines[2:])]


def _split_markdown_row(line: str) -> list[str]:
    """Split a simple Markdown table row into stripped cell values."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _convention_effects(rule: rule_models.RuleMetadata) -> dict[DocstringConvention, rule_models.RuleSettingEffect]:
    """Return docstring convention effects for a rule."""
    effects: dict[DocstringConvention, rule_models.RuleSettingEffect] = {}
    for setting_effects in rule.setting_effects:
        if setting_effects.setting != "docstring_convention":
            continue
        for effect_values in setting_effects.effects:
            for value in effect_values.values:
                if not isinstance(value, DocstringConvention):
                    raise TypeError(f"{rule.code}: Unexpected docstring convention effect value {value!r}")
                effects[value] = effect_values.effect
    return effects


def _convention_cell(rule: rule_models.RuleMetadata, convention: DocstringConvention) -> str:
    """Return the formatting rules table cell for one convention."""
    effect = _convention_effects(rule).get(convention)
    return "-" if effect is None else effect.value


def _conflicts_cell(rule: rule_models.RuleMetadata) -> str:
    """Return the formatting rules table cell for incompatible rules."""
    return ", ".join(str(code) for code in rule.incompatible_with)


def _explicit_cell(rule: rule_models.RuleMetadata) -> str:
    """Return the formatting rules table cell for explicit-selection requirements."""
    selectors = tuple(RuleSelector(selector) for selector in CheckSettings().require_explicit)
    return "Opt-in" if any(selector.selects_code(rule.code) for selector in selectors) else "-"


def _codes_for_mapping_label(cell: str, label: str, code_pattern: str) -> list[str]:
    """Return rule codes from semicolon-separated mapping cell clauses."""
    return [code for clause in cell.split(";") if (stripped := clause.strip()).startswith(label) for code in re.findall(code_pattern, stripped)]


class TestFormattingRulesDoc(unittest.TestCase):
    def test_pydocformatter_rule_tables_match_rule_metadata(self) -> None:
        text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
        rows = _table_rows_after_heading(text, "### pydocformatter comments (PCF)") + _table_rows_after_heading(text, "### pydocformatter docstrings (PDF)")
        row_by_code = {row["Code"]: row for row in rows}
        expected_codes = tuple(str(rule_class.meta.code) for rule_class in rule_collection.RULE_COLLECTION.rules)

        assert tuple(row_by_code) == expected_codes
        for rule_class in rule_collection.RULE_COLLECTION.rules:
            rule = rule_class.meta
            row = row_by_code[str(rule.code)]
            assert row["Name"] == rule.name
            assert row["Message"] == rule.message
            assert row["Fixable"] == rule.fix_availability.value
            assert row["Explicit"] == _explicit_cell(rule)
            assert row["Stable Since"] == rule.stable_since

            if rule.code.prefix == "PDF":
                assert row["None"] == _convention_cell(rule, DocstringConvention.NONE)
                assert row["PEP257"] == _convention_cell(rule, DocstringConvention.PEP257)
                assert row["Google"] == _convention_cell(rule, DocstringConvention.GOOGLE)
                assert row["NumPy"] == _convention_cell(rule, DocstringConvention.NUMPY)
                assert row["reST"] == _convention_cell(rule, DocstringConvention.REST)
                assert row["Conflicts"] == _conflicts_cell(rule)

    def test_rule_list_ruff_replacement_mappings_are_bidirectional(self) -> None:
        text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
        pydocformatter_rows = _table_rows_after_heading(text, "### pydocformatter comments (PCF)") + _table_rows_after_heading(text, "### pydocformatter docstrings (PDF)")
        ruff_rows = _table_rows_after_heading(text, "## Ruff Rules")
        disabled_by_ruff_rule: dict[str, list[str]] = {}
        replaced_by_ruff_rule: dict[str, list[str]] = {}

        for row in pydocformatter_rows:
            for ruff_code in _codes_for_mapping_label(row.get("Ruff Rules", ""), "Disable ", r"(?:D|DOC|E|W)\d{3}"):
                disabled_by_ruff_rule.setdefault(ruff_code, []).append(row["Code"])

        for row in ruff_rows:
            replacements = _codes_for_mapping_label(row["Support by pydocformatter"], "Replaced by ", r"P[CD]F\d{3}")
            if replacements:
                replaced_by_ruff_rule[row["Code"]] = replacements

        assert _sorted_mapping_values(disabled_by_ruff_rule) == _sorted_mapping_values(replaced_by_ruff_rule)

    def test_rule_list_ruff_related_mappings_are_bidirectional(self) -> None:
        text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
        pydocformatter_rows = _table_rows_after_heading(text, "### pydocformatter comments (PCF)") + _table_rows_after_heading(text, "### pydocformatter docstrings (PDF)")
        ruff_rows = _table_rows_after_heading(text, "## Ruff Rules")
        related_by_ruff_rule: dict[str, list[str]] = {}
        related_by_pydocformatter_rule: dict[str, list[str]] = {}

        for row in pydocformatter_rows:
            for ruff_code in _codes_for_mapping_label(row.get("Ruff Rules", ""), "Related to ", r"(?:D|DOC|E|W)\d{3}"):
                related_by_ruff_rule.setdefault(ruff_code, []).append(row["Code"])

        for row in ruff_rows:
            related_rules = _codes_for_mapping_label(row["Support by pydocformatter"], "Related to ", r"P[CD]F\d{3}")
            if related_rules:
                related_by_pydocformatter_rule[row["Code"]] = related_rules

        assert _sorted_mapping_values(related_by_ruff_rule) == _sorted_mapping_values(related_by_pydocformatter_rule)


def _sorted_mapping_values(mapping: dict[str, list[str]]) -> dict[str, list[str]]:
    """Return mapping values sorted for order-insensitive code comparisons."""
    return {key: sorted(values) for key, values in mapping.items()}


if __name__ == "__main__":
    unittest.main()
