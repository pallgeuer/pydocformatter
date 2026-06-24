import typing

import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter.cli.settings_check import CheckSettings, LineEnding


def test_long_trailing_comment_moves_above_code_and_is_independent_of_pcf001() -> None:
    source = "value = compute()  # This trailing comment has enough words that it must move above the code line.\n"
    settings = CheckSettings(select=("PCF004",), line_length=42)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "# This trailing comment has enough words\n# that it must move above the code line.\nvalue = compute()\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF004": 1}
    assert not result.unfixed_findings


def test_tiny_available_width_is_stable_and_does_not_crash() -> None:
    source = "if enabled:\n        # comment text\n        value = 1  # trailing comment text\n"
    result = pcf_helpers.format_pcf(source, line_length=8)
    assert result.new_source == "if enabled:\n        # comment text\n\n        # trailing comment text\n        value = 1\n"
    assert not result.errors


def test_tabs_are_measured_at_indent_width_columns() -> None:
    source = "value\t= 1  # text\n"
    result = pcf_helpers.format_pcf(source, line_length=17, indent_width=4)
    assert result.new_source == "# text\nvalue\t= 1\n"


def test_canonical_trailing_comment_at_exact_line_length_remains_inline() -> None:
    source = "value = 1  # exact\n"
    result = pcf_helpers.format_pcf(source, line_length=len(source.rstrip("\n")))
    assert result.new_source == source
    assert not result.fixed_findings


def test_trailing_comment_one_column_over_limit_moves_above_code() -> None:
    source = "value = 1  # exact\n"
    result = pcf_helpers.format_pcf(source, line_length=len(source.rstrip("\n")) - 1)
    assert result.new_source == "# exact\nvalue = 1\n"


def test_indented_overlong_trailing_comment_moves_to_code_indentation_and_wraps() -> None:
    source = "if enabled:\n    value = compute()  # This explanation has enough words to move and wrap.\n"
    result = pcf_helpers.format_pcf(source, line_length=32)
    assert result.new_source == "if enabled:\n    # This explanation has\n    # enough words to move and\n    # wrap.\n    value = compute()\n"


def test_multiple_trailing_comment_edits_are_applied_in_source_order() -> None:
    source = "first = compute() # first explanation needs wrapping\nsecond = compute()#second explanation needs wrapping\nthird = 3 # short\n"
    result = pcf_helpers.format_pcf(source, line_length=30)
    assert result.new_source == "# first explanation needs\n# wrapping\nfirst = compute()\n# second explanation needs\n# wrapping\nsecond = compute()\nthird = 3  # short\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF002": 3, "PCF004": 2}


def test_moved_trailing_comment_preserves_eof_without_final_newline() -> None:
    source = "value = compute()  # explanation that is too long"
    result = pcf_helpers.format_pcf(source, line_length=24)
    assert result.new_source == "# explanation that is\n# too long\nvalue = compute()"


def test_moved_trailing_comment_uses_configured_line_endings_inside_replacement_only() -> None:
    source = "first = 1\nvalue = compute()  # explanation with enough words to move\r\nlast = 3\n"
    result = pcf_helpers.format_pcf(source, line_length=30, line_ending=LineEnding.CR_LF)
    assert result.new_source == "first = 1\n# explanation with enough\r\n# words to move\r\nvalue = compute()\r\nlast = 3\n"


def test_overlong_unsplittable_trailing_word_moves_without_splitting() -> None:
    source = "value = 1  # supercalifragilisticexpialidocious\n"
    result = pcf_helpers.format_pcf(source, line_length=16)
    assert result.new_source == "# supercalifragilisticexpialidocious\nvalue = 1\n"


def test_short_comment_moves_when_code_alone_makes_the_combined_line_too_long() -> None:
    source = "very_long_variable_name = compute_expensive_value()  # why\n"
    result = pcf_helpers.format_pcf(source, line_length=40)
    assert result.new_source == "# why\nvery_long_variable_name = compute_expensive_value()\n"


def test_empty_trailing_comment_remains_inline_even_when_code_is_overlong() -> None:
    source = "very_long_variable_name = compute_expensive_value() #   \n"
    result = pcf_helpers.format_pcf(source, line_length=20)
    assert result.new_source == "very_long_variable_name = compute_expensive_value()  #\n"


