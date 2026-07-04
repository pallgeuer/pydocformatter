import pytest

import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter.cli.settings_check import CheckSettings, LineEnding


def test_default_standalone_formatting_processes_physical_lines_independently() -> None:
    source = "# First physical line with enough words to require wrapping by itself.\n# Second physical line stays separate."

    result = pcf_helpers.format_pcf(source, line_length=40)

    assert result.new_source == "# First physical line with enough words\n# to require wrapping by itself.\n# Second physical line stays separate."
    assert not result.errors


def test_standalone_joining_is_opt_in() -> None:
    source = "# First prose line.\n# Second prose line with more words.\n"

    result = pcf_helpers.format_pcf(source, line_length=35, comment_join_standalone_lines=True)

    assert result.new_source == "# First prose line. Second prose\n# line with more words.\n"


def test_standalone_joining_does_not_cross_colon_header_lines() -> None:
    source = "# Summary.\n# Accepted values:\n# pending, active, disabled.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == source


def test_standalone_joining_keeps_colon_header_separate_from_following_line() -> None:
    source = "# Accepted values:\n# pending, active, disabled.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == source


def test_colon_header_continues_unfinished_standalone_comment_line() -> None:
    source = "# This sentence has been split\n# with a colon:\n# following prose continues here.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == "# This sentence has been split with a colon:\n# following prose continues here.\n"


def test_colon_header_does_not_continue_after_terminal_punctuation() -> None:
    source = "# This sentence is complete.\n# with a colon:\n# following prose continues here.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == source


def test_colon_header_does_not_continue_for_uppercase_label() -> None:
    source = "# Introductory prose without terminal punctuation\n# Accepted values:\n# pending, active, disabled.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == source


def test_colon_header_does_not_continue_for_single_token_label() -> None:
    source = "# Use one of these values\n# values:\n# pending, active, disabled.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == source


def test_colon_header_does_not_continue_for_numeric_label() -> None:
    source = "# Choose one of these cases\n# 1:\n# first case.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == source


def test_colon_header_boundary_preserves_more_specific_comment_units() -> None:
    source = "# Introductory prose without terminal punctuation\n# - Item:\n# > Quote:\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)

    assert result.new_source == source


def test_default_standalone_formatting_already_keeps_colon_header_lines_independent() -> None:
    source = "# Accepted values:\n# pending, active, disabled.\n"

    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=False)

    assert result.new_source == source


def test_standalone_normalization_preserves_additional_hashes_and_eof_state() -> None:
    result = pcf_helpers.format_pcf("##Heading")

    assert result.new_source == "# #Heading"


def test_list_items_and_block_quotes_reflow_with_stable_prefixes() -> None:
    source = "# - A list item with enough words to wrap using hanging indentation.\n# > A quoted paragraph with enough words to wrap while retaining its prefix.\n"

    result = pcf_helpers.format_pcf(source, line_length=34, comment_format_list_items=True, comment_format_block_quotes=True)

    assert (
        result.new_source == "# - A list item with enough words\n#   to wrap using hanging\n#   indentation.\n# > A quoted paragraph with enough\n# > words to wrap while retaining\n# > its prefix.\n"
    )


def test_ordered_nested_list_item_consumes_more_indented_continuation_lines() -> None:
    source = "#   12) A nested ordered item with enough words to require wrapping.\n#       Its continuation is joined to the same item.\n"

    result = pcf_helpers.format_pcf(source, line_length=38, comment_format_list_items=True)

    assert result.new_source == "#   12) A nested ordered item with\n#       enough words to require\n#       wrapping. Its continuation is\n#       joined to the same item.\n"


