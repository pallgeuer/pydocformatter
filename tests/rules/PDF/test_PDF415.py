"""Tests for PDF415 convention-entry-indentation."""

# Future imports
from __future__ import annotations

# Third-party imports
import pytest

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.definitions.PDF.PDF415_convention_entry_indentation as PDF415_definition
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF100_docstring_indentation import PDF100DocstringIndentation
from pydocformatter.rules.definitions.PDF.PDF101_docstring_reflow import PDF101DocstringReflow
from pydocformatter.rules.definitions.PDF.PDF414_malformed_convention_entry import PDF414MalformedConventionEntry
from pydocformatter.rules.definitions.PDF.PDF415_convention_entry_indentation import PDF415ConventionEntryIndentation
from tests.rules.PDF import helpers as pdf_helpers


format_source = pdf_helpers.formatter_for("PDF415")


def assert_pdf415(source: str, expected_lines: tuple[tuple[int, ...], ...], expected_messages: tuple[str, ...], *, convention: DocstringConvention) -> None:
    """Assert PDF415 findings for source under one convention."""
    result = pdf_helpers.assert_unfixed_lines(
        format_source, source, expected_lines, meta=PDF415ConventionEntryIndentation.meta, settings=CheckSettings(select=("PDF415",), docstring_convention=convention)
    )
    assert tuple(finding.message for finding in result.unfixed_findings) == expected_messages


def test_metadata() -> None:
    """Expose the intended stable diagnostic-only rule identity."""
    assert PDF415ConventionEntryIndentation.meta.name == "convention-entry-indentation"
    assert PDF415ConventionEntryIndentation.meta.stable_since == "1.1.0"


def test_instance_message_rejects_syntax_issue_kind() -> None:
    """Fail explicitly if PDF415 receives an issue owned by PDF414."""
    issue = PDF_definition.ConventionEntryIssue(kind=PDF_definition.ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR, start_line=0)

    with pytest.raises(AssertionError, match="Unsupported PDF415"):
        PDF415_definition._instance_message(issue)


def test_reports_google_entry_head_indentation() -> None:
    """Report a complete Google entry aligned with its section header."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n    value: The value.\n    """\n'
    assert_pdf415(source, ((5,),), ("Google docstring entry 'value' should be indented beyond its section header",), convention=DocstringConvention.GOOGLE)


def test_complete_google_syntax_supplies_entry_indentation_confidence_without_an_owner_name_match() -> None:
    """Report a syntactically complete stale entry without relying on inventory confidence."""
    source = 'def convert():\n    """Convert a value.\n\n    Args:\n    stale (int): The stale value.\n    """\n'
    assert_pdf415(source, ((5,),), ("Google docstring entry 'stale' should be indented beyond its section header",), convention=DocstringConvention.GOOGLE)


def test_bare_google_entry_indentation_requires_an_owner_name_match() -> None:
    """Avoid classifying an unknown colon-ended header-aligned line as a parameter entry."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n    stale: Narrative text.\n    value: The value.\n    """\n'
    assert_pdf415(source, ((6,),), ("Google docstring entry 'value' should be indented beyond its section header",), convention=DocstringConvention.GOOGLE)


def test_balanced_nested_google_type_supplies_entry_indentation_confidence() -> None:
    """Recognize a complete nested type while preserving conservative unknown-name handling."""
    source = 'def convert():\n    """Convert a value.\n\n    Args:\n    stale (Callable[[tuple[int, str]], Literal[")"]]): The stale value.\n    """\n'
    assert_pdf415(source, ((5,),), ("Google docstring entry 'stale' should be indented beyond its section header",), convention=DocstringConvention.GOOGLE)


def test_relative_google_indentation_uses_raw_whitespace_below_the_docstring_margin() -> None:
    """Preserve a valid one-column nesting relationship that virtual margin stripping would collapse."""
    source = 'def convert(value):\n    """Convert a value.\n\n  Args:\n   value: The value.\n    """\n'
    assert_pdf415(source, (), (), convention=DocstringConvention.GOOGLE)


