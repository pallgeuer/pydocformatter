"""Tests for PDF720 exception-missing-description."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF412_repeated_docstring_entry import PDF412RepeatedDocstringEntry
from pydocformatter.rules.definitions.PDF.PDF414_malformed_convention_entry import PDF414MalformedConventionEntry
from pydocformatter.rules.definitions.PDF.PDF415_convention_entry_indentation import PDF415ConventionEntryIndentation
from pydocformatter.rules.definitions.PDF.PDF506_missing_exception_documentation import PDF506MissingExceptionDocumentation
from pydocformatter.rules.definitions.PDF.PDF507_extraneous_exception_documentation import PDF507ExtraneousExceptionDocumentation
from pydocformatter.rules.definitions.PDF.PDF720_exception_missing_description import PDF720ExceptionMissingDescription
from pydocformatter.rules.definitions.PDF.PDF721_warning_missing_description import PDF721WarningMissingDescription
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF720")
format_source = pdf_helpers.formatter_for("PDF720")


def assert_pdf720(source: str, expected_lines: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF720 findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected_lines, meta=PDF720ExceptionMissingDescription.meta, settings=settings)


def test_metadata() -> None:
    """Expose the stable diagnostic-only rule identity."""
    assert PDF720ExceptionMissingDescription.meta.name == "exception-missing-description"
    assert PDF720ExceptionMissingDescription.meta.stable_since == "1.1.0"


@pytest.mark.parametrize("section", ["Raise", "Raises"])
def test_reports_google_exception_aliases_without_descriptions(section: str) -> None:
    source = f'def convert():\n    """Convert a value.\n\n    {section}:\n        ValueError:\n        `TypeError` | errors.CustomError:\n        LookupError: Lookup failed.\n    """\n'
    result = assert_pdf720(source, ((5,), (6,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Exception 'ValueError' docstring entry is missing a description",
        "Exception 'TypeError, errors.CustomError' docstring entry is missing a description",
    )


@pytest.mark.parametrize("section", ["Raise", "Raises"])
def test_reports_numpy_exception_aliases_without_descriptions(section: str) -> None:
    source = (
        f'def convert():\n    """Convert a value.\n\n    {section}\n    {"-" * len(section)}\n    ValueError\n    `TypeError` | errors.CustomError:\n    LookupError\n        Lookup failed.\n    """\n'
    )
    settings = CheckSettings(select=("PDF720",), docstring_convention=DocstringConvention.NUMPY)
    result = assert_pdf720(source, ((6,), (7,)), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Exception 'ValueError' docstring entry is missing a description",
        "Exception 'TypeError, errors.CustomError' docstring entry is missing a description",
    )


@pytest.mark.parametrize("field", ["raise", "raises", "except", "exception"])
def test_reports_rest_exception_aliases_without_descriptions(field: str) -> None:
    source = f'def convert():\n    """Convert a value.\n\n    :{field} ValueError:\n    """\n'
    settings = CheckSettings(select=("PDF720",), docstring_convention=DocstringConvention.REST)
    assert_pdf720(source, ((4,),), settings=settings)


def test_invalid_and_nameless_rest_exception_fields_remain_outside_pdf720() -> None:
    source = 'def convert():\n    """Convert a value.\n\n    :raises:\n    :raises ValueError extra:\n    :raises ValueError:\n    """\n'
    settings = CheckSettings(select=("PDF720",), docstring_convention=DocstringConvention.REST)
    result = assert_pdf720(source, ((6,),), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Exception 'ValueError' docstring entry is missing a description",)


def test_rest_multi_name_entry_is_one_finding_and_indented_continuation_is_prose() -> None:
    source = 'def convert():\n    """Convert a value.\n\n    :raises ValueError, TypeError:\n    :raises LookupError:\n        Lookup failed.\n    """\n'
    settings = CheckSettings(select=("PDF720",), docstring_convention=DocstringConvention.REST)
    result = assert_pdf720(source, ((4,),), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Exception 'ValueError, TypeError' docstring entry is missing a description",)


def test_only_parsed_prose_counts_as_a_description() -> None:
    source = 'def convert():\n    """Convert a value.\n\n    Raises:\n        ValueError:   \n        TypeError:\n            Type conversion failed.\n        RuntimeError:\n            ```text\n            protected only\n            ```\n    """\n'
    result = assert_pdf720(source, ((5,), (8,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Exception 'ValueError' docstring entry is missing a description",
        "Exception 'RuntimeError' docstring entry is missing a description",
    )


def test_protected_structures_terminate_entries_and_later_narrative_does_not_leak_into_descriptions() -> None:
    source = 'def convert():\n    """Convert.\n\n    Raises:\n        ValueError: Raised before the protected example.\n            ```text\n            protected example\n            ```\n        TypeError:\n            ```text\n            protected only\n            ```\n            Narrative after the protected block.\n\n    Warns:\n        RuntimeWarning: Emitted before the protected item.\n            - protected list item\n        UserWarning:\n            - protected only\n            Narrative after the protected item.\n    """\n'
    settings = CheckSettings(select=("PDF720", "PDF721"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF720ExceptionMissingDescription.meta, PDF721WarningMissingDescription.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,), (18,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Exception 'TypeError' docstring entry is missing a description",
        "Warning 'UserWarning' docstring entry is missing a description",
    )


def test_parser_protection_settings_authoritatively_control_description_content() -> None:
    source = 'def convert():\n    """Convert a value.\n\n    Raises:\n        RuntimeError:\n            ```text\n            protected only\n            ```\n    """\n'
    protected = assert_pdf720(source, ((5,),))
    unprotected_settings = CheckSettings(select=("PDF720",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_code_fences=False)
    unprotected = assert_pdf720(source, (), settings=unprotected_settings)

    assert protected.unfixed_findings
    assert not unprotected.unfixed_findings


@pytest.mark.parametrize(
    ("settings_to_disable", "protected_body"),
    [
        (("docstring_parse_list_items",), "            - protected only"),
        (("docstring_parse_headings",), "            Protected heading\n            -----------------"),
        (("docstring_parse_doctests", "docstring_parse_block_quotes"), "            >>> protected_call()"),
        (("docstring_parse_code_fences",), "            ```text\n            protected only\n            ```"),
        (("docstring_parse_block_quotes",), "            > protected only"),
        (("docstring_parse_tables",), "            | Kind | Value |\n            | --- | --- |\n            | status | protected |"),
        (("docstring_parse_directives", "docstring_parse_literal_blocks"), "            .. note::\n                protected only"),
        (("docstring_parse_literal_blocks",), "            Example::\n\n                protected only"),
    ],
)
def test_every_parser_protection_setting_controls_exception_and_warning_completeness(settings_to_disable: tuple[str, ...], protected_body: str) -> None:
    source = f'def convert():\n    """Convert.\n\n    Raises:\n        ValueError:\n{protected_body}\n\n    Warns:\n        RuntimeWarning:\n{protected_body}\n    """\n'
    base_settings = CheckSettings(select=("PDF720", "PDF721"), docstring_convention=DocstringConvention.GOOGLE)
    protected = format_source(source, settings=base_settings)
    unprotected = format_source(source, settings=dataclasses.replace(base_settings, **dict.fromkeys(settings_to_disable, False)))
    exception_line = source.splitlines().index("        ValueError:") + 1
    warning_line = source.splitlines().index("        RuntimeWarning:") + 1

    assert tuple(finding.rule for finding in protected.unfixed_findings) == (PDF720ExceptionMissingDescription.meta, PDF721WarningMissingDescription.meta)
    assert tuple(finding.line_numbers for finding in protected.unfixed_findings) == ((exception_line,), (warning_line,))
    assert not unprotected.unfixed_findings


def test_numpy_protected_descriptions_follow_parser_settings_for_both_entry_families() -> None:
    source = 'def convert():\n    """Convert.\n\n    Raises\n    ------\n    ValueError\n        ```text\n        protected only\n        ```\n\n    Warns\n    -----\n    RuntimeWarning\n        ```text\n        protected only\n        ```\n    """\n'
    base_settings = CheckSettings(select=("PDF720", "PDF721"), docstring_convention=DocstringConvention.NUMPY)
    protected = format_source(source, settings=base_settings)
    unprotected = format_source(source, settings=dataclasses.replace(base_settings, docstring_parse_code_fences=False))

    assert tuple(finding.rule for finding in protected.unfixed_findings) == (PDF720ExceptionMissingDescription.meta, PDF721WarningMissingDescription.meta)
    assert tuple(finding.line_numbers for finding in protected.unfixed_findings) == ((6,), (13,))
    assert not unprotected.unfixed_findings


def test_rest_protected_continuation_follows_parser_settings() -> None:
    source = 'def convert():\n    """Convert.\n\n    :raises ValueError:\n        ```text\n        protected only\n        ```\n    """\n'
    base_settings = CheckSettings(select=("PDF720",), docstring_convention=DocstringConvention.REST)
    protected = format_source(source, settings=base_settings)
    unprotected = format_source(source, settings=dataclasses.replace(base_settings, docstring_parse_code_fences=False))

    assert tuple(finding.rule for finding in protected.unfixed_findings) == (PDF720ExceptionMissingDescription.meta,)
    assert tuple(finding.line_numbers for finding in protected.unfixed_findings) == ((4,),)
    assert not unprotected.unfixed_findings


def test_checks_primary_and_supported_attached_attribute_docstrings() -> None:
    source = (
        '"""Module.\n\nRaises:\n    ModuleError:\n"""\n\n'
        'module_value = 1\n"""Module value.\n\nRaises:\n    ModuleValueError:\n"""\n\n'
        'class Client:\n    """Client.\n\n    Raises:\n        ClientError:\n    """\n\n'
        '    class_value = 1\n    """Class value.\n\n    Raises:\n        ClassValueError:\n    """\n\n'
        '    def method(self):\n        """Run.\n\n        Raises:\n            MethodError:\n        """\n\n'
        '    def __init__(self):\n        """Initialize.\n\n        Raises:\n            InitError:\n        """\n        self.instance_value = 1\n        """Instance value.\n\n        Raises:\n            InstanceValueError:\n        """\n\n'
        'def outer():\n    """Outer.\n\n    Raises:\n        OuterError:\n    """\n\n'
        '    def nested():\n        """Nested.\n\n        Raises:\n            NestedError:\n        """\n'
    )
    result = assert_pdf720(source, ((4,), (11,), (18,), (25,), (32,), (39,), (45,), (52,), (59,)))

    assert len(result.unfixed_findings) == 9


@pytest.mark.parametrize(
    ("source", "expected_lines"),
    [
        ('def convert():\n    r"""Convert.\n\n    Raises:\n        ValueError:\n    """\n', (5,)),
        ('def convert(): """Convert.\\n\\n    Raises:\\n        ValueError:"""; return None\n', (1,)),
        ('def convert():\n    ("Convert.\\n\\n"\n     "Raises:\\n"\n     "    ValueError:")\n', (2, 3, 4)),
        ('def convert():\r\n    """Convert.\r\n\r\n    Raises:\r\n        ValueError:\r\n    """\r\n', (5,)),
    ],
)
def test_reports_supported_literal_shapes_and_line_endings(source: str, expected_lines: tuple[int, ...]) -> None:
    assert_pdf720(source, (expected_lines,))


@pytest.mark.parametrize("indent_width", [1, 4, 8])
def test_tab_indented_entries_follow_the_configured_visual_indent_width(indent_width: int) -> None:
    source = 'def convert():\n\t"""Convert.\n\n\tRaises:\n\t\tValueError:\n\t"""\n'
    settings = CheckSettings(select=("PDF720",), docstring_convention=DocstringConvention.GOOGLE, indent_width=indent_width)

    assert_pdf720(source, ((5,),), settings=settings)


@pytest.mark.parametrize("selector", ["PDF720", "PDF7", "PDF", "ALL"])
def test_normal_selectors_include_rule(selector: str) -> None:
    settings = CheckSettings(select=(selector,), docstring_convention=DocstringConvention.GOOGLE)
    active_codes = {selected.rule.code.tag for selected in rules_selection.select_rules(settings).rules}

    assert "PDF720" in active_codes


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_rule_is_disabled_for_unparsed_conventions(convention: DocstringConvention) -> None:
    source = 'def convert():\n    """Convert.\n\n    Raises:\n        ValueError:\n    """\n'
    settings = CheckSettings(select=("PDF720",), docstring_convention=convention)
    assert_pdf720(source, (), settings=settings)


def test_docstring_suppression_hides_findings() -> None:
    source = 'def convert():\n    """Convert.\n\n    Raises:\n        ValueError:\n    """  # noqa: PDF720\n'
    assert not format_source(source).unfixed_findings


def test_direct_rule_and_formatter_findings_agree_without_fixes() -> None:
    source = 'def convert():\n    """Convert.\n\n    Raises:\n        ValueError:\n    """\n'
    _, context = contexts(source)
    direct = rule_helpers.rule_findings(PDF720ExceptionMissingDescription, context)
    formatted = format_source(source)

    assert tuple(finding.line_numbers for finding in direct) == ((5,),)
    assert tuple(finding.line_numbers for finding in formatted.unfixed_findings) == ((5,),)
    assert not rule_helpers.rule_fix_result(PDF720ExceptionMissingDescription, context).fixed_findings


def test_repetition_and_indentation_diagnostics_remain_independent() -> None:
    repeated = 'def convert():\n    """Convert.\n\n    Raises:\n        ValueError:\n        ValueError:\n    """\n'
    repeated_settings = CheckSettings(select=("PDF412", "PDF720"), docstring_convention=DocstringConvention.GOOGLE)
    repeated_result = format_source(repeated, settings=repeated_settings)

    assert {finding.rule for finding in repeated_result.unfixed_findings} == {PDF412RepeatedDocstringEntry.meta, PDF720ExceptionMissingDescription.meta}
    assert sum(finding.rule == PDF720ExceptionMissingDescription.meta for finding in repeated_result.unfixed_findings) == 2

    indented = 'def convert():\n    """Convert.\n\n    Raises:\n        ValueError:\n        Failure at entry indentation.\n    """\n'
    indented_settings = CheckSettings(select=("PDF415", "PDF720"), docstring_convention=DocstringConvention.GOOGLE)
    indented_result = format_source(indented, settings=indented_settings, fix=False)

    assert {finding.rule for finding in indented_result.unfixed_findings} == {PDF415ConventionEntryIndentation.meta, PDF720ExceptionMissingDescription.meta}


def test_malformed_exception_and_warning_heads_are_owned_only_by_pdf414() -> None:
    source = 'def convert():\n    """Convert.\n\n    Raises:\n        ValueError Failure detail.\n\n    Warns:\n        RuntimeWarning Warning detail.\n    """\n'
    settings = CheckSettings(select=("PDF414", "PDF720", "PDF721"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings, fix=False)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF414MalformedConventionEntry.meta, PDF414MalformedConventionEntry.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (8,))


def test_missing_descriptions_are_independent_of_exception_code_consistency() -> None:
    source = (
        'def raised():\n    """Raise an error.\n\n    Raises:\n        ValueError:\n    """\n    raise ValueError("bad")\n\n\n'
        'def stale():\n    """Document a stale error.\n\n    Raises:\n        TypeError:\n    """\n    return None\n'
    )
    settings = CheckSettings(select=("PDF506", "PDF507", "PDF720"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)
    findings_by_rule = {
        rule: tuple(finding for finding in result.unfixed_findings if finding.rule == rule)
        for rule in (PDF506MissingExceptionDocumentation.meta, PDF507ExtraneousExceptionDocumentation.meta, PDF720ExceptionMissingDescription.meta)
    }

    assert not findings_by_rule[PDF506MissingExceptionDocumentation.meta]
    assert tuple(finding.line_numbers for finding in findings_by_rule[PDF507ExtraneousExceptionDocumentation.meta]) == ((14,),)
    assert tuple(finding.line_numbers for finding in findings_by_rule[PDF720ExceptionMissingDescription.meta]) == ((5,), (14,))