@pytest.mark.parametrize(
    ("source", "settings"),
    (
        ("## Heading\n# ordinary prose\n", CheckSettings(select=("PCF",), line_length=20, comment_preserve_headings=True)),
        ("# >>> value = function()\n# expected output\n", CheckSettings(select=("PCF",), line_length=20, comment_preserve_doctests=True)),
        ("# ```python\n# value = function()\n# ```\n", CheckSettings(select=("PCF",), line_length=20, comment_preserve_code_fences=True)),
        ("# Name | Value\n# ---- | -----\n# one  | two\n", CheckSettings(select=("PCF",), line_length=20, comment_preserve_tables=True)),
        ("# .. note::\n#    preserved directive body\n# ordinary prose\n", CheckSettings(select=("PCF",), line_length=20, comment_preserve_directives=True)),
    ),
)
def test_enabled_structure_detectors_preserve_recognized_regions(source: str, settings: CheckSettings) -> None:
    result = pcf_helpers.format_pcf_settings(source, settings=settings)

    assert result.new_source == source


def test_preserved_structure_code_does_not_prevent_adjacent_prose_formatting() -> None:
    source = "# Prose before a fence with enough words that it must wrap onto another line.\n# ```python\n#     value = compute()\n# ```\n"

    result = pcf_helpers.format_pcf(source, line_length=40, comment_preserve_code_fences=True, comment_detect_statements=True)

    assert result.new_source == "# Prose before a fence with enough words\n# that it must wrap onto another line.\n# ```python\n#     value = compute()\n# ```\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("# ## Preserved heading\n# prose after heading with enough words to wrap\n", "# ## Preserved heading\n# prose after heading\n# with enough words to\n# wrap\n"),
        (
            "# Name | Value\n# ---- | -----\n# one  | two\n# prose after table with enough words to wrap\n",
            "# Name | Value\n# ---- | -----\n# one  | two\n# prose after table with\n# enough words to wrap\n",
        ),
    ),
)
def test_comments_after_preserved_standalone_structures_resume_formatting(source: str, expected: str) -> None:
    assert pcf_helpers.format_pcf(source, line_length=24, comment_detect_statements=False).new_source == expected


def test_restructuredtext_grid_and_simple_tables_are_preserved() -> None:
    source = "# +------+-------+\n# | Name | Value |\n# +======+=======+\n# | one  | two   |\n# +------+-------+\n# =====  =====\n# Name   Value\n# =====  =====\n"

    result = pcf_helpers.format_pcf(source, line_length=12, comment_preserve_tables=True)

    assert result.new_source == source


def test_disabled_code_detection_protects_the_whole_physical_run() -> None:
    source = "# if enabled:\n# prose that is long enough that it would otherwise be wrapped onto another line\n"

    result = pcf_helpers.format_pcf(source, line_length=35, comment_detect_code=True)

    assert result.new_source == source


@pytest.mark.parametrize(
    ("source", "settings"),
    (
        (
            "# value = compute()\n# prose that would otherwise wrap onto another line\n",
            CheckSettings(select=("PCF",), line_length=30, comment_detect_code=False, comment_detect_statements=True),
        ),
        (
            "# package.function(value)\n# prose that would otherwise wrap onto another line\n",
            CheckSettings(select=("PCF",), line_length=30, comment_detect_code=False, comment_detect_expressions=True),
        ),
    ),
)
def test_enabled_ast_code_detection_protects_the_whole_run(source: str, settings: CheckSettings) -> None:
    disabled = pcf_helpers.format_pcf(source, line_length=30, comment_detect_code=False, comment_detect_statements=False, comment_detect_expressions=False)
    enabled = pcf_helpers.format_pcf_settings(source, settings=settings)

    assert disabled.new_source != source
    assert enabled.new_source == source


def test_comment_edits_preserve_untouched_mixed_endings_and_use_configured_generated_endings() -> None:
    source = "first = 1\r\n# This standalone comment has enough words to wrap over another generated line.\nlast = 2\r\n"

    result = pcf_helpers.format_pcf(source, line_length=42, line_ending=LineEnding.LF)

    assert result.new_source == "first = 1\r\n# This standalone comment has enough words\n# to wrap over another generated line.\nlast = 2\r\n"


