import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF507_extraneous_exception_documentation import PDF507ExtraneousExceptionDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF507 selected."""
    resolved_settings = CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf507_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF507 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF507ExtraneousExceptionDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_documented_exception_absent_from_direct_raises() -> None:
    source = 'def function(value):\n    """Validate a value.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    return value\n'
    result = format_source(source)

    assert_pdf507_lines(source, ((5,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring documents exception 'ValueError' that is not explicitly raised",)


@pytest.mark.parametrize("convention", tuple(DocstringConvention))
def test_every_convention_ignores_broad_selection_but_exact_selection_still_applies(convention: DocstringConvention) -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF5",), docstring_convention=convention))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF507" not in active_codes

    source = 'def function(value):\n    """Validate a value.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    return value\n'
    exact = format_source(source, settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in exact.unfixed_findings) == ((5,),)


def test_allows_google_numpy_and_sphinx_documented_exceptions_matching_direct_raise() -> None:
    google = 'def function():\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'
    numpy = 'def function():\n    """Validate.\n\n    Raises\n    ------\n    ValueError\n        Bad value.\n    """\n    raise ValueError("bad")\n'
    sphinx = 'def function():\n    """Validate.\n\n    :raises ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf507_lines(google, ())
    assert_pdf507_lines(numpy, (), settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf507_lines(sphinx, (), settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.NONE))


def test_one_google_entry_can_document_multiple_directly_raised_exceptions() -> None:
    source = 'def function(flag):\n    """Validate.\n\n    Raises:\n        ValueError, TypeError: Bad value.\n    """\n    if flag:\n        raise ValueError("bad")\n    raise TypeError("bad")\n'

    assert_pdf507_lines(source, ())


def test_qualified_raise_matches_final_documented_exception_name() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    raise errors.ValueError("bad")\n'

    assert_pdf507_lines(source, ())


def test_raise_with_cause_uses_primary_exception_name() -> None:
    source = 'def function(cause):\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    raise ValueError("bad") from cause\n'

    assert_pdf507_lines(source, ())


def test_qualified_documented_exception_matches_final_raised_exception_name() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        errors.ValueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf507_lines(source, ())


def test_differently_qualified_exception_names_do_not_match() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        requests.Timeout: Bad value.\n    """\n    raise socket.Timeout("bad")\n'
    result = format_source(source)

    assert_pdf507_lines(source, ((5,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring documents exception 'requests.Timeout' that is not explicitly raised",)


def test_reports_only_stale_exception_when_other_documented_exception_is_raised() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n        TypeError: Bad type.\n    """\n    raise ValueError("bad")\n'
    result = format_source(source)

    assert_pdf507_lines(source, ((6,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring documents exception 'TypeError' that is not explicitly raised",)


def test_reports_only_stale_name_from_multi_name_exception_entry() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        ValueError, TypeError: Bad value.\n    """\n    raise ValueError("bad")\n'
    result = format_source(source)

    assert_pdf507_lines(source, ((5,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring documents exception 'TypeError' that is not explicitly raised",)


def test_exception_documentation_matching_is_case_sensitive() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        valueError: Bad value.\n    """\n    raise ValueError("bad")\n'

    assert_pdf507_lines(source, ((5,),))


def test_reports_each_duplicate_stale_documented_exception() -> None:
    source = 'def function():\n    """Validate.\n\n    Raises:\n        ValueError: First.\n        ValueError: Second.\n    """\n    return 1\n'
    result = format_source(source)

    assert_pdf507_lines(source, ((5,), (6,)))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring documents exception 'ValueError' that is not explicitly raised",
        "Docstring documents exception 'ValueError' that is not explicitly raised",
    )


def test_reports_numpy_and_sphinx_stale_documented_exceptions() -> None:
    numpy = 'def function():\n    """Validate.\n\n    Raises\n    ------\n    ValueError\n        Bad value.\n    """\n'
    sphinx = 'def function():\n    """Validate.\n\n    :raises ValueError: Bad value.\n    """\n'

    assert_pdf507_lines(numpy, ((6,),), settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf507_lines(sphinx, ((4,),), settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.NONE))


def test_concatenated_docstring_exception_field_uses_physical_line_fallback() -> None:
    source = 'def function():\n    ("Validate.\\n\\n"\n     ":raises ValueError: Bad value.")\n'

    assert_pdf507_lines(source, ((2, 3),), settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.NONE))


def test_ignores_prose_only_raises_missing_docstrings_abstracts_and_stubs() -> None:
    source = 'def prose():\n    """Validate.\n\n    Raises:\n        If the value is bad.\n    """\n\n\ndef warning_doc():\n    """Validate.\n\n    Warns:\n        ValueError: Bad value.\n    """\n\n\ndef undocumented():\n    raise ValueError("bad")\n\n\n@abc.abstractmethod\ndef abstract():\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    pass\n\n\ndef stub():\n    """Validate.\n\n    Raises:\n        ValueError: Bad value.\n    """\n    ...\n'

    assert_pdf507_lines(source, ())


def test_sphinx_field_parsing_setting_controls_sphinx_exception_documentation() -> None:
    source = 'def function():\n    """Validate.\n\n    :raises ValueError: Bad value.\n    """\n'

    assert_pdf507_lines(source, (), settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.NONE, docstring_parse_sphinx_fields=False))


def test_nameless_sphinx_exception_field_is_not_comparable_documentation() -> None:
    source = 'def function():\n    """Validate.\n\n    :raises: If the value is bad.\n    """\n'

    assert_pdf507_lines(source, (), settings=CheckSettings(select=("PDF507",), docstring_convention=DocstringConvention.NONE))
