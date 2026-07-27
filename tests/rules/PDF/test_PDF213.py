"""Tests for PDF213 placeholder-docstring."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PDF.PDF202_empty_docstring import PDF202EmptyDocstring
from pydocformatter.rules.definitions.PDF.PDF212_missing_summary import PDF212MissingSummary
from pydocformatter.rules.definitions.PDF.PDF213_placeholder_docstring import PDF213PlaceholderDocstring
from pydocformatter.rules.definitions.PDF.PDF300_summary_trailing_period import PDF300SummaryTrailingPeriod
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF213")
format_source = pdf_helpers.formatter_for("PDF213")


def assert_pdf213(source: str, expected_lines: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF213 findings for source."""
    pdf_helpers.assert_unfixed_lines(format_source, source, expected_lines, meta=PDF213PlaceholderDocstring.meta, settings=settings)


def test_metadata() -> None:
    """Expose the stable diagnostic-only rule identity."""
    assert PDF213PlaceholderDocstring.meta.name == "placeholder-docstring"
    assert PDF213PlaceholderDocstring.meta.message == "Docstring is a placeholder"
    assert PDF213PlaceholderDocstring.meta.stable_since == "1.1.0"


@pytest.mark.parametrize("marker", ["TODO", "TBD", "FIXME", "pass", "XXX", "HACK", "NotImplemented", "..."])
def test_reports_every_default_marker_case_insensitively(marker: str) -> None:
    """Recognize each default marker as the complete docstring value."""
    variants = {marker, marker.lower(), marker.upper()} if marker != "..." else {marker}
    source = "".join(f'def function_{index}():\n    """{variant}"""\n\n\n' for index, variant in enumerate(sorted(variants)))

    assert_pdf213(source, tuple((line,) for line in range(2, len(source.splitlines()) + 1, 4)))


@pytest.mark.parametrize("suffix", ["", ".", ":", ";", "!", "?", "...", "?!", ":;.!?"])
def test_reports_word_markers_with_narrow_terminal_punctuation(suffix: str) -> None:
    """Accept only the configured narrow punctuation suffix language."""
    assert_pdf213(f'def function():\n    """TODO{suffix}"""\n', ((2,),))


def test_reports_surrounding_whitespace_multiline_and_concatenated_values() -> None:
    """Match evaluated whole-docstring values independently of literal layout."""
    source = 'def multiline():\n    """\n    TODO.\n    """\n\n\ndef concatenated():\n    ("Not"\n     "Implemented!")\n'

    assert_pdf213(source, ((2, 3, 4), (8, 9)))


def test_reports_marker_produced_by_escape_evaluation() -> None:
    """Match the evaluated whole-docstring value rather than its source spelling."""
    source = 'def function():\n    """TO\\x44O;"""\n'

    assert_pdf213(source, ((2,),))


def test_reports_primary_and_supported_attached_attribute_docstrings() -> None:
    """Inspect every collected primary and attached docstring owner."""
    source = (
        '"""TODO"""\n\n'
        'module_value = 1\n"""TBD"""\n\n'
        'class Client:\n    """FIXME"""\n\n'
        '    class_value = 1\n    """pass"""\n\n'
        '    def method(self):\n        """XXX"""\n\n'
        '    def __init__(self):\n        self.instance_value = 1\n        """HACK"""\n'
    )

    assert_pdf213(source, ((1,), (4,), (7,), (10,), (13,), (17,)))


@pytest.mark.parametrize(
    "value", ["", "   ", "TODO,", "TODO: Describe retry behavior.", "A TODO", "TODO item", "TODO FIXME", "TODO\nFIXME", "NotImplementedError", "not implemented", "....", "\N{KELVIN SIGN}ACK"]
)
def test_rejects_non_placeholder_boundaries(value: str) -> None:
    """Reject empty values, additional prose, and values outside the exact marker language."""
    source = f"def function():\n    {value!r}\n"

    assert_pdf213(source, ())