@pytest.mark.parametrize(
    ("source", "line_length", "expected"),
    (
        ("#bad spacing   \n", 80, "# bad spacing\n"),
        ("#    excessive leading and trailing spacing    \n", 80, "# excessive leading and trailing spacing\n"),
        ("    #indented comment", 80, "    # indented comment"),
        ("# supercalifragilisticexpialidocious", 12, "# supercalifragilisticexpialidocious"),
        ("# alpha-beta-gamma-delta", 12, "# alpha-beta-gamma-delta"),
        ("#\n#   \n##\n###   \n", 12, "#\n#   \n##\n###   \n"),
    ),
)
def test_standalone_spacing_long_tokens_hash_boundaries_and_eof_are_stable(source: str, line_length: int, expected: str) -> None:
    assert pcf_helpers.format_pcf(source, line_length=line_length).new_source == expected


def test_standalone_wrapping_preserves_missing_final_newline() -> None:
    source = "# alpha beta gamma delta"

    result = pcf_helpers.format_pcf(source, line_length=16, comment_detect_statements=False)

    assert result.new_source == "# alpha beta\n# gamma delta"


def test_indented_wrapping_accounts_for_comment_prefix_width() -> None:
    source = "if enabled:\n    # alpha beta gamma delta epsilon\n    pass\n"
    result = pcf_helpers.format_pcf(source, line_length=18)
    assert result.new_source == "if enabled:\n    # alpha beta\n    # gamma delta\n    # epsilon\n    pass\n"


def test_joining_does_not_cross_code_blank_hash_only_protected_or_indentation_boundaries() -> None:
    source = "# first line\nvalue = 1\n# second line\n\n# third line\n# noqa\n# fourth line\n###\n# fifth line\nif value:\n    # sixth line\n# seventh line\n"
    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)
    assert result.new_source == source


def test_ty_file_level_directive_is_not_joined_with_standalone_prose() -> None:
    source = "# first line\n# ty: ignore[invalid-argument-type]\n# second line\n"
    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)
    assert result.new_source == source


@pytest.mark.parametrize(
    ("marker", "expected"),
    (
        ("-", "# - alpha beta gamma\n#   delta epsilon\n"),
        ("+", "# + alpha beta gamma\n#   delta epsilon\n"),
        ("*", "# * alpha beta gamma\n#   delta epsilon\n"),
        ("1.", "# 1. alpha beta\n#    gamma delta\n#    epsilon\n"),
        ("27)", "# 27) alpha beta\n#     gamma delta\n#     epsilon\n"),
    ),
)
def test_all_supported_list_markers_use_hanging_indentation(marker: str, expected: str) -> None:
    source = f"# {marker} alpha beta gamma delta epsilon\n"
    result = pcf_helpers.format_pcf(source, line_length=20)
    assert result.new_source == expected


def test_list_formatting_can_be_disabled_and_then_uses_plain_wrapping() -> None:
    source = "# - alpha beta gamma delta\n"
    result = pcf_helpers.format_pcf(source, line_length=16, comment_format_list_items=False)
    assert result.new_source == "# - alpha beta\n# gamma delta\n"


def test_list_continuations_stop_at_ordinary_lines_other_items_quotes_and_preserved_regions() -> None:
    source = "# - first item\n#   continued text\n# ordinary prose\n# + second item\n# > quote text\n# ```\n# code()\n# ```\n"
    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)
    assert result.new_source == "# - first item continued text\n# ordinary prose\n# + second item\n# > quote text\n# ```\n# code()\n# ```\n"


def test_tabbed_list_prefix_is_expanded_at_the_actual_comment_column() -> None:
    source = "if enabled:\n\t# \t- alpha beta gamma delta\n\tpass\n"
    result = pcf_helpers.format_pcf(source, line_length=20, indent_width=4)
    assert result.new_source == "if enabled:\n\t#   - alpha beta\n\t#     gamma\n\t#     delta\n\tpass\n"


