# Standard library imports
import warnings

# Third-party imports
import libcst as cst
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import inline_markup, string_literals


def simple_string(source: str) -> cst.SimpleString:
    expression = cst.parse_expression(source)
    assert isinstance(expression, cst.SimpleString)
    return expression


def concatenated_string(source: str) -> cst.ConcatenatedString:
    expression = cst.parse_expression(source)
    assert isinstance(expression, cst.ConcatenatedString)
    return expression


def test_value_fragments_preserve_literal_and_escaped_non_ascii_spellings() -> None:
    fragments = string_literals.value_fragments_for_simple_string(simple_string('"""é \\xe9 \\u00e9"""'))

    assert fragments is not None
    assert tuple(fragment.value for fragment in fragments) == tuple("é é é")
    assert "".join(fragment.source for fragment in fragments) == "é \\xe9 \\u00e9"


def test_value_fragments_validate_named_unicode_escapes() -> None:
    fragments = string_literals.value_fragments_for_simple_string(simple_string(r'"""\N{LATIN SMALL LETTER E WITH ACUTE}"""'))

    assert fragments is not None
    assert tuple(fragment.value for fragment in fragments) == ("\xe9",)
    assert fragments[0].source == r"\N{LATIN SMALL LETTER E WITH ACUTE}"


def test_render_simple_string_from_fragments_preserves_mixed_spellings() -> None:
    node = simple_string('"""é \\xe9 words"""')
    fragments = string_literals.value_fragments_for_simple_string(node)

    assert fragments is not None
    rendered = string_literals.render_simple_string_from_fragments(node, fragments, expected_value="é é words")

    assert rendered == '"""é \\xe9 words"""'


def test_literalized_whitespace_fragments_convert_normal_whitespace_escapes() -> None:
    fragments = (
        string_literals.StringValueFragment(value="a", source="a"),
        string_literals.StringValueFragment(value="\n", source=r"\n"),
        string_literals.StringValueFragment(value="\t", source=r"\t"),
    )

    literalized = string_literals.literalized_whitespace_fragments(fragments, line_ending="\r\n")

    assert tuple(fragment.value for fragment in literalized) == ("a", "\n", "\t")
    assert tuple(fragment.source for fragment in literalized) == ("a", "\r\n", "\t")


def test_literalized_whitespace_fragments_leave_other_escape_spellings_unchanged() -> None:
    fragments = (
        string_literals.StringValueFragment(value="\r", source=r"\r"),
        string_literals.StringValueFragment(value="\n", source=r"\n"),
        string_literals.StringValueFragment(value="\n", source=r"\x0a"),
        string_literals.StringValueFragment(value="\f", source=r"\f"),
        string_literals.StringValueFragment(value="\v", source=r"\v"),
    )

    assert string_literals.literalized_whitespace_fragments(fragments, line_ending="\n") == fragments


def test_concatenated_fragments_preserve_component_escape_spellings_in_target_literal() -> None:
    node = concatenated_string('"é " "\\xe9 " "\\u00e9"')
    fragments = string_literals.fragments_for_concatenated_string(node, target_quote='"""', line_ending="\n")

    assert fragments is not None
    rendered = string_literals.render_simple_string_from_body_source("", '"""', "".join(fragment.source for fragment in fragments), expected_value="é é é")

    assert rendered == '"""é \\xe9 \\u00e9"""'


def test_simple_string_parts_map_complete_concatenated_value_offsets() -> None:
    node = concatenated_string('"first" r"second" "\\u00a0third"')

    parts = string_literals.simple_string_parts(node, value="firstsecond\u00a0third")

    assert parts is not None
    assert all(part.source_map is not None for part in parts)
    assert tuple((part.value_start, part.value_end, part.value) for part in parts) == ((0, 5, "first"), (5, 11, "second"), (11, 17, "\u00a0third"))
    assert parts[2].source_map is not None
    assert parts[2].source_map.fragments[0].source == "\\u00a0"


