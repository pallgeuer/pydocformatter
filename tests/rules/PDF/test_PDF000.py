import libcst as cst
import libcst.metadata as cst_metadata

from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF, DocstringKind
from pydocformatter.rules.definitions.PDF.PDF000_concatenated_docstring_literal import PDF000ConcatenatedDocstringLiteral


def contexts(source: str) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py", settings=CheckSettings(), module=module, metadata_wrapper=wrapper, positions=wrapper.resolve(cst_metadata.PositionProvider), line_ending="\r\n" if "\r\n" in source else "\n"
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def test_check_and_fix_concatenated_docstring() -> None:
    _, context = contexts('def function():\n    ("first " "second")\n')
    findings = PDF000ConcatenatedDocstringLiteral.check(context)
    result = PDF000ConcatenatedDocstringLiteral.fix(context)
    assert len(findings) == 1
    assert findings[0].line_numbers == (2,)
    assert result.module.code == 'def function():\n    ("""first second""")\n'
    fixed_category, _ = contexts(result.module.code)
    prepared = PDF.prepare(fixed_category)
    assert prepared.docstrings[0].kind == DocstringKind.SIMPLE
    assert prepared.docstrings[0].value == "first second"


def test_fix_preserves_complex_evaluated_values() -> None:
    source = 'def function():\n    (r"backslash\\n" "\\nquotes: \\"\\"\\"" "\\x00")\n'
    _, context = contexts(source)
    original = PDF.require_data(context).docstrings[0].value
    result = PDF000ConcatenatedDocstringLiteral.fix(context)
    _, fixed_context = contexts(result.module.code)
    fixed = PDF.require_data(fixed_context).docstrings[0]
    assert fixed.kind == DocstringKind.SIMPLE
    assert fixed.value == original
    assert PDF000ConcatenatedDocstringLiteral.check(fixed_context) == ()


def test_fix_handles_multiple_docstring_owners_in_one_pass() -> None:
    source = '"module " "doc"\n\nclass Outer:\n    "class " "doc"\n\n    def method(self):\n        "method " "doc"\n\n    def unchanged(self):\n        """simple doc"""\n'
    _, context = contexts(source)
    findings = PDF000ConcatenatedDocstringLiteral.check(context)
    result = PDF000ConcatenatedDocstringLiteral.fix(context)
    assert tuple(finding.line_numbers for finding in findings) == ((1,), (4,), (7,))
    assert tuple(finding.line_numbers for finding in result.fixed_findings) == ((1,), (4,), (7,))
    assert result.module.code == '"""module doc"""\n\nclass Outer:\n    """class doc"""\n\n    def method(self):\n        """method doc"""\n\n    def unchanged(self):\n        """simple doc"""\n'


def test_fix_replaces_complete_multiline_expression_and_reports_its_source_span() -> None:
    source = 'def function():\n    (\n        r"first\\n"  # Preserve the raw backslash.\n        " second" \\\n        "\\tthird"\n    )\n    return None\n'
    _, context = contexts(source)
    findings = PDF000ConcatenatedDocstringLiteral.check(context)
    result = PDF000ConcatenatedDocstringLiteral.fix(context)
    assert findings[0].line_numbers == (3, 4, 5)
    assert result.module.code == 'def function():\n    (\n        """first\\\\n second\\tthird"""\n    )\n    return None\n'
    _, fixed_context = contexts(result.module.code)
    assert PDF.require_data(fixed_context).docstrings[0].value == "first\\n second\tthird"


def test_fix_preserves_single_line_suite_statements() -> None:
    _, context = contexts('def function(): "first " "second"; return 1\n')
    result = PDF000ConcatenatedDocstringLiteral.fix(context)
    assert result.module.code == 'def function(): """first second"""; return 1\n'


def test_fix_preserves_crlf_and_multiline_evaluated_value() -> None:
    source = 'def function():\r\n    ("first\\n"\r\n     "second")\r\n'
    category, context = contexts(source)
    result = PDF000ConcatenatedDocstringLiteral.fix(context)
    assert result.fixed_findings[0].line_numbers == (2, 3)
    assert result.module.code == 'def function():\r\n    ("""first\r\nsecond""")\r\n'
    fixed_category, _ = contexts(result.module.code)
    assert PDF.prepare(fixed_category).docstrings[0].value == "first\nsecond"
    assert category.module.config_for_parsing.default_newline == "\r\n"


def test_ignores_concatenations_that_are_not_string_valued_first_expressions() -> None:
    source = 'def formatted():\n    f"first" "second"\n\ndef assigned():\n    value = "first" "second"\n\ndef later():\n    pass\n    "first" "second"\n'
    _, context = contexts(source)
    assert PDF000ConcatenatedDocstringLiteral.check(context) == ()
    assert PDF000ConcatenatedDocstringLiteral.fix(context).module is context.module


def test_simple_docstrings_are_unchanged() -> None:
    _, context = contexts('"""simple"""\n')
    assert PDF000ConcatenatedDocstringLiteral.check(context) == ()
    assert PDF000ConcatenatedDocstringLiteral.fix(context).module is context.module


def test_normalization_rule_runs_before_other_pdf_rules() -> None:
    assert PDF.ordered_rules()[0] is PDF000ConcatenatedDocstringLiteral
