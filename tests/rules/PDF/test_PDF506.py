# Third-party imports
import pytest

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF506_missing_exception_documentation import PDF506MissingExceptionDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF506 selected."""
    resolved_settings = (
        CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
        if settings is None
        else settings
    )
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf506_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF506 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF506MissingExceptionDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_directly_raised_exception_missing_from_docstring() -> None:
    source = 'def function(value):\n    """Validate a value."""\n    if value < 0:\n        raise ValueError("negative")\n'
    result = format_source(source)

    assert_pdf506_lines(source, ((4,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Raised exception 'ValueError' is missing docstring documentation",)


def test_assertions_are_ignored_by_default() -> None:
    source = 'def function(value):\n    """Validate a value."""\n    assert value\n'

    assert_pdf506_lines(source, ())


def test_enabled_assertion_inventory_reports_assertion_specific_message() -> None:
    source = 'def function(value):\n    """Validate a value."""\n    assert value\n'
    settings = CheckSettings(
        select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS, docstring_include_assertion_errors=True
    )
    result = format_source(source, settings=settings)

    assert_pdf506_lines(source, ((3,),), settings=settings)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("AssertionError raised by an assert statement is missing docstring documentation",)


def test_default_missing_documentation_policy_requires_relevant_section_for_assertions() -> None:
    no_section = 'def function(value):\n    """Validate a value."""\n    assert value\n'
    existing_section = 'def function(value):\n    """Validate a value.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    assert value\n'
    settings = CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE, docstring_include_assertion_errors=True)

    assert_pdf506_lines(no_section, (), settings=settings)
    assert_pdf506_lines(existing_section, ((7,),), settings=settings)


def test_documented_assertion_error_is_accepted_in_google_numpy_and_rest() -> None:
    google = 'def function(value):\n    """Validate.\n\n    Raises:\n        AssertionError: Invalid value.\n    """\n    assert value\n'
    numpy = 'def function(value):\n    """Validate.\n\n    Raises\n    ------\n    AssertionError\n        Invalid value.\n    """\n    assert value\n'
    rest = 'def function(value):\n    """Validate.\n\n    :raises AssertionError: Invalid value.\n    """\n    assert value\n'

    assert_pdf506_lines(google, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE, docstring_include_assertion_errors=True))
    assert_pdf506_lines(numpy, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.NUMPY, docstring_include_assertion_errors=True))
    assert_pdf506_lines(rest, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.REST, docstring_include_assertion_errors=True))


@pytest.mark.parametrize(
    ("body", "expected_message"),
    [
        ('    raise AssertionError("bad")\n    assert value\n', "Raised exception 'AssertionError' is missing docstring documentation"),
        ('    assert value\n    raise AssertionError("bad")\n', "AssertionError raised by an assert statement is missing docstring documentation"),
        ('    assert value; raise AssertionError("bad")\n', "AssertionError raised by an assert statement is missing docstring documentation"),
    ],
)
def test_first_assertion_error_occurrence_owns_deduplicated_finding(body: str, expected_message: str) -> None:
    source = f'def function(value):\n    """Validate a value."""\n{body}'
    settings = CheckSettings(
        select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS, docstring_include_assertion_errors=True
    )
    result = format_source(source, settings=settings)

    assert len(result.unfixed_findings) == 1
    assert result.unfixed_findings[0].message == expected_message


def test_enabled_assertions_join_distinct_direct_raises_in_source_order() -> None:
    source = 'def function(value):\n    """Validate a value."""\n    assert value\n    raise ValueError("bad")\n'
    settings = CheckSettings(
        select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS, docstring_include_assertion_errors=True
    )
    result = format_source(source, settings=settings)

    assert_pdf506_lines(source, ((3,), (4,)), settings=settings)
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "AssertionError raised by an assert statement is missing docstring documentation",
        "Raised exception 'ValueError' is missing docstring documentation",
    )


