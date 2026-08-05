"""Tests for PDF312 entry-description-too-generic."""

# Standard library imports
import dataclasses

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF312_entry_description_too_generic import PDF312EntryDescriptionTooGeneric


format_source = pdf_helpers.formatter_for("PDF312")


def test_metadata() -> None:
    """Expose the stable diagnostic-only rule identity."""
    assert PDF312EntryDescriptionTooGeneric.meta.name == "entry-description-too-generic"
    assert PDF312EntryDescriptionTooGeneric.meta.message == "Docstring entry description is too generic"
    assert PDF312EntryDescriptionTooGeneric.meta.stable_since == "1.1.0"


@pytest.mark.parametrize(
    ("section", "head", "message"),
    [
        ("Returns", "int: The return value.", "Return documentation is too generic"),
        ("Returns", "int: The returned value!", "Return documentation is too generic"),
        ("Yields", "str: The yielded value?", "Yield documentation is too generic"),
        ("Raises", "ValueError: The exception.", "Exception documentation for 'ValueError' is too generic"),
        ("Raises", "ValueError: The error.", "Exception documentation for 'ValueError' is too generic"),
        ("Warns", "RuntimeWarning: The warning.", "Warning documentation for 'RuntimeWarning' is too generic"),
    ],
)
def test_reports_unnamed_google_patterns(section: str, head: str, message: str) -> None:
    """Report exact unnamed patterns for function-owned entries."""
    source = f'def value():\n    """Return a value.\n\n    {section}:\n        {head}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (message,)


def test_reports_named_numpy_return_yield_exception_warning_and_method_patterns() -> None:
    """Report named patterns for every NumPy entry family."""
    source = (
        'class Worker:\n    """Run queued work.\n\n    Methods\n    -------\n    run : Callable[[], None]\n        The run method.\n    """\n\n'
        '    def values(self):\n        """Produce values.\n\n        Returns\n        -------\n        count : int\n            The count returned value.\n\n        Yields\n        ------\n        item : str\n            The item yielded value.\n\n        Raises\n        ------\n        ValueError, errors.CustomError\n            The errors.CustomError error.\n\n        Warns\n        -----\n        RuntimeWarning, UserWarning\n            The UserWarning warning.\n        """\n'
    )
    settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (15,), (20,), (25,), (30,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Method documentation for 'run' is too generic",
        "Return documentation for 'count' is too generic",
        "Yield documentation for 'item' is too generic",
        "Exception documentation for 'errors.CustomError' is too generic",
        "Warning documentation for 'UserWarning' is too generic",
    )


def test_reports_every_name_for_unnamed_generic_multi_name_description() -> None:
    """An unnamed generic phrase applies to every name sharing the entry."""
    source = 'def value():\n    """Produce a value.\n\n    Raises\n    ------\n    ValueError, TypeError\n        The exception.\n    """\n'
    settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Exception documentation for 'ValueError', 'TypeError' is too generic",)


@pytest.mark.parametrize(
    ("description", "message"),
    [("The exception.", "Exception documentation for 'ValueError', 'TypeError' is too generic"), ("The ValueError exception.", "Exception documentation for 'ValueError' is too generic")],
)
def test_deduplicates_displayed_names_in_first_occurrence_order(description: str, message: str) -> None:
    """Display each implicated entry name once without reordering it."""
    source = f'def value():\n    """Produce a value.\n\n    Raises\n    ------\n    ValueError, TypeError, ValueError\n        {description}\n    """\n'
    settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (message,)


@pytest.mark.parametrize(
    ("section", "head", "description", "message"),
    [
        ("Returns", "count : int", "The count value.", "Return documentation for 'count' is too generic"),
        ("Returns", "count : int", "The count return value.", "Return documentation for 'count' is too generic"),
        ("Yields", "item : str", "The item value.", "Yield documentation for 'item' is too generic"),
        ("Raises", "ValueError", "The ValueError exception.", "Exception documentation for 'ValueError' is too generic"),
    ],
)
def test_reports_remaining_named_numpy_templates(section: str, head: str, description: str, message: str) -> None:
    """Cover every conservative name-bearing phrase variant."""
    source = f'def value():\n    """Produce a value.\n\n    {section}\n    {"-" * len(section)}\n    {head}\n        {description}\n    """\n'
    settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (message,)


