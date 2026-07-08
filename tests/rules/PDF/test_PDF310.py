# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, LineEnding
from pydocformatter.rules.definitions.PDF.PDF308_entry_description_trailing_period import PDF308EntryDescriptionTrailingPeriod
from pydocformatter.rules.definitions.PDF.PDF309_entry_description_terminal_punctuation import PDF309EntryDescriptionTerminalPunctuation
from pydocformatter.rules.definitions.PDF.PDF310_entry_description_first_word_capitalization import PDF310EntryDescriptionFirstWordCapitalization
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF310")
format_source = pdf_helpers.formatter_for("PDF310")


def test_capitalizes_google_entry_description_first_words() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n\n    Returns:\n        bool: whether connection succeeded.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: Timeout in seconds.\n\n    Returns:\n        bool: Whether connection succeeded.\n    """\n'
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 2
    assert not result.unfixed_findings


def test_capitalizes_numpy_and_rest_entry_descriptions() -> None:
    numpy_source = 'def connect(timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    timeout : int\n        timeout in seconds.\n    """\n'
    rest_source = 'def connect(timeout):\n    """Connect.\n\n    :param timeout: timeout in seconds.\n    """\n'

    numpy = format_source(numpy_source, settings=CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.NUMPY))
    rest = format_source(rest_source, settings=CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.REST))

    assert numpy.new_source == 'def connect(timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    timeout : int\n        Timeout in seconds.\n    """\n'
    assert rest.new_source == 'def connect(timeout):\n    """Connect.\n\n    :param timeout: Timeout in seconds.\n    """\n'
    assert numpy.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert rest.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1


def test_capitalizes_first_continuation_description_line_only() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout:\n            timeout in\n            seconds.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout:\n            Timeout in\n            seconds.\n    """\n'
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert not result.unfixed_findings


def test_capitalizes_inline_description_before_nested_protected_blocks() -> None:
    source = 'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: choose one.\n            - fast\n            - safe\n        timeout: Timeout in seconds.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: Choose one.\n            - fast\n            - safe\n        timeout: Timeout in seconds.\n    """\n'
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert not result.unfixed_findings


def test_capitalizes_method_and_attribute_entry_descriptions() -> None:
    source = 'class Client:\n    """Client.\n\n    Methods:\n        connect: connect to the service.\n\n    Attributes:\n        timeout: timeout in seconds.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'class Client:\n    """Client.\n\n    Methods:\n        connect: Connect to the service.\n\n    Attributes:\n        timeout: Timeout in seconds.\n    """\n'
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 2


@pytest.mark.parametrize(("description", "expected"), [("don't retry.", "Don't retry."), ("retry? when needed.", "Retry? when needed."), ("retry... when needed.", "Retry... when needed.")])
def test_capitalizes_safe_words_with_internal_apostrophes_or_terminal_punctuation(description: str, expected: str) -> None:
    source = f'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: {description}\n    """\n'
    result = format_source(source)

    assert result.new_source == f'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: {expected}\n    """\n'
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert not result.unfixed_findings


@pytest.mark.parametrize(
    "description", ["Already capitalized.", "URL value.", "123 value.", "return_value.", '"return" value.', "return-value.", "iOS device.", "iPhone device.", "eBay item.", "macOS device."]
)
def test_skips_words_without_safe_ascii_capitalization(description: str) -> None:
    source = f'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: {description}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_raw_docstring_prefix_when_fixing_backslash_heavy_description() -> None:
    source = 'def connect(pattern):\n    r"""Connect.\n\n    Args:\n        pattern: match \\d+ values.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(pattern):\n    r"""Connect.\n\n    Args:\n        pattern: Match \\d+ values.\n    """\n'
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert not result.unfixed_findings


def test_reports_escaped_source_mapping_without_fixing_when_escape_precedes_target() -> None:
    source = 'def connect(timeout):\n    """Connect \\u2603.\n\n    Args:\n        timeout: timeout in seconds.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5, 6),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring entry description first word 'timeout' should be capitalized",)
    assert not result.unfixed_findings[0].fixable


def test_reports_unsafe_source_mapping_without_fixing() -> None:
    source = 'def connect(timeout):\n    """Connect.\\n\\n    Args:\\n        timeout: timeout in seconds."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring entry description first word 'timeout' should be capitalized",)
    assert not result.unfixed_findings[0].fixable


def test_reports_escaped_first_word_without_fixing_otherwise_simple_docstring() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: ti\\x6deout in seconds.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring entry description first word 'timeout' should be capitalized",)
    assert not result.unfixed_findings[0].fixable


def test_unfixable_selection_reports_fixable_instance_without_changing_source() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.GOOGLE, unfixable=("PDF310",)))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_combined_entry_description_style_rules_converge() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    settings = CheckSettings(select=("PDF308", "PDF309", "PDF310"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: Timeout in seconds.\n    """\n'
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta]
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert not result.unfixed_findings


@pytest.mark.parametrize(
    "source",
    [
        'def connect(timeout):\r\n    """Connect.\r\n\n    Args:\n        timeout: timeout in seconds\n    """\n',
        'def connect(timeout):\n    """Connect.\n\r\n    Args:\r\n        timeout: timeout in seconds\r\n    """\r\n',
    ],
)
def test_combined_entry_description_style_rules_do_not_fix_mixed_physical_line_endings(source: str) -> None:
    settings = CheckSettings(select=("PDF308", "PDF309", "PDF310"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.modified
    assert not result.errors
    assert not result.fixed_findings
    assert [finding.rule.code.tag for finding in result.unfixed_findings] == ["PDF308", "PDF309", "PDF310"]
    assert [finding.fixable for finding in result.unfixed_findings] == [False, False, False]


def test_preserves_crlf_line_endings() -> None:
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds.\r\n    """\r\n'
    result = format_source(source, settings=CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: Timeout in seconds.\r\n    """\r\n'
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1


def test_lf_source_with_crlf_setting_uses_correct_entry_offsets() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n    """\n'
    settings = CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: Timeout in seconds.\n    """\n'
    assert not result.errors
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_crlf_source_with_lf_setting_uses_correct_entry_offsets() -> None:
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds.\r\n    """\r\n'
    settings = CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: Timeout in seconds.\r\n    """\r\n'
    assert not result.errors
    assert result.fixed_findings[PDF310EntryDescriptionFirstWordCapitalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_skips_rest_type_and_generic_fields() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    :type timeout: int\n    :meta private: generated\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_broad_selection_has_no_convention_effects_like_pdf304() -> None:
    for convention in DocstringConvention:
        selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))

        assert "PDF310" in {rule.rule.code.tag for rule in selection.rules}


def test_none_convention_selection_does_not_parse_convention_entries() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF310",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_direct_rule_and_check_only_findings_agree() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF310EntryDescriptionFirstWordCapitalization, context)
    fixed = rule_helpers.rule_fix_result(PDF310EntryDescriptionFirstWordCapitalization, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((5,),)
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((5,),)
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((5,),)
