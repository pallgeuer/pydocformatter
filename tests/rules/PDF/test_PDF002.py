import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, IndentStyle, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF002_incorrect_indentation import PDF002IncorrectIndentation


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF002",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def format_pdf002(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF002 selected."""
    resolved_settings = CheckSettings(select=("PDF002",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_normalizes_over_indented_plain_continuation_lines() -> None:
    source = 'def function():\n    """Summary.\n      First continuation.\n      Second continuation.\n    """\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    """Summary.\n    First continuation.\n    Second continuation.\n    """\n'
    assert result.fixed_findings[PDF002IncorrectIndentation.meta] == 1
    assert not format_pdf002(result.new_source).modified


def test_normalizes_under_indented_plain_continuation_lines() -> None:
    source = 'def function():\n    """Summary.\n  First continuation.\n  Second continuation.\n    """\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    """Summary.\n    First continuation.\n    Second continuation.\n    """\n'


def test_preserves_canonical_margin_for_under_indented_same_line_closing_quotes() -> None:
    source = 'def function():\n    """Summary.\n  Body.\n  """\n'
    expected = 'def function():\n    """Summary.\n    Body.\n    """\n'
    result = format_pdf002(source)

    assert result.new_source == expected
    assert not format_pdf002(result.new_source).modified


def test_preserves_same_line_closing_quotes_margin_when_pdf006_is_selected() -> None:
    source = 'def function():\n    """Summary.\n  Body.\n  """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002", "PDF006")))

    assert result.new_source == 'def function():\n    """Summary.\n    Body.\n    """\n'


def test_module_docstring_uses_empty_canonical_margin() -> None:
    source = '"""Module summary.\n    Body.\n"""\n'
    result = format_pdf002(source)

    assert result.new_source == '"""Module summary.\nBody.\n"""\n'


def test_parenthesized_docstring_with_inline_opening_quotes_uses_statement_indent() -> None:
    source = 'def function():\n    ("""Summary.\n      Body.\n    """)\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    ("""Summary.\n    Body.\n    """)\n'


def test_parenthesized_docstring_with_separate_line_opening_quotes_uses_quote_column() -> None:
    source = 'def function():\n    (\n        """Summary.\n          Body.\n        """\n    )\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    (\n        """Summary.\n        Body.\n        """\n    )\n'


def test_preserves_relative_indentation_for_nested_and_protected_content() -> None:
    source = 'def function():\n    """Summary.\n        - item\n            nested detail\n        >>> value\n            continued\n    """\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    """Summary.\n    - item\n        nested detail\n    >>> value\n        continued\n    """\n'


def test_tab_crossing_common_margin_preserves_residual_relative_indentation() -> None:
    source = 'def function():\n    """Summary.\n\tAlpha.\n\t    Nested.\n    """\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    """Summary.\n    Alpha.\n        Nested.\n    """\n'


def test_blank_line_normalization_accepts_empty_and_canonical_states() -> None:
    source = 'def function():\n    """Summary.\n\n      \n  \n    Done.\n    """\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    \n\n    Done.\n    """\n'


def test_google_sections_use_canonical_header_entry_and_continuation_indentation() -> None:
    source = 'def function(value):\n    """Summary.\n\n      Args:\n          value: Description.\n              Continued description.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n            Continued description.\n    """\n'


def test_google_section_without_entries_shifts_content_under_one_indent_unit() -> None:
    source = 'def function():\n    """Summary.\n\n      Notes:\n          First note.\n            Nested note.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == 'def function():\n    """Summary.\n\n    Notes:\n        First note.\n          Nested note.\n    """\n'


def test_google_section_on_first_docstring_line_keeps_section_unchanged() -> None:
    source = 'def function(value):\n    """Args:\n          value: Description.\n              Continued description.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == source


def test_numpy_section_on_first_docstring_line_keeps_header_adornment_and_entries_aligned() -> None:
    source = 'def function(value):\n    """Parameters\n      ----------\n        value : int\n            Description.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source


def test_numpy_sections_use_canonical_header_adornment_entry_and_description_indentation() -> None:
    source = 'def function(value):\n    """Summary.\n\n      Parameters\n      ----------\n        value : int\n            Description.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'


def test_numpy_section_without_entries_shifts_other_content_to_canonical_margin() -> None:
    source = 'def function():\n    """Summary.\n\n      Notes\n      -----\n          First note.\n            Nested note.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == 'def function():\n    """Summary.\n\n    Notes\n    -----\n    First note.\n      Nested note.\n    """\n'


def test_none_and_pep257_treat_convention_looking_text_as_ordinary_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n      Args:\n        value: Description.\n    """\n'

    none_result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.NONE))
    pep257_result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.PEP257))

    expected = 'def function(value):\n    """Summary.\n\n    Args:\n      value: Description.\n    """\n'
    assert none_result.new_source == expected
    assert pep257_result.new_source == expected


def test_simple_statement_suite_uses_one_configured_indent_unit_after_line_indent() -> None:
    source = 'def function(): """Summary.\nUnder indented.\n  """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), indent_width=2))

    assert result.new_source == 'def function(): """Summary.\n  Under indented.\n  """\n'


def test_configured_tab_convention_indentation_preserves_base_docstring_tabs() -> None:
    source = 'class Example:\n\tdef method(self, value):\n\t\t"""Summary.\n\t\tArgs:\n\t\t    value: Description.\n\t\t        Continued.\n\t\t"""\n'
    result = format_pdf002(
        source,
        settings=CheckSettings(select=("PDF002",), indent_style=IndentStyle.TAB, indent_width=4, docstring_convention=DocstringConvention.GOOGLE),
    )

    assert result.new_source == 'class Example:\n\tdef method(self, value):\n\t\t"""Summary.\n\t\tArgs:\n\t\t\tvalue: Description.\n\t\t\t\tContinued.\n\t\t"""\n'


def test_configured_tab_convention_indentation_can_extend_space_canonical_margin() -> None:
    source = 'class Example:\n    def method(self, value):\n        """Summary.\n\n          Args:\n              value: Description.\n                  Continued.\n        """\n'
    result = format_pdf002(
        source,
        settings=CheckSettings(select=("PDF002",), indent_style=IndentStyle.TAB, indent_width=2, docstring_convention=DocstringConvention.GOOGLE),
    )

    assert result.new_source == 'class Example:\n    def method(self, value):\n        """Summary.\n\n        Args:\n        \tvalue: Description.\n        \t\tContinued.\n        """\n'


def test_google_sections_mixed_entries_protected_content_and_later_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n      Args:\n          value: Description.\n\n          - choice\n              nested\n\n          other: Other description.\n\n          ```text\n          fake: code\n          ```\n\n      Returns:\n          str: Result.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.GOOGLE))

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n        - choice\n            nested\n\n        other: Other description.\n\n        ```text\n        fake: code\n        ```\n\n    Returns:\n        str: Result.\n    """\n'
    )


def test_numpy_sections_mixed_entries_protected_content_and_later_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n      Parameters\n      ----------\n        value : int\n            Description.\n\n            - choice\n              nested\n\n        other : str\n            Other description.\n\n      Returns\n      -------\n        str\n            Result.\n    """\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), docstring_convention=DocstringConvention.NUMPY))

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    - choice\n      nested\n\n    other : str\n        Other description.\n\n    Returns\n    -------\n    str\n        Result.\n    """\n'
    )


