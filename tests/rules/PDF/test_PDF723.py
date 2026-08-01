"""Tests for PDF723 method-missing-description."""

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
from pydocformatter.rules.definitions.PDF.PDF308_entry_description_trailing_period import PDF308EntryDescriptionTrailingPeriod
from pydocformatter.rules.definitions.PDF.PDF412_repeated_docstring_entry import PDF412RepeatedDocstringEntry
from pydocformatter.rules.definitions.PDF.PDF414_malformed_convention_entry import PDF414MalformedConventionEntry
from pydocformatter.rules.definitions.PDF.PDF723_method_missing_description import PDF723MethodMissingDescription
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF723", convention=DocstringConvention.GOOGLE)
format_source = pdf_helpers.formatter_for("PDF723", convention=DocstringConvention.GOOGLE)


def assert_pdf723(source: str, expected_lines: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF723 findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected_lines, meta=PDF723MethodMissingDescription.meta, settings=settings)


def test_metadata() -> None:
    """Expose the stable diagnostic-only rule identity."""
    assert PDF723MethodMissingDescription.meta.name == "method-missing-description"
    assert PDF723MethodMissingDescription.meta.message == "Method docstring entry is missing a description"
    assert PDF723MethodMissingDescription.meta.stable_since == "1.1.0"


