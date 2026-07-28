# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
from pydocformatter.cli.settings_check import CheckSettings, IndentStyle
from pydocformatter.rules.definition_helpers import ascii_whitespace, inline_markup, text_layout


if TYPE_CHECKING:
    # Third-party imports
    import pytest


def test_display_width_expands_tabs_to_configured_width() -> None:
    assert text_layout.display_width("\t# text", tab_width=4) == 10


def test_ascii_space_and_tab_policy_is_deliberately_closed() -> None:
    """Keep horizontal layout ownership limited to ASCII space and tab."""
    assert ascii_whitespace.SPACE_AND_TAB == " \t"


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


def test_wrap_inline_tokens_measures_exact_source_and_renders_evaluated_text() -> None:
    tokens = (inline_markup.InlineToken(value="alpha", source="alpha"), inline_markup.InlineToken(value="e", source=r"\x65"))

    wrapped = text_layout.wrap_inline_tokens(tokens, width=8, tab_width=4)

    assert wrapped == ("alpha", "e")


def test_wrap_scanned_text_does_not_rescan(monkeypatch: pytest.MonkeyPatch) -> None:
    text = "alpha beta gamma"
    scan = inline_markup.scan_text(text)

    def unexpected_scan(text: str) -> inline_markup.InlineScanResult:
        raise AssertionError(f"Unexpected rescan of {text!r}")

    monkeypatch.setattr(inline_markup, "scan_text", unexpected_scan)

    assert text_layout.wrap_scanned_text(text, scan, width=10) == ("alpha beta", "gamma")


def test_explicit_destination_classification_controls_balancing_independently_of_token_text() -> None:
    ordinary = tuple(inline_markup.InlineToken(value=word, source=word) for word in ("alpha", "beta", "destination", "alpha"))
    destination = (*ordinary[:2], dataclasses.replace(ordinary[2], url_like=True), ordinary[3])

    assert text_layout.wrap_inline_tokens(ordinary, width=16, tab_width=4, url_aware=True) == ("alpha beta", "destination", "alpha")
    assert text_layout.wrap_inline_tokens(destination, width=16, tab_width=4, url_aware=True) == ("alpha", "beta destination", "alpha")
