import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF101_reflow_required import PDF101ReflowRequired


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF101",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def format_pdf001(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF101 selected."""
    resolved_settings = CheckSettings(select=("PDF101",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def assert_physical_lines_fit(source: str, *, line_length: int) -> None:
    """Assert that all generated physical source lines fit within a character budget."""
    assert all(len(line.rstrip("\r\n")) <= line_length for line in source.splitlines(keepends=True))


def test_check_and_fix_single_line_summary() -> None:
    source = 'def area(radius):\n    """Return the area for a circle with the supplied radius after validating that the radius is finite and non-negative."""\n'
    _, context = contexts(source, settings=CheckSettings(select=("PDF101",), line_length=72))

    findings = PDF101ReflowRequired.check(context)
    result = PDF101ReflowRequired.fix(context)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert tuple(finding.line_numbers for finding in result.fixed_findings) == ((2,),)
    assert result.module.code == 'def area(radius):\n    """Return the area for a circle with the supplied radius after\n    validating that the radius is finite and non-negative."""\n'
    _, fixed_context = contexts(result.module.code, settings=CheckSettings(select=("PDF101",), line_length=72))
    assert PDF101ReflowRequired.check(fixed_context) == ()


def test_reflows_multiline_summary_and_paragraph_without_crossing_blank_lines() -> None:
    source = 'def function():\n    """Summary text that should wrap together with the next summary line\n    and keep the paragraph separate.\n\n    Paragraph text that is long enough to wrap independently from the summary paragraph.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=64))

    assert (
        result.new_source
        == 'def function():\n    """Summary text that should wrap together with the next\n    summary line and keep the paragraph separate.\n\n    Paragraph text that is long enough to wrap independently\n    from the summary paragraph.\n    """\n'
    )
    assert result.fixed_findings[PDF101ReflowRequired.meta] == 1
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=64)).modified


def test_reflows_google_section_descriptions_without_rest_field_protection() -> None:
    source = 'def function(value):\n    """Do work.\n\n    Args:\n        value (int): A value with a long description that should use fixed indentation after wrapping.\n\n    :returns: The computed result with enough descriptive words to require wrapping.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.GOOGLE))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    Args:\n        value (int): A value with a long description that should use fixed\n            indentation after wrapping.\n\n    :returns: The computed result with enough descriptive words to require\n    wrapping.\n    """\n'
    )


def test_reflows_rest_field_descriptions_under_rest_convention() -> None:
    source = 'def function(value):\n    """Do work.\n\n    :returns: The computed result with enough descriptive words to require wrapping.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.REST))

    assert result.new_source == 'def function(value):\n    """Do work.\n\n    :returns: The computed result with enough descriptive words to require\n              wrapping.\n    """\n'


def test_reflows_rest_field_inline_description_without_deleting_protected_body() -> None:
    source = 'def function(value):\n    """Do work.\n\n    :param value: Intro text with enough words here to force wrapping around the configured line length.\n        - First choice.\n          Continued choice.\n        - Second choice.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.REST))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    :param value: Intro text with enough words here to force wrapping around\n                  the configured line length.\n        - First choice.\n          Continued choice.\n        - Second choice.\n    """\n'
    )
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.REST)).modified


def test_reflows_rest_field_description_after_protected_body() -> None:
    source = 'def function(value):\n    """Do work.\n\n    :param value: Intro text that should wrap with later prose when the field is formatted.\n        - First choice.\n          Continued choice.\n        More prose after the protected list that is intentionally long enough to require wrapping by PDF101.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.REST))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    :param value: Intro text that should wrap with later prose when the\n                  field is formatted.\n        - First choice.\n          Continued choice.\n        More prose after the protected list that is intentionally long\n        enough to require wrapping by PDF101.\n    """\n'
    )
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.REST)).modified


def test_reflows_rest_field_continuation_description_with_separator_space() -> None:
    source = 'def function(value):\n    """Do work.\n\n    :param value:\n        Description words long enough to require wrapping around the target line width for checking.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.REST))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    :param value: Description words long enough to require wrapping around\n                  the target line width for checking.\n    """\n'
    )
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.REST)).modified