def test_plain_complex_protected_layouts_keep_relative_indentation() -> None:
    source = 'def function():\n    """Summary.\n        Intro::\n\n            code line\n              nested code\n\n        > quoted\n        >   continued\n\n        +------+\n        | cell |\n        +------+\n    """\n'
    result = format_pdf002(source)

    assert (
        result.new_source
        == 'def function():\n    """Summary.\n    Intro::\n\n        code line\n          nested code\n\n    > quoted\n    >   continued\n\n    +------+\n    | cell |\n    +------+\n    """\n'
    )


def test_skips_single_line_concatenated_and_unsafe_escaped_docstrings() -> None:
    source = 'def single():\n    """Summary."""\n\ndef concatenated():\n    ("first " "second")\n\ndef escaped():\n    """first\\n  second"""\n\ndef escaped_content():\n    """Summary.\n      \\x41 content.\n    """\n\ndef continuation():\n    """first\\\n  second"""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_non_docstring_string_expressions() -> None:
    source = 'def function():\n    value = 1\n    """not a docstring\n      not normalized\n    """\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_already_canonical_multiline_docstring_has_no_fix_or_finding() -> None:
    source = 'def function():\n    """Summary.\n    Already canonical.\n        Relative indentation.\n    """\n'
    _, context = contexts(source)
    result = PDF002IncorrectIndentation.fix(context)

    assert PDF002IncorrectIndentation.check(context) == ()
    assert result.module.code == source
    assert result.fixed_findings == ()


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.\n      Over.\n    """\n\ndef second():\n    """Summary.\n      Also over.\n    """\n'
    _, context = contexts(source)
    findings = PDF002IncorrectIndentation.check(context)
    fixed = PDF002IncorrectIndentation.fix(context)
    check_only = format_pdf002(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((3,), (8,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((3,), (8,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((3,), (8,))
    _, fixed_context = contexts(fixed.module.code)
    assert PDF002IncorrectIndentation.check(fixed_context) == ()


def test_one_docstring_reports_all_changed_physical_lines_together() -> None:
    source = 'def function():\n    """Summary.\n      First.\n        Second.\n    """\n'
    _, context = contexts(source)
    result = PDF002IncorrectIndentation.fix(context)

    assert tuple(finding.line_numbers for finding in PDF002IncorrectIndentation.check(context)) == ((3, 4),)
    assert tuple(finding.line_numbers for finding in result.fixed_findings) == ((3, 4),)


def test_trailing_evaluated_newline_preserves_separate_closing_delimiter_line() -> None:
    source = 'def function():\n    """Summary.\n      Body.\n"""\n'
    result = format_pdf002(source)

    assert result.new_source == 'def function():\n    """Summary.\n    Body.\n"""\n'


def test_preserves_raw_prefix_quote_delimiter_non_ascii_and_crlf_line_endings() -> None:
    source = "def function():\r\n    r'''Summary.\r\n      caf\xe9 and \\n text.\r\n    '''\r\n"
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), line_ending=LineEnding.CR_LF))

    assert result.new_source == "def function():\r\n    r'''Summary.\r\n    caf\xe9 and \\n text.\r\n    '''\r\n"
