# Standard library imports
import re
import enum
import json
import pathlib
import itertools

# Third-party imports
import pytest

# First-party imports
import pydocformatter.settings as settings_core
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter.cli.settings_check import SETTINGS_SCHEMA, CheckSettings
from pydocformatter.rules.definitions.PCF.PCF import CommentKind, CommentPlacement
from pydocformatter.rules.definitions.PDF.PDF import DefinitionKind, DocstringKind
from tests import markdown_table_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]
_CODE_RANGE_RE = re.compile(r"^(?P<prefix>[A-Z]+)(?:(?P<hundreds>\d)xx|(?P<start>\d{3})-(?P=prefix)(?P<end>\d{3}))$")
CODE_RANGE_HEADERS = ("Range", "Topic", "Notes")
OPTIONS_HEADERS = ("Setting", "Default", "Effect")


def _options_table_rows(path: pathlib.Path) -> list[dict[str, str]]:
    """Return rows from a category documentation options table."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    section_lines = _section_lines(lines, "Options")
    if section_lines == ["None."]:
        return []
    table = markdown_table_helpers.table_after_heading(text, "## Options", label=path.as_posix(), expected_leading_lines=None)
    assert markdown_table_helpers.table_headers(table, label=path.as_posix()) == OPTIONS_HEADERS
    return list(markdown_table_helpers.table_rows(table, label=path.as_posix()))


def _section_lines(lines: list[str], heading: str) -> list[str]:
    """Return non-empty lines in a level-two Markdown section."""
    heading_index = lines.index(f"## {heading}")
    section_lines: list[str] = []
    for line in lines[heading_index + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            section_lines.append(line)
    return section_lines


def _category_documentation_paths() -> tuple[pathlib.Path, ...]:
    """Return built-in rule category documentation paths."""
    return tuple(
        ROOT / "src" / "pydocformatter" / "rules" / "definitions" / category_class.meta.prefix / f"{category_class.meta.prefix}.md" for category_class in rule_collection.RULE_COLLECTION.categories
    )


@pytest.mark.parametrize("enum_type", [DefinitionKind, DocstringKind, CommentPlacement, CommentKind], ids=lambda enum_type: enum_type.__name__)
def test_internal_classification_enums_require_explicit_string_conversion(enum_type: type[enum.Enum]) -> None:
    member = next(iter(enum_type))
    assert issubclass(enum_type, enum.Enum)
    assert not issubclass(enum_type, enum.StrEnum)
    assert member != member.value
    with pytest.raises(TypeError):
        json.dumps(member)
    assert json.dumps(member.value) == f'"{member.value}"'


def test_category_options_table_defaults_match_settings_defaults() -> None:
    config = CheckSettings()
    definitions_by_key = {definition.key: definition for definition in SETTINGS_SCHEMA.definitions}

    for path in _category_documentation_paths():
        for row in _options_table_rows(path):
            setting_key = row["Setting"].strip("`")
            displayed_default = row["Default"].strip("`")
            if displayed_default == "list":
                continue
            definition = definitions_by_key[setting_key]
            expected_default = settings_core.format_value(getattr(config, definition.field), definition.value_type).strip('"')

            assert displayed_default == expected_default


def test_category_code_ranges_cover_registered_rules() -> None:
    """Category Code ranges tables must cover registered rules without overlap."""
    for category_class in rule_collection.RULE_COLLECTION.categories:
        text = rule_documentation.load_rule_explanation(category_class)
        label = category_class.meta.prefix
        table = markdown_table_helpers.table_after_heading(text, "## Code ranges", label=label, expected_leading_lines=None)
        headers = markdown_table_helpers.table_headers(table, label=label)
        assert headers == CODE_RANGE_HEADERS, f"{category_class.meta.prefix}: invalid Code ranges columns"

        ranges = tuple(_parse_code_range(row["Range"].strip("`"), category_class.meta.prefix) for row in markdown_table_helpers.table_rows(table, label=label))
        assert ranges == tuple(sorted(ranges)), f"{category_class.meta.prefix}: code ranges are not sorted"
        for previous, current in itertools.pairwise(ranges):
            assert previous[1] < current[0], f"{category_class.meta.prefix}: code ranges overlap"

        for rule_class in category_class.ordered_rules():
            assert any(start <= rule_class.meta.code.number <= end for start, end in ranges), f"{rule_class.meta.code}: rule is not covered by category Code ranges"


def _parse_code_range(cell: str, prefix: str) -> tuple[int, int]:
    """Return inclusive numeric bounds for a documented category code range."""
    match = _CODE_RANGE_RE.fullmatch(cell)
    if match is None or match.group("prefix") != prefix:
        raise AssertionError(f"{prefix}: invalid code range {cell!r}")
    if match.group("hundreds") is not None:
        start = int(match.group("hundreds")) * 100
        return (start, start + 99)
    start = int(match.group("start"))
    end = int(match.group("end"))
    if start > end:
        raise AssertionError(f"{prefix}: reversed code range {cell!r}")
    return (start, end)


def test_category_options_sections_document_known_settings() -> None:
    """Category Options sections must be None or a table of known settings."""
    definitions_by_key = {definition.key for definition in SETTINGS_SCHEMA.definitions}
    for category_class, path in zip(rule_collection.RULE_COLLECTION.categories, _category_documentation_paths(), strict=True):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        section_lines = _section_lines(lines, "Options")
        if section_lines == ["None."]:
            continue
        label = category_class.meta.prefix
        table = markdown_table_helpers.table_after_heading(text, "## Options", label=label, expected_leading_lines=None)
        headers = markdown_table_helpers.table_headers(table, label=label)
        assert headers == OPTIONS_HEADERS, f"{category_class.meta.prefix}: invalid Options columns"
        rows = markdown_table_helpers.table_rows(table, label=label)
        for row in rows:
            setting_key = row["Setting"].strip("`")
            assert setting_key in definitions_by_key, f"{category_class.meta.prefix}: unknown Options setting {setting_key}"
