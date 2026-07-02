import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF500_missing_parameter_documentation import PDF500MissingParameterDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF500 selected."""
    resolved_settings = CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf500_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF500 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF500MissingParameterDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_google_parameter_missing_from_existing_parameter_section() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Args:\n        first: First.\n    """\n'

    assert_pdf500_lines(source, ((1,),))


def test_reports_all_parameters_for_empty_parameter_section() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Args:\n    """\n'
    result = format_source(source)

    assert_pdf500_lines(source, ((1,), (1,)))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Function parameter 'first' is missing docstring documentation",
        "Function parameter 'second' is missing docstring documentation",
    )


def test_reports_signature_parameter_when_section_only_documents_extraneous_parameter() -> None:
    source = 'def function(first):\n    """Summary.\n\n    Args:\n        second: Stale parameter.\n    """\n'

    assert_pdf500_lines(source, ((1,),))


def test_reports_missing_parameters_from_google_parameter_section_aliases() -> None:
    source = 'def function(first, second, third):\n    """Summary.\n\n    Keyword Args:\n        first: First.\n\n    Other Arguments:\n        second: Second.\n    """\n'

    assert_pdf500_lines(source, ((1,),))


def test_singular_google_parameter_section_aliases_document_parameters() -> None:
    source = 'def function(first, second, third, fourth):\n    """Summary.\n\n    Arg:\n        first: First.\n\n    Keyword Argument:\n        second: Second.\n\n    Other Arg:\n        third: Third.\n    """\n'

    assert_pdf500_lines(source, ((1,),))


def test_default_policy_ignores_docstring_without_parameter_documentation() -> None:
    source = 'def function(first):\n    """Summary.\n\n    More detail.\n    """\n'

    assert_pdf500_lines(source, ())


def test_ignores_attribute_docstrings_with_parameter_sections() -> None:
    source = 'module_value = 1\n"""Summary.\n\nArgs:\n    missing: Missing.\n"""\n\nclass Example:\n    class_value = 1\n    """Summary.\n\n    Args:\n        missing: Missing.\n    """\n\n    def __init__(self):\n        self.instance_value = 1\n        """Summary.\n\n        Args:\n            missing: Missing.\n        """\n'

    assert_pdf500_lines(source, ())


def test_reports_numpy_parameter_missing_from_existing_parameter_section() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Parameters\n    ----------\n    first : int\n        First.\n    """\n'

    assert_pdf500_lines(source, ((1,),), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.NUMPY))


def test_numpy_convention_does_not_ignore_broad_pdf500_selection() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Parameters\n    ----------\n    first : int\n        First.\n    """\n'

    assert_pdf500_lines(source, ((1,),), settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.NUMPY))


def test_accepts_numpy_comma_separated_documented_parameters() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Parameters\n    ----------\n    first, second : int\n        Values.\n    """\n'

    assert_pdf500_lines(source, (), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.NUMPY))


def test_reports_missing_parameters_from_numpy_parameter_section_aliases() -> None:
    source = 'def function(first, second, third):\n    """Summary.\n\n    Other Parameters\n    ----------------\n    first : int\n        First.\n\n    Receives\n    --------\n    second : int\n        Second.\n    """\n'

    assert_pdf500_lines(source, ((1,),), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.NUMPY))


def test_singular_numpy_parameter_section_aliases_document_parameters() -> None:
    source = 'def function(first, second, third, fourth):\n    """Summary.\n\n    Parameter\n    ---------\n    first : int\n        First.\n\n    Other Parameter\n    ---------------\n    second : int\n        Second.\n\n    Receive\n    -------\n    third : int\n        Third.\n    """\n'

    assert_pdf500_lines(source, ((1,),), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.NUMPY))


def test_reports_parameter_missing_from_rest_fields() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    :param first: First.\n    """\n'

    assert_pdf500_lines(source, ((1,),), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.REST))


def test_typed_rest_parameter_field_satisfies_signature_parameter() -> None:
    source = 'def function(first):\n    """Summary.\n\n    :param int first: First.\n    """\n'

    assert_pdf500_lines(source, (), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.REST))


def test_type_only_rest_field_satisfies_signature_parameter() -> None:
    source = 'def function(first):\n    """Summary.\n\n    :type first: int\n    """\n'

    assert_pdf500_lines(source, (), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.REST))


def test_reports_missing_parameter_from_rest_keyword_field() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    :keyword first: First.\n    """\n'

    assert_pdf500_lines(source, ((1,),), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.REST))


