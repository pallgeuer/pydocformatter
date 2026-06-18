import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF503_extraneous_return_documentation import PDF503ExtraneousReturnDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF503 selected."""
    resolved_settings = CheckSettings(select=("PDF503",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf503_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF503 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF503ExtraneousReturnDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_allows_return_section_for_explicit_none_return() -> None:
    source = 'def function():\n    """Do work.\n\n    Returns:\n        int: Value.\n    """\n    return None\n'

    assert_pdf503_lines(source, ())


def test_allows_bare_none_return_entry_for_explicit_none_return() -> None:
    none_plain = 'def function():\n    """Do work.\n\n    Returns:\n        None\n    """\n    return None\n'
    none_period = 'def function():\n    """Do work.\n\n    Returns:\n        None.\n    """\n    return None\n'

    assert_pdf503_lines(none_plain, ())
    assert_pdf503_lines(none_period, ())


def test_allows_return_section_for_parenthesized_none_return() -> None:
    source = 'def function():\n    """Do work.\n\n    Returns:\n        None: Nothing.\n    """\n    return (None)\n'

    assert_pdf503_lines(source, ())


def test_reports_return_section_for_bare_return() -> None:
    source = 'def function():\n    """Do work.\n\n    Returns:\n        None: Nothing.\n    """\n    return\n'

    assert_pdf503_lines(source, ((4,),))


def test_reports_empty_return_section_and_rest_field() -> None:
    source = 'def section():\n    """Do work.\n\n    Returns:\n    """\n\n\ndef field():\n    """Do work.\n\n    :returns: Value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF503",), docstring_convention=DocstringConvention.REST))

    assert_pdf503_lines('def section():\n    """Do work.\n\n    Returns:\n    """\n', ((4,),))
    assert_pdf503_lines(source, ((11,),), settings=CheckSettings(select=("PDF503",), docstring_convention=DocstringConvention.REST))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring has a return section for a function that does not return",)


def test_reports_rest_rtype_field_but_allows_it_for_explicit_none_return() -> None:
    source = 'def absent():\n    """Do work.\n\n    :rtype: int\n    """\n\n\ndef none():\n    """Do work.\n\n    :rtype: None\n    """\n    return None\n'

    assert_pdf503_lines(source, ((4,),), settings=CheckSettings(select=("PDF503",), docstring_convention=DocstringConvention.REST))


def test_reports_multiple_return_documentation_targets() -> None:
    source = 'def function():\n    """Do work.\n\n    Returns:\n        int: First.\n\n    Returns:\n        int: Second.\n\n    :rtype: int\n    """\n'

    assert_pdf503_lines(source, ((4,), (7,)))


def test_concatenated_docstring_return_field_uses_physical_line_fallback() -> None:
    source = 'def function():\n    ("Do work.\\n\\n"\n     ":returns: Value.")\n'

    assert_pdf503_lines(source, ((2, 3),), settings=CheckSettings(select=("PDF503",), docstring_convention=DocstringConvention.REST))


def test_reports_numpy_return_section_header() -> None:
    source = 'def function():\n    """Do work.\n\n    Returns\n    -------\n    int\n        Value.\n    """\n'

    assert_pdf503_lines(source, ((4,),), settings=CheckSettings(select=("PDF503",), docstring_convention=DocstringConvention.NUMPY))


def test_allows_meaningful_return_but_reports_generators_with_return_docs() -> None:
    returning = 'def function():\n    """Return a value.\n\n    Returns:\n        int: Value.\n    """\n    return 1\n'
    generator = 'def function():\n    """Generate values.\n\n    Returns:\n        int: Value.\n    """\n    yield 1\n'
    generator_with_stop_value = 'def function():\n    """Generate values.\n\n    Yields:\n        int: Value.\n\n    Returns:\n        int: Stop value.\n    """\n    yield 1\n    return 2\n'

    assert_pdf503_lines(returning, ())
    assert_pdf503_lines(generator, ((4,),))
    result = format_source(generator_with_stop_value)

    assert_pdf503_lines(generator_with_stop_value, ((7,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring has a return section for a generator; generator return values are stop values, not ordinary returns",)


def test_reports_return_section_for_generators_with_only_non_meaningful_yields() -> None:
    bare_yield = 'def function():\n    """Generate values.\n\n    Returns:\n        int: Stop value.\n    """\n    yield\n    return 1\n'
    none_yield = 'def function():\n    """Generate values.\n\n    Returns:\n        int: Stop value.\n    """\n    yield None\n    return 1\n'

    for source in (bare_yield, none_yield):
        result = format_source(source)

        assert_pdf503_lines(source, ((4,),))
        assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring has a return section for a generator; generator return values are stop values, not ordinary returns",)


def test_inactive_rest_convention_does_not_parse_rest_return_documentation() -> None:
    source = 'def function():\n    """Do work.\n\n    :returns: Value.\n    """\n'

    assert_pdf503_lines(source, (), settings=CheckSettings(select=("PDF503",), docstring_convention=DocstringConvention.NONE))


def test_ignores_missing_docstrings_abstracts_and_stubs() -> None:
    source = 'def undocumented():\n    pass\n\n\n@abc.abstractmethod\ndef abstract():\n    """Do work.\n\n    Returns:\n        int: Value.\n    """\n    pass\n\n\n@abc.abstractmethod()\ndef abstract_call():\n    """Do work.\n\n    Returns:\n        int: Value.\n    """\n    pass\n\n\ndef stub():\n    """Do work.\n\n    Returns:\n        int: Value.\n    """\n    pass\n'

    assert_pdf503_lines(source, ())
