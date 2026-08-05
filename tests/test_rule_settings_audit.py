"""Rule settings audit consistency tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import ast
import enum
import inspect
import pathlib

# First-party imports
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definition as rule_definition
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter.cli import settings_check
from tests import markdown_table_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "devel" / "rule_settings_audit.md"
REQUIRED_COLUMNS = ("Rule", "Name", "Rule-specific selection effects", "Implementation settings used", "Implicit/helper settings reviewed", "Options settings to document", "Notes")
SHARED_BUNDLE_COLUMNS = ("Bundle", "Settings", "Implementation path")
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


def test_rule_settings_audit_selection_effects_match_metadata() -> None:
    """Check that audited selection effects exactly match rule metadata."""
    row_by_code = {row["Rule"]: row for row in _audit_rows()}

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        code = rule_class.meta.code.tag
        assert row_by_code[code]["Rule-specific selection effects"] == _setting_effects_text(rule_class)


def test_rule_settings_audit_covers_direct_rule_settings() -> None:
    """Check that each rule's direct setting reads appear in its implementation audit."""
    known_setting_fields = {definition.field for definition in settings_check.SETTINGS_SCHEMA.definitions}
    shared_bundles = _shared_setting_bundles()
    row_by_code = {row["Rule"]: row for row in _audit_rows()}

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        code = rule_class.meta.code.tag
        source_path_text = inspect.getsourcefile(rule_class)
        assert source_path_text is not None
        syntax_tree = ast.parse(pathlib.Path(source_path_text).read_text(encoding="utf-8"))
        direct_setting_fields = {node.attr for node in ast.walk(syntax_tree) if isinstance(node, ast.Attribute) and node.attr in known_setting_fields}
        audited_setting_fields: set[str] = set()
        implementation_tokens = OPTION_CODE_SPAN_RE.findall(row_by_code[code]["Implementation settings used"])
        unknown_tokens = tuple(token for token in implementation_tokens if token not in shared_bundles and token not in known_setting_fields)
        for token in implementation_tokens:
            audited_setting_fields.update(shared_bundles.get(token, (token,)))
        missing_fields = direct_setting_fields - audited_setting_fields

        assert not unknown_tokens, f"{code}: Unknown fields or bundles in implementation audit: {unknown_tokens}"
        assert not missing_fields, f"{code}: Direct setting reads missing from implementation audit: {sorted(missing_fields)}"


def _audit_rows() -> tuple[dict[str, str], ...]:
    """Return rows from the tracked per-rule settings audit table."""
    text = AUDIT_PATH.read_text(encoding="utf-8")
    label = AUDIT_PATH.as_posix()
    table = markdown_table_helpers.table_after_heading(text, "## Per-rule settings table", label=label, expected_leading_lines=None)
    assert markdown_table_helpers.table_headers(table, label=label) == REQUIRED_COLUMNS
    return markdown_table_helpers.table_rows(table, label=label)


def _shared_setting_bundles() -> dict[str, tuple[str, ...]]:
    """Return setting fields grouped by the tracked shared bundle names."""
    text = AUDIT_PATH.read_text(encoding="utf-8")
    label = AUDIT_PATH.as_posix()
    table = markdown_table_helpers.table_after_heading(text, "## Shared setting bundles", label=label)
    rows = markdown_table_helpers.table_rows(table, label=label)
    return {row["Bundle"].strip("`"): tuple(OPTION_CODE_SPAN_RE.findall(row["Settings"])) for row in rows}


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


def _setting_effects_text(rule_class: type[rule_definition.RuleBase]) -> str:
    """Return the canonical audit text for one rule's metadata setting effects."""
    effects: list[str] = []
    for setting_effects in rule_class.meta.setting_effects:
        for effect_values in setting_effects.effects:
            values = ", ".join(f"`{_setting_effect_value_text(value)}`" for value in effect_values.values)
            effects.append(f"`{setting_effects.setting}` {effect_values.effect.value.lower()} for {values}")
    return "; ".join(effects) if effects else "None"


def _setting_effect_value_text(value: object) -> str:
    """Return a stable display value for one metadata setting-effect trigger."""
    return str(value.value) if isinstance(value, enum.Enum) else str(value)


def _options_section(rule_class: type[object]) -> str:
    """Return the rule documentation Options section."""
    explanation = rule_documentation.load_rule_explanation(rule_class)
    return explanation.split("## Options", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
