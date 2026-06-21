import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF505_extraneous_yield_documentation import PDF505ExtraneousYieldDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF505 selected."""
    resolved_settings = CheckSettings(select=("PDF505",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf505_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF505 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF505ExtraneousYieldDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_yield_section_for_function_without_meaningful_yield() -> None:
    source = 'def function():\n    """Do work.\n\n    Yields:\n        int: Value.\n    """\n    return 1\n'

    assert_pdf505_lines(source, ((4,),))


def test_allows_yield_section_for_parenthesized_none_yield() -> None:
    source = 'def function():\n    """Generate nothing.\n\n    Yields:\n        None: Nothing.\n    """\n    yield (None)\n'

    assert_pdf505_lines(source, ())


def test_allows_yield_section_for_explicit_none_yield() -> None:
    source = 'def function():\n    """Generate nothing.\n\n    Yields:\n        None: Nothing.\n    """\n    yield None\n'

    assert_pdf505_lines(source, ())


def test_allows_bare_none_yield_entry_for_explicit_none_yield() -> None:
    none_plain = 'def function():\n    """Generate nothing.\n\n    Yields:\n        None\n    """\n    yield None\n'
    none_period = 'def function():\n    """Generate nothing.\n\n    Yields:\n        None.\n    """\n    yield None\n'

    assert_pdf505_lines(none_plain, ())
    assert_pdf505_lines(none_period, ())


def test_reports_yield_section_for_bare_yield() -> None:
    source = 'def function():\n    """Generate nothing.\n\n    Yields:\n        None: Nothing.\n    """\n    yield\n'

    assert_pdf505_lines(source, ((4,),))


def test_reports_mixed_case_singular_google_yield_section_for_function_without_yield() -> None:
    source = 'def function():\n    """Do work.\n\n    yIELD:\n        int: Value.\n    """\n    return 1\n'

    assert_pdf505_lines(source, ((4,),))


def test_reports_yield_section_when_only_lambda_yields() -> None:
    source = 'def function():\n    """Create a generator callback.\n\n    Yields:\n        int: Value.\n    """\n    callback = lambda: (yield 1)\n    return callback\n'

    assert_pdf505_lines(source, ((4,),))


def test_reports_empty_yield_section_and_rest_field() -> None:
    source = 'def section():\n    """Do work.\n\n    Yields:\n    """\n\n\ndef field():\n    """Do work.\n\n    :yields: Value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF505",), docstring_convention=DocstringConvention.REST))

    assert_pdf505_lines('def section():\n    """Do work.\n\n    Yields:\n    """\n', ((4,),))
    assert_pdf505_lines(source, ((11,),), settings=CheckSettings(select=("PDF505",), docstring_convention=DocstringConvention.REST))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring has a yield section for a function that does not yield a meaningful value",)


def test_reports_rest_ytype_field_but_allows_it_for_explicit_none_yield() -> None:
    source = 'def absent():\n    """Do work.\n\n    :ytype: int\n    """\n\n\ndef none():\n    """Generate nothing.\n\n    :ytype: None\n    """\n    yield None\n'

    assert_pdf505_lines(source, ((4,),), settings=CheckSettings(select=("PDF505",), docstring_convention=DocstringConvention.REST))


def test_reports_multiple_yield_documentation_targets() -> None:
    source = 'def function():\n    """Do work.\n\n    Yields:\n        int: First.\n\n    Yields:\n        int: Second.\n\n    :ytype: int\n    """\n'

    assert_pdf505_lines(source, ((4,), (7,)))


def test_concatenated_docstring_yield_field_uses_physical_line_fallback() -> None:
    source = 'def function():\n    ("Do work.\\n\\n"\n     ":yields: Value.")\n'

    assert_pdf505_lines(source, ((2, 3),), settings=CheckSettings(select=("PDF505",), docstring_convention=DocstringConvention.REST))


def test_reports_numpy_yield_section_header() -> None:
    source = 'def function():\n    """Do work.\n\n    Yields\n    ------\n    int\n        Value.\n    """\n'

    assert_pdf505_lines(source, ((4,),), settings=CheckSettings(select=("PDF505",), docstring_convention=DocstringConvention.NUMPY))


def test_allows_meaningful_yield_and_explicit_none_yield_but_reports_bare_yield_docs() -> None:
    yielding = 'def function():\n    """Generate values.\n\n    Yields:\n        int: Value.\n    """\n    yield 1\n'
    bare = 'def function():\n    """Generate values.\n\n    Yields:\n        int: Value.\n    """\n    yield\n'
    yield_from = 'def function(values):\n    """Generate values.\n\n    Yields:\n        int: Value.\n    """\n    yield from values\n'

    assert_pdf505_lines(yielding, ())
    explicit_none = 'def function():\n    """Generate values.\n\n    Yields:\n        None: Nothing.\n    """\n    yield None\n'

    assert_pdf505_lines(bare, ((4,),))
    assert_pdf505_lines(explicit_none, ())
    assert_pdf505_lines(yield_from, ())


def test_inactive_rest_convention_does_not_parse_rest_yield_documentation() -> None:
    source = 'def function():\n    """Do work.\n\n    :yields: Value.\n    """\n'

    assert_pdf505_lines(source, (), settings=CheckSettings(select=("PDF505",), docstring_convention=DocstringConvention.NONE))


def test_ignores_missing_docstrings_abstracts_and_stubs() -> None:
    source = 'def undocumented():\n    pass\n\n\n@abc.abstractmethod\ndef abstract():\n    """Do work.\n\n    Yields:\n        int: Value.\n    """\n    pass\n\n\ndef stub():\n    """Do work.\n\n    Yields:\n        int: Value.\n    """\n    ...\n'

    assert_pdf505_lines(source, ())
