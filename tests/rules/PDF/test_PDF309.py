# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, LineEnding
from pydocformatter.rules.definitions.PDF.PDF309_entry_description_terminal_punctuation import PDF309EntryDescriptionTerminalPunctuation
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF309")
format_source = pdf_helpers.formatter_for("PDF309")


def test_inserts_period_for_missing_terminal_punctuation() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n        retries: retry count?\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n        retries: retry count?\n    """\n'
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings


def test_accepts_exclamation_and_unicode_ellipsis() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds!\n        retries: retry count\\u2026\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_replaces_comma_and_semicolon_but_not_colon() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds,\n        retries: retry count:\n        backoff: backoff seconds;\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("timeout in seconds,", "timeout in seconds.").replace("backoff seconds;", "backoff seconds.")
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 2
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize(
    "structured_content",
    [
        "            - red",
        "            ```text\n            red\n            ```",
        "            >>> choose()",
        "            .. note::\n                red",
        "            .. warning:\n                red",
        "            Example::\n\n                red",
        "            | Color | Value |\n            | --- | --- |\n            | red | 1 |",
        "            Colors\n            ------",
        "            > red",
    ],
)
def test_reports_comma_before_every_nested_structured_content_kind_without_fixing(structured_content: str) -> None:
    """Keep a comma that may introduce a protected entry body."""
    source = f'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: choose one,\n{structured_content}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize(
    "structured_content",
    [
        "        - red",
        "        ```text\n        red\n        ```",
        "        >>> choose()",
        "        .. note::\n            red",
        "        .. warning:\n            red",
        "        Example::\n            red",
        "        | Color | Value |\n        | --- | --- |\n        | red | 1 |",
        "        Colors\n        ------",
        "        > red",
    ],
)
def test_reports_rest_comma_before_every_protected_field_content_kind_without_fixing(structured_content: str) -> None:
    """Preserve a comma that introduces protected content owned by a reStructuredText field."""
    source = f'def connect(mode):\n    """Connect.\n\n    :param mode: choose one,\n{structured_content}\n    """\n'
    settings = CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)
    assert not result.unfixed_findings[0].fixable


def test_reports_escaped_semicolon_as_nonfixable() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\\x3b\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert not result.unfixed_findings[0].fixable


def test_replacement_preserves_raw_prefix_trailing_whitespace_and_crlf_line_endings() -> None:
    source = 'def connect(pattern):\r\n    r"""Connect.\r\n\r\n    Args:\r\n        pattern: match \\d+ values; \t\r\n    """\r\n'
    settings = CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(pattern):\r\n    r"""Connect.\r\n\r\n    Args:\r\n        pattern: match \\d+ values. \t\r\n    """\r\n'
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source, settings=settings).modified


def test_skips_entry_descriptions_ending_with_backslash() -> None:
    source = 'def connect(path):\n    """Connect.\n\n    Args:\n        path: base path \\\\\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_punctuates_final_description_line_before_unrelated_entry_after_protected_block() -> None:
    source = 'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: choose one\n            - fast\n            - safe\n        timeout: timeout in seconds?\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: choose one.\n            - fast\n            - safe\n        timeout: timeout in seconds?\n    """\n'
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings


def test_inserts_period_for_rest_and_skips_type_fields() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    :param timeout: timeout in seconds\n    :type timeout: int\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    :param timeout: timeout in seconds.\n    :type timeout: int\n    """\n'
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1


def test_exact_selection_under_numpy_restores_ignored_broad_default() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    timeout : int\n        timeout in seconds\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    timeout : int\n        timeout in seconds.\n    """\n'
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1


def test_fixes_description_containing_escape() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout \\u2603\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("\\u2603\n", "\\u2603.\n")
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings


def test_unfixable_selection_reports_fixable_instance_without_changing_source() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.GOOGLE, unfixable=("PDF309",)))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_preserves_crlf_line_endings() -> None:
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds\r\n    """\r\n'
    result = format_source(source, settings=CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds.\r\n    """\r\n'
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1


def test_lf_source_with_crlf_setting_uses_correct_entry_offsets() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    settings = CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n    """\n'
    assert not result.errors
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_crlf_source_with_lf_setting_uses_correct_entry_offsets() -> None:
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds\r\n    """\r\n'
    settings = CheckSettings(select=("PDF309",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds.\r\n    """\r\n'
    assert not result.errors
    assert result.fixed_findings[PDF309EntryDescriptionTerminalPunctuation.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_entry_description_punctuation_rules_are_incompatible() -> None:
    settings = CheckSettings(select=("PDF308", "PDF309"), docstring_convention=DocstringConvention.GOOGLE)
    selection = rules_selection.select_rules(settings)

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF308",)
    assert selection.errors == ("Selected rule PDF309 is incompatible with earlier selected rule PDF308; PDF309 has been disabled",)


def test_broad_selection_follows_pdf301_defaults() -> None:
    google = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.GOOGLE))
    numpy = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.NUMPY))
    pep257 = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.PEP257))
    rest = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.REST))

    assert "PDF309" in {rule.rule.code.tag for rule in google.rules}
    assert "PDF309" not in {rule.rule.code.tag for rule in numpy.rules}
    assert "PDF309" not in {rule.rule.code.tag for rule in pep257.rules}
    assert "PDF308" in {rule.rule.code.tag for rule in rest.rules}
    assert "PDF309" not in {rule.rule.code.tag for rule in rest.rules}


def test_direct_rule_and_check_only_findings_agree() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF309EntryDescriptionTerminalPunctuation, context)
    fixed = rule_helpers.rule_fix_result(PDF309EntryDescriptionTerminalPunctuation, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((5,),)
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((5,),)
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((5,),)