def test_simple_string_parts_map_single_and_empty_nested_leaves_without_offset_drift() -> None:
    single = simple_string(r'"""a\u00a0b"""')
    nested = concatenated_string('"" "first" "" "\\u00a0" "last"')

    single_parts = string_literals.simple_string_parts(single, value="a\u00a0b")
    nested_parts = string_literals.simple_string_parts(nested, value="first\u00a0last")

    assert single_parts is not None
    assert single_parts[0].source_map is not None
    assert tuple((part.value_start, part.value_end) for part in single_parts) == ((0, 3),)
    assert single_parts[0].source_map.fragments[1].source == "\\u00a0"
    assert nested_parts is not None
    assert tuple((part.value_start, part.value_end, part.value) for part in nested_parts) == ((0, 0, ""), (0, 5, "first"), (5, 5, ""), (5, 6, "\u00a0"), (6, 10, "last"))


def test_simple_string_parts_reject_mismatched_expected_value() -> None:
    assert string_literals.simple_string_parts(simple_string('"value"'), value="different") is None


def test_simple_string_parts_retain_unmapped_leaves_and_complete_value_offsets() -> None:
    node = concatenated_string(r'"first" "bad \z escape" "last"')

    parts = string_literals.simple_string_parts(node)

    assert parts is not None
    assert tuple((part.value_start, part.value_end, part.value, part.source_map is not None) for part in parts) == ((0, 5, "first", True), (5, 18, "bad \\z escape", False), (18, 22, "last", True))
    assert string_literals.fragments_for_concatenated_string(node, target_quote='"""', line_ending="\n") is None


def test_retarget_fragments_escapes_target_delimiter_without_reescaping_literal_whitespace() -> None:
    fragments = (
        string_literals.StringValueFragment(value="\n", source="\n"),
        string_literals.StringValueFragment(value="\t", source="\t"),
        string_literals.StringValueFragment(value='"', source='"'),
        string_literals.StringValueFragment(value='"', source='"'),
        string_literals.StringValueFragment(value='"', source='"'),
    )

    retargeted = string_literals.retarget_fragments(fragments, quote='"""', line_ending="\n")

    assert tuple(fragment.value for fragment in retargeted) == ("\n", "\t", '"', '"', '"')
    assert tuple(fragment.source for fragment in retargeted) == ("\n", "\t", r"\"", r"\"", r"\"")


def test_render_value_as_simple_string_uses_explicit_non_ascii_policy() -> None:
    assert string_literals.render_value_as_simple_string("café", escape_non_ascii=False) == '"""café"""'
    assert string_literals.render_value_as_simple_string("café", escape_non_ascii=True) == '"""caf\\xe9"""'


def test_parse_simple_string_escape_returns_value_source_and_end() -> None:
    cases = (
        (r"\n tail", 0, "\n", r"\n", 2),
        (r"\x41 tail", 0, "A", r"\x41", 4),
        (r"\u0041 tail", 0, "A", r"\u0041", 6),
        (r"\U00000041 tail", 0, "A", r"\U00000041", 10),
        (r"\101 tail", 0, "A", r"\101", 4),
        (r"\N{LATIN CAPITAL LETTER A} tail", 0, "A", r"\N{LATIN CAPITAL LETTER A}", 26),
        ("prefix \\t tail", 7, "\t", r"\t", 9),
    )

    for body, start, value, source, end in cases:
        parsed = string_literals.parse_simple_string_escape(body, start)

        assert parsed == string_literals.StringEscape(value=value, source=source, end=end)


def test_parse_simple_string_escape_handles_line_continuations() -> None:
    assert string_literals.parse_simple_string_escape("\\\nnext", 0) == string_literals.StringEscape(value="", source="\\\n", end=2)
    assert string_literals.parse_simple_string_escape("\\\r\nnext", 0) == string_literals.StringEscape(value="", source="\\\r\n", end=3)


def test_simple_string_source_map_preserves_zero_value_continuations() -> None:
    source_map = string_literals.source_map_for_simple_string(simple_string('"""alpha\\\nbeta"""'))

    assert source_map is not None
    assert source_map.value == "alphabeta"
    assert source_map.owned_source_for_value_slice(0, 5) == "alpha"
    assert source_map.owned_source_for_value_slice(5, 9) == "\\\nbeta"
    assert source_map.body_source_with_replacements(((0, 5, "first"),)) == "first\\\nbeta"
    assert source_map.body_source_with_replacements(((5, 9, "second"),)) == "alpha\\\nsecond"
    assert source_map.body_source_with_replacements(((5, 9, "second"),), preserve_zero_value_source=False) == "alphasecond"