def test_under_indented_google_exception_list_preserves_every_recovered_name() -> None:
    """Report a complete generic exception-list entry as one issue."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises:\n    `ValueError` | pkg.CustomError: Failure.\n    """\n'
    assert_pdf415(source, ((5,),), ("Google docstring entry 'ValueError', 'pkg.CustomError' should be indented beyond its section header",), convention=DocstringConvention.GOOGLE)


def test_reports_google_continuation_indentation() -> None:
    """Report an immediate Google description aligned with its entry."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        value:\n        The value.\n    """\n'
    assert_pdf415(source, ((6,),), ("Google docstring entry 'value' description should be indented beyond the entry",), convention=DocstringConvention.GOOGLE)


@pytest.mark.parametrize(("section", "entry_type"), [("Returns", "tuple[int, str]"), ("Yields", "str")])
def test_unnamed_google_value_continuation_has_a_clean_message(section: str, entry_type: str) -> None:
    """Describe return and yield continuation indentation without an empty name slot."""
    source = f'def convert():\n    """Convert a value.\n\n    {section}:\n        {entry_type}:\n        Description at entry indentation.\n    """\n'
    assert_pdf415(source, ((6,),), ("Google docstring entry description should be indented beyond the entry",), convention=DocstringConvention.GOOGLE)


@pytest.mark.parametrize(("section", "entry_type"), [("Returns", "tuple[int, str]"), ("Yields", "str")])
def test_unnamed_numpy_value_continuation_has_a_clean_message(section: str, entry_type: str) -> None:
    """Describe NumPy return and yield continuation indentation without an empty name slot."""
    source = f'def convert():\n    """Convert a value.\n\n    {section}\n    {"-" * len(section)}\n    {entry_type}\n    Description at entry indentation.\n    """\n'
    assert_pdf415(source, ((7,),), ("NumPy docstring entry description should be indented beyond the entry",), convention=DocstringConvention.NUMPY)


def test_numpy_exception_continuation_preserves_its_entry_name() -> None:
    """Report an under-indented exception description with its exception identity."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises\n    ------\n    ValueError\n    Description at entry indentation.\n    """\n'
    assert_pdf415(source, ((7,),), ("NumPy docstring entry 'ValueError' description should be indented beyond the entry",), convention=DocstringConvention.NUMPY)


def test_generic_google_section_continuation_retains_its_entry_name() -> None:
    """Keep a parsed name in messages for non-semantic Google section entries."""
    source = 'def convert():\n    """Convert a value.\n\n    Notes:\n        topic:\n        Description at entry indentation.\n    """\n'
    assert_pdf415(source, ((6,),), ("Google docstring entry 'topic' description should be indented beyond the entry",), convention=DocstringConvention.GOOGLE)


def test_reports_numpy_continuation_indentation() -> None:
    """Report an immediate NumPy description aligned with its entry."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Parameters\n    ----------\n    value : int\n    The value.\n    """\n'
    assert_pdf415(source, ((7,),), ("NumPy docstring entry 'value' description should be indented beyond the entry",), convention=DocstringConvention.NUMPY)


def test_numpy_multi_name_continuation_reports_the_complete_entry_identity() -> None:
    """Keep every parsed name in a multi-name continuation diagnostic."""
    source = 'def combine(first, second):\n    """Combine values.\n\n    Parameters\n    ----------\n    first, second : tuple[int, int]\n    Description at entry indentation.\n    """\n'
    assert_pdf415(source, ((7,),), ("NumPy docstring entry 'first', 'second' description should be indented beyond the entry",), convention=DocstringConvention.NUMPY)


@pytest.mark.parametrize("convention", [DocstringConvention.GOOGLE, DocstringConvention.NUMPY])
def test_valid_peer_entry_is_not_mistaken_for_a_continuation(convention: DocstringConvention) -> None:
    """Do not report a valid next entry after an entry with no description."""
    if convention is DocstringConvention.GOOGLE:
        body = "Args:\n        first:\n        second: The second value."
    else:
        body = "Parameters\n    ----------\n    first : int\n    second : str\n        The second value."
    source = f'def convert(first, second):\n    """Convert values.\n\n    {body}\n    """\n'
    assert_pdf415(source, (), (), convention=convention)