@pytest.mark.parametrize(
    "directive",
    (
        "# type: ignore[assignment]",
        "# noqa: F401",
        "# nosec reason",
        "# pragma: no cover",
    ),
)
def test_protected_directives_are_not_extracted_by_pcf004(directive: str) -> None:
    source = f"very_long_variable_name = compute_expensive_value()  {directive}\n"
    settings = CheckSettings(select=("PCF004",), line_length=20)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == source
    assert not result.fixed_findings


def test_canonical_overlong_trailing_comment_in_sensitive_position_is_not_reported_when_syntax_aware() -> None:
    source = "if enabled:  # explanation long enough to move above the header\n    pass\n"
    settings = CheckSettings(select=("PCF004",), line_length=32)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert not result.unfixed_findings


def test_disabled_syntax_aware_extraction_reports_sensitive_position_in_check_mode() -> None:
    source = "if enabled:  # explanation long enough to move above the header\n    pass\n"
    settings = CheckSettings(select=("PCF004",), line_length=32, comment_trailing_extraction_syntax_aware=False)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,),)


def test_syntax_aware_extraction_still_normalizes_spacing_without_moving_sensitive_comment() -> None:
    source = "if enabled:# explanation long enough to move above the header\n    pass\n"
    result = pcf_helpers.format_pcf(source, line_length=32)
    assert result.new_source == "if enabled:  # explanation long enough to move above the header\n    pass\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF002": 1}


def test_extraction_rule_alone_does_not_normalize_suppressed_comment_spacing() -> None:
    source = "if enabled:# explanation long enough to move above the header\n    pass\n"
    settings = CheckSettings(select=("PCF004",), line_length=32)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_content_aware_extraction_still_allows_spacing_normalization() -> None:
    source = "value = compute()#- alpha beta gamma delta epsilon\n"
    result = pcf_helpers.format_pcf(source, line_length=24, comment_format_list_items=False)
    assert result.new_source == "value = compute()  # - alpha beta gamma delta epsilon\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF002": 1}


