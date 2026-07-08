# Standard library imports
import pathlib

# Third-party imports
import pytest

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF510_missing_public_module_attribute_documentation import PDF510MissingPublicModuleAttributeDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None, path: str = "example.py") -> formatter.FormatterResult:
    """Format source with PDF510 selected."""
    resolved_settings = CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, path, settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf510_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None, path: str = "example.py") -> formatter.FormatterResult:
    """Assert PDF510 line findings for source."""
    result = format_source(source, settings=settings, path=path)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF510MissingPublicModuleAttributeDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected
    return result


@pytest.mark.parametrize("convention", tuple(DocstringConvention))
def test_every_convention_ignores_broad_selection_but_exact_selection_still_applies(convention: DocstringConvention) -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF5",), docstring_convention=convention))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF510" not in active_codes

    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\nretries: int\n'
    exact = format_source(source, settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in exact.unfixed_findings) == ((8,),)


def test_reports_google_module_attribute_missing_from_attributes_section() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\nretries: int\n'

    result = assert_pdf510_lines(source, ((8,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Public module attribute 'retries' is missing docstring documentation",)


def test_empty_attributes_section_still_triggers_module_missing_check() -> None:
    source = '"""Client defaults.\n\nAttributes:\n"""\n\ntimeout: float\n'

    assert_pdf510_lines(source, ((6,),))


def test_attached_attribute_docstring_counts_as_documentation_and_triggers_missing_check() -> None:
    source = 'timeout: float\n"""Request timeout."""\n\nretries: int\n'

    assert_pdf510_lines(source, ((4,),))


def test_inert_conventions_do_not_report_attached_module_attribute_docstrings() -> None:
    source = 'timeout: float\n"""Request timeout."""\n\nretries: int\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf510_lines(source, (), settings=CheckSettings(select=("PDF510",), docstring_convention=convention))


def test_attached_attribute_docstring_directive_does_not_suppress_unrelated_missing_module_attribute() -> None:
    source = 'timeout: float\n"""Request timeout."""  # pydocfmt: ignore[PDF510]\n\nretries: int\n'

    assert_pdf510_lines(source.replace("  # pydocfmt: ignore[PDF510]", ""), ((4,),))
    assert_pdf510_lines(source, ((4,),))


def test_accepts_numpy_and_rest_module_attribute_documentation() -> None:
    numpy = '"""Client defaults.\n\nAttributes\n----------\ntimeout : float\n    Request timeout.\n"""\n\ntimeout: float\nretries: int\n'
    rest = '"""Client defaults.\n\n:ivar timeout: Request timeout.\n"""\n\ntimeout: float\nretries: int\n'

    assert_pdf510_lines(numpy, ((10,),), settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf510_lines(rest, ((7,),), settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.REST))


def test_rest_cvar_and_vartype_document_module_attributes() -> None:
    source = '"""Client defaults.\n\n:cvar timeout: Request timeout.\n:vartype retries: int\n"""\n\ntimeout: float\nretries: int\nstale: str\n'

    assert_pdf510_lines(source, ((9,),), settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.REST))


def test_numpy_comma_separated_attribute_entry_documents_multiple_module_attributes() -> None:
    source = '"""Client defaults.\n\nAttributes\n----------\nprimary, fallback : str\n    Request endpoints.\n"""\n\nprimary = fallback = "https://example.com"\nretries: int\n'

    assert_pdf510_lines(source, ((10,),), settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.NUMPY))


def test_private_module_attributes_are_not_required() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\n_token: str\n'

    assert_pdf510_lines(source, ())


def test_private_module_path_is_skipped_by_public_only_but_checked_when_disabled() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\nretries: int\n'

    assert_pdf510_lines(source, (), path="_internal.py")
    assert_pdf510_lines(source, (), path="_package/public.py")
    assert_pdf510_lines(source, (), path="package/_internal/public.py")
    assert_pdf510_lines(source, ((8,),), path="package/__init__.py")
    assert_pdf510_lines(source, ((8,),), path="package/public.py")
    assert_pdf510_lines(source, (), path="_package/__init__.py")
    assert_pdf510_lines(
        source, ((8,),), settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation_public_only=False), path="_internal.py"
    )