def test_valid_generic_google_exception_peer_is_not_mistaken_for_a_continuation() -> None:
    """Accept a generic exception-list entry after an empty exception entry."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises:\n        ValueError:\n        `TypeError` | RuntimeError: The conversion failed.\n    """\n'
    assert_pdf415(source, (), (), convention=DocstringConvention.GOOGLE)


def test_valid_numpy_exception_peer_is_not_mistaken_for_a_continuation() -> None:
    """Accept a second exception entry after an exception with no description."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises\n    ------\n    ValueError\n    pkg.CustomError\n        The conversion failed.\n    """\n'
    assert_pdf415(source, (), (), convention=DocstringConvention.NUMPY)


def test_valid_colon_numpy_exception_peer_is_not_mistaken_for_a_continuation() -> None:
    """Accept a second colon-form exception after an empty colon-form exception entry."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises\n    ------\n    ValueError:\n    pkg.CustomError: The conversion failed.\n    """\n'
    assert_pdf415(source, (), (), convention=DocstringConvention.NUMPY)


def test_empty_colon_numpy_exception_peers_are_not_mistaken_for_continuations() -> None:
    """Accept adjacent colon-form exception entries with empty descriptions."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises\n    ------\n    ValueError:\n    TypeError:\n    """\n'
    assert_pdf415(source, (), (), convention=DocstringConvention.NUMPY)


def test_colon_numpy_exception_checks_its_immediate_continuation_indentation() -> None:
    """Report an aligned description following an empty colon-form exception entry."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises\n    ------\n    ValueError:\n    Failure detail.\n    """\n'
    assert_pdf415(source, ((7,),), ("NumPy docstring entry 'ValueError' description should be indented beyond the entry",), convention=DocstringConvention.NUMPY)


@pytest.mark.parametrize("section", ["Returns", "Yields"])
def test_valid_bare_numpy_value_peer_is_not_mistaken_for_a_continuation(section: str) -> None:
    """Accept an adjacent bare type entry after an empty return or yield entry."""
    source = f'def convert():\n    """Convert a value.\n\n    {section}\n    {"-" * len(section)}\n    tuple[int, str]\n    dict[str, int]\n        Description of the second value.\n    """\n'
    assert_pdf415(source, (), (), convention=DocstringConvention.NUMPY)


@pytest.mark.parametrize(
    "body",
    [
        "Args:\n        value:\n\n        Narrative after a blank line.",
        "Args:\n        value: Inline description.\n        Narrative after a described entry.",
        "Args:\n        value:\n    Returns:\n        str: Result.",
        "Args:\n        value:\n        -----",
        "Args:\n        value:\n        ```text\n        Example text.\n        ```",
    ],
)
def test_google_continuation_guards_do_not_classify_non_immediate_or_structural_content(body: str) -> None:
    """Avoid continuation findings across blanks, after inline text, or on structural boundaries."""
    source = f'def convert(value):\n    """Convert a value.\n\n    {body}\n    """\n'
    assert_pdf415(source, (), (), convention=DocstringConvention.GOOGLE)