def test_spacing_and_extraction_both_report_same_original_line_in_check_mode() -> None:
    source = "value = compute()#ordinary trailing words that need moving\n"
    settings = CheckSettings(select=("PCF002", "PCF004"), line_length=28)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert tuple((finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings) == (("PCF002", (1,)), ("PCF004", (1,)))


def test_pcf_rule_selection_keeps_actions_separate() -> None:
    source = "#bad standalone spacing\nregular = compute()#ordinary trailing words that need moving\nignored = compute()#noqa\n"

    standalone_settings = CheckSettings(select=("PCF001",), line_length=28)
    spacing_settings = CheckSettings(select=("PCF002",), line_length=28)
    directive_settings = CheckSettings(select=("PCF003",), line_length=28)
    extraction_settings = CheckSettings(select=("PCF004",), line_length=28)
    spacing_extraction_directive_settings = CheckSettings(select=("PCF002", "PCF003", "PCF004"), line_length=28)

    standalone = formatter.format_source(source, "example.py", settings=standalone_settings, rule_selection=rules_selection.select_rules(standalone_settings), fix=True)
    spacing = formatter.format_source(source, "example.py", settings=spacing_settings, rule_selection=rules_selection.select_rules(spacing_settings), fix=True)
    directive = formatter.format_source(source, "example.py", settings=directive_settings, rule_selection=rules_selection.select_rules(directive_settings), fix=True)
    extraction = formatter.format_source(source, "example.py", settings=extraction_settings, rule_selection=rules_selection.select_rules(extraction_settings), fix=True)
    spacing_extraction_directive = formatter.format_source(
        source,
        "example.py",
        settings=spacing_extraction_directive_settings,
        rule_selection=rules_selection.select_rules(spacing_extraction_directive_settings),
        fix=True,
    )

    assert standalone.new_source == "# bad standalone spacing\nregular = compute()#ordinary trailing words that need moving\nignored = compute()#noqa\n"
    assert spacing.new_source == "#bad standalone spacing\nregular = compute()  # ordinary trailing words that need moving\nignored = compute()  #noqa\n"
    assert directive.new_source == "#bad standalone spacing\nregular = compute()#ordinary trailing words that need moving\nignored = compute()# noqa\n"
    assert extraction.new_source == "#bad standalone spacing\n\n# ordinary trailing words\n# that need moving\nregular = compute()\nignored = compute()#noqa\n"
    assert spacing_extraction_directive.new_source == "#bad standalone spacing\n\n# ordinary trailing words\n# that need moving\nregular = compute()\nignored = compute()  # noqa\n"


@pytest.mark.parametrize(
    "source",
    (
        "values = [\n    item,  # explanation long enough to move above this item\n]\n",
        "call(\n    value,  # explanation long enough to move above this argument\n)\n",
        "if enabled:  # explanation long enough to move above the header\n    pass\n",
        "if enabled: pass  # explanation long enough to move above one line suite\n",
        "if enabled:\n    pass\nelse:  # explanation long enough to move above the else header\n    pass\n",
        "@decorator  # explanation long enough to move above the decorator\ndef function():\n    pass\n",
        "value = (\n    first +  # explanation long enough to move above this continuation\n    second\n)\n",
    ),
)
def test_overlong_trailing_comments_stay_inline_in_sensitive_syntax_positions_by_default(source: str) -> None:
    assert pcf_helpers.format_pcf(source, line_length=32).new_source == source


@pytest.mark.parametrize(
    "source",
    (
        "class Example:  # explanation long enough to move above the class header\n    pass\n",
        "def function():  # explanation long enough to move above the function header\n    pass\n",
        "with context:  # explanation long enough to move above the with header\n    pass\n",
        "try:  # explanation long enough to move above the try header\n    pass\nexcept Error:  # explanation long enough to move above the except header\n    pass\nfinally:  # explanation long enough to move above the finally header\n    pass\n",
        "try:  # explanation long enough to move above the try star header\n    pass\nexcept* Error:  # explanation long enough to move above except star\n    pass\n",
        "match value:  # explanation long enough to move above the match header\n    case 1:  # explanation long enough to move above the case header\n        pass\n",
    ),
)
def test_syntax_aware_extraction_covers_compound_statement_headers(source: str) -> None:
    assert pcf_helpers.format_pcf(source, line_length=32).new_source == source


def test_syntax_aware_extraction_does_not_protect_ordinary_trailing_comments_inside_match_body() -> None:
    source = "match value:\n    case 1:\n        result = compute()  # explanation long enough to move above this statement\n"
    result = pcf_helpers.format_pcf(source, line_length=36)
    assert result.new_source == "match value:\n    case 1:\n        # explanation long enough to\n        # move above this statement\n        result = compute()\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            "values = [\n    item,  # explanation long enough to move above this item\n]\n",
            "values = [\n    # explanation long enough to\n    # move above this item\n    item,\n]\n",
        ),
        (
            "call(\n    value,  # explanation long enough to move above this argument\n)\n",
            "call(\n    # explanation long enough to\n    # move above this argument\n    value,\n)\n",
        ),
        (
            "if enabled:  # explanation long enough to move above the header\n    pass\n",
            "# explanation long enough to\n# move above the header\nif enabled:\n    pass\n",
        ),
        (
            "if enabled: pass  # explanation long enough to move above one line suite\n",
            "# explanation long enough to\n# move above one line suite\nif enabled: pass\n",
        ),
        (
            "if enabled:\n    pass\nelse:  # explanation long enough to move above the else header\n    pass\n",
            "if enabled:\n    pass\n# explanation long enough to\n# move above the else header\nelse:\n    pass\n",
        ),
        (
            "@decorator  # explanation long enough to move above the decorator\ndef function():\n    pass\n",
            "# explanation long enough to\n# move above the decorator\n@decorator\ndef function():\n    pass\n",
        ),
        (
            "match value:  # explanation long enough to move above the match header\n    case 1:  # explanation long enough to move above the case header\n        pass\n",
            "# explanation long enough to\n# move above the match header\nmatch value:\n    # explanation long enough to\n    # move above the case header\n    case 1:\n        pass\n",
        ),
        (
            "try:  # explanation long enough to move above the try star header\n    pass\nexcept* Error:  # explanation long enough to move above except star\n    pass\n",
            "# explanation long enough to\n# move above the try star header\ntry:\n    pass\n# explanation long enough to\n# move above except star\nexcept* Error:\n    pass\n",
        ),
    ),
)
def test_overlong_trailing_comments_can_move_from_sensitive_syntax_positions_when_syntax_awareness_is_disabled(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source, line_length=32, comment_trailing_extraction_syntax_aware=False)
    assert result.new_source == expected


