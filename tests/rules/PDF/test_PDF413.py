# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF102_docstring_trailing_whitespace import PDF102DocstringTrailingWhitespace
from pydocformatter.rules.definitions.PDF.PDF400_section_name_capitalization import PDF400SectionNameCapitalization
from pydocformatter.rules.definitions.PDF.PDF401_section_name_pluralization import PDF401SectionNamePluralization
from pydocformatter.rules.definitions.PDF.PDF405_section_underline_format import PDF405SectionUnderlineFormat
from pydocformatter.rules.definitions.PDF.PDF413_section_name_superfluous_colon import PDF413SectionNameSuperfluousColon


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF413 selected."""
    resolved_settings = CheckSettings(select=("PDF413",), docstring_convention=DocstringConvention.NUMPY) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_removes_numpy_section_name_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert PDF413SectionNameSuperfluousColon.meta.name == "section-name-superfluous-colon"
    assert not format_source(result.new_source).modified


def test_removes_multiple_numpy_section_name_colons_and_trailing_whitespace() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:\t\n    ----------\n    value : int\n        Description.\n\n    Returns:   \n    -------\n    int\n        Result.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    Returns\n    -------\n    int\n        Result.\n    """\n'
    )
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert not format_source(result.new_source).modified


def test_removes_unparsed_numpy_section_name_colon_before_body() -> None:
    source = 'def function():\n    """Summary.\n\n    Returns:\n    int\n        Result.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Returns\n    int\n        Result.\n    """\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert not format_source(result.new_source).modified


def test_removes_unparsed_multiword_numpy_section_name_colon() -> None:
    source = 'def function():\n    """Summary.\n\n    See Also:\n    Other reference.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    See Also\n    Other reference.\n    """\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1


def test_removes_numpy_section_name_colon_before_same_line_closing_quotes() -> None:
    source = 'def function():\n    """Summary.\n\n    Returns:"""\n'
    result = format_source(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Returns"""\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_noncanonical_numpy_section_name_spelling_when_removing_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    parameter:\n    ---------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    parameter\n    ---------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1


def test_preserves_crlf_line_endings_when_removing_numpy_section_name_colon() -> None:
    source = 'def function(value):\r\n    """Summary.\r\n\r\n    Parameters:\t\r\n    ----------\r\n    value : int\r\n        Description.\r\n    """\r\n'
    settings = CheckSettings(select=("PDF413",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\r\n    """Summary.\r\n\r\n    Parameters\r\n    ----------\r\n    value : int\r\n        Description.\r\n    """\r\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1


def test_removes_numpy_section_name_colons_from_multiple_docstrings() -> None:
    source = '"""Module summary.\n\nAttributes:\n----------\nvalue : int\n    Description.\n"""\n\ndef function(value):\n    """Summary.\n\n    Parameters:\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == '"""Module summary.\n\nAttributes\n----------\nvalue : int\n    Description.\n"""\n\ndef function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    )
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 2


def test_does_not_remove_pure_numpy_section_name_trailing_whitespace() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters   \n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_unrecognized_colon_heading() -> None:
    source = 'def function():\n    """Summary.\n\n    Unknown:\n    -------\n    Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_non_d406_section_colon_shapes() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters :\n    ----------\n    value : int\n        Description.\n\n    Returns::\n    -------\n    int\n        Result.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_same_line_section_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters: value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_check_only_reports_parsed_and_unparsed_section_name_colon_lines() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:\n    ----------\n    value : int\n        Description.\n\n    Returns:\n    int\n        Result.\n    """\n'
    settings = CheckSettings(select=("PDF413",), docstring_convention=DocstringConvention.NUMPY)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4, 9),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Parameters' should not end with a colon; Docstring section 'Returns' should not end with a colon",)


def test_removes_unparsed_section_before_parsed_section_in_source_order() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns:\n    int\n        Result.\n\n    Parameters:\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Returns\n    int\n        Result.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source).modified


