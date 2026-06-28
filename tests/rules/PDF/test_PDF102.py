import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
import tests.rule_helpers as rule_helpers
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF100_docstring_indentation import PDF100DocstringIndentation
from pydocformatter.rules.definitions.PDF.PDF102_docstring_trailing_whitespace import PDF102DocstringTrailingWhitespace
from pydocformatter.rules.definitions.PDF.PDF103_docstring_blank_line_whitespace import PDF103DocstringBlankLineWhitespace


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF102",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
        line_bounds=None,
    )
    return category, RuleContext(
        path=category.path,
        settings=category.settings,
        module=category.module,
        metadata_wrapper=category.metadata_wrapper,
        positions=category.positions,
        line_ending=category.line_ending,
        source=category.source,
        source_lines=category.source_lines,
        line_bounds=category.line_bounds,
        category_data=PDF.prepare(category),
    )


def format_pdf003(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF102 selected."""
    resolved_settings = CheckSettings(select=("PDF102",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_removes_trailing_whitespace_from_non_empty_lines_before_newlines() -> None:
    source = 'def function():\n    """Summary.   \n    \n    Body.\t \n    """\n'
    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Summary.\n    \n    Body.\n    """\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
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

    assert result.new_source == 'def function():\n    """Summary.\n"""\n'


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.  \n    Body.  \n    """\n\ndef second():\n    """Other.  \n    """\n'
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

    assert result.new_source == "def function():\r\n    r'''Summary.\r\n    caf\xe9 and \\n text.\r\n    '''\r\n"


def test_pdf000_can_literalize_escaped_newline_before_pdf003_trims_it() -> None:
    source = 'def function():\n    """Summary.  \\nBody.  """\n'
    settings = CheckSettings(select=("PDF000", "PDF102"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\nBody.  """\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_pdf003_and_pdf004_own_different_lines_in_same_docstring() -> None:
    source = 'def function():\n    """Summary.  \n      \n    Body.  \n    """\n'
    settings = CheckSettings(select=("PDF102", "PDF103"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert result.fixed_findings[PDF103DocstringBlankLineWhitespace.meta] == 1


def test_pdf002_pdf003_and_pdf004_can_normalize_same_docstring_in_order() -> None:
    source = 'def function():\n    """Summary.\n      Body.  \n      \n    """\n'
    settings = CheckSettings(select=("PDF100", "PDF102", "PDF103"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n    Body.\n\n    """\n'
    assert result.fixed_findings[PDF100DocstringIndentation.meta] == 1
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert result.fixed_findings[PDF103DocstringBlankLineWhitespace.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified
