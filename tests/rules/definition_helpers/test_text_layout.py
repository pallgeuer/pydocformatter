import pytest

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


def test_is_url_token_detects_scheme_and_www_urls() -> None:
    assert text_layout.is_url_token("https://example.com/path")
    assert text_layout.is_url_token("www.example.com/path")
    assert text_layout.is_url_token("(https://example.com/path).")
    assert not text_layout.is_url_token("example.com/path")


def test_wrap_text_preserves_default_greedy_url_wrapping() -> None:
    text = "alpha beta https://example.com/path alpha"

    assert text_layout.wrap_text(text, width=29) == ("alpha beta", "https://example.com/path", "alpha")


def test_wrap_text_can_balance_words_around_url_tokens() -> None:
    text = "alpha beta https://example.com/path alpha"

    assert text_layout.wrap_text(text, width=29, url_aware=True) == ("alpha", "beta https://example.com/path", "alpha")


def test_wrap_text_keeps_long_urls_unbroken_when_url_aware() -> None:
    text = "alpha https://example.com/very/long/path beta"

    assert text_layout.wrap_text(text, width=20, url_aware=True) == ("alpha", "https://example.com/very/long/path", "beta")


def test_wrap_text_url_aware_without_urls_preserves_default_wrapping() -> None:
    text = "alpha beta gamma delta epsilon"

    assert text_layout.wrap_text(text, width=16, url_aware=True) == text_layout.wrap_text(text, width=16)


def test_wrap_text_can_balance_www_url_tokens() -> None:
    text = "alpha beta www.example.com/path gamma"

    assert text_layout.wrap_text(text, width=25, url_aware=True) == ("alpha", "beta www.example.com/path", "gamma")


def test_wrap_text_can_balance_punctuated_url_tokens() -> None:
    text = "alpha beta (https://example.com/path) gamma"

    assert text_layout.wrap_text(text, width=31, url_aware=True) == ("alpha", "beta (https://example.com/path)", "gamma")


def test_wrap_text_url_aware_handles_long_url_paragraph_without_recursion() -> None:
    words = ("alpha",) * 520 + ("https://example.com/path",) + ("beta",) * 5
    text = " ".join(words)

    wrapped = text_layout.wrap_text(text, width=80, url_aware=True)

    assert "https://example.com/path" in " ".join(wrapped)
    assert len(wrapped) <= len(text_layout.wrap_text(text, width=80))
    assert all(text_layout.display_width(line, tab_width=8) <= 80 for line in wrapped)


def test_wrap_text_url_aware_falls_back_to_greedy_when_candidate_budget_is_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    text = "alpha beta https://example.com/path alpha"
    monkeypatch.setattr(text_layout, "_BALANCED_WRAP_MAX_CANDIDATES", 1)

    assert text_layout.wrap_text(text, width=29, url_aware=True) == text_layout.wrap_text(text, width=29)


def test_wrap_text_url_aware_falls_back_to_greedy_when_word_budget_is_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    text = "alpha beta https://example.com/path alpha"
    monkeypatch.setattr(text_layout, "_BALANCED_WRAP_MAX_WORDS", 1)

    assert text_layout.wrap_text(text, width=29, url_aware=True) == text_layout.wrap_text(text, width=29)
