# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF511_extraneous_module_attribute_documentation import PDF511ExtraneousModuleAttributeDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF511 selected."""
    resolved_settings = CheckSettings(select=("PDF511",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf511_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF511 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF511ExtraneousModuleAttributeDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_google_module_attribute_documentation_absent_from_module() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n    stale (object): Removed attribute.\n"""\n\ntimeout: float\n'
    result = format_source(source)

    assert_pdf511_lines(source, ((5,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Module docstring documents attribute 'stale' that is not present",)


def test_private_module_attributes_may_be_voluntarily_documented_when_present() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    _timeout (float): Internal timeout.\n"""\n\n_timeout: float\n'

    assert_pdf511_lines(source, ())


def test_class_attributes_do_not_satisfy_module_attribute_documentation() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\nclass Client:\n    timeout: float\n'

    assert_pdf511_lines(source, ((4,),))


def test_reports_numpy_and_rest_stale_module_attributes() -> None:
    numpy = '"""Client defaults.\n\nAttributes\n----------\nstale : str\n    Removed attribute.\n"""\n'
    rest = '"""Client defaults.\n\n:cvar stale: Removed attribute.\n:vartype other: str\n"""\n'

    assert_pdf511_lines(numpy, ((5,),), settings=CheckSettings(select=("PDF511",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf511_lines(rest, ((3,), (4,)), settings=CheckSettings(select=("PDF511",), docstring_convention=DocstringConvention.REST))


def test_numpy_comma_separated_attribute_entry_reports_only_stale_module_names() -> None:
    source = '"""Client defaults.\n\nAttributes\n----------\nprimary, stale : str\n    Request endpoints.\n"""\n\nprimary: str\n'

    assert_pdf511_lines(source, ((5,),), settings=CheckSettings(select=("PDF511",), docstring_convention=DocstringConvention.NUMPY))


def test_none_and_pep257_conventions_do_not_parse_attribute_sections() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    stale (object): Removed attribute.\n"""\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf511_lines(source, (), settings=CheckSettings(select=("PDF511",), docstring_convention=convention))


def test_multi_target_assignment_makes_each_target_present() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    primary (str): Primary endpoint.\n    fallback (str): Fallback endpoint.\n"""\n\nprimary = fallback = "https://example.com"\n'

    assert_pdf511_lines(source, ())


def test_tuple_unpacked_assignment_makes_each_target_present() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    primary (str): Primary endpoint.\n    fallback (str): Fallback endpoint.\n    aliases (tuple[str, ...]): Endpoint aliases.\n"""\n\nprimary, (fallback, *aliases) = endpoints\n'

    assert_pdf511_lines(source, ())


def test_unsupported_list_destructuring_assignment_does_not_make_attribute_present() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    primary (str): Primary endpoint.\n"""\n\n[primary, fallback] = endpoints\n'

    assert_pdf511_lines(source, ((4,),))
