import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.parameter_documentation as parameter_documentation
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF501_extraneous_parameter_documentation import PDF501ExtraneousParameterDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF501 selected."""
    resolved_settings = CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf501_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF501 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF501ExtraneousParameterDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_google_documented_parameter_absent_from_signature() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Args:\n        first: First.\n        second: Second.\n    """\n'

    assert_pdf501_lines(source, ((6,),))


def test_does_not_scan_typed_dict_classes_without_unpacked_keyword_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_typed_dict_keys_by_name(module: object) -> dict[str, frozenset[str]]:
        raise AssertionError("TypedDict keys should not be collected without unpacked keyword parameters")

    monkeypatch.setattr(parameter_documentation, "typed_dict_keys_by_name", fail_typed_dict_keys_by_name)
    source = 'def function(first):\n    """Summary.\n\n    Args:\n        first: First.\n        second: Second.\n    """\n'

    assert_pdf501_lines(source, ((6,),))


def test_reports_google_parameter_alias_sections() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Keyword Args:\n        first: First.\n\n    Other Arguments:\n        second: Stale parameter.\n    """\n'

    assert_pdf501_lines(source, ((8,),))


def test_reports_singular_google_parameter_alias_sections() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Arg:\n        first: First.\n\n    Keyword Argument:\n        second: Stale parameter.\n    """\n'

    assert_pdf501_lines(source, ((8,),))


def test_parameter_name_matching_is_case_sensitive_and_exact() -> None:
    source = 'def function(first, options):\n    """Summary.\n\n    Args:\n        First: Wrong case.\n        options.value: Attribute, not parameter.\n    """\n'

    assert_pdf501_lines(source, ((5,), (6,)))


def test_reports_each_repeated_extraneous_documented_parameter() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Args:\n        second: Second.\n        second: More second.\n    """\n'
    result = format_source(source)

    assert_pdf501_lines(source, ((5,), (6,)))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring documents parameter 'second' that is not in the function signature",
        "Docstring documents parameter 'second' that is not in the function signature",
    )


def test_reports_numpy_comma_separated_documented_parameter_absent_from_signature() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Parameters\n    ----------\n    first, second : int\n        Values.\n    """\n'

    assert_pdf501_lines(source, ((6,),), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.NUMPY))


def test_reports_numpy_parameter_alias_sections() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Other Parameters\n    ----------------\n    first : int\n        First.\n\n    Receives\n    --------\n    second : int\n        Stale parameter.\n    """\n'

    assert_pdf501_lines(source, ((11,),), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.NUMPY))


def test_reports_singular_numpy_parameter_alias_sections() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Parameter\n    ---------\n    first : int\n        First.\n\n    Other Parameter\n    ---------------\n    second : int\n        Stale parameter.\n\n    Receive\n    -------\n    third : int\n        Stale parameter.\n    """\n'

    assert_pdf501_lines(source, ((11,), (16,)), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.NUMPY))


def test_reports_rest_documented_parameter_absent_from_signature() -> None:
    source = 'def function(first):\n    """Summary.\n\n    :param second: Second.\n    """\n'

    assert_pdf501_lines(source, ((4,),), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))


def test_typed_rest_parameter_field_satisfies_signature_parameter() -> None:
    source = 'def function(first):\n    """Summary.\n\n    :param int first: First.\n    """\n'

    assert_pdf501_lines(source, (), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))


def test_reports_normalized_typed_rest_parameter_absent_from_signature() -> None:
    source = 'def function(first):\n    """Summary.\n\n    :param int second: Second.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))

    assert_pdf501_lines(source, ((4,),), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring documents parameter 'second' that is not in the function signature",)


def test_reports_rest_keyword_documented_parameter_absent_from_signature() -> None:
    source = 'def function(first):\n    """Summary.\n\n    :keyword second: Second.\n    """\n'

    assert_pdf501_lines(source, ((4,),), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))


