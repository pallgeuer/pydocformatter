import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF202_empty_docstring import PDF202EmptyDocstring


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF202",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=False)


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF202",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_reports_empty_and_whitespace_only_docstrings_without_fixing() -> None:
    source = '""""""\n\n\ndef function():\n    """   """\n\n\nclass Example:\n    """\n    \n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (5,), (9, 10, 11))
    assert [finding.fixable for finding in result.unfixed_findings] == [False, False, False]


def test_reports_empty_concatenated_docstring_on_physical_lines() -> None:
    source = 'def function():\n    (""\n     "")\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)


def test_reports_simple_suite_and_concatenated_whitespace_docstrings() -> None:
    source = 'def inline(): ""\n\n\ndef concatenated():\n    (" "\n     "\\t")\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (5, 6))


def test_does_not_report_content_absent_docstrings_or_non_docstring_strings() -> None:
    source = 'def documented():\n    """Value."""\n\n\ndef undocumented():\n    pass\n\n\ndef not_docstring():\n    value = 1\n    """"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_escaped_whitespace_but_skips_bytes_and_fstring_first_expressions() -> None:
    source = 'def escaped():\n    """\\t\\n"""\n\n\ndef bytes_expression():\n    b""\n\n\ndef fstring_expression(value):\n    f"{value}"\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """   """\n'
    _, context = contexts(source)
    findings = PDF202EmptyDocstring.check(context)
    check_only = format_source(source, fix=False)
    fix_enabled = format_source(source, fix=True)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
    assert tuple(finding.line_numbers for finding in fix_enabled.unfixed_findings) == ((2,),)
    assert check_only.new_source == source
    assert fix_enabled.new_source == source
