"""Rule settings audit consistency tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import pathlib

# First-party imports
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter.cli import settings_check


ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "devel" / "rule_settings_audit.md"
REQUIRED_COLUMNS = ("Rule", "Name", "Rule-specific selection effects", "Implementation settings used", "Implicit/helper settings reviewed", "Options settings to document", "Notes")
OPTION_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
OPTION_BULLET_RE = re.compile(r"^- `(?P<setting>[^`]+)`: (?P<description>.+)$")


def test_rule_settings_audit_covers_registered_rules() -> None:
    """Check that every registered rule has exactly one settings-audit row."""
    rows = _audit_rows()
    row_by_code = {row["Rule"]: row for row in rows}
    expected_codes = tuple(rule_class.meta.code.tag for rule_class in rule_collection.RULE_COLLECTION.rules)

    assert len(row_by_code) == len(rows)
    assert tuple(row_by_code) == expected_codes

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        row = row_by_code[rule_class.meta.code.tag]
        assert row["Name"] == rule_class.meta.name


def test_rule_settings_audit_options_match_rule_docs() -> None:
    """Check that audited option settings match parseable rule Options bullets."""
    known_setting_keys = {definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions}
    row_by_code = {row["Rule"]: row for row in _audit_rows()}

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        code = rule_class.meta.code.tag
        audited_options = _audited_options(row_by_code[code])
        options_section = _options_section(rule_class).strip()
        documented_options = _documented_options(code, options_section)
        unknown_options = tuple(option for option in (*audited_options, *documented_options) if option not in known_setting_keys)

        assert not unknown_options, f"{code}: Unknown settings in audit or Options section: {unknown_options}"
        assert documented_options == audited_options
        if not audited_options:
            assert options_section == "None."


def _audit_rows() -> tuple[dict[str, str], ...]:
    """Return rows from the tracked per-rule settings audit table."""
    lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    heading_index = lines.index("## Per-rule settings table")
    table_lines: list[str] = []
    for line in lines[heading_index + 1 :]:
        if not line.startswith("|"):
            if table_lines:
                break
            continue
        table_lines.append(line)
    headers = _split_markdown_row(table_lines[0])
    assert tuple(headers) == REQUIRED_COLUMNS
    return tuple(dict(zip(headers, cells, strict=True)) for cells in (_split_markdown_row(line) for line in table_lines[2:]))


def _split_markdown_row(line: str) -> tuple[str, ...]:
    """Split a simple audit table row into stripped cell text."""
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def _audited_options(row: dict[str, str]) -> tuple[str, ...]:
    """Return setting keys listed in one audit row's Options column."""
    options = row["Options settings to document"]
    if options == "None":
        return ()
    return tuple(OPTION_CODE_SPAN_RE.findall(options))


def _documented_options(rule_code: str, section: str) -> tuple[str, ...]:
    """Return setting keys documented as rule Options bullets."""
    if section == "None.":
        return ()
    keys: list[str] = []
    for line_number, line in enumerate(section.splitlines(), start=1):
        match = OPTION_BULLET_RE.fullmatch(line)
        assert match is not None, f"{rule_code}: malformed Options line {line_number}: {line}"
        keys.append(match.group("setting"))
        assert match.group("description").strip(), f"{rule_code}: empty Options description on line {line_number}"
    documented_options = tuple(keys)
    assert len(set(documented_options)) == len(documented_options), f"{rule_code}: duplicate Options setting bullets"
    return documented_options


def _options_section(rule_class: type[object]) -> str:
    """Return the rule documentation Options section."""
    explanation = rule_documentation.load_rule_explanation(rule_class)
    return explanation.split("## Options", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
