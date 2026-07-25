# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, LineEnding
from pydocformatter.rules.definitions.PDF.PDF004_docstring_suspicious_unicode import PDF004DocstringSuspiciousUnicode
from pydocformatter.rules.definitions.PDF.PDF101_docstring_reflow import PDF101DocstringReflow


format_pdf004 = pdf_helpers.formatter_for("PDF004")
pytestmark = pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")


@pytest.mark.parametrize(("source_spelling", "replacement"), [("\u00a0", " "), ("\\u00a0", " "), ("\\N{NO-BREAK SPACE}", " "), ("\\240", " ")])
def test_fixes_literal_and_escaped_no_break_space_indentation(source_spelling: str, replacement: str) -> None:
    source = f'def function():\n    """Summary.\\n{source_spelling}Indented."""\n'

    result = format_pdf004(source)

    assert result.new_source == f'def function():\n    """Summary.\\n{replacement}Indented."""\n'
    assert result.fixed_findings[PDF004DocstringSuspiciousUnicode.meta] == 1
    assert result.unfixed_findings == ()


@pytest.mark.parametrize(
    ("body", "expected"), [("\\u00a0Summary.", " Summary."), (" \\u2007Summary.", "  Summary."), ("\\t\\u202fSummary.", "\\t Summary."), ("Summary.\\n \\t\\u00a0Body.", "Summary.\\n \\t Body.")]
)
def test_fixes_nonbreaking_spaces_anywhere_in_a_logical_indentation_prefix(body: str, expected: str) -> None:
    source = f'def function():\n    """{body}"""\n'

    result = format_pdf004(source)

    assert result.new_source == f'def function():\n    """{expected}"""\n'
    assert result.fixed_findings[PDF004DocstringSuspiciousUnicode.meta] == 1


