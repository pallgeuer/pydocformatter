import libcst as cst

import pydocformatter.rules.definition_helpers.string_literals as string_literals


def simple_string(source: str) -> cst.SimpleString:
    expression = cst.parse_expression(source)
    assert isinstance(expression, cst.SimpleString)
    return expression


def concatenated_string(source: str) -> cst.ConcatenatedString:
    expression = cst.parse_expression(source)
    assert isinstance(expression, cst.ConcatenatedString)
    return expression


def test_value_fragments_preserve_literal_and_escaped_non_ascii_spellings() -> None:
    fragments = string_literals.value_fragments_for_simple_string(simple_string('"""é \\xe9 \\u00e9"""'), line_ending="\n")

    assert fragments is not None
    assert tuple(fragment.value for fragment in fragments) == tuple("é é é")
    assert "".join(fragment.source for fragment in fragments) == "é \\xe9 \\u00e9"


def test_value_fragments_validate_named_unicode_escapes() -> None:
    fragments = string_literals.value_fragments_for_simple_string(simple_string(r'"""\N{LATIN SMALL LETTER E WITH ACUTE}"""'), line_ending="\n")

    assert fragments is not None
    assert tuple(fragment.value for fragment in fragments) == ("\xe9",)
    assert fragments[0].source == r"\N{LATIN SMALL LETTER E WITH ACUTE}"


def test_render_simple_string_from_fragments_preserves_mixed_spellings() -> None:
    node = simple_string('"""é \\xe9 words"""')
    fragments = string_literals.value_fragments_for_simple_string(node, line_ending="\n")

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


def test_wrap_source_words_counts_escape_source_widths() -> None:
    words = (string_literals.SourceWord(value="éé", source="\\xe9\\xe9"), string_literals.SourceWord(value="tail", source="tail"))

    wrapped = string_literals.wrap_source_words(words, width=9, initial_indent="", subsequent_indent="", tab_width=4)

    assert tuple(line.value for line in wrapped) == ("éé", "tail")
    assert tuple(line.source for line in wrapped) == ("\\xe9\\xe9", "tail")


def test_wrap_source_words_non_positive_width_uses_one_word_per_line() -> None:
    words = (string_literals.SourceWord(value="alpha", source="alpha"), string_literals.SourceWord(value="beta", source="beta"))

    wrapped = string_literals.wrap_source_words(words, width=0, initial_indent="> ", subsequent_indent="  ", tab_width=4)

    assert tuple(line.value for line in wrapped) == ("> alpha", "  beta")
    assert tuple(line.source for line in wrapped) == ("> alpha", "  beta")


def test_wrap_source_words_allows_distinct_initial_width() -> None:
    words = tuple(string_literals.SourceWord(value=word, source=word) for word in ("alpha", "beta", "gamma"))

    wrapped = string_literals.wrap_source_words(words, width=16, initial_width=9, subsequent_width=16, tab_width=4)

    assert tuple(line.value for line in wrapped) == ("alpha", "beta gamma")
    assert tuple(line.source for line in wrapped) == ("alpha", "beta gamma")


def test_wrap_source_words_reserves_final_suffix_width() -> None:
    words = tuple(string_literals.SourceWord(value=word, source=word) for word in ("alpha", "beta", "gamma"))

    wrapped = string_literals.wrap_source_words(words, width=16, final_suffix_width=3, tab_width=4)

    assert tuple(line.value for line in wrapped) == ("alpha beta", "gamma")
    assert tuple(line.source for line in wrapped) == ("alpha beta", "gamma")


def test_render_simple_string_from_body_source_returns_none_for_invalid_literal() -> None:
    assert string_literals.render_simple_string_from_body_source("", '"""', 'bad """ delimiter', expected_value='bad """ delimiter') is None