def test_block_quotes_join_only_identical_prefixes_and_preserve_nested_prefixes() -> None:
    source = "# > alpha beta\n# > gamma delta\n# >> nested alpha\n# >> nested beta\n# > final quote\n"
    result = pcf_helpers.format_pcf(source, line_length=22)
    assert result.new_source == "# > alpha beta gamma\n# > delta\n# >> nested alpha\n# >> nested beta\n# > final quote\n"


def test_block_quote_formatting_can_be_disabled_and_then_uses_plain_wrapping() -> None:
    source = "# > alpha beta gamma delta\n"
    result = pcf_helpers.format_pcf(source, line_length=17, comment_format_block_quotes=False)
    assert result.new_source == "# > alpha beta\n# gamma delta\n"


@pytest.mark.parametrize("marker", ("TODO", "FIXME", "XXX", "HACK", "BUG", "DEBUG", "NOTE", "OPTIMIZE", "REVIEW"))
def test_task_marker_comments_use_hanging_indentation(marker: str) -> None:
    source = f"#{marker}: alpha beta gamma delta epsilon zeta eta theta iota kappa lambda\n"
    result = pcf_helpers.format_pcf(source, line_length=28, comment_detect_statements=False)
    assert result.new_source is not None
    lines = result.new_source.splitlines()
    assert lines[0].startswith(f"# {marker}: ")
    assert all(line.startswith("# " + " " * len(f"{marker}: ")) for line in lines[1:])


def test_task_marker_continuations_are_reflowed_as_one_unit() -> None:
    source = "# TODO: alpha beta gamma\n#       delta epsilon extra words\n#       zeta eta\n"
    result = pcf_helpers.format_pcf(source, line_length=30, comment_detect_statements=False)
    assert result.new_source == "# TODO: alpha beta gamma delta\n#       epsilon extra words\n#       zeta eta\n"


def test_task_marker_formatting_can_be_disabled_and_then_uses_plain_wrapping() -> None:
    source = "#TODO: alpha beta gamma delta\n"
    result = pcf_helpers.format_pcf(source, line_length=20, comment_format_task_markers=False, comment_detect_statements=False)
    assert result.new_source == "# TODO: alpha beta\n# gamma delta\n"


def test_task_marker_statement_like_payload_normalizes_without_wrapping() -> None:
    source = "#TODO: value = compute()\n"
    result = pcf_helpers.format_pcf(source, line_length=10)
    assert result.new_source == "# TODO: value = compute()\n"


def test_task_marker_code_like_continuation_keeps_empty_marker_line() -> None:
    source = "#TODO:\n#       value = compute()\n"
    result = pcf_helpers.format_pcf(source, line_length=10)
    assert result.new_source == "# TODO:\n#       value = compute()\n"


def test_task_marker_statement_like_continuations_normalize_without_joining() -> None:
    source = "#TODO: refactor these calls\n#       x = foo()\n#       y = bar()\n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "# TODO: refactor these calls\n#       x = foo()\n#       y = bar()\n"


def test_task_marker_statement_like_continuations_wrap_when_statement_detection_is_disabled() -> None:
    source = "#TODO: refactor these calls\n#       x = foo()\n#       y = bar()\n"
    result = pcf_helpers.format_pcf(source, line_length=32, comment_detect_statements=False)
    assert result.new_source == "# TODO: refactor these calls x =\n#       foo() y = bar()\n"


def test_task_marker_expression_like_payload_follows_expression_detection_setting() -> None:
    source = '#TODO: very_long(code="line", that="should_not_wrap")\n'
    default = pcf_helpers.format_pcf(source, line_length=32, comment_detect_statements=False, comment_detect_expressions=False)
    expression_aware = pcf_helpers.format_pcf(source, line_length=32, comment_detect_statements=False, comment_detect_expressions=True)
    assert default.new_source == '# TODO: very_long(code="line",\n#       that="should_not_wrap")\n'
    assert expression_aware.new_source == '# TODO: very_long(code="line", that="should_not_wrap")\n'


