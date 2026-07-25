# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF412_repeated_docstring_entry import PDF412RepeatedDocstringEntry


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF412 selected."""
    resolved_settings = CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_reports_repeated_google_parameter_and_attribute_entries_without_fixing() -> None:
    source = 'class Example:\n    """Summary.\n\n    Attributes:\n        value: First value.\n        value: Second value.\n    """\n\n    def function(self, arg):\n        """Summary.\n\n        Args:\n            arg: First value.\n            arg: Second value.\n        """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF412RepeatedDocstringEntry.meta, PDF412RepeatedDocstringEntry.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (14,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring attribute entry 'value' repeats earlier entry", "Docstring parameter entry 'arg' repeats earlier entry")


def test_reports_google_parameter_repeats_across_distinct_sections() -> None:
    source = 'def function(value, option):\n    """Summary.\n\n    Args:\n        value: First value.\n\n    Keyword Args:\n        value: Second value.\n        option: Option.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)


def test_repeated_entry_state_resets_between_docstrings() -> None:
    source = 'def first(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n\n\ndef second(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_allows_same_name_in_distinct_google_entry_kinds() -> None:
    source = (
        'class Example:\n    """Summary.\n\n    Args:\n        value: Constructor value.\n\n    Attributes:\n        value: Stored value.\n\n    Methods:\n        value: Return the value.\n    """\n'
    )
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_google_parameter_entries_ignore_leading_stars() -> None:
    source = 'def function(*args, **kwargs):\n    """Summary.\n\n    Args:\n        *args: First args.\n        args: Second args.\n        **kwargs: First kwargs.\n        kwargs: Second kwargs.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (8,))


def test_reports_repeated_google_method_entries() -> None:
    source = 'class Example:\n    """Summary.\n\n    Methods:\n        run: Start the operation.\n        run: Start it again.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)


def test_google_exception_entries_compare_exact_parsed_names() -> None:
    source = (
        'def function():\n    """Summary.\n\n    Raises:\n        ValueError: First value error.\n        valueError: Distinct spelling.\n        `ValueError`: Same parsed value error.\n    """\n'
    )
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_exception_and_warning_entries_are_distinct_repetition_families() -> None:
    source = 'def function():\n    """Summary.\n\n    Raises:\n        RuntimeWarning: Raised first.\n\n    Warns:\n        RuntimeWarning: Emitted first.\n        RuntimeWarning: Emitted again.\n\n    Raises:\n        RuntimeWarning: Raised again.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,), (12,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring warning entry 'RuntimeWarning' repeats earlier entry",
        "Docstring exception entry 'RuntimeWarning' repeats earlier entry",
    )


def test_reports_all_repeated_names_from_one_warning_entry_in_one_message() -> None:
    source = 'def function():\n    """Summary.\n\n    Warn:\n        RuntimeWarning, UserWarning: First warnings.\n\n    Warns:\n        `RuntimeWarning` | UserWarning | FutureWarning: Repeated warnings.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring warning entry repeats earlier entries: 'RuntimeWarning', 'UserWarning'",)