def test_reflows_malformed_google_section_entries_with_canonical_indentation() -> None:
    source = 'def function(value):\n    """Do work.\n\n      Args:\n          value: Description words long enough to wrap around the target line width for checking indentation.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=72, docstring_convention=DocstringConvention.GOOGLE))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n      Args:\n        value: Description words long enough to wrap around the target\n            line width for checking indentation.\n    """\n'
    )


def test_reflows_long_google_entry_prefix_with_description_on_following_lines() -> None:
    source = 'def function(value):\n    """Do work.\n\n    Args:\n        value (Mapping[str, Sequence[tuple[str, object, bytes, float]]]): A value with enough descriptive words to require wrapping after a long type prefix.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.GOOGLE))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    Args:\n        value (Mapping[str, Sequence[tuple[str, object, bytes, float]]]):\n            A value with enough descriptive words to require wrapping after\n            a long type prefix.\n    """\n'
    )
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.GOOGLE)).modified


def test_reflows_google_exception_entries_with_fixed_continuation_indent() -> None:
    source = (
        'def function(value):\n    """Do work.\n\n    Raises:\n        VeryLongCustomApplicationError: An error with enough descriptive words to require wrapping after an exception name.\n    """\n'
    )
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.GOOGLE))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    Raises:\n        VeryLongCustomApplicationError: An error with enough descriptive\n            words to require wrapping after an exception name.\n    """\n'
    )


def test_google_entry_continuation_indent_uses_configured_indent_width() -> None:
    source = 'def function(value):\n    """Do work.\n\n  Args:\n    value (int): A value with a long description that should use configured indentation after wrapping.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, indent_width=2, docstring_convention=DocstringConvention.GOOGLE))

    assert (
        result.new_source == 'def function(value):\n    """Do work.\n\n  Args:\n    value (int): A value with a long description that should use configured\n    indentation after wrapping.\n    """\n'
    )


def test_reflows_numpy_descriptions_list_items_and_block_quotes() -> None:
    source = 'def function(value):\n    """Do work.\n\n    Parameters\n    ----------\n    value : int\n        A value with a long description that should wrap using the existing indentation.\n\n    - A list item with enough words to require wrapping with hanging indentation.\n    > A block quote with enough words to require prefix preserving wrapping.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=72, docstring_convention=DocstringConvention.NUMPY))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    Parameters\n    ----------\n    value : int\n        A value with a long description that should wrap using the\n        existing indentation.\n\n    - A list item with enough words to require wrapping with hanging\n      indentation.\n    > A block quote with enough words to require prefix preserving\n    > wrapping.\n    """\n'
    )


def test_reflows_malformed_numpy_section_descriptions_with_canonical_indentation() -> None:
    source = 'def function(value):\n    """Do work.\n\n      Parameters\n      ----------\n      value : int\n          Description words long enough to wrap around the target line width for checking indentation.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=72, docstring_convention=DocstringConvention.NUMPY))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n      Parameters\n      ----------\n      value : int\n        Description words long enough to wrap around the target line\n        width for checking indentation.\n    """\n'
    )


def test_protected_blocks_are_unchanged_while_adjacent_prose_reflows() -> None:
    source = 'def function():\n    """Prose before a code fence that is long enough to require wrapping.\n\n    ```python\n    value = compute()\n    ```\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=58))

    assert result.new_source == 'def function():\n    """Prose before a code fence that is long enough to\n    require wrapping.\n\n    ```python\n    value = compute()\n    ```\n    """\n'


def test_fix_preserves_crlf_for_generated_lines() -> None:
    source = 'def function():\r\n    """Summary text with enough words to wrap onto another line."""\r\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=48, line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def function():\r\n    """Summary text with enough words to wrap\r\n    onto another line."""\r\n'


def test_ambiguous_and_concatenated_docstrings_are_skipped() -> None:
    source = 'def escaped():\n    """first\\nsecond line with enough words to require wrapping"""\n\ndef concatenated():\n    ("first line " "with enough words to require wrapping")\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=28))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_long_words_are_not_split() -> None:
    source = 'def function():\n    """supercalifragilisticexpialidocious short words after it."""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=20))

    assert result.new_source == 'def function():\n    """supercalifragilisticexpialidocious\n    short words\n    after it."""\n'