def test_ignores_numpy_section_name_inside_prose_continuation() -> None:
    source = 'def function():\n    """Summary.\n\n    This callable\n    returns:\n    values.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_capitalized_section_name_inside_section_prose() -> None:
    source = 'def function():\n    """Summary.\n\n    Notes\n    -----\n    Some narrative prose.\n    Returns:\n    This is still prose, not a section.\n    See Also:\n    This is still prose, not a section.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_section_underline_format_does_not_promote_section_prose_label() -> None:
    source = 'def function():\n    """Summary.\n\n    Notes\n    -----\n    Some narrative prose.\n    Returns:\n    This is still prose, not a section.\n    """\n'
    settings = CheckSettings(select=("PDF405", "PDF413"), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_section_like_text_inside_code_fences() -> None:
    source = 'def function(value):\n    """Summary.\n\n    ```text\n    Parameters:\n    ----------\n    ```\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_section_like_text_inside_nested_entries_and_protected_blocks() -> None:
    cases = (
        'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Returns:\n            Nested description.\n    """\n',
        'def function():\n    """Summary.\n\n    Example::\n\n        Returns:\n        -------\n    """\n',
        'def function():\n    """Summary.\n\n    >>> Returns:\n    >>> pass\n    """\n',
        'def function():\n    """Summary.\n\n    > Returns:\n    > -------\n    """\n',
    )

    for source in cases:
        result = format_source(source)

        assert result.new_source == source
        assert not result.fixed_findings
        assert not result.unfixed_findings


def test_disabled_code_fence_parsing_allows_section_name_colon_fix() -> None:
    source = 'def function():\n    """Summary.\n\n    ```text\n\n    Returns:\n    -------\n    ```\n    """\n'
    settings = CheckSettings(select=("PDF413",), docstring_convention=DocstringConvention.NUMPY, docstring_parse_code_fences=False)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\n\n    ```text\n\n    Returns\n    -------\n    ```\n    """\n'
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1


def test_reports_unsafe_numpy_section_name_colon_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Parameters:\\n"\n     "----------\\n"\n     "value : int\\n"\n     "    Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5, 6),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Parameters' should not end with a colon",)


def test_ignored_outside_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:\n    ----------\n    value : int\n        Description.\n    """\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE, DocstringConvention.REST):
        result = format_source(source, settings=CheckSettings(select=("PDF413",), docstring_convention=convention))

        assert result.new_source == source
        assert not result.fixed_findings
        assert not result.unfixed_findings


def test_converges_with_numpy_section_underline_format() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:\n    ===\n    value : int\n        Description.\n    """\n'
    settings = CheckSettings(select=("PDF405", "PDF413"), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_converges_with_numpy_section_underline_format_after_unparsed_colon_section() -> None:
    source = 'def function():\n    """Summary.\n\n    Returns:\n    int\n        Result.\n    """\n'
    settings = CheckSettings(select=("PDF405", "PDF413"), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Returns\n    -------\n    int\n        Result.\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_converges_with_numpy_section_name_and_underline_rules() -> None:
    source = 'def function():\n    """Summary.\n\n    return:\n    ------\n    int\n        Result.\n    """\n'
    settings = CheckSettings(select=("PDF400", "PDF401", "PDF405", "PDF413"), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Returns\n    -------\n    int\n        Result.\n    """\n'
    assert result.fixed_findings[PDF400SectionNameCapitalization.meta] == 1
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_pdf102_and_pdf413_cover_distinct_d406_shapes_together() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:   \n    ----------\n    value : int\n        Description.\n\n    Returns   \n    -------\n    int\n        Result.\n    """\n'
    settings = CheckSettings(select=("PDF102", "PDF413"), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    Returns\n    -------\n    int\n        Result.\n    """\n'
    )
    assert result.fixed_findings[PDF102DocstringTrailingWhitespace.meta] == 1
    assert result.fixed_findings[PDF413SectionNameSuperfluousColon.meta] == 1


def test_all_pdf_rules_converge_malformed_numpy_colon_headers_without_reflowing_them() -> None:
    source = 'def related():\n    """Return related references.\n\n    See Also:\n    Other reference.\n    """\n\ndef value():\n    """Return the value.\n\n    Returns:"""\n'
    settings = CheckSettings(select=("PDF",), ignore=("PDF602",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def related():\n    """Return related references.\n\n    See Also\n    --------\n    Other reference.\n    """\n\ndef value():\n    """Return the value.\n\n    Returns\n    -------\n    """\n'
    )
    assert [(rule.code.tag, count) for rule, count in sorted(result.fixed_findings.items(), key=lambda item: item[0].code)] == [("PDF109", 1), ("PDF405", 2), ("PDF413", 2)]
    assert tuple((finding.rule.code.tag, finding.line_numbers, finding.message) for finding in result.unfixed_findings) == (
        ("PDF406", (12,), "Docstring section 'Returns' should not be empty"),
        ("PDF503", (12,), "Docstring has return documentation for a function that does not return"),
    )
