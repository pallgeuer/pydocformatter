# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF408_repeated_section import PDF408RepeatedSection


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF408 selected."""
    resolved_settings = CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_reports_repeated_google_sections_without_fixing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Args:\n        value: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF408RepeatedSection.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Args' repeats earlier section 'Args'",)


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
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring section 'Arguments' repeats earlier section 'Args'",
        "Docstring section 'Returns' repeats earlier section 'Return'",
    )


def test_reports_google_argument_subsection_alias_repeats() -> None:
    source = 'def function(value, option, other):\n    """Summary.\n\n    Keyword Args:\n        option: Option.\n\n    Keyword Arguments:\n        option: More option detail.\n\n    Other Args:\n        other: Other value.\n\n    Other Arguments:\n        other: More other detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (13,))


def test_reports_google_singular_plural_narrative_alias_repeats_without_warns() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Example:\n        function(1)\n\n    Examples:\n        function(2)\n\n    Method:\n        run: First method.\n\n    Methods:\n        close: Second method.\n\n    Note:\n        First note.\n\n    Notes:\n        Second note.\n\n    Reference:\n        First reference.\n\n    References:\n        Second reference.\n\n    Warning:\n        First warning.\n\n    Warn:\n        RuntimeWarning: First warning.\n\n    Warns:\n        UserWarning: Second warning.\n\n    Warnings:\n        Third warning.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (13,), (19,), (25,), (34,), (37,))


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


def test_reports_singular_google_alias_repeats() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Arg:\n        value: Description.\n\n    Args:\n        value: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Args' repeats earlier section 'Arg'",)


def test_literal_block_setting_controls_section_like_text_detection() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Example::\n\n        Args:\n            value: In literal text.\n\n    Args:\n        value: Description.\n    """\n'
    protected = format_source(source)
    unprotected = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False))

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
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_numpy_section_repeats_are_case_insensitive() -> None:
    source = 'def function(value):\n    """Summary.\n\n    PARAMETERS\n    ----------\n    value : int\n        Description.\n\n    parameters\n    ----------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_numpy_colon_section_does_not_count_as_repeat() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters:\n        value: Description.\n\n    Parameters\n    ----------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_numpy_warn_alias_repeats() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warn\n    ----\n    RuntimeWarning\n        First warning.\n\n    Warns\n    -----\n    UserWarning\n        Second warning.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_allows_numpy_warnings_admonition_and_warns_section() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warnings\n    --------\n    Be careful.\n\n    Warns\n    -----\n    RuntimeWarning\n        Runtime warning.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_numpy_section_without_underline_is_still_counted() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    value : int\n        Unparsed text.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)


def test_reports_numpy_section_alias_repeats() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameter\n    ---------\n    value : int\n        Description.\n\n    Parameters\n    ----------\n    value : int\n        More detail.\n\n    Other Parameter\n    ---------------\n    other : int\n        Description.\n\n    Other Params\n    ------------\n    other : int\n        More detail.\n\n    Warning\n    -------\n    RuntimeWarning\n        First warning.\n\n    Warnings\n    --------\n    UserWarning\n        Second warning.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,), (19,), (29,))


def test_reports_repeated_rest_fields() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value: Description.\n    :type value: int\n    :parameter value: More detail.\n    :returns: Result.\n    :return: More result.\n    :rtype: str\n    :raises ValueError: Bad value.\n    :exception ValueError: More bad value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF408RepeatedSection.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring field ':return:' repeats earlier field ':returns:'",)


def test_rest_type_fields_repeat_independently_from_value_fields() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value: Description.\n    :type value: int\n    :type value: str\n    :returns: Result.\n    :rtype: int\n    :rtype: str\n    :yields: Streamed result.\n    :ytype: int\n    :ytype: str\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,), (12,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring field ':rtype:' repeats earlier field ':rtype:'", "Docstring field ':ytype:' repeats earlier field ':ytype:'")


def test_rest_named_attribute_repeats_are_not_reported_by_pdf408() -> None:
    source = 'class Example:\n    """Summary.\n\n    :ivar value: First value.\n    :vartype value: int\n    :var value: Second value.\n    :vartype value: str\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_unknown_rest_fields_repeat_only_with_same_field_name_and_argument() -> None:
    source = 'def function():\n    """Summary.\n\n    :meta private: yes\n    :meta public: yes\n    :meta private: still yes\n    :custom: first\n    :custom: second\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (8,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring field ':meta private:' repeats earlier field ':meta private:'",
        "Docstring field ':custom:' repeats earlier field ':custom:'",
    )


def test_argumentless_rest_fields_do_not_repeat_by_empty_argument() -> None:
    source = 'def function():\n    """Summary.\n\n    :param:\n    :param:\n    :raises:\n    :raises:\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_rest_fields_are_not_checked_without_rest_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value: Description.\n    :parameter value: More detail.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_google_convention_ignores_repeated_numpy_only_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    Parameters\n    ----------\n    value : int\n        More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Args:\n        value: More detail.\n    """\n'
    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        result = format_source(source, settings=CheckSettings(select=("PDF408",), docstring_convention=convention))

        assert result.new_source == source
        assert not result.fixed_findings
        assert not result.unfixed_findings
