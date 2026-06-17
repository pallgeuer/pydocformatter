import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF504_missing_yield_documentation import PDF504MissingYieldDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF504 selected."""
    resolved_settings = (
        CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
        if settings is None
        else settings
    )
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf504_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF504 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF504MissingYieldDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_meaningful_yield_missing_from_docstring() -> None:
    source = 'def function():\n    """Generate values."""\n    yield 1\n'

    assert_pdf504_lines(source, ((3,),))


def test_default_policy_ignores_docstring_without_yield_documentation() -> None:
    source = 'def function():\n    """Generate values."""\n    yield 1\n'

    assert_pdf504_lines(source, (), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.GOOGLE))


def test_reports_async_generator_yield_missing_from_docstring() -> None:
    source = 'async def function():\n    """Generate values."""\n    yield 1\n'

    assert_pdf504_lines(source, ((3,),))


def test_empty_yield_section_does_not_satisfy_meaningful_yield() -> None:
    source = 'def function():\n    """Generate values.\n\n    Yields:\n    """\n    yield 1\n'

    assert_pdf504_lines(source, ((6,),))


def test_google_numpy_and_sphinx_yield_documentation_satisfy_meaningful_yield() -> None:
    google = 'def function():\n    """Generate values.\n\n    Yields:\n        int: Value.\n    """\n    yield 1\n'
    numpy = 'def function():\n    """Generate values.\n\n    Yields\n    ------\n    int\n        Value.\n    """\n    yield 1\n'
    sphinx = 'def function():\n    """Generate values.\n\n    :yields: Value.\n    """\n    yield 1\n'

    assert_pdf504_lines(google, ())
    assert_pdf504_lines(numpy, (), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf504_lines(sphinx, (), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.NONE))


def test_google_bare_none_yield_entry_satisfies_meaningful_yield() -> None:
    none_plain = 'def function():\n    """Generate values.\n\n    Yields:\n        None\n    """\n    yield 1\n'
    none_period = 'def function():\n    """Generate values.\n\n    Yields:\n        None.\n    """\n    yield 1\n'

    assert_pdf504_lines(none_plain, ())
    assert_pdf504_lines(none_period, ())


def test_ytype_satisfies_meaningful_yield_documentation() -> None:
    source = 'def function():\n    """Generate values.\n\n    :ytype: int\n    """\n    yield 1\n'

    assert_pdf504_lines(source, (), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.NONE))


def test_yield_from_requires_yield_documentation() -> None:
    source = 'def function(values):\n    """Generate values."""\n    yield from values\n'

    assert_pdf504_lines(source, ((3,),))


def test_ignores_bare_yield_yield_none_missing_docstrings_abstracts_and_stubs() -> None:
    source = 'def bare():\n    """Generate nothing."""\n    yield\n\n\ndef none():\n    """Generate nothing."""\n    yield None\n\n\ndef undocumented():\n    yield 1\n\n\n@abc.abstractmethod\ndef abstract():\n    """Generate values."""\n    yield 1\n\n\ndef stub():\n    """Generate values."""\n    raise NotImplementedError\n'

    assert_pdf504_lines(source, ())


def test_parenthesized_none_yield_is_not_meaningful() -> None:
    source = 'def function():\n    """Generate nothing."""\n    yield (None)\n'

    assert_pdf504_lines(source, ())


def test_yield_inside_lambda_does_not_count_for_enclosing_function() -> None:
    source = 'def function():\n    """Create a generator callback."""\n    callback = lambda: (yield 1)\n    return callback\n'

    assert_pdf504_lines(source, ())


def test_sphinx_field_parsing_setting_controls_sphinx_yield_documentation() -> None:
    source = 'def function():\n    """Generate values.\n\n    :yields: Value.\n    """\n    yield 1\n'

    assert_pdf504_lines(
        source,
        ((6,),),
        settings=CheckSettings(
            select=("PDF504",), docstring_convention=DocstringConvention.NONE, docstring_parse_sphinx_fields=False, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS
        ),
    )


def test_reports_first_meaningful_yield_after_non_meaningful_yields() -> None:
    source = 'def function(values):\n    """Generate values."""\n    yield\n    yield None\n    yield from values\n'

    assert_pdf504_lines(source, ((5,),))


def test_nested_function_yield_is_checked_independently() -> None:
    source = 'def outer():\n    """Create a generator."""\n    def inner():\n        """Generate values."""\n        yield 1\n    return inner\n'

    assert_pdf504_lines(source, ((5,),))