def test_disabled_structure_settings_fall_back_to_plain_reflow() -> None:
    source = 'def function():\n    """- A list item with enough words to require wrapping with hanging indentation.\n\n    > A block quote with enough words to require prefix preserving wrapping.\n    """\n'
    result = format_pdf001(
        source,
        settings=CheckSettings(
            select=("PDF101",),
            line_length=48,
            docstring_parse_list_items=False,
            docstring_parse_block_quotes=False,
        ),
    )

    assert (
        result.new_source
        == 'def function():\n    """- A list item with enough words to\n    require wrapping with hanging indentation.\n\n    > A block quote with enough words to require\n    prefix preserving wrapping.\n    """\n'
    )


def test_tab_indented_docstrings_preserve_tabs_and_use_configured_tab_width() -> None:
    source = 'class Example:\n\tdef method(self):\n\t\t"""Summary words that should wrap according to tab-expanded indentation width."""\n'

    width_four = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=54, indent_width=4))
    width_eight = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=54, indent_width=8))

    assert width_four.new_source == 'class Example:\n\tdef method(self):\n\t\t"""Summary words that should wrap according to\n\t\ttab-expanded indentation width."""\n'
    assert width_eight.new_source == 'class Example:\n\tdef method(self):\n\t\t"""Summary words that should wrap\n\t\taccording to tab-expanded indentation\n\t\twidth."""\n'


def test_fallback_prefix_uses_cst_physical_lines_when_form_feed_precedes_docstring() -> None:
    source = 'x = 1\f\nclass Example:\n\tdef method(self):\n\t\t"""Summary words that should wrap according to tab-expanded indentation width."""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=54, indent_width=4))

    assert result.new_source == 'x = 1\f\nclass Example:\n\tdef method(self):\n\t\t"""Summary words that should wrap according to\n\t\ttab-expanded indentation width."""\n'


def test_reflow_preserves_raw_tab_indent_when_dedent_crosses_tab_stop() -> None:
    source = 'def function(value):\n    """Do work.\n\n    Args:\n\tvalue (int): A value with a long description that should wrap using tab indentation after wrapping.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=76, docstring_convention=DocstringConvention.GOOGLE))

    assert (
        result.new_source
        == 'def function(value):\n    """Do work.\n\n    Args:\n\tvalue (int): A value with a long description that should wrap using\n\t    tab indentation after wrapping.\n    """\n'
    )


def test_preserves_raw_prefix_and_single_quote_delimiter_when_rendering_is_safe() -> None:
    source = "def function():\n    r'''A raw docstring with backslash \\n characters and enough words to wrap safely.'''\n"
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=60))

    assert result.new_source == "def function():\n    r'''A raw docstring with backslash \\n characters and\n    enough words to wrap safely.'''\n"


def test_fix_keeps_non_ascii_code_points_escaped_for_ascii_source() -> None:
    source = '# -*- coding: ascii -*-\ndef function():\n    """A \\xe9 value with enough surrounding words to require wrapping onto another physical line."""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=58))

    assert result.modified
    assert result.new_source is not None
    new_source = result.new_source
    assert new_source.isascii()
    assert "\\xe9" in new_source
    compile(new_source.encode("ascii"), "example.py", "exec")
    _, fixed_context = contexts(new_source, settings=CheckSettings(select=("PDF101",), line_length=58))
    assert "\xe9" in PDF.require_data(fixed_context).docstrings[0].value
    assert not format_pdf001(new_source, settings=CheckSettings(select=("PDF101",), line_length=58)).modified


def test_reflows_escaped_delimiters_and_backslashes_when_source_spelling_is_preserved() -> None:
    source = "def delimiter():\n    '''A docstring containing an escaped delimiter \\'\\'\\' and enough words to need wrapping.'''\n\ndef backslash():\n    \"\"\"A docstring containing a literal backslash \\\\ and enough words to need wrapping.\"\"\"\n"
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=50))

    assert (
        result.new_source
        == "def delimiter():\n    '''A docstring containing an escaped delimiter\n    \\'\\'\\' and enough words to need wrapping.'''\n\ndef backslash():\n    \"\"\"A docstring containing a literal backslash\n    \\\\ and enough words to need wrapping.\"\"\"\n"
    )
    assert result.fixed_findings[PDF101ReflowRequired.meta] == 2
    assert not result.unfixed_findings


def test_reflow_preserves_mixed_literal_and_escaped_non_ascii_spellings() -> None:
    source = 'def function():\n    """café \\xe9 words around enough to wrap."""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=40))

    assert result.new_source == 'def function():\n    """café \\xe9 words around enough to\n    wrap."""\n'
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=40)).modified


