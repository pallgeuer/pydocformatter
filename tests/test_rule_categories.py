# Standard library imports
import enum
import json
import pathlib

# Third-party imports
import pytest

# First-party imports
import pydocformatter.settings as settings_core
from pydocformatter.cli.settings_check import SETTINGS_SCHEMA, CheckSettings
from pydocformatter.rules.definitions.PCF.PCF import CommentKind, CommentPlacement
from pydocformatter.rules.definitions.PDF.PDF import DefinitionKind, DocstringKind


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _options_table_rows(path: pathlib.Path) -> list[dict[str, str]]:
    """Return rows from a category documentation options table."""
    lines = path.read_text(encoding="utf-8").splitlines()
    heading_index = lines.index("## Options")
    table_lines: list[str] = []
    for line in lines[heading_index + 1 :]:
        if line.startswith("|"):
            table_lines.append(line)
        elif table_lines:
            break
    headers = _split_markdown_row(table_lines[0])
    return [dict(zip(headers, cells, strict=True)) for cells in (_split_markdown_row(line) for line in table_lines[2:])]


def _split_markdown_row(line: str) -> list[str]:
    """Split one simple Markdown table row into stripped cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


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

    for relative_path in ("src/pydocformatter/rules/definitions/PCF/PCF.md", "src/pydocformatter/rules/definitions/PDF/PDF.md"):
        for row in _options_table_rows(ROOT / relative_path):
            setting_key = row["Setting"].strip("`")
            displayed_default = row["Default"].strip("`")
            if displayed_default == "list":
                continue
            definition = definitions_by_key[setting_key]
            expected_default = settings_core.format_value(getattr(config, definition.field), definition.value_type).strip('"')

            assert displayed_default == expected_default