def test_every_syntactic_assertion_shape_is_collected_with_nested_ownership_boundaries() -> None:
    source = 'async def outer(value):\n    """Validate outer."""\n    if value:\n        assert True\n    try:\n        assert value\n    except ValueError:\n        assert False\n\n    class Nested:\n        assert False\n\n    def inner():\n        """Validate inner."""\n        assert value\n\n    return inner\n'
    settings = CheckSettings(
        select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS, docstring_include_assertion_errors=True
    )

    assert_pdf506_lines(source, ((4,), (15,)), settings=settings)


def test_default_policy_ignores_docstring_without_exception_documentation() -> None:
    source = 'def function(value):\n    """Validate a value."""\n    if value < 0:\n        raise ValueError("negative")\n'

    assert_pdf506_lines(source, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.GOOGLE))


def test_google_numpy_and_rest_exception_documentation_satisfy_direct_raise() -> None:
    google = 'def function():\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'
    numpy = 'def function():\n    """Validate.\n\n    Raises\n    ------\n    ValueError\n        Bad value.\n    """\n    raise ValueError("bad")\n'
    rest = 'def function():\n    """Validate.\n\n    :raises ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf506_lines(google, ())
    assert_pdf506_lines(numpy, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf506_lines(rest, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.REST))


def test_singular_google_raise_section_satisfies_direct_raise() -> None:
    source = 'def function():\n    """Validate.\n\n    Raise:\n        ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf506_lines(source, ())


def test_mixed_case_singular_google_raise_section_satisfies_direct_raise() -> None:
    source = 'def function():\n    """Validate.\n\n    rAIse:\n        ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf506_lines(source, ())


def test_rest_exception_field_aliases_satisfy_direct_raises() -> None:
    source = 'def function(flag):\n    """Validate.\n\n    :except ValueError: Bad value.\n    :exception TypeError: Bad type.\n    """\n    if flag:\n        raise ValueError("bad")\n    raise TypeError("bad")\n'

    assert_pdf506_lines(source, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.REST))


def test_one_google_entry_can_document_multiple_directly_raised_exceptions() -> None:
    source = 'def function(flag):\n    """Validate.\n\n    Raises:\n        ValueError, TypeError: Bad value.\n    """\n    if flag:\n        raise ValueError("bad")\n    raise TypeError("bad")\n'

    assert_pdf506_lines(source, ())


def test_backticked_pipe_separated_google_entry_can_document_multiple_directly_raised_exceptions() -> None:
    source = 'def function(flag):\n    """Validate.\n\n    Raises:\n        `ValueError` | errors.CustomError: Bad value.\n    """\n    if flag:\n        raise ValueError("bad")\n    raise errors.CustomError("bad")\n'

    assert_pdf506_lines(source, ())


def test_backticked_pipe_separated_numpy_and_rest_entries_can_document_multiple_directly_raised_exceptions() -> None:
    numpy = 'def function(flag):\n    """Validate.\n\n    Raises\n    ------\n    `ValueError` | errors.CustomError\n        Bad value.\n    """\n    if flag:\n        raise ValueError("bad")\n    raise errors.CustomError("bad")\n'
    rest = 'def function(flag):\n    """Validate.\n\n    :raises `ValueError | errors.CustomError`: Bad value.\n    """\n    if flag:\n        raise ValueError("bad")\n    raise errors.CustomError("bad")\n'

    assert_pdf506_lines(numpy, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf506_lines(rest, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.REST))


def test_qualified_raise_matches_final_documented_exception_name() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    raise errors.ValueError("bad")\n'

    assert_pdf506_lines(source, ())


def test_raise_with_cause_uses_primary_exception_name() -> None:
    source = 'def function(cause):\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    raise ValueError("bad") from cause\n'

    assert_pdf506_lines(source, ())


def test_qualified_documented_exception_matches_final_raised_exception_name() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        errors.ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf506_lines(source, ())


