from collections.abc import Mapping

import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.module_bindings as module_bindings
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.definition_helpers.static_names as static_names
import pydocformatter.rules_selection as rules_selection
import tests.rule_helpers as rule_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF302_non_imperative_summary import PDF302NonImperativeSummary


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF302",)) if settings is None else settings,
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
    resolved_settings = CheckSettings(select=("PDF302",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


@pytest.mark.parametrize("summary", ("Returns the value.", "Calculates the value.", "Does the work.", "Has the value.", "This returns the value."))
def test_reports_non_imperative_function_summaries(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (f"Docstring summary first word '{summary.split()[0]}' is not imperative",)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize("summary", ("returns the value.", "RETURNS the value.", "'returns' the value."))
def test_non_imperative_detection_is_case_insensitive_after_normalization(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


@pytest.mark.parametrize("summary", ("Return the value.", "Compute the value.", "Widget object."))
def test_accepts_imperative_or_unknown_function_summaries(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize("summary", ("Trys invalid form.", "Processs invalid form."))
def test_accepts_invalid_synthetic_third_person_forms(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_applies_only_to_functions_and_skips_tests_and_properties() -> None:
    source = '"""Returns module value."""\n\nclass Example:\n    """Returns class value."""\n\n    @property\n    def value(self):\n        """Returns property value."""\n\n    @functools.cached_property()\n    def cached(self):\n        """Returns cached value."""\n\n    def test_value(self):\n        """Returns test value."""\n\n    def runTest(self):\n        """Returns test value."""\n\n    def value(self):\n        """Returns value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((21,),)


def test_ignores_attribute_docstrings() -> None:
    source = 'module_value = 1\n"""Returns module value."""\n\nclass Example:\n    class_value = 1\n    """Returns class value."""\n\n    def __init__(self):\n        self.instance_value = 1\n        """Returns instance value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize(
    "decorator",
    (
        "builtins.property",
        "enum.property",
        "abc.abstractproperty",
        "types.DynamicClassAttribute",
        "types.DynamicClassAttribute()",
    ),
)
def test_skips_qualified_property_like_decorators(decorator: str) -> None:
    source = f'class Example:\n    @{decorator}\n    def value(self):\n        """Returns property value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize("decorator", ("value.getter", "value.setter", "value.deleter"))
def test_skips_property_accessor_decorators(decorator: str) -> None:
    source = f'class Example:\n    @{decorator}\n    def value(self):\n        """Returns property accessor value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_skips_import_alias_property_like_decorators() -> None:
    source = 'from functools import cached_property as cp\nfrom project import Property as P\n\n\nclass Example:\n    @cp\n    def cached(self):\n        """Returns cached value."""\n\n    @P\n    def custom(self):\n        """Returns custom value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_property_decorators=("builtins.property", "functools.cached_property", "project.Property")))

    assert result.new_source == source
    assert not result.unfixed_findings


def test_skips_called_import_alias_property_like_decorators() -> None:
    source = 'from functools import cached_property as cp\nfrom project import Property as P\n\n\nclass Example:\n    @cp()\n    def cached(self):\n        """Returns cached value."""\n\n    @P(read_only=True)\n    def custom(self):\n        """Returns custom value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_property_decorators=("builtins.property", "functools.cached_property", "project.Property")))

    assert result.new_source == source
    assert not result.unfixed_findings


def test_later_property_import_alias_rebinding_does_not_affect_prior_decorator() -> None:
    source = 'from functools import cached_property as cp\n\nclass Example:\n    @cp\n    def cached(self):\n        """Returns cached value."""\n\ncp = decorator\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_import_after_local_assignment_matches_later_property_decorator() -> None:
    source = 'functools = object()\nimport functools\n\nclass Example:\n    @functools.cached_property\n    def cached(self):\n        """Returns cached value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_unqualified_property_decorator_configuration_is_syntactic_only() -> None:
    source = 'from project import Property as P\n\n\nclass Example:\n    @P\n    def aliased(self):\n        """Returns aliased value."""\n\n    @Property\n    def syntactic(self):\n        """Returns syntactic value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_property_decorators=("Property",)))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_shadowed_property_import_alias_is_not_treated_as_configured_property() -> None:
    source = 'from functools import cached_property as cp\ncp = decorator\n\n\nclass Example:\n    @cp\n    def cached(self):\n        """Returns cached value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)


def test_class_local_shadowed_property_import_alias_is_not_treated_as_configured_property() -> None:
    source = 'from functools import cached_property as cp\n\nclass Example:\n    cp = decorator\n\n    @cp\n    def cached(self):\n        """Returns cached value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)


def test_shadowed_dotted_property_decorator_is_not_treated_as_configured_property() -> None:
    source = 'class Builtins:\n    property = object()\n\nbuiltins = Builtins()\n\n\nclass Example:\n    @builtins.property\n    def value(self):\n        """Returns property value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((10,),)


def test_static_name_bindings_are_cached_on_prepared_pdf_data(monkeypatch: pytest.MonkeyPatch) -> None:
    category, context = contexts('from functools import cached_property as cp\n\nclass Example:\n    @cp\n    def cached(self):\n        """Returns cached value."""\n')
    class_node = category.module.body[1]
    assert isinstance(class_node, cst.ClassDef)
    function_node = class_node.body.body[0]
    assert isinstance(function_node, cst.FunctionDef)
    calls = 0
    original = module_bindings.collect_top_level_bindings

    def counted_collect_top_level_bindings(module: cst.Module, *, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange] | None = None) -> module_bindings.ModuleBindings:
        nonlocal calls
        calls += 1
        return original(module, positions=positions)

    monkeypatch.setattr(module_bindings, "collect_top_level_bindings", counted_collect_top_level_bindings)
    data = PDF.require_data(context)

    assert data._module_bindings is None
    assert static_names.configured_expression_name(function_node.decorators[0].decorator, ("functools.cached_property",), context=context) == "cp"
    assert static_names.configured_expression_name(function_node.decorators[0].decorator, ("functools.cached_property",), context=context) == "cp"
    assert calls == 1
    assert data._module_bindings is not None


def test_property_decorator_setting_replaces_exact_property_decorator_names() -> None:
    source = (
        'class Example:\n    @property\n    def value(self):\n        """Returns property value."""\n\n    @project.Property\n    def custom(self):\n        """Returns custom property value."""\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_property_decorators=("project.Property",)))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


def test_empty_property_decorator_setting_keeps_accessors_but_does_not_skip_exact_decorators() -> None:
    source = 'class Example:\n    @property\n    def value(self):\n        """Returns property value."""\n\n    @functools.cached_property()\n    def cached(self):\n        """Returns cached value."""\n\n    @value.getter\n    def value(self):\n        """Returns accessor value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_property_decorators=()))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (8,))


def test_static_but_non_exact_property_decorator_names_do_not_suppress_findings() -> None:
    source = 'class Example:\n    @project.property\n    def first(self):\n        """Returns first value."""\n\n    @project.property()\n    def second(self):\n        """Returns second value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (8,))


def test_complex_non_property_decorators_do_not_suppress_findings() -> None:
    source = 'class Example:\n    @decorators[0]\n    def first(self):\n        """Returns first value."""\n\n    @decorators[0].property\n    def second(self):\n        """Returns second value."""\n\n    @setter\n    def third(self):\n        """Returns third value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (8,), (12,))


def test_protected_structures_and_heading_setting_control_summary_status() -> None:
    source = 'def heading():\n    """Returns\n    =======\n    """\n\n\ndef field():\n    """:return: value"""\n'
    protected = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_parse_headings=False))

    assert not protected.unfixed_findings
    assert tuple(finding.line_numbers for finding in disabled.unfixed_findings) == ((2,),)


def test_leading_blank_and_adornment_lines_are_not_summary_word_targets() -> None:
    source = 'def function():\n    """\n    ====\n    Returns value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_parse_headings=False))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


def test_skips_summary_without_a_whitespace_delimited_first_word() -> None:
    source = 'def function():\n    """\\u00a0"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize("summary", ('"Returns" the value.', "(Returns) the value.", "Returns: the value."))
def test_normalizes_first_word_punctuation_before_mood_check(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


def test_reports_concatenated_and_escaped_newline_physical_lines() -> None:
    source = 'def concatenated():\n    ("Returns "\n     "value.")\n\n\ndef escaped():\n    """Returns value\\ncontinued."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3), (7,))


def test_reports_async_and_nested_function_summaries() -> None:
    source = 'async def outer():\n    """Returns outer value."""\n\n    def inner():\n        """Returns inner value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (5,))


def test_google_convention_ignores_broad_selection_but_exact_selection_still_applies() -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.GOOGLE))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF302" not in active_codes

    exact = format_source('def function():\n    """Returns value."""\n', settings=CheckSettings(select=("PDF302",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in exact.unfixed_findings) == ((2,),)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """Returns value."""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF302NonImperativeSummary, context)
    fixed = rule_helpers.rule_fix_result(PDF302NonImperativeSummary, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert fixed.module.code == source
    assert not fixed.fixed_findings
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