def test_custom_markers_replace_defaults_and_empty_list_only_suppresses_findings() -> None:
    """Use the resolved marker inventory without changing rule selection."""
    source = 'def custom():\n    """WIP!"""\n\n\ndef default():\n    """TODO"""\n'
    custom = CheckSettings(select=("PDF213",), docstring_placeholder_markers=("Wip",))
    empty = dataclasses.replace(custom, docstring_placeholder_markers=())

    assert_pdf213(source, ((2,),), settings=custom)
    assert_pdf213(source, (), settings=empty)
    active_codes = {selected.rule.code.tag for selected in rules_selection.select_rules(empty).rules}
    assert "PDF213" in active_codes


def test_custom_ascii_marker_language_supports_digits_hyphens_and_underscores() -> None:
    """Match every configured label shape accepted by setting validation."""
    source = 'def first():\n    """wip-2?!"""\n\n\ndef second():\n    """PHASE_1:"""\n\n\ndef default():\n    """TODO"""\n'
    settings = CheckSettings(select=("PDF213",), docstring_placeholder_markers=("WIP-2", "phase_1"))

    assert_pdf213(source, ((2,), (6,)), settings=settings)


@pytest.mark.parametrize("selector", ["PDF213", "PDF2", "PDF", "ALL"])
def test_normal_selectors_include_rule(selector: str) -> None:
    """Keep PDF213 broadly selected."""
    active_codes = {selected.rule.code.tag for selected in rules_selection.select_rules(CheckSettings(select=(selector,))).rules}

    assert "PDF213" in active_codes


def test_whole_docstring_suppression_covers_multiline_and_concatenated_literals() -> None:
    """Allow suppression from any physical line occupied by the docstring expression."""
    multiline = 'def function():\n    """\n    TODO\n    """  # noqa: PDF213\n'
    concatenated = 'def function():\n    ("TO"\n     "DO")  # noqa: PDF213\n'

    assert not format_source(multiline).unfixed_findings
    assert not format_source(concatenated).unfixed_findings


def test_empty_missing_summary_and_placeholder_rules_remain_independent() -> None:
    """Keep empty, missing-summary, and placeholder ownership distinct."""
    source = 'def empty():\n    """"""\n\n\ndef structure_only():\n    """- item"""\n\n\ndef placeholder():\n    """TODO"""\n'
    settings = CheckSettings(select=("PDF202", "PDF212", "PDF213"))
    result = format_source(source, settings=settings)

    assert tuple((finding.rule, finding.line_numbers) for finding in result.unfixed_findings) == (
        (PDF202EmptyDocstring.meta, (2,)),
        (PDF212MissingSummary.meta, (6,)),
        (PDF213PlaceholderDocstring.meta, (10,)),
    )


def test_punctuation_fix_can_reveal_comma_ended_placeholder_on_the_next_pass() -> None:
    """Report a placeholder after a selected punctuation rule safely canonicalizes its ending."""
    source = 'def function():\n    """TODO,"""\n'
    settings = CheckSettings(select=("PDF213", "PDF300"))
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function():\n    """TODO."""\n'
    assert result.fixed_findings[PDF300SummaryTrailingPeriod.meta] == 1
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF213PlaceholderDocstring.meta,)


def test_direct_rule_and_formatter_findings_agree_without_fixes() -> None:
    """Return the same diagnostic through the direct hook and formatter."""
    source = 'def function():\n    """TODO"""\n'
    _, context = contexts(source)
    direct = rule_helpers.rule_findings(PDF213PlaceholderDocstring, context)
    formatted = format_source(source)

    assert tuple(finding.line_numbers for finding in direct) == ((2,),)
    assert tuple(finding.line_numbers for finding in formatted.unfixed_findings) == ((2,),)
    assert not rule_helpers.rule_fix_result(PDF213PlaceholderDocstring, context).fixed_findings