@pytest.mark.parametrize(
    "comment",
    (
        "- alpha beta gamma delta epsilon",
        "* alpha beta gamma delta epsilon",
        "> alpha beta gamma delta epsilon",
        "| alpha beta gamma delta epsilon",
        "+ alpha beta gamma delta epsilon",
        "<= alpha beta gamma delta epsilon",
        ">= alpha beta gamma delta epsilon",
        "== alpha beta gamma delta epsilon",
        "!= alpha beta gamma delta epsilon",
        "-> alpha beta gamma delta epsilon",
        "=> alpha beta gamma delta epsilon",
    ),
)
def test_operator_like_trailing_comments_stay_inline_regardless_of_structure_settings(comment: str) -> None:
    source = f"value = compute()  # {comment}\n"
    result = pcf_helpers.format_pcf(
        source,
        line_length=24,
        comment_format_list_items=False,
        comment_format_block_quotes=False,
        comment_preserve_tables=False,
    )
    assert result.new_source == source


@pytest.mark.parametrize(
    ("comment", "expected"),
    (
        ("and alpha beta gamma delta epsilon", "# and alpha beta gamma\n# delta epsilon\nvalue = compute()\n"),
        ("or alpha beta gamma delta epsilon", "# or alpha beta gamma\n# delta epsilon\nvalue = compute()\n"),
        ("not alpha beta gamma delta epsilon", "# not alpha beta gamma\n# delta epsilon\nvalue = compute()\n"),
    ),
)
def test_boolean_operator_words_starting_ordinary_prose_do_not_block_extraction(comment: str, expected: str) -> None:
    source = f"value = compute()  # {comment}\n"
    result = pcf_helpers.format_pcf(
        source,
        line_length=24,
        comment_format_list_items=False,
        comment_format_block_quotes=False,
        comment_preserve_tables=False,
    )
    assert result.new_source == expected


@pytest.mark.parametrize(
    "comment",
    (
        "notebook alpha beta gamma delta epsilon",
        "orphan alpha beta gamma delta epsilon",
        "android alpha beta gamma delta epsilon",
        "value->attribute alpha beta gamma delta epsilon",
        "a+b alpha beta gamma delta epsilon",
        "value|default alpha beta gamma delta epsilon",
    ),
)
def test_operator_like_safety_does_not_block_embedded_operator_words_or_tokens(comment: str) -> None:
    source = f"value = compute()  # {comment}\n"
    result = pcf_helpers.format_pcf(source, line_length=24)
    assert result.new_source is not None
    assert result.new_source != source
    assert result.new_source.endswith("value = compute()\n")


@pytest.mark.parametrize(
    ("source", "kwargs"),
    (
        ("value = compute()  # 1. alpha beta gamma delta epsilon\n", {"comment_format_list_items": True}),
        ("value = compute()  # # alpha beta gamma delta epsilon\n", {"comment_preserve_headings": True}),
        ("value = compute()  # ----\n", {"comment_preserve_headings": True}),
        ("value = compute()  # >>> alpha beta gamma delta epsilon\n", {"comment_preserve_doctests": True}),
        ("value = compute()  # ``` alpha beta gamma delta epsilon\n", {"comment_preserve_code_fences": True}),
        ("value = compute()  # .. note:: alpha beta gamma delta epsilon\n", {"comment_preserve_directives": True}),
        ("value = compute()  # :--- | ---:\n", {"comment_preserve_tables": True}),
        ("value = compute()  # =====  =====\n", {"comment_preserve_tables": True}),
        ("value = compute()  # return alpha beta gamma delta epsilon\n", {"comment_detect_code": True}),
        ("value = compute()  # value = compute()\n", {"comment_detect_statements": True}),
        ("value = compute()  # package.function(value)\n", {"comment_detect_expressions": True}),
    ),
)
def test_enabled_standalone_detectors_make_matching_trailing_content_unsafe(source: str, kwargs: dict[str, bool]) -> None:
    result = pcf_helpers.format_pcf(source, line_length=24, **typing.cast(typing.Any, kwargs))
    assert result.new_source == source


def test_content_detection_keeps_indented_disabled_code_inline_when_spacing_is_unselected() -> None:
    source = "value = compute()  #     x = y alpha beta gamma delta epsilon\n"
    settings = CheckSettings(select=("PCF004",), line_length=24, comment_detect_code=True)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == source


