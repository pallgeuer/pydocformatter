# Third-party imports
import libcst as cst
import pytest
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF302_non_imperative_summary import PDF302NonImperativeSummary
from pydocformatter.rules.definitions.PDF.PDF304_summary_first_word_capitalization import PDF304SummaryFirstWordCapitalization
from pydocformatter.source_path import SourcePathContext
from tests import rule_helpers


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        source_path=SourcePathContext.for_path("example.py"),
        settings=CheckSettings(select=("PDF304",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
        line_bounds=None,
    )
    return category, RuleContext(
        path=category.path,
        source_path=category.source_path,
        settings=category.settings,
        module=category.module,
        metadata_wrapper=category.metadata_wrapper,
        positions=category.positions,
        line_ending=category.line_ending,
        source=category.source,
        source_lines=category.source_lines,
        line_bounds=category.line_bounds,
        category_data=PDF.prepare(category),
    )


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF304",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('def function():\n    """return value."""\n', 'def function():\n    """Return value."""\n'),
        ('def function():\n    """return?"""\n', 'def function():\n    """Return?"""\n'),
        ('def function():\n    """return..."""\n', 'def function():\n    """Return..."""\n'),
        ('def function():\n    """don\'t return."""\n', 'def function():\n    """Don\'t return."""\n'),
        ('def function():\n    r"""return \\d+ values."""\n', 'def function():\n    r"""Return \\d+ values."""\n'),
        ('def function():\n    """  return value."""\n', 'def function():\n    """  Return value."""\n'),
        ('def function(): """return value."""\n', 'def function(): """Return value."""\n'),
        ("def function():\n    '''return value.'''\n", "def function():\n    '''Return value.'''\n"),
    ],
)
def test_capitalizes_safe_function_summary_first_words(source: str, expected: str) -> None:
    result = format_source(source)

    assert result.new_source == expected
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 1
    assert not result.unfixed_findings
    assert result.new_source is not None
    assert not format_source(result.new_source).modified


def test_preserves_crlf_line_endings() -> None:
    source = 'def function():\r\n    """return value."""\r\n'
    result = format_source(source, settings=CheckSettings(select=("PDF304",), line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def function():\r\n    """Return value."""\r\n'
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 1


def test_capitalizes_safe_summary_first_words_for_all_docstring_owners() -> None:
    source = '"""module summary."""\n\nclass Example:\n    """class summary."""\n\n    class_value = 1\n    """class value."""\n\n    def __init__(self):\n        """initialize example."""\n        self.instance_value = 1\n        """instance value."""\n\nmodule_value = 1\n"""module value."""\n'
    result = format_source(source)

    assert (
        result.new_source
        == '"""Module summary."""\n\nclass Example:\n    """Class summary."""\n\n    class_value = 1\n    """Class value."""\n\n    def __init__(self):\n        """Initialize example."""\n        self.instance_value = 1\n        """Instance value."""\n\nmodule_value = 1\n"""Module value."""\n'
    )
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 6
    assert not result.unfixed_findings


def test_capitalizes_first_summary_word_in_multiline_docstrings() -> None:
    source = '"""module summary.\n\nDetails follow.\n"""\n\n\ndef function():\n    """function summary.\n\n    Details follow.\n    """\n'
    result = format_source(source)

    assert result.new_source == '"""Module summary.\n\nDetails follow.\n"""\n\n\ndef function():\n    """Function summary.\n\n    Details follow.\n    """\n'
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 2


@pytest.mark.parametrize("summary", ["Return value.", "RETURN value.", "\u00e9clair value.", "return_value.", "123 value.", "iOS device.", "iPhone device.", "eBay item.", "macOS device."])
def test_skips_words_without_safe_ascii_capitalization(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


@pytest.mark.parametrize("summary", ["return: value.", "return, value.", "return; value.", '"return" value.', "(return) value.", "return-value."])
def test_skips_punctuated_or_quoted_words_that_are_not_plain_ascii_prose(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_but_does_not_fix_unsafe_source_mappings() -> None:
    source = 'def concatenated():\n    ("return "\n     "value.")\n\n\ndef escaped():\n    """return value\\ncontinued."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring summary first word 'return' should be capitalized",
        "Docstring summary first word 'return' should be capitalized",
    )
    assert [finding.fixable for finding in result.unfixed_findings] == [False, False]


def test_applies_to_all_docstring_summaries_and_respects_summary_parsing() -> None:
    source = '"""module summary."""\n\nclass Example:\n    """class summary."""\n\n\ndef field():\n    """:return: field summary"""\n\n\ndef function():\n    """function summary."""\n'
    result = format_source(source)

    assert (
        result.new_source == '"""Module summary."""\n\nclass Example:\n    """Class summary."""\n\n\ndef field():\n    """:return: field summary"""\n\n\ndef function():\n    """Function summary."""\n'
    )
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 3


def test_underlined_title_style_summary_obeys_heading_parsing_setting() -> None:
    source = 'def function():\n    """title\n    =====\n    """\n'
    protected = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF304",), docstring_parse_headings=False))

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert disabled.new_source == 'def function():\n    """Title\n    =====\n    """\n'
    assert disabled.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 1


def test_leading_blank_and_adornment_lines_are_not_capitalization_targets() -> None:
    source = 'def function():\n    """\n    ====\n    return value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF304",), docstring_parse_headings=False))

    assert result.new_source == 'def function():\n    """\n    ====\n    Return value.\n    """\n'
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 1


def test_mixed_safe_and_unsafe_instances_are_reported_independently() -> None:
    source = 'def safe():\n    """return value."""\n\n\ndef unsafe():\n    """return value\\ncontinued."""\n'
    result = format_source(source)

    assert result.new_source == 'def safe():\n    """Return value."""\n\n\ndef unsafe():\n    """return value\\ncontinued."""\n'
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 1
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_pdf304_fix_can_leave_pdf302_finding_for_capitalized_non_imperative_summary() -> None:
    source = 'def function():\n    """returns value."""\n'
    settings = CheckSettings(select=("PDF302", "PDF304"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Returns value."""\n'
    assert result.fixed_findings[PDF304SummaryFirstWordCapitalization.meta] == 1
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF302NonImperativeSummary.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


def test_unfixable_selection_reports_fixable_instance_without_changing_source() -> None:
    source = 'def function():\n    """return value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF304",), unfixable=("PDF304",)))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """return value."""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF304SummaryFirstWordCapitalization, context)
    fixed = rule_helpers.rule_fix_result(PDF304SummaryFirstWordCapitalization, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert tuple(finding.message for finding in findings) == ("Docstring summary first word 'return' should be capitalized",)
    assert [finding.fixable for finding in findings] == [True]
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2,),)
    assert fixed.module.code == 'def function():\n    """Return value."""\n'
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)


def test_suspicious_unicode_blocks_first_word_capitalization() -> None:
    source = 'def function():\n    """return\u202e value."""\n'

    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
