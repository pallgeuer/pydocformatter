import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF513_duplicate_module_attribute_documentation import PDF513DuplicateModuleAttributeDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF513 selected."""
    resolved_settings = CheckSettings(select=("PDF513",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf513_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF513 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF513DuplicateModuleAttributeDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected
    return result


def test_reports_google_duplicate_module_attribute_documentation_on_attached_docstring() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\n'
    result = assert_pdf513_lines(source, ((8,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attached docstring for module attribute 'timeout' duplicates module docstring attribute documentation",)


def test_no_finding_when_only_one_module_attribute_documentation_style_is_present() -> None:
    attached_only = 'timeout: float\n"""Request timeout in seconds."""\n'
    owner_only = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\n'

    assert_pdf513_lines(attached_only, ())
    assert_pdf513_lines(owner_only, ())


def test_none_and_pep257_conventions_do_not_parse_module_attribute_entries() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf513_lines(source, (), settings=CheckSettings(select=("PDF513",), docstring_convention=convention))


def test_broad_pdf5_selection_includes_module_duplicate_rule_under_parsed_conventions() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\n'

    active = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.GOOGLE))
    inert = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.PEP257))

    assert tuple(finding.rule for finding in active.unfixed_findings) == (PDF513DuplicateModuleAttributeDocumentation.meta,)
    assert not inert.unfixed_findings


def test_reports_numpy_comma_separated_module_attribute_duplicates_by_name() -> None:
    source = '"""Client defaults.\n\nAttributes\n----------\nprimary, fallback : str\n    Request endpoints.\n"""\n\nprimary = fallback = "https://example.com"\n"""Request endpoint values."""\n'

    result = assert_pdf513_lines(source, ((10,), (10,)), settings=CheckSettings(select=("PDF513",), docstring_convention=DocstringConvention.NUMPY))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Attached docstring for module attribute 'primary' duplicates module docstring attribute documentation",
        "Attached docstring for module attribute 'fallback' duplicates module docstring attribute documentation",
    )


def test_multi_target_module_docstring_reports_only_targets_also_documented_by_module_docstring() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    primary (str): Primary endpoint.\n"""\n\nprimary = fallback = "https://example.com"\n"""Request endpoint values."""\n'

    assert_pdf513_lines(source, ((8,),))


def test_tuple_unpacked_module_attribute_docstring_duplicates_each_documented_target() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    primary (str): Primary endpoint.\n    aliases (tuple[str, ...]): Endpoint aliases.\n"""\n\nprimary, (fallback, *aliases) = endpoints\n"""Request endpoints."""\n'

    assert_pdf513_lines(source, ((9,), (9,)))


def test_reports_rest_module_attribute_duplicates() -> None:
    source = '"""Client defaults.\n\n:ivar timeout: Request timeout.\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\n'

    assert_pdf513_lines(source, ((7,),), settings=CheckSettings(select=("PDF513",), docstring_convention=DocstringConvention.REST))


def test_rest_cvar_and_vartype_module_attribute_duplicates() -> None:
    source = '"""Client defaults.\n\n:cvar timeout: Request timeout.\n:vartype retries: int\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\nretries: int\n"""Retry attempts."""\n'

    assert_pdf513_lines(source, ((8,), (10,)), settings=CheckSettings(select=("PDF513",), docstring_convention=DocstringConvention.REST))


def test_reports_each_attached_module_docstring_duplicate_for_same_owner_entry() -> None:
    source = (
        '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\n\ntimeout = 30.0\n"""Default timeout in seconds."""\n'
    )

    assert_pdf513_lines(source, ((8,), (11,)))


def test_repeated_module_attribute_entries_each_duplicate_attached_docstring() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n    timeout (float): Timeout in seconds.\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\n'

    assert_pdf513_lines(source, ((9,), (9,)))


def test_multiline_attached_module_docstring_targets_all_docstring_lines() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\n"""Request timeout.\n\nMeasured in seconds.\n"""\n'

    assert_pdf513_lines(source, ((8, 9, 10, 11),))


def test_attached_module_docstring_suppression_only_suppresses_that_duplicate() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n    retries (int): Retry count.\n"""\n\ntimeout: float\n"""Request timeout in seconds."""  # pydocfmt: ignore[PDF513]\n\nretries: int\n"""Retry attempts."""\n'

    assert_pdf513_lines(source, ((12,),))


def test_module_docstring_suppression_does_not_suppress_attached_docstring_duplicate() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.  # pydocfmt: ignore[PDF513]\n"""\n\ntimeout: float\n"""Request timeout in seconds."""\n'

    assert_pdf513_lines(source, ((8,),))


def test_private_module_path_and_private_attribute_duplicates_are_reported() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    _token (str): Internal token.\n"""\n\n_token: str\n"""Internal token."""\n'

    assert_pdf513_lines(source, ((8,),), settings=CheckSettings(select=("PDF513",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation_public_only=True))


def test_class_attached_docstring_does_not_duplicate_module_docstring() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\nclass Client:\n    timeout: float\n    """Request timeout in seconds."""\n'

    assert_pdf513_lines(source, ())


def test_function_local_attached_docstring_does_not_duplicate_module_docstring() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ndef configure():\n    timeout = 30.0\n    """Request timeout in seconds."""\n'

    assert_pdf513_lines(source, ())