@pytest.mark.parametrize(
    "source",
    (
        "# # ATX heading\n",
        "# ###### Deep heading\n",
        "# Heading text\n# ------------\n",
        "# ============\n# Heading text\n# ============\n",
    ),
)
def test_heading_variants_are_preserved(source: str) -> None:
    assert pcf_helpers.format_pcf(source, line_length=8, comment_preserve_headings=True).new_source == source


def test_heading_preservation_can_be_disabled_without_misclassifying_short_adornments() -> None:
    source = "## Long heading words\n# title\n# --\n"
    result = pcf_helpers.format_pcf(source, line_length=14, comment_preserve_headings=False, comment_detect_statements=False)
    assert result.new_source == "# # Long\n# heading\n# words\n# title\n# --\n"


def test_doctest_preservation_starts_at_first_prompt_and_ends_at_run_boundary() -> None:
    source = "# prose before prompt with enough words to wrap\n# >>> value = compute()\n# output that stays untouched\n#\n# prose after separator with enough words to wrap\n"
    result = pcf_helpers.format_pcf(source, line_length=26)
    assert (
        result.new_source == "# prose before prompt with\n# enough words to wrap\n# >>> value = compute()\n# output that stays untouched\n#\n# prose after separator\n# with enough words to\n# wrap\n"
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("# ```python\n# code()\n# ````\n# prose after fence is long\n", "# ```python\n# code()\n# ````\n# prose after fence\n# is long\n"),
        ("# ~~~~\n# code()\n# ```\n# still fenced\n", "# ~~~~\n# code()\n# ```\n# still fenced\n"),
        ("# ```\n# unclosed code()\n# remains protected\n", "# ```\n# unclosed code()\n# remains protected\n"),
    ),
)
def test_fence_matching_handles_longer_closers_mismatched_markers_and_unclosed_fences(source: str, expected: str) -> None:
    assert pcf_helpers.format_pcf(source, line_length=20, comment_detect_statements=False).new_source == expected


@pytest.mark.parametrize("fence", ("```", "~~~"))
def test_fence_like_lines_with_trailing_text_do_not_close_preserved_regions(fence: str) -> None:
    source = f"# {fence}python\n# {fence}not-a-close\n# alpha beta gamma delta epsilon\n# {fence}\n"
    result = pcf_helpers.format_pcf(source, line_length=18, comment_preserve_code_fences=True, comment_preserve_headings=False, comment_detect_statements=False)
    assert result.new_source == source
    assert not result.fixed_findings


def test_code_fence_preservation_can_be_disabled() -> None:
    source = "# ```python\n# ordinary words requiring wrapping\n# ```\n"
    result = pcf_helpers.format_pcf(source, line_length=18, comment_preserve_code_fences=False, comment_preserve_headings=False, comment_detect_statements=False)
    assert result.new_source == "# ```python\n# ordinary words\n# requiring\n# wrapping\n# ```\n"


def test_table_detection_requires_structure_and_does_not_preserve_arbitrary_pipes_or_dashes() -> None:
    source = "# prose | with | pipes and enough words to wrap\n# not | a | delimiter\n# --- only one border\n"
    result = pcf_helpers.format_pcf(source, line_length=24, comment_detect_statements=False)
    assert result.new_source == "# prose | with | pipes\n# and enough words to\n# wrap\n# not | a | delimiter\n# --- only one border\n"


def test_table_preservation_can_be_disabled() -> None:
    source = "# Name | Description\n# --- | ---\n# one | several descriptive words\n"
    result = pcf_helpers.format_pcf(source, line_length=18, comment_preserve_tables=False, comment_detect_statements=False)
    assert result.new_source == "# Name |\n# Description\n# --- | ---\n# one | several\n# descriptive\n# words\n"


def test_directive_preservation_includes_only_more_indented_body_and_resumes_formatting() -> None:
    source = "# .. note::\n#    :class: important\n#    directive body remains untouched\n# ordinary prose after directive needs wrapping\n"
    result = pcf_helpers.format_pcf(source, line_length=25)
    assert result.new_source == "# .. note::\n#    :class: important\n#    directive body remains untouched\n# ordinary prose after\n# directive needs\n# wrapping\n"