@pytest.mark.parametrize(
    ("source", "kwargs", "expected"),
    (
        ("value = compute()  # 1. alpha beta gamma delta epsilon\n", {"comment_format_list_items": False}, "# 1. alpha beta gamma\n# delta epsilon\nvalue = compute()\n"),
        ("value = compute()  # # alpha beta gamma delta epsilon\n", {"comment_preserve_headings": False}, "# # alpha beta gamma\n# delta epsilon\nvalue = compute()\n"),
        ("long_variable_name = compute()  # ----\n", {"comment_preserve_headings": False, "comment_preserve_tables": False}, "# ----\nlong_variable_name = compute()\n"),
        (
            "value = compute()  # >>> alpha beta gamma delta epsilon\n",
            {"comment_preserve_doctests": False, "comment_format_block_quotes": False},
            "# >>> alpha beta gamma\n# delta epsilon\nvalue = compute()\n",
        ),
        ("value = compute()  # ``` alpha beta gamma delta epsilon\n", {"comment_preserve_code_fences": False}, "# ``` alpha beta gamma\n# delta epsilon\nvalue = compute()\n"),
        ("value = compute()  # .. note:: alpha beta gamma delta epsilon\n", {"comment_preserve_directives": False}, "# .. note:: alpha beta\n# gamma delta epsilon\nvalue = compute()\n"),
        ("value = compute()  # :--- | ---:\n", {"comment_preserve_tables": False}, "# :--- | ---:\nvalue = compute()\n"),
        ("value = compute()  # =====  =====\n", {"comment_preserve_tables": False}, "# =====  =====\nvalue = compute()\n"),
        ("value = compute()  # return alpha beta gamma delta epsilon\n", {"comment_detect_code": False}, "# return alpha beta\n# gamma delta epsilon\nvalue = compute()\n"),
        ("value = compute()  # value = compute()\n", {"comment_detect_statements": False}, "# value = compute()\nvalue = compute()\n"),
        ("value = compute()  # package.function(value)\n", {"comment_detect_expressions": False}, "# package.function(value)\nvalue = compute()\n"),
    ),
)
def test_disabled_standalone_detectors_allow_matching_trailing_content_to_extract(source: str, kwargs: dict[str, bool], expected: str) -> None:
    result = pcf_helpers.format_pcf(source, line_length=24, **typing.cast(typing.Any, kwargs))
    assert result.new_source == expected


@pytest.mark.parametrize(
    "kwargs",
    (
        {"comment_preserve_headings": False},
        {"comment_preserve_tables": False},
    ),
)
def test_overlapping_content_detectors_must_all_allow_extraction(kwargs: dict[str, bool]) -> None:
    source = "long_variable_name = compute()  # ----\n"
    result = pcf_helpers.format_pcf(source, line_length=24, **typing.cast(typing.Any, kwargs))
    assert result.new_source == source


def test_content_awareness_can_be_disabled_for_structure_and_operator_like_comments() -> None:
    source = "value = compute()  # - alpha beta gamma delta epsilon\nother = compute()  # >>> alpha beta gamma delta epsilon\n"
    result = pcf_helpers.format_pcf(source, line_length=24, comment_trailing_extraction_content_aware=False)
    assert result.new_source == "# - alpha beta gamma\n# delta epsilon\nvalue = compute()\n# >>> alpha beta gamma\n# delta epsilon\nother = compute()\n"


def test_content_gate_still_applies_when_syntax_gate_is_disabled() -> None:
    source = "if enabled:  # - alpha beta gamma delta epsilon\n    pass\n"
    result = pcf_helpers.format_pcf(source, line_length=24, comment_trailing_extraction_syntax_aware=False)
    assert result.new_source == source


def test_syntax_gate_still_applies_when_content_gate_is_disabled() -> None:
    source = "if enabled:  # explanation long enough to move above the header\n    pass\n"
    result = pcf_helpers.format_pcf(source, line_length=32, comment_trailing_extraction_content_aware=False)
    assert result.new_source == source


def test_aggressive_extraction_requires_disabling_both_safety_gates() -> None:
    source = "if enabled:  # - alpha beta gamma delta epsilon\n    pass\n"
    result = pcf_helpers.format_pcf(source, line_length=24, comment_trailing_extraction_syntax_aware=False, comment_trailing_extraction_content_aware=False)
    assert result.new_source == "# - alpha beta gamma\n# delta epsilon\nif enabled:\n    pass\n"


