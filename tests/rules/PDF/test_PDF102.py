# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF100_docstring_indentation import PDF100DocstringIndentation
from pydocformatter.rules.definitions.PDF.PDF102_docstring_trailing_whitespace import PDF102DocstringTrailingWhitespace
from pydocformatter.rules.definitions.PDF.PDF103_docstring_blank_line_whitespace import PDF103DocstringBlankLineWhitespace
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    resolved_settings = CheckSettings(select=("PDF102",)) if settings is None else settings
    return rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=resolved_settings)


def format_pdf003(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF102 selected."""
    resolved_settings = CheckSettings(select=("PDF102",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_removes_trailing_whitespace_from_non_empty_lines_before_newlines() -> None:
    source = 'def function():\n    """Summary.   \n    \n    Body.\t \n    """\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Summary.   \n    \n    Body.\n    """\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not format_pdf003(result.new_source).modified


def test_removes_trailing_whitespace_from_attribute_docstring_lines() -> None:
    source = 'value = 1\n"""Summary.   \nBody.\t \n"""\n'
    result = format_pdf003(source)

    assert result.new_source == 'value = 1\n"""Summary.   \nBody.\n"""\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not result.unfixed_findings
    assert not format_pdf003(result.new_source).modified


def test_does_not_touch_whitespace_only_lines_or_final_non_empty_content_before_closing_quotes() -> None:
    source = 'def one_line():\n    """Summary.  """\n\ndef multi_line():\n    """Summary.\n    Body.  """\n\ndef blank_lines():\n    """Summary.\n      \n    """\n'
    result = format_pdf003(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_non_space_tab_whitespace_lines_are_non_empty_content() -> None:
    source = 'def function():\n    """Summary.\n\xa0  \n\x0c\t\n    Body."""\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Summary.\n\xa0\n\x0c\n    Body."""\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not format_pdf003(result.new_source).modified


def test_trims_final_non_empty_line_when_followed_by_evaluated_newline() -> None:
    source = 'def function():\n    """Summary.  \n"""\n'
    result = format_pdf003(source)

    assert result.new_source == source
    assert not result.fixed_findings


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary. \n    Body.\t\n    """\n\ndef second():\n    """Other.\t \n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF102DocstringTrailingWhitespace, context)
    fixed = rule_helpers.rule_fix_result(PDF102DocstringTrailingWhitespace, context)
    check_only = format_pdf003(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2, 3), (7,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2, 3), (7,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2, 3), (7,))
    _, fixed_context = contexts(fixed.module.code)
    assert rule_helpers.rule_findings(PDF102DocstringTrailingWhitespace, fixed_context) == ()


