"""Tests for PDF418 malformed reStructuredText directive introducers."""

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF418_malformed_rest_directive_introducer import PDF418MalformedRestDirectiveIntroducer
from pydocformatter.rules.models import FixAvailability


format_source = pdf_helpers.formatter_for("PDF418")


def assert_pdf418_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF418 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF418MalformedRestDirectiveIntroducer.meta, settings=settings)


def test_metadata() -> None:
    assert PDF418MalformedRestDirectiveIntroducer.meta.fix_availability is FixAvailability.NEVER


@pytest.mark.parametrize(
    "name", ["version-added", "versionadded", "version-changed", "VersionChanged", "version-deprecated", "DEPRECATED", "version-removed", "versionremoved", "py:function", "domain.sub:thing"]
)
def test_reports_unambiguous_malformed_directives_without_bodies(name: str) -> None:
    source = f'def function():\n    """Summary.\n\n    .. {name}: argument\n    """\n'
    result = assert_pdf418_lines(source, ((4,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == (f"reST directive '{name}' must be followed by two colons",)


def test_reports_multiple_directives_in_source_order() -> None:
    source = 'def function():\n    """Summary.\n\n    .. versionadded: 1.0\n    .. py:function: function()\n    """\n'
    result = assert_pdf418_lines(source, ((4,), (5,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "reST directive 'versionadded' must be followed by two colons",
        "reST directive 'py:function' must be followed by two colons",
    )


@pytest.mark.parametrize("convention", tuple(DocstringConvention))
def test_reports_under_every_docstring_convention(convention: DocstringConvention) -> None:
    source = 'def function():\n    """.. deprecated: 1.0"""\n'

    assert_pdf418_lines(source, ((2,),), settings=CheckSettings(select=("PDF418",), docstring_convention=convention))


def test_reports_crlf_source_lines_without_changing_line_endings() -> None:
    source = 'def function():\r\n    """Summary.\r\n\r\n    .. versionchanged: 1.0\r\n    """\r\n'
    result = assert_pdf418_lines(source, ((4,),))

    assert result.new_source == source


def test_reports_arbitrary_directive_name_only_with_indented_body() -> None:
    with_body = 'def function():\n    """Summary.\n\n    .. caution: Important\n        Keep this body unchanged.\n    """\n'
    unicode_with_body = 'def function():\n    """Summary.\n\n    .. n\N{LATIN SMALL LETTER O WITH DIAERESIS}te : Important\n        Keep this body unchanged.\n    """\n'
    without_body = 'def function():\n    """Summary.\n\n    .. caution: ordinary text\n    """\n'

    assert_pdf418_lines(with_body, ((4,),))
    assert_pdf418_lines(unicode_with_body, ((4,),))
    assert_pdf418_lines(without_body, ())


def test_accepts_valid_directives_and_rejects_near_misses() -> None:
    source = 'def function():\n    """Summary.\n\n    .. note :: Valid.\n    .. py:function:: signature\n    .. n\N{LATIN SMALL LETTER O WITH DIAERESIS}te:: Valid.\n    .. note::text\n    . note::\n    note:\n    ... note:\n    :param value: Description.\n    """\n'

    assert_pdf418_lines(source, ())


def test_protects_malformed_directive_body_from_pdf101_reflow_when_pdf418_is_unselected() -> None:
    source = 'def function():\n    """Summary.\n\n    .. caution:\n        This deliberately long directive body stays on its original physical line during docstring reflow.\n    """\n'
    settings = CheckSettings(select=("PDF101",), line_length=50)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_arbitrary_directive_confidence_skips_blank_lines_before_the_indented_body() -> None:
    source = 'def function():\n    """Summary.\n\n    .. custom:\n\n        Body.\n    """\n'

    assert_pdf418_lines(source, ((4,),))


def test_reports_inside_google_section_and_preserves_nested_body() -> None:
    source = 'def function(value):\n    """Convert a value.\n\n    Args:\n        .. custom:\n            Nested directive body.\n        value (int): Input value.\n    """\n'

    assert_pdf418_lines(source, ((5,),), settings=CheckSettings(select=("PDF418",), docstring_convention=DocstringConvention.GOOGLE))


@pytest.mark.parametrize(
    ("convention", "source", "expected_line"),
    [
        (DocstringConvention.REST, 'def function(value):\n    """Convert a value.\n\n    :param value: Input value.\n        .. custom:\n            Nested directive body.\n    """\n', 5),
        (
            DocstringConvention.NUMPY,
            'def function(value):\n    """Convert a value.\n\n    Parameters\n    ----------\n    value : int\n        .. custom:\n            Nested directive body.\n    """\n',
            7,
        ),
    ],
)
def test_reports_inside_rest_and_numpy_entry_bodies(convention: DocstringConvention, source: str, expected_line: int) -> None:
    assert_pdf418_lines(source, ((expected_line,),), settings=CheckSettings(select=("PDF418",), docstring_convention=convention))


def test_ignores_malformed_examples_inside_protected_content() -> None:
    source = 'def function():\n    """Summary.\n\n    .. note::\n        .. versionchanged: protected directive body\n\n    Example::\n\n        .. note:\n            Literal example.\n\n    ~~~text\n    .. deprecated:\n    ~~~\n    """\n'

    assert_pdf418_lines(source, ())


def test_ignores_malformed_examples_inside_remaining_opaque_structures() -> None:
    source = 'def function():\n    """Summary.\n\n    >>> render()\n    .. versionadded: doctest content\n\n    | Value |\n    | ----- |\n    | .. versionchanged: table content |\n\n    - Item\n      .. deprecated: list content\n\n    > Quote\n    > .. versionadded: quoted content\n    """\n'

    assert_pdf418_lines(source, ())


def test_concatenated_docstring_falls_back_to_the_complete_expression() -> None:
    source = 'def function():\n    (\n        """Summary.\\n\\n"""\n        """.. versionadded: 1.0"""\n    )\n'

    assert_pdf418_lines(source, ((3, 4),))


def test_checks_attached_attribute_docstrings() -> None:
    source = 'value = 1\n"""Value.\n\n.. versionadded: 1.0\n"""\n'

    assert_pdf418_lines(source, ((4,),))


def test_directive_parsing_disabled_removes_protection_and_rule_selection() -> None:
    settings = CheckSettings(select=("PDF418",), docstring_parse_directives=False)
    source = 'def function():\n    """.. note:\n        Body.\n    """\n'
    selected = rules_selection.select_rules(settings)

    assert "PDF418" not in tuple(rule.rule.code.tag for rule in selected.rules)
    assert_pdf418_lines(source, (), settings=settings)


def test_broad_pdf_selection_enables_rule_when_directive_parsing_is_enabled() -> None:
    settings = CheckSettings(select=("PDF",))
    selected = rules_selection.select_rules(settings)

    assert "PDF418" in tuple(rule.rule.code.tag for rule in selected.rules)


def test_docstring_expression_suppression_hides_finding() -> None:
    source = 'def function():\n    """.. versionadded: 1.0"""  # noqa: PDF418\n'

    assert_pdf418_lines(source, ())


def test_preceding_local_suppression_hides_finding() -> None:
    source = 'def function():\n    # pydocfmt: ignore[PDF418]\n    """.. versionadded: 1.0"""\n'

    assert_pdf418_lines(source, ())