def test_directive_preservation_can_be_disabled() -> None:
    source = "# .. note::\n#    ordinary directive body words\n"
    result = pcf_helpers.format_pcf(source, line_length=20, comment_preserve_directives=False, comment_detect_statements=False)
    assert result.new_source == "# .. note::\n# ordinary directive\n# body words\n"


@pytest.mark.parametrize(
    "code", ("if enabled:", "for item in items:", "while ready:", "def function():", "class Example:", "try:", "except ValueError:", "print(value)", "return value", "    indented_code()")
)
def test_disabled_code_heuristic_recognizes_all_documented_forms(code: str) -> None:
    source = f"# {code}\n# prose that otherwise needs wrapping\n"
    assert pcf_helpers.format_pcf(source, line_length=24, comment_detect_code=True, comment_detect_statements=False).new_source == source


@pytest.mark.parametrize("prose", ("different behavior is useful", "format values carefully", "classification matters", "printer output is useful", "returning values is useful"))
def test_disabled_code_heuristic_requires_keyword_boundaries(prose: str) -> None:
    source = f"# {prose}\n"
    assert pcf_helpers.format_pcf(source, line_length=20, comment_detect_code=True, comment_detect_statements=False).new_source != source


@pytest.mark.parametrize("statement", ("value = compute()", "import package", "from package import name", "for item in items:\n#     value = process(item)", "def function():\n#     return value"))
def test_statement_detection_recognizes_single_and_multiline_python(statement: str) -> None:
    source = f"# {statement}\n# prose that otherwise wraps\n"
    assert pcf_helpers.format_pcf(source, line_length=20, comment_detect_statements=True).new_source == source


def test_statement_detection_parses_a_multiline_candidate_when_individual_lines_are_incomplete() -> None:
    source = "# value = (\n#     compute()\n# )\n"
    assert pcf_helpers.format_pcf(source, line_length=10, comment_detect_statements=True).new_source == source


@pytest.mark.parametrize(
    "expression", ("package.function(value)", "value.attribute", "values[index]", "left + right", "left < right", "[item for item in values]", "{'key': value}", "lambda value: value")
)
def test_expression_detection_recognizes_nontrivial_expressions(expression: str) -> None:
    source = f"# {expression}\n# prose that otherwise wraps\n"
    assert pcf_helpers.format_pcf(source, line_length=20, comment_detect_statements=False, comment_detect_expressions=True).new_source == source


@pytest.mark.parametrize("expression", ("name", "123", "'text'", "None", "True"))
def test_expression_detection_excludes_bare_names_and_scalar_constants(expression: str) -> None:
    source = f"# {expression}\n# prose that otherwise requires wrapping\n"
    assert pcf_helpers.format_pcf(source, line_length=20, comment_detect_statements=False, comment_detect_expressions=True).new_source != source


def test_code_detection_strips_enabled_list_and_quote_prefixes_and_protects_the_whole_run() -> None:
    source = "# - value = compute()\n# > package.function(value)\n# prose that otherwise wraps\n"
    statements = pcf_helpers.format_pcf(source, line_length=20, comment_detect_statements=True, comment_detect_expressions=False)
    expressions = pcf_helpers.format_pcf(source, line_length=20, comment_detect_statements=False, comment_detect_expressions=True)
    assert statements.new_source == source
    assert expressions.new_source == source


def test_preserved_regions_split_multiline_code_candidates_without_hiding_adjacent_formatting() -> None:
    source = "# prose before fence that needs wrapping\n# ```\n# value = compute()\n# ```\n# prose after fence that also needs wrapping\n"
    result = pcf_helpers.format_pcf(source, line_length=24, comment_detect_statements=True)
    assert result.new_source == "# prose before fence\n# that needs wrapping\n# ```\n# value = compute()\n# ```\n# prose after fence that\n# also needs wrapping\n"