def test_numpy_exception_and_warning_entries_repeat_only_within_their_own_families() -> None:
    source = 'def function():\n    """Summary.\n\n    Raises\n    ------\n    RuntimeWarning\n        Raised first.\n\n    Warns\n    -----\n    RuntimeWarning\n        Emitted first.\n    RuntimeWarning\n        Emitted again.\n\n    Raises\n    ------\n    RuntimeWarning\n        Raised again.\n    """\n'
    settings = CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((13,), (18,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring warning entry 'RuntimeWarning' repeats earlier entry",
        "Docstring exception entry 'RuntimeWarning' repeats earlier entry",
    )


def test_reports_repeated_generic_named_google_entries() -> None:
    source = 'def function():\n    """Summary.\n\n    See Also:\n        helper: Related helper.\n        helper: More helper detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)


def test_reports_numpy_repeated_names_in_comma_separated_entries() -> None:
    source = 'def function(value, other):\n    """Summary.\n\n    Parameters\n    ----------\n    value, other : int\n        First values.\n    other : str\n        Second other value.\n    value, third : float\n        Second value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,), (10,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring parameter entry 'other' repeats earlier entry", "Docstring parameter entry 'value' repeats earlier entry")


def test_reports_repeated_names_within_one_numpy_entry() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value, value : int\n        Duplicate names in one declaration.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring parameter entry 'value' repeats earlier entry",)


def test_reports_rest_named_value_and_type_fields_independently() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value: First value.\n    :type value: int\n    :parameter value: Second value.\n    :type value: str\n    :raises ValueError: First error.\n    :exception ValueError: Second error.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (7,), (9,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring reST parameter entry 'value' repeats earlier entry",
        "Docstring reST parameter type entry 'value' repeats earlier entry",
        "Docstring reST exception entry 'ValueError' repeats earlier entry",
    )


def test_reports_rest_parameter_aliases_and_type_prefix_duplicates() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param int value: First value.\n    :keyword value: Second value.\n    :type *value: int\n    :type value: str\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring reST parameter entry 'value' repeats earlier entry",
        "Docstring reST parameter type entry 'value' repeats earlier entry",
    )


def test_reports_rest_attribute_value_and_type_fields_independently() -> None:
    source = 'class Example:\n    """Summary.\n\n    :ivar value: First value.\n    :vartype value: int\n    :var value: Second value.\n    :vartype value: str\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring reST attribute entry 'value' repeats earlier entry",
        "Docstring reST attribute type entry 'value' repeats earlier entry",
    )


def test_allows_rest_value_and_type_pair_for_same_name() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value: Description.\n    :type value: int\n    :ivar attribute: Description.\n    :vartype attribute: str\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_unknown_rest_fields_remain_outside_pdf412() -> None:
    source = 'def function():\n    """Summary.\n\n    :meta private: yes\n    :meta private: still yes\n    :custom: first\n    :custom: second\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_rest_exception_aliases_and_multi_name_fields_once_per_repeated_entry() -> None:
    source = 'def function():\n    """Summary.\n\n    :raises ValueError, TypeError: First errors.\n    :exception TypeError: Repeated type error.\n    :except ValueError, RuntimeError: Repeated value error.\n    :raise RuntimeError, RuntimeError: Repeated runtime error.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (6,), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring reST exception entry 'TypeError' repeats earlier entry",
        "Docstring reST exception entry 'ValueError' repeats earlier entry",
        "Docstring reST exception entry 'RuntimeError' repeats earlier entry",
    )


def test_return_and_yield_singletons_remain_outside_pdf412() -> None:
    source = 'def function():\n    """Summary.\n\n    Returns:\n        int: First value.\n\n    Returns:\n        int: Second value.\n\n    Yields:\n        int: First yielded value.\n\n    Yields:\n        int: Second yielded value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_each_later_duplicate_on_later_entry_line() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: First value.\n        value: Second value.\n        value: Third value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (7,))


def test_literal_block_setting_controls_entry_like_text_detection() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        Example::\n\n            value: In literal text.\n\n        value: Description.\n    """\n'
    protected = format_source(source)
    unprotected = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False))

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert not protected.unfixed_findings
    assert unprotected.new_source == source
    assert not unprotected.fixed_findings
    assert tuple(finding.line_numbers for finding in unprotected.unfixed_findings) == ((9,),)


def test_reports_repeated_entries_in_concatenated_docstring_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Args:\\n"\n     "    value: Description.\\n"\n     "    value: More detail.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5),)


def test_ignored_without_google_numpy_or_rest_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: First value.\n        value: Second value.\n    """\n'
    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        result = format_source(source, settings=CheckSettings(select=("PDF412",), docstring_convention=convention))

        assert result.new_source == source
        assert not result.fixed_findings
        assert not result.unfixed_findings