def test_rest_starred_parameter_fields_match_varargs_and_report_absent_kwargs() -> None:
    source = 'def function(*args):\n    """Summary.\n\n    :param tuple[str, ...] *args: Args.\n    :kwarg **kwargs: Kwargs.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))

    assert_pdf501_lines(source, ((5,),), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring documents parameter '**kwargs' that is not in the function signature",)


def test_rest_type_only_field_reports_absent_parameter() -> None:
    source = 'def function():\n    """Summary.\n\n    :type value: int\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))

    assert_pdf501_lines(source, ((4,),), settings=CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.REST))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring documents parameter 'value' that is not in the function signature",)


def test_none_and_pep257_conventions_do_not_parse_rest_parameter_documentation() -> None:
    source = 'def function(first):\n    """Summary.\n\n    :param second: Second.\n    """\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf501_lines(source, (), settings=CheckSettings(select=("PDF501",), docstring_convention=convention))


def test_rest_fields_do_not_contribute_to_google_parameter_documentation() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Args:\n        first: First.\n\n    :param second: Second.\n    """\n'

    assert_pdf501_lines(source, ())


def test_protected_content_inside_parameter_section_is_not_parameter_documentation() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Args:\n        first: First.\n\n        ```text\n        second: Example text, not a parameter entry.\n        ```\n    """\n'

    assert_pdf501_lines(source, ())


def test_varargs_and_kwargs_match_starless_documented_names() -> None:
    source = 'def function(*args, **kwargs):\n    """Summary.\n\n    Args:\n        *args: Args.\n        **kwargs: Kwargs.\n    """\n'

    assert_pdf501_lines(source, ())


def test_positional_only_keyword_only_varargs_and_unpack_parameters_count_as_present() -> None:
    source = 'def function(first, /, second, *args, third, **kwargs: Unpack[Options]):\n    """Summary.\n\n    Args:\n        first: First.\n        second: Second.\n        args: Args.\n        third: Third.\n        kwargs: Kwargs.\n    """\n'

    assert_pdf501_lines(source, ())


def test_stringized_unpack_parameter_counts_as_present() -> None:
    source = 'def function(**kwargs: "typing.Unpack[Options]"):\n    """Summary.\n\n    Args:\n        kwargs: Kwargs.\n    """\n'

    assert_pdf501_lines(source, ())


def test_unpack_parameter_allows_documented_unpacked_keyword_names() -> None:
    source = 'def first(**kwargs: Unpack[Options]):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        verbose: Verbose.\n    """\n\n\ndef second(**kwargs: typing.Unpack[Options]):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        verbose: Verbose.\n    """\n\n\ndef third(**kwargs: typing_extensions.Unpack[Options]):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        verbose: Verbose.\n    """\n'

    assert_pdf501_lines(source, ())


def test_stringized_unpack_parameter_allows_documented_unpacked_keyword_names() -> None:
    source = 'def first(**kwargs: "Unpack[Options]"):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        verbose: Verbose.\n    """\n\n\ndef second(**kwargs: "typing.Unpack[Options]"):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        verbose: Verbose.\n    """\n\n\ndef third(**kwargs: "typing_extensions.Unpack[Options]"):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        verbose: Verbose.\n    """\n'

    assert_pdf501_lines(source, ())


def test_local_typed_dict_unpack_allows_typed_dict_keys_and_reports_other_names() -> None:
    source = 'class Options(TypedDict):\n    timeout: int\n    verbose: bool\n\n\ndef function(first, **kwargs: Unpack[Options]):\n    """Summary.\n\n    Args:\n        frist: Typo.\n        timeout: Timeout.\n        verbose: Verbose.\n        kwargs: Kwargs.\n    """\n'

    assert_pdf501_lines(source, ((10,),))


def test_scans_typed_dict_classes_once_when_unpacked_keyword_parameter_needs_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def counting_typed_dict_keys_by_name(module: object) -> dict[str, frozenset[str]]:
        nonlocal calls
        calls += 1
        return {"Options": frozenset({"timeout"})}

    monkeypatch.setattr(parameter_documentation, "typed_dict_keys_by_name", counting_typed_dict_keys_by_name)
    source = 'class Options(TypedDict):\n    timeout: int\n\n\ndef first(**kwargs: Unpack[Options]):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        tmieout: Typo.\n    """\n\n\ndef second(**kwargs: Unpack[Options]):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        tiemout: Typo.\n    """\n'

    assert_pdf501_lines(source, ((10,), (19,)))
    assert calls == 1