def test_complex_mixed_run_formats_each_semantic_unit_without_crossing_boundaries() -> None:
    source = "# Introductory prose line one.\n# Introductory prose line two.\n# - List item with several descriptive words.\n#   continuation words for the item.\n# > Quoted words on one line.\n# > More quoted words.\n# ## Preserved heading\n# Closing prose with several descriptive words.\n"
    result = pcf_helpers.format_pcf(source, line_length=34, comment_join_standalone_lines=True)
    assert (
        result.new_source
        == "# Introductory prose line one.\n# Introductory prose line two.\n# - List item with several\n#   descriptive words.\n#   continuation words for the\n#   item.\n# > Quoted words on one line. More\n# > quoted words.\n# ## Preserved heading\n# Closing prose with several\n# descriptive words.\n"
    )


def test_standalone_rule_is_independent_of_trailing_rule_selection() -> None:
    source = "#bad standalone spacing\nvalue = 1 #bad trailing spacing\n"
    settings = CheckSettings(select=("PCF001",))
    result = pcf_helpers.format_pcf_settings(source, settings=settings)
    assert result.new_source == "# bad standalone spacing\nvalue = 1 #bad trailing spacing\n"


def test_read_only_check_reports_multiline_semantic_units_without_changing_source() -> None:
    source = "# first prose\n# second prose\n# - list item continuation words\n#   more continuation words\n"
    checked = pcf_helpers.format_pcf(source, fix=False, line_length=24, comment_join_standalone_lines=True)
    assert checked.new_source == source
    assert tuple(finding.line_numbers for finding in checked.unfixed_findings) == ((1, 2), (3, 4))


def test_joined_paragraph_stops_before_block_quote_and_resumes_after_it() -> None:
    source = "# ordinary first line\n# ordinary second line\n# > quoted first line\n# > quoted second line\n# ordinary final line\n"
    result = pcf_helpers.format_pcf(source, line_length=80, comment_join_standalone_lines=True)
    assert result.new_source == "# ordinary first line ordinary second line\n# > quoted first line quoted second line\n# ordinary final line\n"


def test_tab_equivalent_block_quote_prefixes_normalize_as_one_finding() -> None:
    source = "# >\t> alpha beta\n# >\t> gamma delta\n"
    result = pcf_helpers.format_pcf(source, line_length=30, indent_width=4)
    assert result.new_source == "# > > alpha beta gamma delta\n"
    assert sum(result.fixed_findings.values()) == 1
    assert not result.errors


def test_empty_list_markers_and_quotes_are_not_mistaken_for_nonempty_structured_text() -> None:
    source = "# -\n# 1.\n# >\n# ordinary words requiring wrapping\n"
    result = pcf_helpers.format_pcf(source, line_length=20, comment_detect_statements=False)
    assert result.new_source == "# -\n# 1.\n# >\n# ordinary words\n# requiring wrapping\n"


def test_disabling_structure_formatting_also_disables_structure_prefix_stripping_for_code_detection() -> None:
    source = "# - value = compute()\n# > other = compute()\n# prose that needs wrapping here\n"
    result = pcf_helpers.format_pcf(source, line_length=20, comment_format_list_items=False, comment_format_block_quotes=False, comment_detect_statements=True)
    assert result.new_source == "# - value =\n# compute()\n# > other =\n# compute()\n# prose that needs\n# wrapping here\n"


def test_multiline_expression_detection_requires_the_complete_segment_to_parse() -> None:
    code_only = "# (first +\n#  second)\n"
    mixed = f"{code_only}# prose that needs wrapping\n"
    protected = pcf_helpers.format_pcf(code_only, line_length=12, comment_detect_statements=False, comment_detect_expressions=True)
    formatted = pcf_helpers.format_pcf(mixed, line_length=18, comment_detect_statements=False, comment_detect_expressions=True)
    assert protected.new_source == code_only
    assert formatted.new_source == "# (first +\n# second)\n# prose that needs\n# wrapping\n"