def test_reports_unnamed_method_pattern() -> None:
    """Cover the class-owned method phrase that does not repeat its name."""
    source = 'class Worker:\n    """Run queued work.\n\n    Methods:\n        run: The method.\n    """\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Method documentation for 'run' is too generic",)


def test_reports_google_method_patterns_with_boundary_underscores() -> None:
    """Match preserved or omitted underscores only for names that own those boundaries."""
    source = (
        'class Worker:\n    """Run queued work.\n\n    Methods:\n'
        "        _run: The _run method.\n"
        "        __init__: The init method.\n"
        "        close_: The close_ method.\n"
        "        plain: The _plain method.\n"
        '    """\n'
    )
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (6,), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Method documentation for '_run' is too generic",
        "Method documentation for '__init__' is too generic",
        "Method documentation for 'close_' is too generic",
    )


def test_reports_numpy_method_pattern_with_boundary_underscores() -> None:
    """Apply boundary-underscore matching to NumPy method entries."""
    source = 'class Worker:\n    """Run queued work.\n\n    Methods\n    -------\n    __init__ : Callable[[], None]\n        The __init__ method.\n    """\n'
    settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Method documentation for '__init__' is too generic",)


def test_reports_rest_return_yield_and_exception_patterns_but_skips_type_fields() -> None:
    """Apply reST value-entry patterns without treating types as prose."""
    source = 'def values():\n    """Produce values.\n\n    :return: The returned value.\n    :yield item: The item value.\n    :raises ValueError: The ValueError exception.\n    :rtype: The return value\n    :ytype item: The yielded value\n    """\n'
    settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (5,), (6,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Return documentation is too generic",
        "Yield documentation for 'item' is too generic",
        "Exception documentation for 'ValueError' is too generic",
    )


