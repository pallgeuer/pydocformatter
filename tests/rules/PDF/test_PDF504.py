# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF504_missing_yield_documentation import PDF504MissingYieldDocumentation
from tests import rule_helpers


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


def test_non_summary_policy_checks_body_docstrings_but_not_summary_only_docstrings() -> None:
    source = 'def summary_only():\n    """Generate values."""\n    yield 1\n\n\ndef detailed():\n    """Generate values.\n\n    More detail.\n    """\n    yield 1\n'
    settings = CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS)

    assert_pdf504_lines(source, ((11,),), settings=settings)


def test_reports_async_generator_yield_missing_from_docstring() -> None:
    source = 'async def function():\n    """Generate values."""\n    yield 1\n'

    assert_pdf504_lines(source, ((3,),))


def test_empty_yield_section_does_not_satisfy_meaningful_yield() -> None:
    source = 'def function():\n    """Generate values.\n\n    Yields:\n    """\n    yield 1\n'

    assert_pdf504_lines(source, ((6,),))


def test_google_numpy_and_rest_yield_documentation_satisfy_meaningful_yield() -> None:
    google = 'def function():\n    """Generate values.\n\n    Yields:\n        int: Value.\n    """\n    yield 1\n'
    numpy = 'def function():\n    """Generate values.\n\n    Yields\n    ------\n    int\n        Value.\n    """\n    yield 1\n'
    rest = 'def function():\n    """Generate values.\n\n    :yields: Value.\n    """\n    yield 1\n'

    assert_pdf504_lines(google, ())
    assert_pdf504_lines(numpy, (), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf504_lines(rest, (), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.REST))


def test_mixed_case_singular_google_yield_section_satisfies_meaningful_yield() -> None:
    source = 'def function():\n    """Generate values.\n\n    yIELD:\n        int: Value.\n    """\n    yield 1\n'

    assert_pdf504_lines(source, ())


def test_google_bare_none_yield_entry_satisfies_meaningful_yield() -> None:
    none_plain = 'def function():\n    """Generate values.\n\n    Yields:\n        None\n    """\n    yield 1\n'
    none_period = 'def function():\n    """Generate values.\n\n    Yields:\n        None.\n    """\n    yield 1\n'

    assert_pdf504_lines(none_plain, ())
    assert_pdf504_lines(none_period, ())


def test_ytype_activates_check_without_documenting_meaningful_yield() -> None:
    source = 'def function():\n    """Generate values.\n\n    :ytype: int\n    """\n    yield 1\n'

    assert_pdf504_lines(source, ((6,),), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.REST))


def test_paired_empty_yield_value_field_remains_missing_but_content_satisfies_rule() -> None:
    source = 'def missing():\n    """Generate values.\n\n    :ytype: int\n    :yield:\n    """\n    yield 1\n\n\ndef documented():\n    """Generate values.\n\n    :ytype: int\n    :yields: Result value.\n    """\n    yield 1\n'

    assert_pdf504_lines(source, ((7,),), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.REST))


def test_surplus_nonempty_yield_type_field_does_not_rescue_an_empty_value_field() -> None:
    source = 'def function():\n    """Generate values.\n\n    :ytype: int\n    :yield:\n    :ytype: str\n    """\n    yield 1\n'

    assert_pdf504_lines(source, ((8,),), settings=CheckSettings(select=("PDF504",), docstring_convention=DocstringConvention.REST))


def test_private_type_only_yield_field_activates_public_only_policy_but_broad_policy_remains_private_aware() -> None:
    source = 'def _explicit():\n    """Generate values.\n\n    :ytype: int\n    """\n    yield 1\n\n\ndef _broad():\n    """Generate values."""\n    yield 1\n'
    public_only = CheckSettings(
        select=("PDF504",),
        docstring_convention=DocstringConvention.REST,
        docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS,
        docstring_missing_documentation_public_only=True,
    )
    include_private = CheckSettings(
        select=("PDF504",),
        docstring_convention=DocstringConvention.REST,
        docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS,
        docstring_missing_documentation_public_only=False,
    )

    assert_pdf504_lines(source, ((6,),), settings=public_only)
    assert_pdf504_lines(source, ((6,), (11,)), settings=include_private)


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


def test_none_and_pep257_conventions_keep_missing_yield_documentation_inert() -> None:
    source = 'def function():\n    """Generate values.\n\n    :yields: Value.\n    """\n    yield 1\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf504_lines(source, (), settings=CheckSettings(select=("PDF504",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS))


def test_direct_rule_hook_remains_inert_for_unparsed_conventions() -> None:
    source = 'def function():\n    """Generate values.\n\n    :ytype: int\n    """\n    yield 1\n'
    contexts = pdf_helpers.contexts_for("PDF504")

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        _, context = contexts(source, settings=CheckSettings(select=("PDF504",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS))

        assert not rule_helpers.rule_findings(PDF504MissingYieldDocumentation, context)


def test_reports_first_meaningful_yield_after_non_meaningful_yields() -> None:
    source = 'def function(values):\n    """Generate values."""\n    yield\n    yield None\n    yield from values\n'

    assert_pdf504_lines(source, ((5,),))


def test_nested_function_yield_is_checked_independently() -> None:
    source = 'def outer():\n    """Create a generator."""\n    def inner():\n        """Generate values."""\n        yield 1\n    return inner\n'

    assert_pdf504_lines(source, ((5,),))