def test_reflow_counts_opening_delimiter_width_for_first_physical_line() -> None:
    source = 'def f():\n    """alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron."""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=40))

    assert result.new_source == 'def f():\n    """alpha beta gamma delta epsilon\n    zeta eta theta iota kappa lambda mu\n    nu xi omicron."""\n'
    assert_physical_lines_fit(result.new_source, line_length=40)


def test_reflow_counts_module_docstring_opening_delimiter_width() -> None:
    source = '"""alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron."""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=40))

    assert result.new_source == '"""alpha beta gamma delta epsilon zeta\neta theta iota kappa lambda mu nu xi\nomicron."""\n'
    assert_physical_lines_fit(result.new_source, line_length=40)


def test_reflow_counts_prefixed_and_single_quote_opening_delimiter_widths() -> None:
    raw = 'def f():\n    r"""alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"""\n'
    single_quoted = "def f():\n    '''alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron.'''\n"

    raw_result = format_pdf001(raw, settings=CheckSettings(select=("PDF101",), line_length=40))
    single_quoted_result = format_pdf001(single_quoted, settings=CheckSettings(select=("PDF101",), line_length=40))

    assert raw_result.new_source == 'def f():\n    r"""alpha beta gamma delta epsilon\n    zeta eta theta iota kappa lambda mu\n    nu xi omicron"""\n'
    assert single_quoted_result.new_source == "def f():\n    '''alpha beta gamma delta epsilon\n    zeta eta theta iota kappa lambda mu\n    nu xi omicron.'''\n"
    assert_physical_lines_fit(raw_result.new_source, line_length=40)
    assert_physical_lines_fit(single_quoted_result.new_source, line_length=40)


def test_reflow_counts_same_line_closing_delimiter_width_when_pdf001_renders_it() -> None:
    source = 'def f():\n    """alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau"""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=30))

    assert result.new_source == 'def f():\n    """alpha beta gamma delta\n    epsilon zeta eta theta\n    iota kappa lambda mu nu xi\n    omicron pi rho sigma\n    tau"""\n'
    assert_physical_lines_fit(result.new_source, line_length=30)


def test_reflow_uses_region_offsets_when_description_matches_entry_prefix() -> None:
    source = 'def function(x):\n    """Do work.\n\n    Args:\n        x: x words around enough to wrap after a matching entry name.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=52, docstring_convention=DocstringConvention.GOOGLE))

    assert result.modified
    assert result.new_source == 'def function(x):\n    """Do work.\n\n    Args:\n        x: x words around enough to wrap after a\n            matching entry name.\n    """\n'
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=52, docstring_convention=DocstringConvention.GOOGLE)).modified


def test_reflow_counts_escaped_non_ascii_source_width_when_wrapping() -> None:
    escaped = 'def function():\n    """\\xe9\\xe9\\xe9 tail words"""\n'
    literal = 'def function():\n    """ééé tail words"""\n'

    escaped_result = format_pdf001(escaped, settings=CheckSettings(select=("PDF101",), line_length=20))
    literal_result = format_pdf001(literal, settings=CheckSettings(select=("PDF101",), line_length=20))

    assert escaped_result.new_source == 'def function():\n    """\\xe9\\xe9\\xe9\n    tail words"""\n'
    assert literal_result.new_source == 'def function():\n    """ééé tail\n    words"""\n'


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_unsupported_escape_reports_non_fixable_finding_without_crashing() -> None:
    source = "def function():\n    " + r'"""bad \z words enough to wrap around the target line width."""' + "\n"
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=40))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_check_mode_reports_all_reflowable_docstrings_without_modifying_source() -> None:
    source = '"""Module docstring with enough words to require wrapping."""\n\ndef function():\n    """Function docstring with enough words to require wrapping."""\n'
    check_result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=42), fix=False)
    fix_result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=42), fix=True)

    assert check_result.new_source == source
    assert not check_result.modified
    assert tuple(finding.line_numbers for finding in check_result.unfixed_findings) == ((1,), (4,))
    assert fix_result.fixed_findings[PDF101ReflowRequired.meta] == 2
    assert fix_result.new_source == '"""Module docstring with enough words to\nrequire wrapping."""\n\ndef function():\n    """Function docstring with enough\n    words to require wrapping."""\n'


