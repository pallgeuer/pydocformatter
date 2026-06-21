import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli import settings_check
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF103_docstring_blank_line_whitespace import PDF103DocstringBlankLineWhitespace


def contexts(source: str, *, settings: settings_check.CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=settings_check.CheckSettings(select=("PDF103",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def format_pdf004(source: str, *, settings: settings_check.CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF103 selected."""
    resolved_settings = settings_check.CheckSettings(select=("PDF103",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_default_blank_style_makes_ordinary_blank_lines_truly_blank() -> None:
    source = 'def function():\n    """Summary.\n      \n    Body.\n    """\n'
    result = format_pdf004(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF103DocstringBlankLineWhitespace.meta] == 1
    assert not format_pdf004(result.new_source).modified


def test_multiple_blank_line_kinds_in_one_docstring_are_reported_together() -> None:
    source = 'def function():\n    """Summary.\n   \n\t \n    Body.\n      """\n'
    _, context = contexts(source)
    findings = PDF103DocstringBlankLineWhitespace.check(context)
    result = format_pdf004(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n\n    Body.\n    """\n'
    assert tuple(finding.line_numbers for finding in findings) == ((3, 4, 6),)
    assert result.fixed_findings[PDF103DocstringBlankLineWhitespace.meta] == 1
    assert not format_pdf004(result.new_source).modified


def test_aligned_style_aligns_ordinary_blank_lines_to_canonical_margin() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    settings = settings_check.CheckSettings(select=("PDF103",), docstring_blank_line_style=settings_check.DocstringBlankLineStyle.ALIGNED)
    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\n    \n    Body.\n    """\n'
    assert not format_pdf004(result.new_source, settings=settings).modified


def test_aligned_style_simple_suite_uses_configured_tab_indent_unit() -> None:
    source = 'def function(): """Summary.\n\n"""\n'
    settings = settings_check.CheckSettings(select=("PDF103",), docstring_blank_line_style=settings_check.DocstringBlankLineStyle.ALIGNED, indent_style=settings_check.IndentStyle.TAB)
    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def function(): """Summary.\n\t\n"""\n'
    assert not format_pdf004(result.new_source, settings=settings).modified


def test_whitespace_only_opening_quote_line_belongs_to_pdf004() -> None:
    source = 'def function():\n    """   \n    Body.\n    """\n'
    result = format_pdf004(source)

    assert result.new_source == 'def function():\n    """\n    Body.\n    """\n'


def test_whitespace_only_closing_quote_line_is_always_aligned() -> None:
    source = 'def function():\n    """Summary.\n      """\n'
    result = format_pdf004(source)

    assert result.new_source == 'def function():\n    """Summary.\n    """\n'


def test_whitespace_only_single_line_docstrings_are_final_lines() -> None:
    source = '"""   """\n\ndef block_suite():\n    """   """\n\ndef simple_suite(): """   """\n'
    result = format_pdf004(source, settings=settings_check.CheckSettings(select=("PDF103",), indent_width=2))

    assert result.new_source == '""""""\n\ndef block_suite():\n    """    """\n\ndef simple_suite(): """  """\n'


def test_empty_docstrings_are_not_treated_as_closing_quote_prefixes() -> None:
    source = 'def block_suite():\n    """"""\n\ndef simple_suite(): """"""\n'

    default_result = format_pdf004(source)
    aligned_result = format_pdf004(source, settings=settings_check.CheckSettings(select=("PDF103",), docstring_blank_line_style=settings_check.DocstringBlankLineStyle.ALIGNED))

    assert default_result.new_source == source
    assert aligned_result.new_source == source
    assert not default_result.fixed_findings
    assert not aligned_result.fixed_findings


def test_module_docstring_closing_quote_prefix_uses_empty_margin() -> None:
    source = '"""Summary.\n    """\n'
    result = format_pdf004(source)

    assert result.new_source == '"""Summary.\n"""\n'


def test_parenthesized_and_simple_suite_canonical_margins_are_used_for_aligned_blank_lines() -> None:
    source = 'def parenthesized():\n    (\n        """Summary.\n\n        """\n    )\n\ndef simple(): """Summary.\n\n  """\n'
    settings = settings_check.CheckSettings(select=("PDF103",), docstring_blank_line_style=settings_check.DocstringBlankLineStyle.ALIGNED, indent_width=2)
    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def parenthesized():\n    (\n        """Summary.\n        \n        """\n    )\n\ndef simple(): """Summary.\n  \n  """\n'


def test_aligned_style_preserves_tab_canonical_margin() -> None:
    source = 'class Example:\n\tdef method(self):\n\t\t"""Summary.\n\n\t\t"""\n'
    settings = settings_check.CheckSettings(select=("PDF103",), docstring_blank_line_style=settings_check.DocstringBlankLineStyle.ALIGNED, indent_width=4)
    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'class Example:\n\tdef method(self):\n\t\t"""Summary.\n\t\t\n\t\t"""\n'


def test_raw_prefixed_docstring_preserves_literal_backslashes_and_quote_style() -> None:
    source = 'def function(): r"""Path C:\\\\temp\n      \n    """\n'
    result = format_pdf004(source)

    assert result.new_source == 'def function(): r"""Path C:\\\\temp\n\n    """\n'
    assert not format_pdf004(result.new_source).modified


def test_default_blank_style_preserves_crlf_line_endings() -> None:
    source = 'def function():\r\n    """Summary.\r\n      \r\n    """\r\n'
    result = format_pdf004(source)

    assert result.new_source == 'def function():\r\n    """Summary.\r\n\r\n    """\r\n'


def test_does_not_touch_non_empty_trailing_whitespace() -> None:
    source = 'def function():\n    """Summary.  \n    Body.  """\n'
    result = format_pdf004(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_does_not_treat_non_space_tab_whitespace_as_blank_lines() -> None:
    source = 'def function():\n    """Summary.\n\xa0\n\x0c\n\x0b\n    Body."""\n'
    result = format_pdf004(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.\n      \n    """\n\ndef second():\n    """   \n    Body.\n    """\n'
    _, context = contexts(source)
    findings = PDF103DocstringBlankLineWhitespace.check(context)
    fixed = PDF103DocstringBlankLineWhitespace.fix(context)
    check_only = format_pdf004(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((3,), (7,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((3,), (7,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((3,), (7,))
    _, fixed_context = contexts(fixed.module.code)
    assert PDF103DocstringBlankLineWhitespace.check(fixed_context) == ()


def test_skips_concatenated_escaped_and_non_docstring_strings() -> None:
    source = 'def concatenated():\n    ("Summary.\\n"\n     "   \\n"\n     "Body.")\n\ndef escaped():\n    """Summary.\\n   \\nBody."""\n\ndef not_docstring():\n    value = 1\n    """Summary.\n      \n    Body."""\n'
    result = format_pdf004(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf000_can_literalize_escaped_blank_line_before_pdf004_normalizes_it() -> None:
    source = 'def function():\n    """Summary.\\n   \\nBody."""\n'
    settings = settings_check.CheckSettings(select=("PDF000", "PDF103"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\nBody."""\n'
    assert result.fixed_findings[PDF103DocstringBlankLineWhitespace.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified
