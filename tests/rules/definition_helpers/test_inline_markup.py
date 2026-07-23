# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import inline_markup, string_literals


@pytest.mark.parametrize(
    ("text", "kind", "url_like"),
    [
        ("before `code with spaces` after", inline_markup.InlineMarkupKind.REST_INTERPRETED, False),
        ("before ``literal with spaces`` after", inline_markup.InlineMarkupKind.REST_LITERAL, False),
        ("before [nested [label]](target) after", inline_markup.InlineMarkupKind.MARKDOWN_LINK, True),
        (r"before ![escaped \] label](<target-path> 'title') after", inline_markup.InlineMarkupKind.MARKDOWN_LINK, True),
        ('before [](target "title") after', inline_markup.InlineMarkupKind.MARKDOWN_LINK, True),
        ("before [label]() after", inline_markup.InlineMarkupKind.MARKDOWN_LINK, True),
        ("before [label][reference] after", inline_markup.InlineMarkupKind.MARKDOWN_LINK, False),
        ("before [label][] after", inline_markup.InlineMarkupKind.MARKDOWN_LINK, False),
        ("before <https://example.com/path> after", inline_markup.InlineMarkupKind.AUTOLINK, True),
        ("before <person.name+tag@example.com> after", inline_markup.InlineMarkupKind.AUTOLINK, True),
        ("before :py-class:`Client value` after", inline_markup.InlineMarkupKind.REST_ROLE, False),
        ("before `Client value`:py.class: after", inline_markup.InlineMarkupKind.REST_ROLE, False),
        ("before `label <target value>`_ after", inline_markup.InlineMarkupKind.REST_INTERPRETED, True),
        ("before `phrase reference`__ after", inline_markup.InlineMarkupKind.REST_INTERPRETED, False),
        ("before |replacement name| after", inline_markup.InlineMarkupKind.REST_SUBSTITUTION, False),
    ],
)
def test_scanner_recognizes_supported_same_line_constructs(text: str, kind: inline_markup.InlineMarkupKind, url_like: bool) -> None:
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    markup = tuple(token for token in result.tokens if token.kind is not None)
    assert len(markup) == 1
    assert markup[0].kind is kind
    assert markup[0].url_like is url_like


@pytest.mark.parametrize("title", ['"title here"', "'title here'", "(title here)"])
def test_markdown_inline_links_accept_all_title_delimiters(title: str) -> None:
    result = inline_markup.scan_text(f"before [label](target {title}) after")

    assert not result.ambiguous
    assert tuple(token.kind for token in result.tokens) == (None, inline_markup.InlineMarkupKind.MARKDOWN_LINK, None)


@pytest.mark.parametrize("text", ["[label](<target>)", "![label](<target>)"])
def test_markdown_angle_destinations_accept_an_immediate_outer_closer(text: str) -> None:
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    assert result.tokens[0].kind is inline_markup.InlineMarkupKind.MARKDOWN_LINK


@pytest.mark.parametrize("text", [r"[label](foo\))", '[label](a\\((b)c "title")', r"[label](target\ with\ spaces)"])
def test_escaped_destination_characters_do_not_skip_the_following_character(text: str) -> None:
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    assert tuple(token.value for token in result.tokens) == (text,)
    assert result.tokens[0].kind is inline_markup.InlineMarkupKind.MARKDOWN_LINK