def test_rest_starred_parameter_fields_satisfy_varargs_and_kwargs() -> None:
    source = 'def function(*args, **kwargs):\n    """Summary.\n\n    :param tuple[str, ...] *args: Args.\n    :kwarg **kwargs: Kwargs.\n    """\n'

    assert_pdf500_lines(source, (), settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.REST))


def test_none_and_pep257_conventions_keep_missing_parameter_documentation_inert() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    :param first: First.\n    """\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf500_lines(
            source,
            (),
            settings=CheckSettings(select=("PDF500",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS),
        )


def test_rest_fields_do_not_satisfy_google_parameter_documentation() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Args:\n        first: First.\n\n    :param second: Second.\n    """\n'

    assert_pdf500_lines(source, ((1,),))


def test_protected_content_inside_parameter_section_does_not_document_parameter() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Args:\n        first: First.\n\n        ```text\n        second: Example text, not a parameter entry.\n        ```\n    """\n'

    assert_pdf500_lines(source, ((1,),))


def test_parameter_name_matching_is_case_sensitive_and_exact() -> None:
    source = 'def function(first, options):\n    """Summary.\n\n    Args:\n        First: Wrong case.\n        options.value: Attribute, not parameter.\n    """\n'

    assert_pdf500_lines(source, ((1,), (1,)))


def test_non_summary_policy_reports_public_docstrings_with_more_than_summary() -> None:
    source = 'def function(first):\n    """Summary.\n\n    More detail.\n    """\n'

    assert_pdf500_lines(
        source,
        ((1,),),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_non_summary_policy_does_not_report_summary_only_or_empty_docstrings_without_sections() -> None:
    summary_only = 'def summary_only(first):\n    """Summary."""\n'
    empty = 'def empty(first):\n    """"""\n'
    settings = CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS)

    assert_pdf500_lines(summary_only, (), settings=settings)
    assert_pdf500_lines(empty, (), settings=settings)


def test_all_docstrings_policy_reports_summary_only_and_empty_public_docstrings() -> None:
    source = 'def summary_only(first):\n    """Summary."""\n\n\ndef empty(second):\n    """"""\n'

    assert_pdf500_lines(
        source,
        ((1,), (5,)),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS),
    )


def test_all_docstrings_policy_public_only_ignores_private_summary_only_docstrings_without_sections() -> None:
    source = 'def _summary_only(first):\n    """Summary."""\n\n\ndef __repr__(self, second):\n    """Summary."""\n'

    assert_pdf500_lines(
        source,
        (),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS),
    )


def test_public_only_broad_policy_does_not_report_private_docstrings_without_sections() -> None:
    source = 'def _function(first):\n    """Summary.\n\n    More detail.\n    """\n'

    assert_pdf500_lines(
        source,
        (),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_public_only_broad_policy_does_not_report_private_methods_in_public_classes_without_sections() -> None:
    source = 'class Container:\n    def _method(self, first):\n        """Summary.\n\n        More detail.\n        """\n'

    assert_pdf500_lines(
        source,
        (),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_public_only_broad_policy_still_reports_private_docstrings_with_sections() -> None:
    source = 'def _function(first, second):\n    """Summary.\n\n    Args:\n        first: First.\n    """\n'

    assert_pdf500_lines(
        source,
        ((1,),),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS),
    )


def test_broad_policy_can_include_private_docstrings_without_sections() -> None:
    source = 'def _function(first):\n    """Summary.\n\n    More detail.\n    """\n\n\ndef __repr__(second):\n    """Summary."""\n'

    assert_pdf500_lines(
        source,
        ((1,), (8,)),
        settings=CheckSettings(
            select=("PDF500",),
            docstring_convention=DocstringConvention.GOOGLE,
            docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS,
            docstring_missing_documentation_public_only=False,
        ),
    )


def test_nested_inside_private_definition_is_private_for_broad_policy() -> None:
    source = 'class _Container:\n    def method(self, first):\n        """Summary.\n\n        More detail.\n        """\n\n\ndef _outer():\n    def inner(second):\n        """Summary.\n\n        More detail.\n        """\n'

    assert_pdf500_lines(
        source,
        (),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_public_dunder_exceptions_are_checked_by_broad_policy() -> None:
    source = 'class Callable:\n    def __new__(cls, name):\n        """Summary.\n\n        More detail.\n        """\n\n    def __init__(self, first):\n        """Summary.\n\n        More detail.\n        """\n\n    def __call__(self, second):\n        """Summary.\n\n        More detail.\n        """\n'

    assert_pdf500_lines(
        source,
        ((2,), (8,), (14,)),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_protocol_dunders_are_private_for_broad_policy() -> None:
    source = 'class Comparable:\n    def __exit__(self, exc_type, exc, traceback):\n        """Summary.\n\n        More detail.\n        """\n\n    def __repr__(self):\n        """Summary.\n\n        More detail.\n        """\n\n    def __add__(self, other):\n        """Summary.\n\n        More detail.\n        """\n'

    assert_pdf500_lines(
        source,
        (),
        settings=CheckSettings(select=("PDF500",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_implicit_class_receiver_is_not_required_but_staticmethod_parameter_is_required() -> None:
    source = 'class Container:\n    def method(self, first):\n        """Summary.\n\n        Args:\n        """\n\n    @staticmethod\n    def static(self, second):\n        """Summary.\n\n        Args:\n            second: Second.\n        """\n'

    assert_pdf500_lines(source, ((2,), (9,)))


def test_classmethod_receiver_is_not_required() -> None:
    source = 'class Container:\n    @classmethod\n    def create(cls, first):\n        """Summary.\n\n        Args:\n        """\n'

    assert_pdf500_lines(source, ((3,),))


def test_varargs_and_kwargs_match_starless_documented_names() -> None:
    source = 'def function(*args, **kwargs):\n    """Summary.\n\n    Args:\n        args: Args.\n        kwargs: Kwargs.\n    """\n'

    assert_pdf500_lines(source, ())


def test_unpack_parameters_are_not_required() -> None:
    source = 'def first(**kwargs: Unpack[Options]):\n    """Summary.\n\n    Args:\n    """\n\n\ndef second(**kwargs: typing.Unpack[Options]):\n    """Summary.\n\n    Args:\n    """\n\n\ndef third(**kwargs: typing_extensions.Unpack[Options]):\n    """Summary.\n\n    Args:\n    """\n'

    assert_pdf500_lines(source, ())


def test_stringized_unpack_parameters_are_not_required() -> None:
    source = 'def first(**kwargs: "Unpack[Options]"):\n    """Summary.\n\n    Args:\n    """\n\n\ndef second(**kwargs: "typing.Unpack[Options]"):\n    """Summary.\n\n    Args:\n    """\n\n\ndef third(**kwargs: "typing_extensions.Unpack[Options]"):\n    """Summary.\n\n    Args:\n    """\n'

    assert_pdf500_lines(source, ())


def test_reports_positional_only_keyword_only_and_vararg_parameter_lines() -> None:
    source = 'def function(\n    first,\n    /,\n    second,\n    *args,\n    third,\n    **kwargs,\n):\n    """Summary.\n\n    Args:\n        first: First.\n        args: Args.\n        kwargs: Kwargs.\n    """\n'
    result = format_source(source)

    assert_pdf500_lines(source, ((4,), (6,)))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Function parameter 'second' is missing docstring documentation",
        "Function parameter 'third' is missing docstring documentation",
    )


def test_reports_async_function_parameters() -> None:
    source = 'async def function(first, second):\n    """Summary.\n\n    Args:\n        first: First.\n    """\n'

    assert_pdf500_lines(source, ((1,),))


def test_reports_multiline_signature_parameter_lines() -> None:
    source = 'def function(\n    first,\n    second,\n):\n    """Summary.\n\n    Args:\n        first: First.\n    """\n'

    assert_pdf500_lines(source, ((3,),))
