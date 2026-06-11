import pydocformatter.rules.definition_helpers.text_layout as text_layout


def test_display_width_expands_tabs_to_configured_width() -> None:
    assert text_layout.display_width("\t# text", tab_width=4) == 10


def test_wrap_text_uses_shared_no_word_breaking_policy() -> None:
    assert text_layout.wrap_text("alpha beta", width=7, initial_indent="- ", subsequent_indent="  ") == ("- alpha", "  beta")
    assert text_layout.wrap_text("alpha beta", width=0, initial_indent="> ") == ("> alpha beta",)