def test_plain_text_scanning_bypasses_delimiter_indexing(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_delimiter_index(text: str) -> None:
        raise AssertionError(f"Unexpected delimiter indexing for {text!r}")

    monkeypatch.setattr(inline_markup, "_delimiter_index", unexpected_delimiter_index)

    result = inline_markup.scan_text("plain prose and www.example.com")

    assert tuple(token.value for token in result.tokens) == ("plain", "prose", "and", "www.example.com")
    assert result.tokens[-1].url_like


def test_plain_source_aware_scanning_bypasses_delimiter_indexing(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_delimiter_index(text: str) -> None:
        raise AssertionError(f"Unexpected delimiter indexing for {text!r}")

    monkeypatch.setattr(inline_markup, "_delimiter_index", unexpected_delimiter_index)
    text = "plain prose and www.example.com"
    fragments = tuple(string_literals.StringValueFragment(value=char, source=r"\x61" if index == 2 else char) for index, char in enumerate(text))

    result = inline_markup.scan_fragments(fragments)

    assert tuple(token.value for token in result.tokens) == ("plain", "prose", "and", "www.example.com")
    assert tuple(token.source for token in result.tokens) == (r"pl\x61in", "prose", "and", "www.example.com")
    assert result.tokens[-1].url_like


@pytest.mark.parametrize("role", ["py-class", "py_class", "py+class", "py:class", "py.class"])
def test_rest_roles_accept_supported_isolated_internal_punctuation(role: str) -> None:
    result = inline_markup.scan_text(f"before :{role}:`value` after")

    assert not result.ambiguous
    assert result.tokens[1].kind is inline_markup.InlineMarkupKind.REST_ROLE


def test_punctuation_envelope_keeps_adjacent_source_together() -> None:
    result = inline_markup.scan_text("before ([label with spaces](target)), after")

    assert tuple(token.value for token in result.tokens) == ("before", "([label with spaces](target)),", "after")
    assert result.tokens[1].url_like


def test_adjacent_constructs_share_one_indivisible_envelope() -> None:
    result = inline_markup.scan_text("before `one`/[two](target) after")

    assert tuple(token.value for token in result.tokens) == ("before", "`one`/[two](target)", "after")
    assert result.tokens[1].kind is inline_markup.InlineMarkupKind.MIXED
    assert result.tokens[1].url_like


def test_markdown_destination_allows_three_nested_parenthesis_levels() -> None:
    result = inline_markup.scan_text("before [label](a(b(c(d)))) after")

    assert not result.ambiguous
    assert result.tokens[1].kind is inline_markup.InlineMarkupKind.MARKDOWN_LINK


@pytest.mark.parametrize(
    "text",
    [
        "before [label](a(b(c(d(e))))) after",
        "before [label](missing after",
        "before [label][missing after",
        "before <https://example.com/missing after",
        "before `missing after",
        "before :py:class:`missing after",
        "before `value`:py-class after",
    ],
)
def test_scanner_reports_evidence_gated_ambiguity(text: str) -> None:
    assert inline_markup.scan_text(text).ambiguous


@pytest.mark.parametrize(
    "text",
    ["ordinary [ unmatched bracket", "ordinary | unmatched pipe", "ordinary < unmatched angle", "[shortcut] reference", "<span>raw HTML</span>", "*emphasis with spaces*", "``` fence-like opener"],
)
def test_scanner_leaves_excluded_or_generic_syntax_as_prose(text: str) -> None:
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    assert all(token.kind is None for token in result.tokens)


def test_escaped_inner_backtick_is_content_when_a_later_close_exists() -> None:
    result = inline_markup.scan_text(r"before `literal \` content` after")

    assert not result.ambiguous
    assert result.tokens[1].value == r"`literal \` content`"


@pytest.mark.parametrize("text", ["[" * 20_000, "<" * 20_000, "\\" * 20_000])
def test_scanner_handles_large_unmatched_delimiter_runs_as_ordinary_prose(text: str) -> None:
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    assert tuple(token.value for token in result.tokens) == (text,)


def test_scanner_handles_many_adjacent_recognized_constructs_as_one_envelope() -> None:
    text = "/".join(["`value`"] * 2_000)
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    assert tuple(token.value for token in result.tokens) == (text,)
    assert result.tokens[0].kind is inline_markup.InlineMarkupKind.REST_INTERPRETED


@pytest.mark.parametrize("text", ["```python", "~~~python", "    ```{python}"])
def test_scanner_treats_line_leading_fence_openers_with_info_strings_as_ordinary(text: str) -> None:
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    assert all(token.kind is None for token in result.tokens)


def test_scanner_handles_long_escaped_markdown_destination_in_linear_indexed_pass() -> None:
    text = "[label](" + "\\" * 20_000 + "target)"
    result = inline_markup.scan_text(text)

    assert not result.ambiguous
    assert result.tokens[0].kind is inline_markup.InlineMarkupKind.MARKDOWN_LINK


@pytest.mark.parametrize(
    "text",
    [
        "![incomplete image",
        "[label](   ",
        "[label](<target with space>)",
        "[label](<unterminated)",
        "[label](target unsupported-title)",
        "[label](target 'unterminated)",
        "[label](target (nested(title)))",
        "[label](target 'title' trailing)",
    ],
)
def test_scanner_rejects_distinct_strong_malformed_markdown_shapes(text: str) -> None:
    assert inline_markup.scan_text(text).ambiguous


def test_scanner_accepts_escaped_destination_whitespace_and_keeps_inline_markdown_code_inside_words_atomic() -> None:
    link = inline_markup.scan_text(r"before [label](target\ with\ spaces) after")
    code = inline_markup.scan_text("before prefix`code with spaces`suffix after")

    assert not link.ambiguous
    assert link.tokens[1].kind is inline_markup.InlineMarkupKind.MARKDOWN_LINK
    assert not code.ambiguous
    assert code.tokens[1].value == "prefix`code with spaces`suffix"
    assert code.tokens[1].kind is inline_markup.InlineMarkupKind.MARKDOWN_CODE


def test_generic_nested_angle_text_and_complete_shortcut_reference_remain_ordinary() -> None:
    for text in ("<http://first<second>", "[label]"):
        result = inline_markup.scan_text(text)
        assert not result.ambiguous
        assert all(token.kind is None for token in result.tokens)


def test_source_fragment_validation_rejects_multi_character_evaluated_fragments() -> None:
    with pytest.raises(ValueError, match="one evaluated character"):
        inline_markup.scan_fragments((string_literals.StringValueFragment(value="two", source="two"),))


def test_source_aware_scanning_preserves_exact_escape_spellings_inside_atomic_markup() -> None:
    text = "before [label with words](target) after"
    fragments = tuple(string_literals.StringValueFragment(value=char, source="\\x20" if char == " " else char) for char in text)
    result = inline_markup.scan_fragments(fragments)

    assert result.tokens[1].value == "[label with words](target)"
    assert result.tokens[1].source == r"[label\x20with\x20words](target)"
    assert result.tokens[1].kind is inline_markup.InlineMarkupKind.MARKDOWN_LINK


def test_source_aware_hard_break_preserves_mixed_escape_spellings() -> None:
    fragments = (
        string_literals.StringValueFragment(value="x", source="x"),
        string_literals.StringValueFragment(value=" ", source=r"\x20"),
        string_literals.StringValueFragment(value=" ", source=r"\040"),
    )
    hard_break = inline_markup.terminal_hard_break(fragments, has_following_newline=True)

    assert hard_break is not None
    assert hard_break.value == "  "
    assert hard_break.source == r"\x20\040"


@pytest.mark.parametrize(
    ("text", "has_newline", "kind", "suffix"),
    [
        ("text  ", True, inline_markup.HardBreakKind.SPACES, "  "),
        ("text    ", True, inline_markup.HardBreakKind.SPACES, "    "),
        ("text\\", True, inline_markup.HardBreakKind.BACKSLASH, "\\"),
        ("text\\\\\\", True, inline_markup.HardBreakKind.BACKSLASH, "\\\\\\"),
    ],
)
def test_terminal_hard_break_recognizes_supported_suffixes(text: str, has_newline: bool, kind: inline_markup.HardBreakKind, suffix: str) -> None:
    hard_break = inline_markup.terminal_text_hard_break(text, has_following_newline=has_newline)

    assert hard_break is not None
    assert hard_break.kind is kind
    assert hard_break.value == suffix


@pytest.mark.parametrize(("text", "has_newline"), [("text ", True), ("text\\\\", True), ("text  ", False), ("   ", True)])
def test_terminal_hard_break_rejects_non_boundaries(text: str, has_newline: bool) -> None:
    assert inline_markup.terminal_text_hard_break(text, has_following_newline=has_newline) is None


def test_layout_scanning_joins_lines_and_splits_at_exact_hard_breaks() -> None:
    lines = (
        inline_markup.layout_line_for_text("alpha beta", has_following_newline=True),
        inline_markup.layout_line_for_text("gamma \t  ", has_following_newline=True),
        inline_markup.layout_line_for_text("delta", has_following_newline=False),
    )
    result = inline_markup.scan_layout_lines(lines)

    assert tuple(segment.text for segment in result.segments) == ("alpha beta gamma", "delta")
    assert tuple(token.value for token in result.segments[0].scan.tokens) == ("alpha", "beta", "gamma")
    assert result.segments[0].hard_break is not None
    assert result.segments[0].hard_break.value == "   "
    assert not result.ambiguous


def test_layout_scanning_preserves_line_identity_for_duplicate_ambiguities() -> None:
    result = inline_markup.scan_layout_lines((
        inline_markup.layout_line_for_text("[label](missing  ", has_following_newline=True),
        inline_markup.layout_line_for_text("ordinary words", has_following_newline=True),
        inline_markup.layout_line_for_text("[label](missing", has_following_newline=False),
    ))

    assert result.ambiguous
    assert tuple(ambiguity.line_index for ambiguity in result.ambiguities) == (0, 2)
    assert tuple(tuple(ambiguity.line_index for ambiguity in segment.scan.ambiguities) for segment in result.segments) == ((0,), (2,))
