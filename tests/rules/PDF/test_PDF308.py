import pydocformatter.rules_selection as rules_selection
import tests.rule_helpers as rule_helpers
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, LineEnding
from pydocformatter.rules.definitions.PDF.PDF308_entry_description_trailing_period import PDF308EntryDescriptionTrailingPeriod

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


def test_reports_but_does_not_fix_non_period_punctuation() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: timeout in seconds?\n        retries: retry count;\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (6,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring entry description should end with a period",
        "Docstring entry description should end with a period",
    )


def test_reports_but_does_not_fix_escaped_unicode_ellipsis() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: waiting\\u2026\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5, 6),)
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


def test_reports_escaped_source_mapping_without_fixing_when_escape_precedes_target() -> None:
    source = 'def connect(timeout):\n    """Connect \\u2603.\n\n    Args:\n        timeout: timeout in seconds\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5, 6),)
    assert not result.unfixed_findings[0].fixable


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


def test_reports_unsafe_source_mapping_without_fixing() -> None:
    source = 'def connect(timeout):\n    """Connect.\\n\\n    Args:\\n        timeout: timeout in seconds"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert not result.unfixed_findings[0].fixable


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