def test_simple_string_source_map_preserves_internal_zero_value_source_during_deletion() -> None:
    source_map = string_literals.source_map_for_simple_string(simple_string('"""a \\\n b"""'))

    assert source_map is not None
    preserved = source_map.preserved_source_for_value_deletion(1, 3)
    assert preserved == "\\\n"
    assert source_map.body_source_with_replacements(((1, 3, preserved),)) == "a\\\nb"


def test_simple_string_source_map_attributes_mixed_logical_and_physical_lines_exactly() -> None:
    source_map = string_literals.source_map_for_simple_string(simple_string('"""first\\nsecond\\\nthird\nfourth"""'))

    assert source_map is not None
    assert source_map.has_escaped_newline(0, len(source_map.value))
    assert source_map.physical_line_numbers(0, len(source_map.value), first_line_number=10) == (10, 11, 12)
    assert source_map.owned_source_for_value_slice(6, 17) == "second\\\nthird"
    assert source_map.physical_newline_ends == (15, 21)


def test_simple_string_source_map_preserves_zero_value_source_around_transformed_fragments() -> None:
    node = simple_string('"""a\\\nb"""')
    source_map = string_literals.source_map_for_simple_string(node)

    assert source_map is not None
    transformed = tuple(string_literals.StringValueFragment(value=fragment.value, source=fragment.source.upper()) for fragment in source_map.fragments)

    assert source_map.body_source_for_fragments(transformed) == "A\\\nB"


def test_simple_string_source_map_rejects_unsupported_escapes() -> None:
    assert string_literals.source_map_for_simple_string(simple_string(r'"""bad \z escape"""')) is None


def test_simple_string_source_map_accepts_a_pre_evaluated_value() -> None:
    node = simple_string(r'"""caf\xe9"""')

    source_map = string_literals.source_map_for_simple_string(node, value="caf\xe9")

    assert source_map is not None
    assert source_map.value == "caf\xe9"
    assert string_literals.source_map_for_simple_string(node, value="different") is None


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('"""first\nsecond"""', True),
        ('"""first\r\nsecond"""', True),
        ('"""first\\\nsecond"""', True),
        (r'"""caf\xe9"""', True),
        (r'r"""first\nsecond"""', True),
        (r'"""first\nsecond"""', False),
        (r'"""bad \z escape"""', False),
    ],
)
def test_simple_string_direct_line_mapping_matches_supported_source_semantics(source: str, expected: bool) -> None:
    node = simple_string(source)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        value = string_literals.evaluated_string_value(node)

    assert isinstance(value, str)
    assert string_literals.simple_string_has_direct_line_mapping(node, value=value) is expected


def test_parse_simple_string_escape_returns_none_for_invalid_escape() -> None:
    assert string_literals.parse_simple_string_escape("\\", 0) is None
    assert string_literals.parse_simple_string_escape(r"\x4", 0) is None
    assert string_literals.parse_simple_string_escape(r"\u004g", 0) is None
    assert string_literals.parse_simple_string_escape(r"\N{NOT A NAME}", 0) is None
    assert string_literals.parse_simple_string_escape(r"\d", 0) is None


def test_wrap_source_tokens_counts_escape_source_widths() -> None:
    words = (inline_markup.InlineToken(value="éé", source="\\xe9\\xe9"), inline_markup.InlineToken(value="tail", source="tail"))

    wrapped = string_literals.wrap_source_tokens(words, width=9, initial_indent="", subsequent_indent="", tab_width=4)

    assert tuple(line.value for line in wrapped) == ("éé", "tail")
    assert tuple(line.source for line in wrapped) == ("\\xe9\\xe9", "tail")


def test_wrap_source_tokens_non_positive_width_uses_one_word_per_line() -> None:
    words = (inline_markup.InlineToken(value="alpha", source="alpha"), inline_markup.InlineToken(value="beta", source="beta"))

    wrapped = string_literals.wrap_source_tokens(words, width=0, initial_indent="> ", subsequent_indent="  ", tab_width=4)

    assert tuple(line.value for line in wrapped) == ("> alpha", "  beta")
    assert tuple(line.source for line in wrapped) == ("> alpha", "  beta")


def test_wrap_source_tokens_allows_distinct_initial_width() -> None:
    words = tuple(inline_markup.InlineToken(value=word, source=word) for word in ("alpha", "beta", "gamma"))

    wrapped = string_literals.wrap_source_tokens(words, width=16, initial_width=9, subsequent_width=16, tab_width=4)

    assert tuple(line.value for line in wrapped) == ("alpha", "beta gamma")
    assert tuple(line.source for line in wrapped) == ("alpha", "beta gamma")