def test_reflows_module_docstring_with_trailing_newline_and_separate_closing_delimiter() -> None:
    source = '"""\nModule docstring with enough words to require wrapping onto a second source line.\n"""\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=42))

    assert result.new_source == '"""\nModule docstring with enough words to\nrequire wrapping onto a second source\nline.\n"""\n'
    assert result.fixed_findings[PDF101ReflowRequired.meta] == 1
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=42)).modified


def test_reflow_joins_short_lines_without_requiring_an_overlong_input_line() -> None:
    source = 'def function():\n    """Summary line one\n    line two with words\n    line three.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=72))

    assert result.new_source == 'def function():\n    """Summary line one line two with words line three.\n    """\n'
    assert result.fixed_findings[PDF101ReflowRequired.meta] == 1
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF101",), line_length=72)).modified


def test_protected_structures_stay_opaque_between_reflowed_regions() -> None:
    source = 'def function():\n    """Introductory prose that should wrap before protected structures.\n\n    # Heading that should stay exactly as it is even though it is long enough to wrap\n    >>> call_with_a_very_long_argument_name_that_should_not_be_wrapped()\n    result with many words that should remain part of the doctest transcript\n\n    .. note:: This directive title is long enough that normal prose would wrap here\n\n        Directive body with enough words that it would wrap if it was not protected.\n\n    Example::\n\n        literal_body_call(with_a_very_long_argument_name_that_should_not_wrap)\n\n    | Column A | Column B |\n    | --- | --- |\n    | value with words that should not wrap | another value that should not wrap |\n\n    Trailing prose that should wrap after protected structures and continue with enough extra detail to require another line.\n    """\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=64))

    assert (
        result.new_source
        == 'def function():\n    """Introductory prose that should wrap before protected\n    structures.\n\n    # Heading that should stay exactly as it is even though it is long enough to wrap\n    >>> call_with_a_very_long_argument_name_that_should_not_be_wrapped()\n    result with many words that should remain part of the doctest transcript\n\n    .. note:: This directive title is long enough that normal prose would wrap here\n\n        Directive body with enough words that it would wrap if it was not protected.\n\n    Example::\n\n        literal_body_call(with_a_very_long_argument_name_that_should_not_wrap)\n\n    | Column A | Column B |\n    | --- | --- |\n    | value with words that should not wrap | another value that should not wrap |\n\n    Trailing prose that should wrap after protected structures\n    and continue with enough extra detail to require another\n    line.\n    """\n'
    )
    check_result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=64), fix=False)
    assert tuple(finding.line_numbers for finding in check_result.unfixed_findings) == ((2, 20),)


def test_disabling_all_generic_structure_parsing_reflows_special_looking_lines_as_plain_text() -> None:
    source = 'def function():\n    """# Heading\n    >>> call()\n    - item\n    > quote\n    :param value: description\n    """\n'
    settings = CheckSettings(
        select=("PDF101",),
        line_length=44,
        docstring_parse_list_items=False,
        docstring_parse_headings=False,
        docstring_parse_doctests=False,
        docstring_parse_code_fences=False,
        docstring_parse_block_quotes=False,
        docstring_parse_tables=False,
        docstring_parse_directives=False,
        docstring_parse_literal_blocks=False,
    )
    result = format_pdf001(source, settings=settings)

    assert result.new_source == 'def function():\n    """# Heading >>> call() - item > quote\n    :param value: description\n    """\n'


def test_single_line_suite_docstring_reflow_uses_literal_column_for_generated_lines() -> None:
    source = 'def function(): """Summary text with enough words to wrap onto a second source line."""; return None\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=48))

    assert result.new_source == 'def function(): """Summary text with enough\n                words to wrap onto a second\n                source line."""; return None\n'


def test_lf_line_ending_setting_only_controls_generated_docstring_lines() -> None:
    source = 'def function():\r\n    """Summary text with enough words to wrap onto another line."""\r\nvalue = 1\r\n'
    result = format_pdf001(source, settings=CheckSettings(select=("PDF101",), line_length=48, line_ending=LineEnding.LF))

    assert result.new_source == 'def function():\r\n    """Summary text with enough words to wrap\n    onto another line."""\r\nvalue = 1\r\n'
