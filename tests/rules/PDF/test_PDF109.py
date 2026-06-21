import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, IndentStyle, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF109_multiline_closing_quotes_separate_line import PDF109MultilineClosingQuotesSeparateLine


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF109",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def format_pdf105(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF109 selected."""
    resolved_settings = CheckSettings(select=("PDF109",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_moves_closing_quotes_below_final_content_line() -> None:
    source = 'def function():\n    """Summary.\n\n    Body."""\n'
    result = format_pdf105(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1
    assert not format_pdf105(result.new_source).modified


def test_preserves_first_line_content_whitespace_when_moving_closing_quotes() -> None:
    source = 'def function():\n    """  Summary with leading spaces.\n    More content."""\n'
    result = format_pdf105(source)

    assert result.new_source == 'def function():\n    """  Summary with leading spaces.\n    More content.\n    """\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1


def test_moves_closing_quotes_below_single_content_line() -> None:
    source = 'def function():\n    """\n    Summary."""\n'
    result = format_pdf105(source)

    assert result.new_source == 'def function():\n    """\n    Summary.\n    """\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1
    assert not format_pdf105(result.new_source).modified


def test_leaves_already_separate_docstrings() -> None:
    source = 'def separate():\n    """Summary.\n\n    Body.\n    """\n\ndef one():\n    """Summary.\n    """\n'
    result = format_pdf105(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_final_content_trailing_whitespace_for_other_rules() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.  """\n'
    result = format_pdf105(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.  \n    """\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1


def test_skips_non_raw_backslash_escape_even_when_separating_would_be_possible() -> None:
    source = 'def function():\n    """Summary.\n\n    Body \\"""\n'
    result = format_pdf105(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_parenthesized_and_simple_suite_docstrings_use_canonical_margin() -> None:
    source = 'class Parenthesized:\n    (\n        """Class.\n\n        Body."""\n    )\n\ndef simple(): """Summary.\nBody."""; return None\n'
    result = format_pdf105(source, settings=CheckSettings(select=("PDF109",), indent_width=2))

    assert result.new_source == 'class Parenthesized:\n    (\n        """Class.\n\n        Body.\n        """\n    )\n\ndef simple(): """Summary.\nBody.\n  """; return None\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 2
    assert not format_pdf105(result.new_source, settings=CheckSettings(select=("PDF109",), indent_width=2)).modified


def test_tab_simple_suite_uses_configured_tab_margin() -> None:
    source = 'def function(): """Summary.\nBody."""\n'
    settings = CheckSettings(select=("PDF109",), indent_style=IndentStyle.TAB)
    result = format_pdf105(source, settings=settings)

    assert result.new_source == 'def function(): """Summary.\nBody.\n\t"""\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1


def test_module_decorated_async_method_and_nested_class_use_owner_specific_margins() -> None:
    source = '"""Module.\n\nBody."""\n\nclass Outer:\n    @decorator\n    async def method(self): """Method.\nBody."""; return None\n\n    class Inner:\n        """Class.\n\n        Body."""\n'
    result = format_pdf105(source)

    assert (
        result.new_source
        == '"""Module.\n\nBody.\n"""\n\nclass Outer:\n    @decorator\n    async def method(self): """Method.\nBody.\n        """; return None\n\n    class Inner:\n        """Class.\n\n        Body.\n        """\n'
    )
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 3
    assert not format_pdf105(result.new_source).modified


def test_preserves_crlf_for_generated_closing_separator() -> None:
    source = 'def function():\r\n    """Summary.\r\n\r\n    Body."""\r\n'
    settings = CheckSettings(select=("PDF109",), line_ending=LineEnding.CR_LF)
    result = format_pdf105(source, settings=settings)

    assert result.new_source == 'def function():\r\n    """Summary.\r\n\r\n    Body.\r\n    """\r\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1
    assert not format_pdf105(result.new_source, settings=settings).modified


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.\n\n    Body."""\n\ndef second():\n    """Other.\n\n    Body."""\n'
    _, context = contexts(source)
    findings = PDF109MultilineClosingQuotesSeparateLine.check(context)
    fixed = PDF109MultilineClosingQuotesSeparateLine.fix(context)
    check_only = format_pdf105(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((4,), (9,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((4,), (9,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((4,), (9,))
    _, fixed_context = contexts(fixed.module.code)
    assert PDF109MultilineClosingQuotesSeparateLine.check(fixed_context) == ()


def test_preserves_raw_prefix_quote_delimiter_and_skips_unsafe_shapes() -> None:
    source = "def raw():\n    r'''Path C:\\\\temp.\n    Body.'''\n\ndef escaped():\n    '''Summary.\\nBody.'''\n\ndef concatenated():\n    ('Summary.\\n'\n     'Body.')\n"
    result = format_pdf105(source)

    assert result.new_source == "def raw():\n    r'''Path C:\\\\temp.\n    Body.\n    '''\n\ndef escaped():\n    '''Summary.\\nBody.'''\n\ndef concatenated():\n    ('Summary.\\n'\n     'Body.')\n"
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1


def test_pdf006_trims_final_content_whitespace_before_pdf105_separates_quotes() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.  """\n'
    settings = CheckSettings(select=("PDF105", "PDF109"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF109MultilineClosingQuotesSeparateLine.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_fix_noops_for_blank_and_single_content_docstrings() -> None:
    source = 'def blank():\n    """  \n    """\n\ndef one():\n    """Summary."""\n'
    _, context = contexts(source)
    fixed = PDF109MultilineClosingQuotesSeparateLine.fix(context)

    assert fixed.module.code == source
    assert fixed.fixed_findings == ()
