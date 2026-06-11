import pathlib
import unittest

import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.models as rule_models
from pydocformatter.cli.settings_check import DocstringConvention

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAT_RULES_PATH = ROOT / "docs" / "formatting_rules.md"


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


def _ignored_conventions(rule: rule_models.RuleMetadata) -> set[DocstringConvention]:
    """Return docstring conventions that ignore a rule."""
    ignored: set[DocstringConvention] = set()
    for setting_effects in rule.setting_effects:
        if setting_effects.setting != "docstring_convention":
            continue
        for effect_values in setting_effects.effects:
            if effect_values.effect != rule_models.RuleSettingEffect.IGNORED:
                continue
            for value in effect_values.values:
                if not isinstance(value, DocstringConvention):
                    raise AssertionError(f"{rule.code}: Unexpected docstring convention effect value {value!r}")
                ignored.add(value)
    return ignored


def _convention_cell(rule: rule_models.RuleMetadata, convention: DocstringConvention) -> str:
    """Return the formatting rules table cell for one convention."""
    return "Ignored" if convention in _ignored_conventions(rule) else "-"


def _conflicts_cell(rule: rule_models.RuleMetadata) -> str:
    """Return the formatting rules table cell for incompatible rules."""
    return ", ".join(str(code) for code in rule.incompatible_with)


class TestFormattingRulesDoc(unittest.TestCase):
    def test_pydocformatter_rule_tables_match_rule_metadata(self) -> None:
        text = FORMAT_RULES_PATH.read_text(encoding="utf-8")
        rows = _table_rows_after_heading(text, "### pydocformatter comments (PCF)") + _table_rows_after_heading(text, "### pydocformatter docstrings (PDF)")
        row_by_code = {row["Code"]: row for row in rows}
        expected_codes = tuple(str(rule_class.meta.code) for rule_class in rule_collection.RULE_COLLECTION.rules)

        self.assertEqual(tuple(row_by_code), expected_codes)
        for rule_class in rule_collection.RULE_COLLECTION.rules:
            rule = rule_class.meta
            row = row_by_code[str(rule.code)]
            self.assertEqual(row["Name"], rule.name)
            self.assertEqual(row["Message"], rule.message)
            self.assertEqual(row["Fixable"], rule.fix_availability.value)
            self.assertEqual(row["Stable Since"], rule.stable_since)

            if rule.code.prefix == "PDF":
                self.assertEqual(row["None"], _convention_cell(rule, DocstringConvention.NONE))
                self.assertEqual(row["Google"], _convention_cell(rule, DocstringConvention.GOOGLE))
                self.assertEqual(row["NumPy"], _convention_cell(rule, DocstringConvention.NUMPY))
                self.assertEqual(row["PEP257"], _convention_cell(rule, DocstringConvention.PEP257))
                self.assertEqual(row["Conflicts"], _conflicts_cell(rule))


if __name__ == "__main__":
    unittest.main()