def test_skips_concatenated_escaped_and_non_docstring_strings() -> None:
    source = 'def concatenated():\n    ("Summary.  \\n"\n     "Body.  ")\n\ndef escaped():\n    """Summary.  \\nBody.  """\n\ndef not_docstring():\n    value = 1\n    """Summary.  \n    Body.  """\n'
    result = format_pdf003(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_raw_prefix_quote_delimiter_non_ascii_and_crlf_line_endings() -> None:
    source = "def function():\r\n    r'''Summary.  \r\n    caf\xe9 and \\n text.\t \r\n    '''\r\n"
    result = format_pdf003(source, settings=CheckSettings(select=("PDF102",), line_ending=LineEnding.CR_LF))

    assert result.new_source == "def function():\r\n    r'''Summary.  \r\n    caf\xe9 and \\n text.\r\n    '''\r\n"


def test_pdf000_can_literalize_escaped_newline_before_pdf003_trims_it() -> None:
    source = 'def function():\n    """Summary.  \\nBody.  """\n'
    settings = CheckSettings(select=("PDF000", "PDF102"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.  \nBody.  """\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 0
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_pdf003_and_pdf004_own_different_lines_in_same_docstring() -> None:
    source = 'def function():\n    """Summary. \n      \n    Body. \n    """\n'
    settings = CheckSettings(select=("PDF102", "PDF103"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert result.fixed_findings[PDF103DocstringBlankLineWhitespace.meta] == 1


def test_pdf002_pdf003_and_pdf004_can_normalize_same_docstring_in_order() -> None:
    source = 'def function():\n    """Summary.\n      Body. \n      \n    """\n'
    settings = CheckSettings(select=("PDF100", "PDF102", "PDF103"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n    Body.\n\n    """\n'
    assert result.fixed_findings[PDF100DocstringIndentation.meta] == 1
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert result.fixed_findings[PDF103DocstringBlankLineWhitespace.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_preserves_exact_space_hard_break_runs_and_escaped_source_spellings() -> None:
    source = 'def function():\n    """Two spaces.  \n    Three spaces.   \n    Escaped spaces.\\x20\\x20\n    Body."""\n'
    result = format_pdf003(source)

    assert result.new_source == source
    assert not result.fixed_findings


def test_removes_only_tabs_immediately_before_preserved_space_hard_break() -> None:
    source = 'def function():\n    """Literal tab.\t  \n    Escaped tab.\\t\\x20\\x20\n    Body."""\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Literal tab.  \n    Escaped tab.\\x20\\x20\n    Body."""\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not format_pdf003(result.new_source).modified


def test_backslash_breaks_are_not_trailing_whitespace() -> None:
    source = 'def function():\n    r"""Odd backslash.\\\n    Even backslashes.\\\\\n    Body."""\n'
    result = format_pdf003(source)

    assert result.new_source == source
    assert not result.fixed_findings


def test_removes_escaped_single_space_and_tab_with_physical_newline_mapping() -> None:
    source = 'def function():\n    """Summary.\\x20\n    Body.\\t\n    """\n'
    fixed = format_pdf003(source)
    checked = format_pdf003(source, fix=False)

    assert fixed.new_source == 'def function():\n    """Summary.\n    Body.\n    """\n'
    assert tuple((finding.line_numbers, finding.fixable) for finding in checked.unfixed_findings) == (((2, 3), True),)
    assert fixed.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1


def test_escaped_newline_with_removable_whitespace_is_fixed_exactly() -> None:
    source = 'def function():\n    """Summary. \\nBody. \\nTail."""\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Summary.\\nBody.\\nTail."""\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1


def test_fix_preserves_source_continuations_outside_trailing_whitespace() -> None:
    source = 'def function():\n    """Summary. \n    code(\\\n    argument)\n    """\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Summary.\n    code(\\\n    argument)\n    """\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1


def test_fix_preserves_source_continuation_inside_edited_logical_line() -> None:
    source = 'def function():\n    """Summary code(\\\nargument) \n    Tail."""\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Summary code(\\\nargument)\n    Tail."""\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not format_pdf003(result.new_source).modified


def test_fix_preserves_source_continuation_inside_deleted_trailing_whitespace() -> None:
    source = 'def function():\n    """Summary.\t\\\n \n    Tail."""\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Summary.\\\n\n    Tail."""\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not format_pdf003(result.new_source).modified


def test_fix_preserves_source_continuation_between_tabs_before_hard_break() -> None:
    source = 'def function():\n    """Boundary.\t\\\n\t  \n    Tail."""\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Boundary.\\\n  \n    Tail."""\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not format_pdf003(result.new_source).modified


def test_preserved_space_run_keeps_separated_spaces_when_preceding_tabs_are_removed() -> None:
    source = 'def function():\n    """Boundary. \\t\\x20\\x20\n    Body."""\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Boundary. \\x20\\x20\n    Body."""\n'
    assert not format_pdf003(result.new_source).modified


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_unsupported_escape_with_ordinary_trailing_space_is_not_reported_without_a_complete_safe_edit() -> None:
    source = "def function():\n    " + r'"""Bad \z value. ' + '\n    Body.\n    """\n'
    result = format_pdf003(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf101_and_pdf102_share_escaped_hard_break_ownership_without_overlapping_fixes() -> None:
    source = 'def function():\n    """Alpha beta gamma delta epsilon\\t\\x20\\x20\n    zeta eta theta.\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF102"), line_length=36)
    first = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert first.new_source is not None
    second = formatter.format_source(first.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert first.new_source == 'def function():\n    """Alpha beta gamma delta\n    epsilon\\x20\\x20\n    zeta eta theta.\n    """\n'
    assert {rule.code.tag: count for rule, count in first.fixed_findings.items()} == {"PDF101": 1}
    assert second.new_source == first.new_source
    assert not second.fixed_findings