def test_overlapping_preserved_structures_do_not_extend_past_their_combined_region() -> None:
    source = "# ```text\n# >>> prompt inside fence\n# ```\n# prose after overlapping structures needs wrapping\n"
    result = pcf_helpers.format_pcf(source, line_length=24, comment_preserve_code_fences=True, comment_preserve_doctests=False, comment_detect_statements=True)
    assert result.new_source == "# ```text\n# >>> prompt inside fence\n# ```\n# prose after\n# overlapping structures\n# needs wrapping\n"


def test_directive_with_tab_indented_body_at_end_of_run_is_preserved() -> None:
    source = "# \t.. note::\n# \t\tbody with a very long line remains untouched\n"
    result = pcf_helpers.format_pcf(source, line_length=12, indent_width=4)
    assert result.new_source == source


def test_unicode_code_points_each_count_as_one_width_column() -> None:
    wide = pcf_helpers.format_pcf("# \u8868\u8868\u8868 alpha beta\n", line_length=12, comment_detect_statements=False)
    combining = pcf_helpers.format_pcf("# e\u0301e\u0301e\u0301 alpha beta\n", line_length=12, comment_detect_statements=False)
    assert wide.new_source == "# \u8868\u8868\u8868 alpha\n# beta\n"
    assert combining.new_source == "# e\u0301e\u0301e\u0301\n# alpha beta\n"


def test_url_aware_wrapping_balances_standalone_comment_url_lines_when_enabled() -> None:
    source = "# alpha beta https://example.com/path alpha\n"

    disabled = pcf_helpers.format_pcf(source, line_length=31, url_aware_wrapping=False)
    default = pcf_helpers.format_pcf(source, line_length=31)

    assert disabled.new_source == "# alpha beta\n# https://example.com/path\n# alpha\n"
    assert default.new_source == "# alpha\n# beta https://example.com/path\n# alpha\n"


def test_url_aware_wrapping_applies_to_standalone_list_items() -> None:
    source = "# - alpha beta https://example.com/path alpha\n"

    disabled = pcf_helpers.format_pcf(source, line_length=33, url_aware_wrapping=False)
    default = pcf_helpers.format_pcf(source, line_length=33)

    assert disabled.new_source == "# - alpha beta\n#   https://example.com/path\n#   alpha\n"
    assert default.new_source == "# - alpha\n#   beta https://example.com/path\n#   alpha\n"


def test_url_aware_wrapping_applies_to_standalone_block_quotes() -> None:
    source = "# > alpha beta https://example.com/path alpha\n"

    disabled = pcf_helpers.format_pcf(source, line_length=33, url_aware_wrapping=False)
    default = pcf_helpers.format_pcf(source, line_length=33)

    assert disabled.new_source == "# > alpha beta\n# > https://example.com/path\n# > alpha\n"
    assert default.new_source == "# > alpha\n# > beta https://example.com/path\n# > alpha\n"


@pytest.mark.parametrize(
    ("source", "line_length", "join_lines", "indent_width"),
    (
        (
            "# first prose line with words\n# second prose line with words\n# - list item with continuation words\n#   more continuation words\n# > quote line with words\n# > another quote line\n",
            24,
            True,
            4,
        ),
        (
            "# ```python\n# value = compute()\n# ```\n# ordinary prose after fence that wraps\n",
            22,
            False,
            4,
        ),
        (
            "if enabled:\n\t# \t- alpha beta gamma delta\n\tpass\n",
            20,
            False,
            4,
        ),
    ),
)
def test_complex_standalone_formatting_is_idempotent(source: str, line_length: int, join_lines: bool, indent_width: int) -> None:
    first = pcf_helpers.format_pcf(source, line_length=line_length, comment_join_standalone_lines=join_lines, indent_width=indent_width)
    assert first.new_source is not None
    second = pcf_helpers.format_pcf(first.new_source, line_length=line_length, comment_join_standalone_lines=join_lines, indent_width=indent_width)
    assert second.new_source == first.new_source
    assert not second.fixed_findings
    assert not second.errors