def test_reports_google_method_entries_without_descriptions() -> None:
    """Check inline and continuation Google method descriptions."""
    source = 'class Client:\n    """Coordinate operations.\n\n    Methods:\n        connect:\n        close: Close the connection.\n        reset:\n            Reset the connection.\n    """\n'
    result = assert_pdf723(source, ((5,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Method 'connect' docstring entry is missing a description",)


def test_reports_balanced_google_method_signatures_without_descriptions() -> None:
    """Treat empty and complex balanced signatures as method entry heads."""
    source = 'class Client:\n    """Coordinate operations.\n\n    Methods:\n        connect():\n        convert(value: tuple[int, str], *, mode=Literal[")", "safe"]): Convert the value.\n    """\n'
    result = assert_pdf723(source, ((5,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Method 'connect' docstring entry is missing a description",)


def test_reports_numpy_method_entries_without_descriptions() -> None:
    """Check canonical signature-shaped NumPy method heads."""
    source = 'class Client:\n    """Coordinate operations.\n\n    Methods\n    -------\n    connect(timeout=30)\n    close()\n        Close the connection.\n    """\n'
    settings = CheckSettings(select=("PDF723",), docstring_convention=DocstringConvention.NUMPY)

    assert_pdf723(source, ((6,),), settings=settings)


def test_preserves_legacy_numpy_type_bearing_method_entries() -> None:
    """Keep existing type-bearing NumPy method entries compatible."""
    source = 'class Client:\n    """Coordinate operations.\n\n    Methods\n    -------\n    connect : Callable[[], None]\n    close : Callable[[], None]\n        Close the connection.\n    """\n'
    settings = CheckSettings(select=("PDF723",), docstring_convention=DocstringConvention.NUMPY)

    assert_pdf723(source, ((6,),), settings=settings)


@pytest.mark.parametrize(("convention", "body", "expected_line"), [(DocstringConvention.GOOGLE, "Methods:\n        run():", 5), (DocstringConvention.NUMPY, "Methods\n    -------\n    run()", 6)])
def test_valid_method_signatures_are_shared_with_structural_rules(convention: DocstringConvention, body: str, expected_line: int) -> None:
    """Report only PDF723 when valid method signatures lack descriptions."""
    source = f'class Client:\n    """Client.\n\n    {body}\n    """\n'
    settings = CheckSettings(select=("PDF414", "PDF415", "PDF723"), docstring_convention=convention)
    result = format_source(source, settings=settings)

    assert tuple((finding.rule, finding.line_numbers) for finding in result.unfixed_findings) == ((PDF723MethodMissingDescription.meta, (expected_line,)),)


def test_google_whitespace_only_descriptions_remain_missing() -> None:
    """Reject inline and continuation descriptions containing no prose."""
    source = 'class Client:\n    """Client.\n\n    Methods:\n        connect:   \n        close:\n            \t\n    """\n'

    assert_pdf723(source, ((5,), (6,)))


def test_protected_only_body_does_not_count_as_prose() -> None:
    """Use the parser's protected-content boundary for method completeness."""
    source = 'class Client:\n    """Coordinate operations.\n\n    Methods:\n        connect:\n            ```text\n            protected only\n            ```\n        close: Close the connection.\n    """\n'

    assert_pdf723(source, ((5,),))


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
def test_every_parser_protection_setting_controls_method_completeness(settings_to_disable: tuple[str, ...], protected_body: str) -> None:
    """Treat disabled protected syntax as ordinary parsed description text."""
    source = f'class Client:\n    """Coordinate operations.\n\n    Methods:\n        connect:\n{protected_body}\n    """\n'
    base_settings = CheckSettings(select=("PDF723",), docstring_convention=DocstringConvention.GOOGLE)
    protected = assert_pdf723(source, ((5,),), settings=base_settings)
    unprotected = assert_pdf723(source, (), settings=dataclasses.replace(base_settings, **dict.fromkeys(settings_to_disable, False)))

    assert protected.unfixed_findings
    assert not unprotected.unfixed_findings


def test_numpy_protected_description_follows_parser_settings() -> None:
    """Apply parser-protection settings to NumPy method entries too."""
    source = 'class Client:\n    """Coordinate operations.\n\n    Methods\n    -------\n    connect : Callable[[], None]\n        ```text\n        protected only\n        ```\n    """\n'
    base_settings = CheckSettings(select=("PDF723",), docstring_convention=DocstringConvention.NUMPY)
    protected = assert_pdf723(source, ((6,),), settings=base_settings)
    unprotected = assert_pdf723(source, (), settings=dataclasses.replace(base_settings, docstring_parse_code_fences=False))

    assert protected.unfixed_findings
    assert not unprotected.unfixed_findings


def test_narrative_after_protected_structure_does_not_leak_into_method_description() -> None:
    """Keep entry termination at a protected structure authoritative."""
    source = 'class Client:\n    """Coordinate operations.\n\n    Methods:\n        connect:\n            - protected only\n            Narrative after the protected item.\n        close: Close the connection.\n    """\n'

    assert_pdf723(source, ((5,),))


def test_checks_nested_and_function_local_class_docstrings() -> None:
    """Apply to every primary class docstring regardless of owner chain."""
    source = (
        'class Outer:\n    """Outer.\n\n    Methods:\n        outer:\n    """\n\n'
        '    class Inner:\n        """Inner.\n\n        Methods:\n            inner:\n        """\n\n'
        'def factory():\n    class Local:\n        """Local.\n\n        Methods:\n            local:\n        """\n    return Local\n'
    )

    assert_pdf723(source, ((5,), (12,), (20,)))


def test_excludes_non_class_and_attached_attribute_docstrings() -> None:
    """Do not assign class-method semantics to other docstring owners."""
    source = (
        '"""Module.\n\nMethods:\n    module:\n"""\n\n'
        'value = 1\n"""Value.\n\nMethods:\n    module_attribute:\n"""\n\n'
        'def function():\n    """Function.\n\n    Methods:\n        function_entry:\n    """\n\n'
        'class Client:\n    class_value = 1\n    """Value.\n\n    Methods:\n        class_attribute:\n    """\n\n'
        '    def method(self):\n        """Method.\n\n        Methods:\n            method_entry:\n        """\n'
    )

    assert_pdf723(source, ())


def test_unknown_documented_method_names_remain_in_scope() -> None:
    """Check prose completeness without performing method inventory validation."""
    source = 'class Client:\n    """Client.\n\n    Methods:\n        unknown:\n    """\n'

    assert_pdf723(source, ((5,),))


def test_empty_and_malformed_method_sections_are_owned_by_structural_rules() -> None:
    """Skip absent parsed entries and high-confidence malformed heads."""
    empty = 'class Client:\n    """Client.\n\n    Methods:\n    """\n'
    malformed = 'class Client:\n    """Client.\n\n    Methods:\n        connect Execute it.\n    """\n\n    def connect(self):\n        pass\n'
    malformed_settings = CheckSettings(select=("PDF414", "PDF723"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(malformed, settings=malformed_settings, fix=False)

    assert_pdf723(empty, ())
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF414MalformedConventionEntry.meta,)


def test_repeated_and_style_diagnostics_remain_independent() -> None:
    """Allow repetition and present-description style rules to report separately."""
    source = 'class Client:\n    """Client.\n\n    Methods:\n        connect:\n        connect:\n        close: close the connection\n    """\n'
    settings = CheckSettings(select=("PDF308", "PDF412", "PDF723"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace("close the connection\n", "close the connection.\n")
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert sum(finding.rule == PDF723MethodMissingDescription.meta for finding in result.unfixed_findings) == 2
    assert sum(finding.rule == PDF412RepeatedDocstringEntry.meta for finding in result.unfixed_findings) == 1


@pytest.mark.parametrize("selector", ["PDF723", "PDF7", "PDF", "ALL"])
def test_normal_selectors_include_rule_under_supported_conventions(selector: str) -> None:
    """Keep PDF723 broadly selected for Google and NumPy."""
    for convention in (DocstringConvention.GOOGLE, DocstringConvention.NUMPY):
        active_codes = {selected.rule.code.tag for selected in rules_selection.select_rules(CheckSettings(select=(selector,), docstring_convention=convention)).rules}

        assert "PDF723" in active_codes


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.REST])
def test_rule_is_disabled_outside_google_and_numpy(convention: DocstringConvention) -> None:
    """Disable the rule when the selected convention cannot parse method entries."""
    source = 'class Client:\n    """Client.\n\n    Methods:\n        connect:\n    """\n'

    assert_pdf723(source, (), settings=CheckSettings(select=("PDF723",), docstring_convention=convention))


def test_docstring_suppression_hides_findings() -> None:
    """Suppress the class docstring finding from its closing line."""
    source = 'class Client:\n    """Client.\n\n    Methods:\n        connect:\n    """  # noqa: PDF723\n'

    assert not format_source(source).unfixed_findings


def test_direct_rule_and_formatter_findings_agree_without_fixes() -> None:
    """Return the same diagnostic through the direct hook and formatter."""
    source = 'class Client:\n    """Client.\n\n    Methods:\n        connect:\n    """\n'
    _, context = contexts(source)
    direct = rule_helpers.rule_findings(PDF723MethodMissingDescription, context)
    formatted = format_source(source)

    assert tuple(finding.line_numbers for finding in direct) == ((5,),)
    assert tuple(finding.line_numbers for finding in formatted.unfixed_findings) == ((5,),)
    assert not rule_helpers.rule_fix_result(PDF723MethodMissingDescription, context).fixed_findings