def test_wrap_source_tokens_reserves_final_suffix_width() -> None:
    words = tuple(inline_markup.InlineToken(value=word, source=word) for word in ("alpha", "beta", "gamma"))

    wrapped = string_literals.wrap_source_tokens(words, width=16, final_suffix_width=3, tab_width=4)

    assert tuple(line.value for line in wrapped) == ("alpha beta", "gamma")
    assert tuple(line.source for line in wrapped) == ("alpha beta", "gamma")


def test_wrap_source_tokens_respects_variable_widths_indents_and_final_suffix() -> None:
    words = tuple(inline_markup.InlineToken(value=word, source=word) for word in ("alpha", "beta", "gamma", "delta"))

    wrapped = string_literals.wrap_source_tokens(words, width=12, initial_width=12, subsequent_width=18, final_suffix_width=5, initial_indent="> ", subsequent_indent="  ", tab_width=4)

    assert tuple(line.value for line in wrapped) == ("> alpha beta", "  gamma delta")
    assert tuple(line.source for line in wrapped) == ("> alpha beta", "  gamma delta")


def test_wrap_source_tokens_keeps_long_words_unsplit_with_variable_widths() -> None:
    words = tuple(inline_markup.InlineToken(value=word, source=word) for word in ("supercalifragilistic", "short", "words"))

    wrapped = string_literals.wrap_source_tokens(words, width=10, initial_width=10, subsequent_width=10, final_suffix_width=3, tab_width=4)

    assert tuple(line.value for line in wrapped) == ("supercalifragilistic", "short", "words")
    assert tuple(line.source for line in wrapped) == ("supercalifragilistic", "short", "words")


def test_wrap_source_tokens_uses_tab_expanded_source_widths_with_variable_widths() -> None:
    words = tuple(inline_markup.InlineToken(value=word, source=word) for word in ("tab\tword", "tail", "more"))

    wrapped = string_literals.wrap_source_tokens(words, width=12, initial_width=12, subsequent_width=12, tab_width=4)

    assert tuple(line.value for line in wrapped) == ("tab\tword", "tail more")
    assert tuple(line.source for line in wrapped) == ("tab\tword", "tail more")


def test_wrap_source_tokens_can_balance_words_around_url_tokens() -> None:
    words = tuple(inline_markup.InlineToken(value=word, source=word, url_like=word.startswith("https://")) for word in ("alpha", "beta", "https://example.com/path", "alpha"))

    wrapped = string_literals.wrap_source_tokens(words, width=29, tab_width=4, url_aware=True)

    assert tuple(line.value for line in wrapped) == ("alpha", "beta https://example.com/path", "alpha")
    assert tuple(line.source for line in wrapped) == ("alpha", "beta https://example.com/path", "alpha")


def test_wrap_source_tokens_url_balancing_preserves_source_spelling() -> None:
    words = (
        inline_markup.InlineToken(value="alpha", source="alpha"),
        inline_markup.InlineToken(value="https://example.com/path", source="https://example.com/path", url_like=True),
        inline_markup.InlineToken(value="tail", source=r"t\x61il"),
    )

    wrapped = string_literals.wrap_source_tokens(words, width=30, tab_width=4, url_aware=True)

    assert tuple(line.value for line in wrapped) == ("alpha https://example.com/path", "tail")
    assert tuple(line.source for line in wrapped) == ("alpha https://example.com/path", r"t\x61il")


def test_wrap_source_tokens_url_balancing_respects_variable_widths_and_final_suffix() -> None:
    words = tuple(inline_markup.InlineToken(value=word, source=word, url_like=word.startswith("https://")) for word in ("alpha", "beta", "https://example.com/path", "gamma"))

    wrapped = string_literals.wrap_source_tokens(words, width=35, initial_width=18, subsequent_width=35, final_suffix_width=6, tab_width=4, url_aware=True)

    assert tuple(line.value for line in wrapped) == ("alpha", "beta https://example.com/path", "gamma")
    assert tuple(line.source for line in wrapped) == ("alpha", "beta https://example.com/path", "gamma")


def test_render_simple_string_from_body_source_returns_none_for_invalid_literal() -> None:
    assert string_literals.render_simple_string_from_body_source("", '"""', 'bad """ delimiter', expected_value='bad """ delimiter') is None