@pytest.mark.parametrize("description", ["The return value in bytes.", "The result.", "A return value.", "The return-value.", "`The return value`.", "The return value:"])
def test_skips_false_positive_boundaries(description: str) -> None:
    """Require one of the exact conservative phrases."""
    source = f'def value():\n    """Return a value.\n\n    Returns:\n        int: {description}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_targets_entry_heads_and_applies_owner_restrictions() -> None:
    """Use entry-head lines and only the intended function or class owners."""
    source = (
        '"""Module.\n\nReturns:\n    int: The return value.\n"""\n\n'
        'class Worker:\n    """Run work.\n\n    Methods:\n        run:\n            The run\n            method.\n    """\n\n'
        '    def run(self):\n        """Run work.\n\n        Returns:\n            int:\n                The return\n                value.\n\n        Methods:\n            nested: The nested method.\n        """\n'
    )
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((11,), (20,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Method documentation for 'run' is too generic", "Return documentation is too generic")


def test_skips_parsed_entries_in_attached_attribute_docstrings() -> None:
    """Keep non-definition docstring owners outside the rule."""
    source = 'value = 1\n"""Store a value.\n\nReturns:\n    int: The return value.\n"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_local_suppression_before_docstring_suppresses_all_findings() -> None:
    """Honor complete-expression PDF suppression."""
    source = 'def value():\n    # pydocfmt: ignore[PDF312]\n    """Return a value.\n\n    Raises:\n        ValueError: The error.\n        TypeError: The exception.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_concatenated_docstring_mapping_and_component_suppression() -> None:
    """Use whole-expression targets and honor a directive on any component token."""
    source = 'def value():\n    ("Return a value.\\n\\n"\n     "Returns:\\n"\n     "    int: The return value.")\n'
    suppressed = 'def value():\n    ("Return a value.\\n\\n"  # pydocfmt: ignore[PDF312]\n     "Returns:\\n"\n     "    int: The return value.")\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Return documentation is too generic",)
    assert not format_source(suppressed).unfixed_findings


@pytest.mark.parametrize("description", ["\\u2003The return value.", "The return value.\\u00a0", "The\\freturn value.", "\\vThe return value.\\v"])
def test_skips_generic_descriptions_with_nonstandard_whitespace(description: str) -> None:
    """Use full evaluated fragment spans when enforcing the ASCII-only matcher contract."""
    source = f'def value():\n    """Return a value.\n\n    Returns:\n        int: {description}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_skips_missing_and_protected_only_descriptions() -> None:
    """Leave missing prose to completeness rules."""
    source = 'class Worker:\n    """Run work.\n\n    Methods:\n        run:\n            - protected only\n        close:\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_literal_block_parsing_setting_controls_generic_description_checks() -> None:
    """Inspect convention-looking examples only when literal protection is disabled."""
    source = 'def value():\n    """Return a value.\n\n    Returns:\n        Example::\n\n            int: The return value.\n    """\n'
    unprotected_settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False)
    protected = format_source(source)
    unprotected = format_source(source, settings=unprotected_settings)

    assert not protected.unfixed_findings
    assert tuple(finding.line_numbers for finding in unprotected.unfixed_findings) == ((7,),)
    assert tuple(finding.message for finding in unprotected.unfixed_findings) == ("Return documentation is too generic",)


@pytest.mark.parametrize(
    ("settings_to_disable", "body", "line_number"),
    [
        (("docstring_parse_code_fences", "docstring_parse_headings"), "Returns:\n        ```text\n        int: The return value.\n        ```", 6),
        (("docstring_parse_list_items",), "Returns:\n        - Example\n            int: The return value.", 6),
        (("docstring_parse_doctests",), 'Returns:\n        >>> print("example")\n        int: The return value.', 6),
    ],
)
def test_protected_structure_settings_control_nested_generic_descriptions(settings_to_disable: tuple[str, ...], body: str, line_number: int) -> None:
    """Inspect nested entries only after every matching protection is disabled."""
    source = f'def value():\n    """Return a value.\n\n    {body}\n    """\n'
    protected_settings = CheckSettings(select=("PDF312",), docstring_convention=DocstringConvention.GOOGLE)
    partially_unprotected_settings = dataclasses.replace(protected_settings, **{settings_to_disable[0]: False})
    unprotected_settings = dataclasses.replace(protected_settings, **dict.fromkeys(settings_to_disable, False))

    assert not format_source(source, settings=protected_settings).unfixed_findings
    if len(settings_to_disable) > 1:
        assert not format_source(source, settings=partially_unprotected_settings).unfixed_findings
    result = format_source(source, settings=unprotected_settings)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((line_number,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Return documentation is too generic",)


def test_converges_after_entry_capitalization_and_punctuation_fixes() -> None:
    """Keep the diagnostic after earlier entry-description fixes."""
    source = 'def value():\n    """Return a value.\n\n    Returns:\n        int: the return value\n    """\n'
    settings = CheckSettings(select=("PDF308", "PDF310", "PDF312"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace("the return value", "The return value.")
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF312EntryDescriptionTooGeneric.meta,)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Return documentation is too generic",)


def test_broad_selection_and_unparsed_convention_effects() -> None:
    """Enable parsed conventions and disable unparsed conventions."""
    for convention in (DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST):
        selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))
        assert "PDF312" in {rule.rule.code.tag for rule in selection.rules}
    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))
        assert "PDF312" not in {rule.rule.code.tag for rule in selection.rules}
        exact_selection = rules_selection.select_rules(CheckSettings(select=("PDF312",), docstring_convention=convention))
        assert "PDF312" not in {rule.rule.code.tag for rule in exact_selection.rules}