def test_url_aware_wrapping_balances_extracted_trailing_comment_url_lines_when_enabled() -> None:
    source = "value = compute()  # alpha beta https://example.com/path alpha\n"

    disabled = pcf_helpers.format_pcf(source, line_length=31, url_aware_wrapping=False)
    default = pcf_helpers.format_pcf(source, line_length=31)

    assert disabled.new_source == "# alpha beta\n# https://example.com/path\n# alpha\nvalue = compute()\n"
    assert default.new_source == "# alpha\n# beta https://example.com/path\n# alpha\nvalue = compute()\n"


def test_standalone_and_trailing_edits_on_adjacent_lines_converge_without_overlap() -> None:
    source = "#standalone explanation with enough words to wrap\nvalue = compute()#trailing explanation with enough words to move\n"
    result = pcf_helpers.format_pcf(source, line_length=28)
    assert result.new_source == "# standalone explanation\n# with enough words to wrap\n\n# trailing explanation with\n# enough words to move\nvalue = compute()\n"
    assert not result.errors


def test_extracted_trailing_comment_adds_boundary_after_adjacent_standalone_comment() -> None:
    source = "# standalone explanation\nvalue = compute()  # trailing explanation with enough words to move\n"
    result = pcf_helpers.format_pcf(source, line_length=28)
    assert result.new_source == "# standalone explanation\n\n# trailing explanation with\n# enough words to move\nvalue = compute()\n"
    assert not result.errors


def test_extracted_trailing_comment_does_not_add_boundary_after_hash_only_comment() -> None:
    source = "#\nvalue = compute()  # trailing explanation with enough words to move\n"
    result = pcf_helpers.format_pcf(source, line_length=28)
    assert result.new_source == "#\n# trailing explanation with\n# enough words to move\nvalue = compute()\n"
    assert not result.errors


def test_extracted_trailing_comment_stays_separate_from_joined_standalone_paragraph() -> None:
    source = "# Existing note.\nvalue = compute()  # Extracted explanation has enough words to require moving above code.\n"
    first = pcf_helpers.format_pcf(source, line_length=34, comment_join_standalone_lines=True)
    assert first.new_source == "# Existing note.\n\n# Extracted explanation has enough\n# words to require moving above\n# code.\nvalue = compute()\n"
    assert {rule.code.tag: count for rule, count in first.fixed_findings.items()} == {"PCF004": 1}
    second = pcf_helpers.format_pcf(first.new_source, line_length=34, comment_join_standalone_lines=True)
    assert second.new_source == first.new_source
    assert not second.fixed_findings
    assert not second.errors


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            "# Existing outer note.\nif enabled:\n    value = compute()  # Extracted explanation has enough words to require moving.\n",
            "# Existing outer note.\nif enabled:\n    # Extracted explanation has\n    # enough words to require\n    # moving.\n    value = compute()\n",
        ),
        (
            "#\nvalue = compute()  # Extracted explanation has enough words to require moving.\n",
            "#\n# Extracted explanation has enough\n# words to require moving.\nvalue = compute()\n",
        ),
        (
            "# noqa\nvalue = compute()  # Extracted explanation has enough words to require moving.\n",
            "# noqa\n# Extracted explanation has enough\n# words to require moving.\nvalue = compute()\n",
        ),
    ),
)
def test_extraction_boundary_blank_is_only_inserted_after_same_indent_regular_standalone_comments(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source, line_length=34)
    assert result.new_source == expected


def test_cr_only_source_uses_detected_line_endings_for_all_generated_lines() -> None:
    source = "# alpha beta gamma delta\rvalue = 1 # comment\r"
    result = pcf_helpers.format_pcf(source, line_length=16, line_ending=LineEnding.AUTO)
    assert result.new_source == "# alpha beta\r# gamma delta\r\r# comment\rvalue = 1"


def test_complex_trailing_extraction_is_idempotent() -> None:
    source = "values = [\n    first,  # first explanation is long enough to move\n    second, # short\n]\n"
    first = pcf_helpers.format_pcf(source, line_length=32)
    assert first.new_source is not None
    second = pcf_helpers.format_pcf(first.new_source, line_length=32)
    assert second.new_source == first.new_source
    assert not second.fixed_findings
    assert not second.errors
