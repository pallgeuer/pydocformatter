# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF417_numpy_return_entry_shape import PDF417NumpyReturnEntryShape
from pydocformatter.rules.models import FixAvailability


format_source = pdf_helpers.formatter_for("PDF417", convention=DocstringConvention.NUMPY)


def assert_pdf417_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF417 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF417NumpyReturnEntryShape.meta, settings=settings)


def test_metadata() -> None:
    """Expose the intended diagnostic-only return-shape policy."""
    assert PDF417NumpyReturnEntryShape.meta.fix_availability is FixAvailability.NEVER


def test_single_named_return_entry_remains_diagnostic_when_fixing() -> None:
    """Preserve an authored return name while reporting the NumPy shape violation."""
    source = 'def function():\n    """Return a value.\n\n    Returns\n    -------\n    result : int\n        Value.\n    """\n    return 1\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF417NumpyReturnEntryShape.meta,)


def test_compact_multi_name_return_entry_remains_diagnostic() -> None:
    """Avoid guessing how a shared multi-name return entry should be split."""
    source = 'def function():\n    """Return values.\n\n    Returns\n    -------\n    first, second : int\n        Values.\n    """\n    return 1, 2\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF417NumpyReturnEntryShape.meta,)


def test_single_bare_return_entry_is_valid() -> None:
    source = 'def function():\n    """Return a value.\n\n    Returns\n    -------\n    int\n        Value.\n    """\n    return 1\n'

    assert_pdf417_lines(source, ())


def test_single_named_return_entry_is_reported() -> None:
    source = 'def function():\n    """Return a value.\n\n    Returns\n    -------\n    result : int\n        Value.\n    """\n    return 1\n'
    result = assert_pdf417_lines(source, ((6,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Single-value NumPy Returns entry should contain only the type",)


@pytest.mark.parametrize(
    "entries",
    ["    first : int\n        First.\n    second : str\n        Second.\n", "    int\n        First.\n    str\n        Second.\n", "    first : int\n        First.\n    str\n        Second.\n"],
)
def test_multiple_separate_return_entries_allow_named_bare_and_mixed_shapes(entries: str) -> None:
    source = f'def function():\n    """Return values.\n\n    Returns\n    -------\n{entries}    """\n    return 1, "two"\n'

    assert_pdf417_lines(source, ())


def test_compact_multi_name_return_entry_is_reported() -> None:
    source = 'def function():\n    """Return values.\n\n    Returns\n    -------\n    first, second : int\n        Values.\n    """\n    return 1, 2\n'
    result = assert_pdf417_lines(source, ((6,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("NumPy Returns entry should document each returned value in a separate entry",)


def test_compact_multi_name_entry_is_reported_inside_multiple_entry_section() -> None:
    source = 'def function():\n    """Return values.\n\n    Returns\n    -------\n    first, second : int\n        Values.\n    third : str\n        Third.\n    """\n    return 1, 2, "three"\n'

    assert_pdf417_lines(source, ((6,),))


@pytest.mark.parametrize("type_text", ["tuple[int, int]", "list[int]", "None", "Widget | None"])
def test_single_bare_type_spelling_does_not_trigger_runtime_arity_or_type_validation(type_text: str) -> None:
    source = f'def function():\n    """Return a value.\n\n    Returns\n    -------\n    {type_text}\n        Value.\n    """\n    return None\n'

    assert_pdf417_lines(source, ())


def test_repeated_returns_sections_are_checked_independently() -> None:
    source = 'def function():\n    """Return values.\n\n    Returns\n    -------\n    first : int\n        First.\n\n    Returns\n    -------\n    str\n        Second.\n    """\n    return 1\n'

    assert_pdf417_lines(source, ((6,),))


def test_only_return_sections_in_documented_functions_are_checked() -> None:
    source = 'def undocumented():\n    return 1\n\n\ndef generator(value):\n    """Yield a value.\n\n    Parameters\n    ----------\n    value : int\n        Input value.\n\n    Yields\n    ------\n    result : int\n        Output value.\n    """\n    yield value\n\n\ndef function():\n    """Return a value.\n\n    Return\n    ------\n    result : int\n        Output value.\n    """\n    return 1\n'

    assert_pdf417_lines(source, ((26,),))


def test_module_class_and_attached_attribute_docstrings_are_not_checked() -> None:
    source = '"""Module.\n\nReturns\n-------\nresult : int\n    Value.\n"""\n\n\nclass Owner:\n    """Owner.\n\n    Returns\n    -------\n    result : int\n        Value.\n    """\n\n\nvalue = 1\n"""Value.\n\nReturns\n-------\nresult : int\n    Value.\n"""\n'

    assert_pdf417_lines(source, ())


def test_nested_functions_and_methods_are_checked_as_primary_function_docstrings() -> None:
    source = 'def outer():\n    """Return outer.\n\n    Returns\n    -------\n    outer_result : int\n        Value.\n    """\n\n    def inner():\n        """Return inner.\n\n        Returns\n        -------\n        inner_result : int\n            Value.\n        """\n        return 1\n\n    return inner()\n\n\nclass Owner:\n    def method(self):\n        """Return method.\n\n        Returns\n        -------\n        method_result : int\n            Value.\n        """\n        return 1\n'

    assert_pdf417_lines(source, ((6,), (15,), (29,)))


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE, DocstringConvention.REST])
def test_non_numpy_conventions_disable_rule_even_for_exact_selection(convention: DocstringConvention) -> None:
    selected = rules_selection.select_rules(CheckSettings(select=("PDF417",), docstring_convention=convention))

    assert "PDF417" not in tuple(rule.rule.code.tag for rule in selected.rules)


def test_numpy_broad_selection_enables_diagnostic_only_rule() -> None:
    selected = rules_selection.select_rules(CheckSettings(select=("PDF",), docstring_convention=DocstringConvention.NUMPY))
    source = 'def function():\n    """Return a value.\n\n    Returns\n    -------\n    result : int\n        Value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF",), docstring_convention=DocstringConvention.NUMPY))

    assert "PDF417" in tuple(rule.rule.code.tag for rule in selected.rules)
    assert result.new_source == source
    assert not result.fixed_findings
    assert PDF417NumpyReturnEntryShape.meta in {finding.rule for finding in result.unfixed_findings}


def test_protected_entry_like_content_is_ignored() -> None:
    source = 'def function():\n    """Return a value.\n\n    Returns\n    -------\n    int\n        Example::\n\n            result : int\n    """\n    return 1\n'

    assert_pdf417_lines(source, ())


def test_docstring_suppression_hides_return_shape_finding() -> None:
    source = 'def function():\n    """Return a value.\n\n    Returns\n    -------\n    result : int\n        Value.\n    """  # noqa: PDF417\n'

    assert_pdf417_lines(source, ())
