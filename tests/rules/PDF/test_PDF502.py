# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF502_missing_return_documentation import PDF502MissingReturnDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF502 selected."""
    resolved_settings = (
        CheckSettings(select=("PDF502",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
        if settings is None
        else settings
    )
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf502_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF502 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF502MissingReturnDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_meaningful_return_missing_from_docstring() -> None:
    source = 'def function(value):\n    """Return a value."""\n    return value\n'

    assert_pdf502_lines(source, ((3,),))


def test_default_policy_ignores_docstring_without_return_documentation() -> None:
    source = 'def function(value):\n    """Return a value."""\n    return value\n'

    assert_pdf502_lines(source, (), settings=CheckSettings(select=("PDF502",), docstring_convention=DocstringConvention.GOOGLE))


def test_reports_async_function_return_missing_from_docstring() -> None:
    source = 'async def function(value):\n    """Return a value."""\n    return await value\n'

    assert_pdf502_lines(source, ((3,),))


def test_reports_return_on_function_with_non_abstract_dynamic_decorator() -> None:
    source = '@decorators[0]\ndef function():\n    """Return a value."""\n    return 1\n'

    assert_pdf502_lines(source, ((4,),))


def test_empty_return_section_does_not_satisfy_meaningful_return() -> None:
    source = 'def function(value):\n    """Return a value.\n\n    Returns:\n    """\n    return value\n'

    assert_pdf502_lines(source, ((6,),))


def test_google_numpy_and_rest_return_documentation_satisfy_meaningful_return() -> None:
    google = 'def function():\n    """Return a value.\n\n    Returns:\n        int: Value.\n    """\n    return 1\n'
    numpy = 'def function():\n    """Return a value.\n\n    Returns\n    -------\n    int\n        Value.\n    """\n    return 1\n'
    rest = 'def function():\n    """Return a value.\n\n    :returns: Value.\n    """\n    return 1\n'

    assert_pdf502_lines(google, ())
    assert_pdf502_lines(numpy, (), settings=CheckSettings(select=("PDF502",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf502_lines(rest, (), settings=CheckSettings(select=("PDF502",), docstring_convention=DocstringConvention.REST))


def test_singular_google_return_section_satisfies_meaningful_return() -> None:
    source = 'def function():\n    """Return a value.\n\n    Return:\n        int: Value.\n    """\n    return 1\n'

    assert_pdf502_lines(source, ())


def test_mixed_case_singular_google_return_section_satisfies_meaningful_return() -> None:
    source = 'def function():\n    """Return a value.\n\n    rETurn:\n        int: Value.\n    """\n    return 1\n'

    assert_pdf502_lines(source, ())


def test_google_bare_none_return_entry_satisfies_meaningful_return() -> None:
    none_plain = 'def function():\n    """Return a value.\n\n    Returns:\n        None\n    """\n    return 1\n'
    none_period = 'def function():\n    """Return a value.\n\n    Returns:\n        None.\n    """\n    return 1\n'

    assert_pdf502_lines(none_plain, ())
    assert_pdf502_lines(none_period, ())


def test_rtype_satisfies_meaningful_return_documentation() -> None:
    source = 'def function():\n    """Return a value.\n\n    :rtype: int\n    """\n    return 1\n'

    assert_pdf502_lines(source, (), settings=CheckSettings(select=("PDF502",), docstring_convention=DocstringConvention.REST))


def test_none_and_pep257_conventions_keep_missing_return_documentation_inert_for_google_sections() -> None:
    source = 'def function():\n    """Return a value.\n\n    Returns:\n        int: Value.\n    """\n    return 1\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf502_lines(source, (), settings=CheckSettings(select=("PDF502",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS))


def test_parameter_section_does_not_satisfy_meaningful_return() -> None:
    source = 'def function(value):\n    """Return a value.\n\n    Args:\n        value: Value.\n    """\n    return value\n'

    assert_pdf502_lines(source, ((7,),))


def test_none_and_pep257_conventions_keep_missing_return_documentation_inert_for_rest_fields() -> None:
    source = 'def function():\n    """Return a value.\n\n    :returns: Value.\n    """\n    return 1\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf502_lines(source, (), settings=CheckSettings(select=("PDF502",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS))


def test_ignores_bare_return_return_none_generators_missing_docstrings_abstracts_and_stubs() -> None:
    source = 'def bare():\n    """Return nothing."""\n    return\n\n\ndef none():\n    """Return nothing."""\n    return None\n\n\ndef generator():\n    """Generate values."""\n    yield 1\n    return 1\n\n\ndef undocumented():\n    return 1\n\n\n@abc.abstractmethod\ndef abstract():\n    """Return a value."""\n    return 1\n\n\ndef stub():\n    """Return a value."""\n    raise NotImplementedError()\n'

    assert_pdf502_lines(source, ())


def test_ignores_generator_stop_value_after_non_meaningful_yield() -> None:
    bare_yield = 'def function():\n    """Generate values."""\n    yield\n    return 1\n'
    none_yield = 'def function():\n    """Generate values."""\n    yield None\n    return 1\n'

    assert_pdf502_lines(bare_yield, ())
    assert_pdf502_lines(none_yield, ())


def test_parenthesized_none_return_is_not_meaningful() -> None:
    source = 'def function():\n    """Return nothing."""\n    return (None)\n'

    assert_pdf502_lines(source, ())


def test_simple_suite_return_after_docstring_is_checked() -> None:
    source = 'def function(): """Return a value."""; return 1\n'

    assert_pdf502_lines(source, ((1,),))


def test_reports_first_meaningful_return_after_non_meaningful_returns() -> None:
    source = 'def function(flag):\n    """Return a value."""\n    if flag == 1:\n        return\n    if flag == 2:\n        return None\n    return flag\n'

    assert_pdf502_lines(source, ((7,),))


def test_nested_function_return_is_checked_independently() -> None:
    source = 'def outer():\n    """Create a function."""\n    def inner():\n        """Return a value."""\n        return 1\n    return None\n'

    assert_pdf502_lines(source, ((5,),))


def test_nested_class_method_return_does_not_count_for_outer_function() -> None:
    source = 'def outer():\n    """Create a class."""\n    class Inner:\n        def method(self):\n            """Return a value.\n\n            Returns:\n                int: Value.\n            """\n            return 1\n    return None\n'

    assert_pdf502_lines(source, ())
