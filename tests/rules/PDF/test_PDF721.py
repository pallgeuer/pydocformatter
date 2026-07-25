"""Tests for PDF721 warning-missing-description."""

# Future imports
from __future__ import annotations

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF409_docstring_entry_spacing import PDF409DocstringEntrySpacing
from pydocformatter.rules.definitions.PDF.PDF410_exception_entry_normalization import PDF410ExceptionEntryNormalization
from pydocformatter.rules.definitions.PDF.PDF721_warning_missing_description import PDF721WarningMissingDescription
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF721")
format_source = pdf_helpers.formatter_for("PDF721")


def assert_pdf721(source: str, expected_lines: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF721 findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected_lines, meta=PDF721WarningMissingDescription.meta, settings=settings)


def test_metadata() -> None:
    """Expose the stable diagnostic-only rule identity."""
    assert PDF721WarningMissingDescription.meta.name == "warning-missing-description"
    assert PDF721WarningMissingDescription.meta.stable_since == "1.1.0"


@pytest.mark.parametrize("section", ["Warn", "Warns"])
def test_reports_google_warning_aliases_without_descriptions(section: str) -> None:
    source = f'def convert():\n    """Convert a value.\n\n    {section}:\n        RuntimeWarning:\n        `UserWarning` | warnings.CustomWarning:\n        FutureWarning: Future behavior changed.\n    """\n'
    result = assert_pdf721(source, ((5,), (6,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Warning 'RuntimeWarning' docstring entry is missing a description",
        "Warning 'UserWarning, warnings.CustomWarning' docstring entry is missing a description",
    )


@pytest.mark.parametrize("section", ["Warn", "Warns"])
def test_reports_numpy_warning_sections_without_descriptions(section: str) -> None:
    source = f'def convert():\n    """Convert a value.\n\n    {section}\n    {"-" * len(section)}\n    RuntimeWarning\n    UserWarning: Warning detail.\n    """\n'
    settings = CheckSettings(select=("PDF721",), docstring_convention=DocstringConvention.NUMPY)
    assert_pdf721(source, ((6,),), settings=settings)


@pytest.mark.parametrize("section", ["Warning", "Warnings"])
def test_google_warning_admonitions_are_not_emitted_warning_entries(section: str) -> None:
    source = f'def convert():\n    """Convert a value.\n\n    {section}:\n        RuntimeWarning:\n    """\n'
    assert_pdf721(source, ())


@pytest.mark.parametrize("section", ["Warning", "Warnings"])
def test_numpy_warning_cautions_are_not_emitted_warning_entries(section: str) -> None:
    source = f'def convert():\n    """Convert a value.\n\n    {section}\n    {"-" * len(section)}\n    Experimental\n    """\n'
    settings = CheckSettings(select=("PDF721",), docstring_convention=DocstringConvention.NUMPY)

    assert_pdf721(source, (), settings=settings)


def test_protected_only_warning_body_does_not_count_as_prose() -> None:
    source = 'def convert():\n    """Convert.\n\n    Warns:\n        RuntimeWarning:\n            ```text\n            protected only\n            ```\n    """\n'
    assert_pdf721(source, ((5,),))


def test_checks_attached_attribute_docstrings() -> None:
    source = 'value = 1\n"""Value.\n\nWarns:\n    RuntimeWarning:\n"""\n'
    assert_pdf721(source, ((5,),))


@pytest.mark.parametrize("selector", ["PDF721", "PDF7", "PDF", "ALL"])
def test_normal_selectors_include_rule_under_supported_conventions(selector: str) -> None:
    for convention in (DocstringConvention.GOOGLE, DocstringConvention.NUMPY):
        settings = CheckSettings(select=(selector,), docstring_convention=convention)
        active_codes = {selected.rule.code.tag for selected in rules_selection.select_rules(settings).rules}

        assert "PDF721" in active_codes


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.REST])
def test_rule_is_disabled_outside_google_and_numpy(convention: DocstringConvention) -> None:
    source = 'def convert():\n    """Convert.\n\n    Warns:\n        RuntimeWarning:\n    """\n'
    settings = CheckSettings(select=("PDF721",), docstring_convention=convention)
    assert_pdf721(source, (), settings=settings)


def test_docstring_suppression_hides_findings() -> None:
    source = 'def convert():\n    """Convert.\n\n    Warns:\n        RuntimeWarning:\n    """  # noqa: PDF721\n'
    assert not format_source(source).unfixed_findings


def test_direct_rule_and_formatter_findings_agree_without_fixes() -> None:
    source = 'def convert():\n    """Convert.\n\n    Warns:\n        RuntimeWarning:\n    """\n'
    _, context = contexts(source)
    direct = rule_helpers.rule_findings(PDF721WarningMissingDescription, context)
    formatted = format_source(source)

    assert tuple(finding.line_numbers for finding in direct) == ((5,),)
    assert tuple(finding.line_numbers for finding in formatted.unfixed_findings) == ((5,),)
    assert not rule_helpers.rule_fix_result(PDF721WarningMissingDescription, context).fixed_findings


def test_spacing_normalization_and_missing_description_remain_independent_for_warning_lists() -> None:
    source = 'def convert():\n    """Convert.\n\n    Warns:\n        `RuntimeWarning` | UserWarning   :\n    """\n'
    settings = CheckSettings(select=("PDF409", "PDF410", "PDF721"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def convert():\n    """Convert.\n\n    Warns:\n        RuntimeWarning, UserWarning:\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF721WarningMissingDescription.meta,)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Warning 'RuntimeWarning, UserWarning' docstring entry is missing a description",)


def test_concatenated_warning_entry_keeps_all_overlapping_diagnostics_unfixed() -> None:
    source = 'def convert():\n    ("Convert.\\n\\n"\n     "Warns:\\n"\n     "    `RuntimeWarning` | UserWarning   :")\n'
    settings = CheckSettings(select=("PDF409", "PDF410", "PDF721"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF409DocstringEntrySpacing.meta, PDF410ExceptionEntryNormalization.meta, PDF721WarningMissingDescription.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4), (2, 3, 4), (2, 3, 4))
