import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF406_repeated_section import PDF406RepeatedSection


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF406 selected."""
    resolved_settings = CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_reports_repeated_google_sections_without_fixing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Args:\n        value: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF406RepeatedSection.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_reports_each_repeated_google_section_after_first() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Args:\n        value: More detail.\n\n    Args:\n        value: Even more detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (10,))


def test_reports_google_section_alias_repeats() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Arguments:\n        value: More detail.\n\n    Return:\n        int: Result.\n\n    Returns:\n        int: More result detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (13,))


def test_reports_google_argument_subsection_alias_repeats() -> None:
    source = 'def function(value, option, other):\n    """Summary.\n\n    Keyword Args:\n        option: Option.\n\n    Keyword Arguments:\n        option: More option detail.\n\n    Other Args:\n        other: Other value.\n\n    Other Arguments:\n        other: More other detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (13,))


def test_reports_google_singular_plural_narrative_alias_repeats_without_warns() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Example:\n        function(1)\n\n    Examples:\n        function(2)\n\n    Note:\n        First note.\n\n    Notes:\n        Second note.\n\n    Warning:\n        First warning.\n\n    Warns:\n        Second warning.\n\n    Warnings:\n        Third warning.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (13,), (22,))


def test_allows_google_warning_admonition_and_warns_section() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warning:\n        Be careful.\n\n    Warns:\n        RuntimeWarning: Runtime warning.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_allows_google_warnings_admonition_and_warns_section() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warnings:\n        Be careful.\n\n    Warns:\n        RuntimeWarning: Runtime warning.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_google_warning_and_warnings_as_singular_plural_repeats() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warning:\n        Be careful.\n\n    Warnings:\n        Also be careful.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_reports_repeated_google_narrative_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Examples:\n        function(1)\n\n    Examples:\n        function(2)\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_reports_google_yield_alias_repeats() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Yield:\n        int: A value.\n\n    Yields:\n        int: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_allows_different_same_rank_google_sections() -> None:
    source = 'def function(value, option):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Keyword Args:\n        option: Option.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_repeated_section_state_resets_between_docstrings() -> None:
    source = 'def first(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n\n\ndef second(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_google_section_repeats_are_case_insensitive() -> None:
    source = 'def function(value):\n    """Summary.\n\n    ARGS:\n        value: Description.\n\n    args:\n        value: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_reports_repeated_google_sections_without_required_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args\n        value: Description.\n\n    Args:\n        value: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_unrecognized_singular_google_alias_is_not_reported() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Arg:\n        value: Description.\n\n    Args:\n        value: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_literal_block_setting_controls_section_like_text_detection() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Example::\n\n        Args:\n            value: In literal text.\n\n    Args:\n        value: Description.\n    """\n'
    protected = format_source(source)
    unprotected = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False))

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert not protected.unfixed_findings
    assert unprotected.new_source == source
    assert not unprotected.fixed_findings
    assert tuple(finding.line_numbers for finding in unprotected.unfixed_findings) == ((9,),)


def test_section_like_text_inside_code_fence_does_not_count_as_repeat() -> None:
    source = (
        'def function(value):\n    """Summary.\n\n    Examples:\n        ```text\n        Args:\n            value: In an example.\n        ```\n\n    Args:\n        value: Description.\n    """\n'
    )
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_repeated_sections_in_concatenated_docstring_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Args:\\n"\n     "    value: Description.\\n\\n"\n     "Args:\\n"\n     "    value: More detail.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5, 6),)


def test_reports_repeated_numpy_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    Parameters\n    ----------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_numpy_section_repeats_are_case_insensitive() -> None:
    source = 'def function(value):\n    """Summary.\n\n    PARAMETERS\n    ----------\n    value : int\n        Description.\n\n    parameters\n    ----------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_numpy_colon_section_does_not_count_as_repeat() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:\n        value: Description.\n\n    Parameters\n    ----------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_numpy_warn_alias_repeats() -> None:
    source = (
        'def function(value):\n    """Summary.\n\n    Warns\n    -----\n    RuntimeWarning\n        First warning.\n\n    Warnings\n    --------\n    UserWarning\n        Second warning.\n    """\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_numpy_section_without_underline_is_still_counted() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    value : int\n        Unparsed text.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)


def test_reports_numpy_section_alias_repeats() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Other Parameters\n    ----------------\n    value : int\n        Description.\n\n    Other Params\n    ------------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_google_convention_ignores_repeated_numpy_only_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    Parameters\n    ----------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Args:\n        value: More detail.\n    """\n'
    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=convention))

        assert result.new_source == source
        assert not result.fixed_findings
        assert not result.unfixed_findings