def test_existing_module_path_privacy_ignores_non_package_underscore_parents(tmp_path: pathlib.Path) -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\nretries: int\n'
    workspace = tmp_path / "_workspace"
    package = workspace / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    public_module = package / "public.py"
    public_module.write_text(source, encoding="utf-8")
    standalone_module = workspace / "public.py"
    standalone_module.write_text(source, encoding="utf-8")

    assert_pdf510_lines(source, ((8,),), path=str(public_module))
    assert_pdf510_lines(source, ((8,),), path=str(standalone_module))


def test_existing_module_path_privacy_uses_package_suffix(tmp_path: pathlib.Path) -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n"""\n\ntimeout: float\nretries: int\n'
    workspace = tmp_path / "_workspace"
    private_package = workspace / "_package"
    private_package.mkdir(parents=True)
    (private_package / "__init__.py").write_text(source, encoding="utf-8")
    private_module = private_package / "public.py"
    private_module.write_text(source, encoding="utf-8")
    package = workspace / "package"
    private_child = package / "_internal"
    private_child.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (private_child / "__init__.py").write_text("", encoding="utf-8")
    private_child_module = private_child / "public.py"
    private_child_module.write_text(source, encoding="utf-8")
    private_standalone = workspace / "_internal.py"
    private_standalone.write_text(source, encoding="utf-8")

    assert_pdf510_lines(source, (), path=str(private_package / "__init__.py"))
    assert_pdf510_lines(source, (), path=str(private_module))
    assert_pdf510_lines(source, (), path=str(private_child_module))
    assert_pdf510_lines(source, (), path=str(private_standalone))


def test_all_docstrings_policy_reports_summary_only_public_module_docstring() -> None:
    source = '"""Client defaults."""\n\ntimeout: float\n'

    assert_pdf510_lines(source, (), settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.GOOGLE))
    assert_pdf510_lines(
        source, ((3,),), settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
    )


def test_inert_conventions_do_not_report_broad_module_missing_policies() -> None:
    summary = '"""Client defaults."""\n\ntimeout: float\n'
    body = '"""Client defaults.\n\nUsed by the transport layer.\n"""\n\ntimeout: float\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf510_lines(summary, (), settings=CheckSettings(select=("PDF510",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS))
        assert_pdf510_lines(body, (), settings=CheckSettings(select=("PDF510",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS))


def test_multi_target_assignment_reports_only_undocumented_targets_on_shared_line() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n    primary (str): Primary endpoint.\n"""\n\nprimary = fallback = "https://example.com"\n'

    assert_pdf510_lines(source, ((8,),))


def test_tuple_unpacked_assignment_reports_only_undocumented_module_targets() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    timeout (float): Request timeout.\n    primary (str): Primary endpoint.\n"""\n\nprimary, (fallback, *aliases) = endpoints\n'

    assert_pdf510_lines(source, ((8,), (8,)))


def test_multiline_tuple_unpacked_assignment_reports_target_lines() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    primary (str): Primary endpoint.\n"""\n\n(\n    primary,\n    (\n        fallback,\n        *aliases,\n    ),\n) = endpoints\n'

    assert_pdf510_lines(source, ((10,), (11,)))


def test_tuple_unpacked_attribute_docstring_documents_supported_module_targets() -> None:
    source = 'primary, fallback = endpoints\n"""Request endpoints."""\n\nretries: int\n'

    assert_pdf510_lines(source, ((4,),))


def test_non_summary_policy_reports_body_only_module_docstring() -> None:
    source = '"""Client defaults.\n\nUsed by the transport layer.\n"""\n\ntimeout: float\n'

    assert_pdf510_lines(
        source,
        ((6,),),
        settings=CheckSettings(select=("PDF510",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_class_attribute_documentation_does_not_trigger_module_missing_check() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n\nmodule_timeout: float\n'

    assert_pdf510_lines(source, ())