def test_differently_qualified_exception_names_do_not_match() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        requests.Timeout: Bad value.\n    """\n    raise socket.Timeout("bad")\n'
    result = format_source(source)

    assert_pdf506_lines(source, ((7,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Raised exception 'socket.Timeout' is missing docstring documentation",)


def test_reports_each_distinct_missing_exception_in_source_order() -> None:
    source = 'def function(flag):\n    """Validate."""\n    if flag:\n        raise ValueError("bad")\n    raise TypeError("bad")\n'
    result = format_source(source)

    assert_pdf506_lines(source, ((4,), (5,)))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Raised exception 'ValueError' is missing docstring documentation",
        "Raised exception 'TypeError' is missing docstring documentation",
    )


def test_exception_documentation_matching_is_case_sensitive() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        valueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf506_lines(source, ((7,),))


def test_deduplicates_repeated_missing_exception_by_name() -> None:
    source = 'def function(first):\n    """Validate."""\n    if first:\n        raise ValueError("first")\n    raise ValueError("second")\n'

    assert_pdf506_lines(source, ((4,),))


def test_ignores_bare_raise_dynamic_raise_warning_docs_missing_docstrings_abstracts_stubs_and_nested_raises() -> None:
    source = 'def bare():\n    """Validate."""\n    try:\n        call()\n    except ValueError:\n        raise\n\n\ndef dynamic(error):\n    """Validate."""\n    raise error\n\n\ndef dynamic_subscript(errors):\n    """Validate."""\n    raise errors[0]\n\n\ndef warning_doc():\n    """Validate.\n\n    Warns:\n        ValueError: Bad value.\n    """\n    raise ValueError("bad")\n\n\ndef undocumented():\n    raise ValueError("bad")\n\n\n@abc.abstractmethod\ndef abstract():\n    """Validate."""\n    raise ValueError("bad")\n\n\ndef stub():\n    """Validate."""\n    raise NotImplementedError\n\n\ndef outer():\n    """Validate."""\n    def inner():\n        raise ValueError("bad")\n'

    assert_pdf506_lines(source, ((25,),))


def test_none_and_pep257_conventions_keep_missing_exception_documentation_inert() -> None:
    source = 'def function():\n    """Validate.\n\n    :raises ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf506_lines(source, (), settings=CheckSettings(select=("PDF506",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS))


def test_simple_suite_raise_after_docstring_is_checked() -> None:
    source = 'def function(): """Validate."""; raise ValueError("bad")\n'

    assert_pdf506_lines(source, ((1,),))


def test_numpy_warnings_section_is_not_exception_documentation() -> None:
    missing_source = 'def function():\n    """Validate.\n\n    Warnings\n    --------\n    ValueError\n        Bad value.\n    """\n    raise ValueError("bad")\n'
    extraneous_source = 'def function():\n    """Validate.\n\n    Warnings\n    --------\n    ValueError\n        Bad value.\n    """\n'

    assert_pdf506_lines(
        missing_source,
        ((9,),),
        settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.NUMPY, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS),
    )
    assert_pdf506_lines(extraneous_source, (), settings=CheckSettings(select=("PDF506",), docstring_convention=DocstringConvention.NUMPY))


@pytest.mark.parametrize(
    ("convention", "body"),
    [
        (DocstringConvention.GOOGLE, "Warns:\n        RuntimeWarning: Runtime risk."),
        (DocstringConvention.NUMPY, "Warn\n    ----\n    RuntimeWarning\n        Runtime risk."),
        (DocstringConvention.NUMPY, "Warnings\n    --------\n    RuntimeWarning\n        Runtime risk."),
    ],
)
def test_warning_only_sections_do_not_activate_default_missing_exception_policy(convention: DocstringConvention, body: str) -> None:
    source = f'def function():\n    """Validate.\n\n    {body}\n    """\n    raise ValueError("bad")\n'
    settings = CheckSettings(select=("PDF506",), docstring_convention=convention)

    assert_pdf506_lines(source, (), settings=settings)