def test_disabling_directive_protection_can_expose_a_same_indented_continuation_candidate() -> None:
    """Follow the directive parser setting when classifying an immediate continuation."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        value:\n        .. note:: Narrative detail.\n    """\n'
    protected = CheckSettings(select=("PDF415",), docstring_convention=DocstringConvention.GOOGLE)
    unprotected = CheckSettings(select=("PDF415",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_directives=False)

    assert not format_source(source, settings=protected).unfixed_findings
    result = format_source(source, settings=unprotected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Google docstring entry 'value' description should be indented beyond the entry",)


@pytest.mark.parametrize(
    ("convention", "body", "expected_rule", "expected_message"),
    [
        (
            DocstringConvention.GOOGLE,
            "Args:\n        first:\n        second (int) Missing separator.",
            PDF414MalformedConventionEntry.meta,
            "Google docstring entry 'second' is missing the colon before its description",
        ),
        (
            DocstringConvention.NUMPY,
            "Parameters\n    ----------\n    first : int\n    second list[int]",
            PDF414MalformedConventionEntry.meta,
            "NumPy docstring entry 'second' is missing the colon before its type",
        ),
    ],
)
def test_malformed_next_entry_outranks_a_possible_continuation_issue(convention: DocstringConvention, body: str, expected_rule: object, expected_message: str) -> None:
    """Keep one syntax issue when the same line could first look like an under-indented continuation."""
    source = f'def combine(first, second):\n    """Combine values.\n\n    {body}\n    """\n'
    settings = CheckSettings(select=("PDF414", "PDF415"), docstring_convention=convention)
    result = format_source(source, settings=settings)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (expected_rule,)
    assert tuple(finding.message for finding in result.unfixed_findings) == (expected_message,)


def test_indented_continuations_are_allowed() -> None:
    """Allow descriptions nested beyond their entry heads."""
    google = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        value:\n            The value.\n    """\n'
    numpy = 'def convert(value):\n    """Convert a value.\n\n    Parameters\n    ----------\n    value : int\n        The value.\n    """\n'
    assert_pdf415(google, (), (), convention=DocstringConvention.GOOGLE)
    assert_pdf415(numpy, (), (), convention=DocstringConvention.NUMPY)


def test_docstring_suppression_hides_findings() -> None:
    """Honor whole-docstring suppression from the closing delimiter line."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n    value: The value.\n    """  # noqa: PDF415\n'
    result = format_source(source)
    assert not result.unfixed_findings


def test_signature_line_suppression_does_not_hide_docstring_indentation_findings() -> None:
    """Keep suppression attachment on the malformed docstring rather than its owner signature."""
    source = 'def convert(value):  # noqa: PDF415\n    """Convert a value.\n\n    Args:\n    value: The value.\n    """\n'
    result = format_source(source)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)


def test_implicitly_concatenated_docstring_uses_whole_expression_line_fallback() -> None:
    """Report an unmapped malformed continuation against the complete expression."""
    source = 'def convert(value):\n    (\n        "Convert a value.\\n\\n"\n        "Args:\\n"\n        "    value:\\n"\n        "    Description at entry indentation."\n    )\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3, 4, 5, 6),)


def test_pdf100_and_pdf415_report_independent_indentation_facts() -> None:
    """Allow the source formatter and convention diagnostic to coexist."""
    source = 'def convert(value):\n    """Convert a value.\n\n      Args:\n      value: The value.\n    """\n'
    settings = CheckSettings(select=("PDF100", "PDF415"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings, fix=False)

    assert {finding.rule for finding in result.unfixed_findings} == {PDF100DocstringIndentation.meta, PDF415ConventionEntryIndentation.meta}


def test_pdf101_does_not_reflow_a_diagnosed_numpy_continuation() -> None:
    """Keep uncertain continuation indentation unchanged while retaining PDF415."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Parameters\n    ----------\n    value : int\n    Description at entry indentation that would otherwise be wrapped.\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF415"), docstring_convention=DocstringConvention.NUMPY, line_length=45)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert PDF101DocstringReflow.meta not in result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF415ConventionEntryIndentation.meta,)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("NumPy docstring entry 'value' description should be indented beyond the entry",)


@pytest.mark.parametrize("selector", ["PDF415", "PDF4", "PDF", "ALL"])
def test_normal_selectors_include_rule(selector: str) -> None:
    """Keep the objective diagnostic in normal broad selection."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n    value: The value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=(selector,), docstring_convention=DocstringConvention.GOOGLE), fix=False)
    assert PDF415ConventionEntryIndentation.meta in {finding.rule for finding in result.unfixed_findings}


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.REST])
def test_rule_is_disabled_outside_google_and_numpy(convention: DocstringConvention) -> None:
    """Disable exact selection when the indentation grammar is unsupported."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n    value: The value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF415",), docstring_convention=convention))
    assert not result.unfixed_findings
