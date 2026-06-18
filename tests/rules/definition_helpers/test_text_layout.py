import pydocformatter.rules.definition_helpers.text_layout as text_layout
from pydocformatter.cli.settings_check import CheckSettings, IndentStyle


def test_display_width_expands_tabs_to_configured_width() -> None:
    assert text_layout.display_width("\t# text", tab_width=4) == 10


def test_leading_width_expands_tabs_to_python_default_width() -> None:
    assert text_layout.leading_width("\t  value") == 10


def test_indent_unit_uses_configured_style() -> None:
    assert text_layout.indent_unit(CheckSettings(indent_style=IndentStyle.SPACE, indent_width=2)) == "  "
    assert text_layout.indent_unit(CheckSettings(indent_style=IndentStyle.TAB, indent_width=2)) == "\t"


def test_has_space_tab_content_ignores_only_spaces_and_tabs() -> None:
    assert not text_layout.has_space_tab_content(" \t")
    assert text_layout.has_space_tab_content(" \t\n")
    assert text_layout.has_space_tab_content(" value")


def test_strip_indent_preserves_virtual_prefix_for_partial_tabs() -> None:
    assert text_layout.strip_indent("\tvalue", 4) == "    value"
    assert text_layout.strip_indent_with_mapping("\tvalue", 4) == ("    value", 1, 4)


def test_wrap_text_uses_shared_no_word_breaking_policy() -> None:
    assert text_layout.wrap_text("alpha beta", width=7, initial_indent="- ", subsequent_indent="  ") == ("- alpha", "  beta")
    assert text_layout.wrap_text("alpha beta", width=0, initial_indent="> ") == ("> alpha beta",)