def test_qualified_local_typed_dict_unpack_allows_typed_dict_keys_and_reports_other_names() -> None:
    source = 'class Options(typing.TypedDict):\n    timeout: int\n\n\ndef function(**kwargs: "typing.Unpack[Options]"):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        tmieout: Typo.\n    """\n'

    assert_pdf501_lines(source, ((10,),))


def test_unresolved_unpack_parameter_keeps_conservative_suppression() -> None:
    source = 'def function(first, **kwargs: Unpack[Options]):\n    """Summary.\n\n    Args:\n        frist: Typo.\n        timeout: Timeout.\n    """\n'

    assert_pdf501_lines(source, ())


def test_regular_kwargs_do_not_allow_unrelated_documented_names() -> None:
    source = 'def function(**kwargs):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        kwargs: Kwargs.\n    """\n'

    assert_pdf501_lines(source, ((5,),))


def test_unpacked_varargs_do_not_allow_unrelated_documented_names() -> None:
    source = 'def function(*args: Unpack[Values]):\n    """Summary.\n\n    Args:\n        timeout: Timeout.\n        args: Args.\n    """\n'

    assert_pdf501_lines(source, ((5,),))


def test_reports_each_absent_name_from_numpy_multi_name_entry_on_same_line() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Parameters\n    ----------\n    first, second, third : int\n        Values.\n    """\n'
    settings = CheckSettings(select=("PDF501",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert_pdf501_lines(source, ((6,), (6,)), settings=settings)
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring documents parameter 'second' that is not in the function signature",
        "Docstring documents parameter 'third' that is not in the function signature",
    )


def test_implicit_class_receiver_counts_as_present() -> None:
    source = 'class Container:\n    def method(self, first):\n        """Summary.\n\n        Args:\n            self: Receiver.\n            first: First.\n        """\n'

    assert_pdf501_lines(source, ())


def test_classmethod_receiver_counts_as_present() -> None:
    source = 'class Container:\n    @classmethod\n    def create(cls, first):\n        """Summary.\n\n        Args:\n            cls: Receiver.\n            first: First.\n        """\n'

    assert_pdf501_lines(source, ())


def test_staticmethod_self_name_counts_as_ordinary_signature_parameter() -> None:
    source = 'class Container:\n    @staticmethod\n    def static(self, first):\n        """Summary.\n\n        Args:\n            self: Ordinary parameter.\n            first: First.\n        """\n'

    assert_pdf501_lines(source, ())


def test_staticmethod_alias_self_name_counts_as_ordinary_signature_parameter() -> None:
    source = 'class Container:\n    @builtins.staticmethod\n    def static(self, first):\n        """Summary.\n\n        Args:\n            self: Ordinary parameter.\n            first: First.\n        """\n'

    assert_pdf501_lines(source, ())


def test_ignores_non_parameter_sections() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Returns:\n        second: Not a parameter.\n    """\n'

    assert_pdf501_lines(source, ())


def test_reports_documented_parameter_for_function_without_signature_parameters() -> None:
    source = 'def function():\n    """Summary.\n\n    Args:\n        value: Value.\n    """\n'

    assert_pdf501_lines(source, ((5,),))


def test_reports_private_function_documented_parameter_independent_of_pdf500_visibility_settings() -> None:
    source = 'def _function():\n    """Summary.\n\n    Args:\n        value: Value.\n    """\n'

    assert_pdf501_lines(source, ((5,),))


def test_reports_async_function_documented_parameter_absent_from_signature() -> None:
    source = 'async def function(first):\n    """Summary.\n\n    Args:\n        second: Second.\n    """\n'

    assert_pdf501_lines(source, ((5,),))


def test_reports_concatenated_docstring_with_physical_line_fallback() -> None:
    source = 'def function(first):\n    ("Summary.\\n\\n"\n     "Args:\\n"\n     "    second: Second.")\n'

    assert_pdf501_lines(source, ((2, 3, 4),))
