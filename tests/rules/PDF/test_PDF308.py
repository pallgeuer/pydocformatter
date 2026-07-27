# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, LineEnding
from pydocformatter.rules.definitions.PDF.PDF308_entry_description_trailing_period import PDF308EntryDescriptionTrailingPeriod
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF308")
format_source = pdf_helpers.formatter_for("PDF308")


def test_inserts_period_for_google_entry_descriptions() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n\n    Returns:\n        bool: whether connection succeeded\n\n    Raises:\n        TimeoutError: if the connection times out\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n\n    Returns:\n        bool: whether connection succeeded.\n\n    Raises:\n        TimeoutError: if the connection times out.\n    """\n'
    )
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 3
    assert not result.unfixed_findings


def test_inserts_period_for_numpy_and_rest_entry_descriptions() -> None:
    numpy_source = 'def connect(timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    timeout : int\n        timeout in seconds\n    """\n'
    rest_source = 'def connect(timeout):\n    """Connect.\n\n    :param timeout: timeout in seconds\n    """\n'

    numpy = format_source(numpy_source, settings=CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.NUMPY))
    rest = format_source(rest_source, settings=CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.REST))

    assert numpy.new_source == 'def connect(timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    timeout : int\n        timeout in seconds.\n    """\n'
    assert rest.new_source == 'def connect(timeout):\n    """Connect.\n\n    :param timeout: timeout in seconds.\n    """\n'
    assert numpy.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert rest.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1


def test_replaces_comma_and_semicolon_but_not_expressive_or_structural_punctuation() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds?\n        retries: retry count;\n        delay: delay seconds,\n        mode: selected mode:\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("retry count;", "retry count.").replace("delay seconds,", "delay seconds.")
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 2
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (8,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring entry description should end with a period", "Docstring entry description should end with a period")


def test_reports_comma_before_nested_structure_without_fixing() -> None:
    source = 'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: choose one,\n            - fast\n            - safe\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize(
    "structured_content",
    [
        "        - fast",
        "        ```text\n        fast\n        ```",
        "        >>> choose()",
        "        .. note::\n            fast",
        "        Example::\n            fast",
        "        | Mode | Value |\n        | --- | --- |\n        | fast | 1 |",
        "        Modes\n        -----",
        "        > fast",
    ],
)
def test_reports_rest_comma_before_protected_field_content_without_fixing(structured_content: str) -> None:
    """Preserve a comma that introduces protected content owned by a reStructuredText field."""
    source = f'def connect(mode):\n    """Connect.\n\n    :param mode: choose one,\n{structured_content}\n    """\n'
    settings = CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)
    assert not result.unfixed_findings[0].fixable


def test_rest_prose_after_protected_content_remains_the_terminal_description_target() -> None:
    """Fix the final prose comma when protected content occurs earlier in the field body."""
    source = 'def connect(mode):\n    """Connect.\n\n    :param mode: choose one,\n        - fast\n        Final prose,\n    """\n'
    settings = CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace("Final prose,", "Final prose.")
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_reports_escaped_comma_as_nonfixable() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\\x2c\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert not result.unfixed_findings[0].fixable


def test_replacement_preserves_raw_prefix_and_earlier_escape_spelling() -> None:
    """Replace a literal terminal character without reconstructing other source spelling."""
    source = 'def connect(pattern):\n    r"""Connect.\n\n    Args:\n        pattern: match \\d+ values;\n    """\n\n\ndef escaped(timeout):\n    """Connect \\u2603.\n\n    Args:\n        timeout: wait \\u2603,\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("values;", "values.").replace("\\u2603,\n", "\\u2603.\n")
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 2
    assert not result.unfixed_findings


def test_replacement_preserves_trailing_spaces_and_crlf_line_endings() -> None:
    """Replace punctuation before trailing spaces without changing physical line endings."""
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds;   \r\n    """\r\n'
    settings = CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds.   \r\n    """\r\n'
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_replacement_preserves_source_continuation_before_terminal_character() -> None:
    """Use the exact terminal source slice even when earlier value text spans physical lines."""
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: wait \\\n            forever;\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("forever;", "forever.")
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_reports_but_does_not_fix_escaped_unicode_ellipsis() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: waiting\\u2026\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert not result.unfixed_findings[0].fixable


def test_skips_entry_descriptions_ending_with_backslash() -> None:
    source = 'def connect(path):\n    """Connect.\n\n    Args:\n        path: base path \\\\\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_punctuates_final_continuation_description_line_only() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout:\n            timeout in\n            seconds\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout:\n            timeout in\n            seconds.\n    """\n'
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_punctuates_inline_description_before_nested_protected_blocks() -> None:
    source = 'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: choose one\n            - fast\n            - safe\n        timeout: timeout in seconds.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(mode):\n    """Connect.\n\n    Args:\n        mode: choose one.\n            - fast\n            - safe\n        timeout: timeout in seconds.\n    """\n'
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_local_suppression_before_docstring_suppresses_entry_description_fixes() -> None:
    source = 'def connect(timeout, retries):\n    # pydocfmt: ignore[PDF308]\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n        retries: retry count\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_crlf_line_endings() -> None:
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds\r\n    """\r\n'
    result = format_source(source, settings=CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds.\r\n    """\r\n'
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1


def test_lf_source_with_crlf_setting_uses_correct_entry_offsets() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    settings = CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds.\n    """\n'
    assert not result.errors
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_crlf_source_with_lf_setting_uses_correct_entry_offsets() -> None:
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds\r\n    """\r\n'
    settings = CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: timeout in seconds.\r\n    """\r\n'
    assert not result.errors
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_preserves_raw_docstring_prefix_when_fixing_backslash_heavy_description() -> None:
    source = 'def connect(pattern):\n    r"""Connect.\n\n    Args:\n        pattern: match \\d+ values\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def connect(pattern):\n    r"""Connect.\n\n    Args:\n        pattern: match \\d+ values.\n    """\n'
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_fixes_target_when_escape_precedes_it() -> None:
    source = 'def connect(timeout):\n    """Connect \\u2603.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("timeout in seconds\n", "timeout in seconds.\n")
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_unfixable_selection_reports_fixable_instance_without_changing_source() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.GOOGLE, unfixable=("PDF308",)))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_skips_empty_type_only_and_generic_rest_field_descriptions() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    :param timeout:\n    :type timeout: int\n    :meta private: generated\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_fixes_target_with_escaped_logical_newlines() -> None:
    source = 'def connect(timeout):\n    """Connect.\\n\\n    Args:\\n        timeout: timeout in seconds"""\n'
    result = format_source(source)

    assert result.new_source == source.replace('seconds"""', 'seconds."""')
    assert result.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1
    assert not result.unfixed_findings


def test_broad_selection_follows_pdf300_google_default() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    broad = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.GOOGLE))
    exact = format_source(source)

    assert "PDF308" not in {rule.rule.code.tag for rule in broad.rules}
    assert exact.fixed_findings[PDF308EntryDescriptionTrailingPeriod.meta] == 1


def test_exact_selection_under_pep257_does_not_parse_convention_entries() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF308",), docstring_convention=DocstringConvention.PEP257))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_direct_rule_and_check_only_findings_agree() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF308EntryDescriptionTrailingPeriod, context)
    fixed = rule_helpers.rule_fix_result(PDF308EntryDescriptionTrailingPeriod, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((5,),)
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((5,),)
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((5,),)