def test_raw_ascii_escape_notation_is_not_mistaken_for_evaluated_unicode() -> None:
    source = 'def function():\n    r"""Literal \\u202e and \\u00a0 notation."""\n'

    result = format_pdf004(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_maps_and_fixes_supported_concatenated_leaves() -> None:
    source = 'def function():\n    ("Summary.\\n"  # keep\n     "\\u00a0Indented.")\n'

    result = format_pdf004(source)

    assert result.new_source == 'def function():\n    ("Summary.\\n"  # keep\n     " Indented.")\n'
    assert result.fixed_findings[PDF004DocstringSuspiciousUnicode.meta] == 1


def test_keeps_mapped_code_points_fixable_when_another_code_point_is_unmapped() -> None:
    source = 'def function():\n    ("Bad\\z\\u202e.\\n" "\\u00a0Indented.")\n'

    result = format_pdf004(source)

    assert result.new_source == 'def function():\n    ("Bad\\z\\u202e.\\n" " Indented.")\n'
    assert result.fixed_findings[PDF004DocstringSuspiciousUnicode.meta] == 1
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert result.unfixed_findings[0].message.endswith("U+202E RIGHT-TO-LEFT OVERRIDE")
    assert not result.unfixed_findings[0].fixable


def test_one_unmapped_occurrence_makes_every_occurrence_of_that_code_point_diagnostic_only() -> None:
    source = 'def function():\n    ("Bad\\z\\n\\u00a0first." "\\n\\u00a0Second.")\n'

    result = format_pdf004(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert result.unfixed_findings[0].message.endswith("U+00A0 NO-BREAK SPACE")
    assert not result.unfixed_findings[0].fixable


def test_unmapped_diagnostics_are_ordered_by_first_occurrence() -> None:
    source = 'def function():\n    ("\\u202e\\u200b\\u202e\\z")\n'

    result = format_pdf004(source, fix=False)

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE",
        "Docstring contains suspicious Unicode character U+200B ZERO WIDTH SPACE",
    )


def test_groups_repeated_fixable_characters_by_code_point_and_physical_line() -> None:
    source = 'def function():\n    """Summary.\\n\\u00a0\\u00a0First.\n\u2007Second.\n\u2007\u2007Third."""\n'

    checked = format_pdf004(source, fix=False)
    fixed = format_pdf004(source)

    assert tuple((finding.line_numbers, finding.message) for finding in checked.unfixed_findings) == (
        ((2,), "Docstring contains suspicious Unicode character U+00A0 NO-BREAK SPACE"),
        ((3,), "Docstring contains suspicious Unicode character U+2007 FIGURE SPACE"),
        ((4,), "Docstring contains suspicious Unicode character U+2007 FIGURE SPACE"),
    )
    assert fixed.new_source == 'def function():\n    """Summary.\\n  First.\n Second.\n  Third."""\n'
    assert fixed.fixed_findings[PDF004DocstringSuspiciousUnicode.meta] == 3


@pytest.mark.parametrize("convention", tuple(DocstringConvention))
def test_detection_is_independent_of_docstring_convention(convention: DocstringConvention) -> None:
    source = 'def function():\n    """Summary.\\n\\u00a0Indented."""\n'
    settings = CheckSettings(select=("PDF004",), docstring_convention=convention)

    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\\n Indented."""\n'
    assert result.fixed_findings[PDF004DocstringSuspiciousUnicode.meta] == 1


def test_preserves_crlf_while_fixing_literal_and_escaped_occurrences() -> None:
    source = 'def function():\r\n    """Summary.\r\n\u00a0First.\r\n\\u202fSecond."""\r\n'
    settings = CheckSettings(select=("PDF004",), line_ending=LineEnding.CR_LF)

    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def function():\r\n    """Summary.\r\n First.\r\n Second."""\r\n'
    assert result.fixed_findings[PDF004DocstringSuspiciousUnicode.meta] == 2


def test_reports_diagnostic_only_characters_by_code_point_and_physical_line() -> None:
    source = 'def function():\n    """A\\u202eB\\u202e.\n    C\\u200bD.\n    E\\u202eF."""\n'

    result = format_pdf004(source, fix=False)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (3,), (4,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE",
        "Docstring contains suspicious Unicode character U+200B ZERO WIDTH SPACE",
        "Docstring contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE",
    )
    assert all(not finding.fixable for finding in result.unfixed_findings)


@pytest.mark.parametrize("char", ["\u00a0", "\u2007", "\u202f"])
def test_accepts_nonbreaking_spaces_inside_prose(char: str) -> None:
    source = f'def function():\n    """Keep{char}together."""\n'

    result = format_pdf004(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert result.unfixed_findings == ()


def test_checks_attached_attribute_docstrings() -> None:
    source = 'value = 1\n"""Attribute\\u202edocumentation."""\n'

    result = format_pdf004(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert result.unfixed_findings[0].message.endswith("U+202E RIGHT-TO-LEFT OVERRIDE")


def test_rule_is_selected_broadly_and_is_sometimes_fixable() -> None:
    default_selection = rules_selection.select_rules(CheckSettings())
    category_selection = rules_selection.select_rules(CheckSettings(select=("PDF",)))

    assert PDF004DocstringSuspiciousUnicode.meta in tuple(rule.rule for rule in default_selection.rules)
    selected = next(rule for rule in category_selection.rules if rule.rule == PDF004DocstringSuspiciousUnicode.meta)
    assert selected.fixable


def test_unfixable_selection_reports_fixable_occurrences_without_editing() -> None:
    source = 'def function():\n    """Summary.\\n\\u00a0Indented."""\n'
    settings = CheckSettings(select=("PDF004",), unfixable=("PDF004",))

    result = format_pdf004(source, settings=settings)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple((finding.line_numbers, finding.fixable) for finding in result.unfixed_findings) == (((2,), False),)


@pytest.mark.parametrize("source", ['def function():\n    """Summary\\u202e."""  # noqa: PDF004\n', 'def function():\n    # pydocfmt: ignore[PDF004]\n    """\\u00a0Summary."""\n'])
def test_docstring_suppressions_hide_diagnostic_and_fixable_occurrences(source: str) -> None:
    result = format_pdf004(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf101_does_not_consume_diagnostic_only_characters() -> None:
    source = 'def function():\n    """Keep  abc\\u202edef unchanged."""\n'
    settings = CheckSettings(select=("PDF004", "PDF101"))

    result = format_pdf004(source, settings=settings)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF004DocstringSuspiciousUnicode.meta, PDF101DocstringReflow.meta)


@pytest.mark.parametrize("char", ["\v", "\f", "\x1c", "\x1d", "\x1e", "\x1f", "\x85", "\u2028", "\u2029"])
def test_pdf101_does_not_trim_diagnostic_whitespace_before_pdf004_reports_it(char: str) -> None:
    source = f'def function():\n    """Bad  words.{char}"""\n'
    settings = CheckSettings(select=("PDF004", "PDF101"))

    result = format_pdf004(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert PDF004DocstringSuspiciousUnicode.meta in tuple(finding.rule for finding in result.unfixed_findings)


def test_pdf101_preserves_interior_nonbreaking_spaces_while_reflowing() -> None:
    source = 'def function():\n    """Normalize  but keep two\u00a0words together."""\n'
    settings = CheckSettings(select=("PDF004", "PDF101"))

    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def function():\n    """Normalize but keep two\u00a0words together."""\n'
    assert result.fixed_findings[PDF101DocstringReflow.meta] == 1
    assert result.unfixed_findings == ()


def test_pdf004_and_pdf100_apply_overlapping_indentation_fixes_convergently() -> None:
    source = 'def function():\n    """Summary.\n\u00a0  Body.\n    """\n'
    settings = CheckSettings(select=("PDF004", "PDF100"))

    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\n    Body.\n    """\n'
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PDF004": 1, "PDF100": 1}
    assert result.new_source is not None
    assert not format_pdf004(result.new_source, settings=settings).modified


def test_pdf004_fix_unblocks_pdf101_reflow_in_the_same_formatting_run() -> None:
    source = 'def function():\n    """Summary.\n\u00a0Body  words."""\n'
    settings = CheckSettings(select=("PDF004", "PDF101"))

    result = format_pdf004(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary. Body words."""\n'
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PDF004": 1, "PDF101": 1}
    assert result.new_source is not None
    assert not format_pdf004(result.new_source, settings=settings).modified
