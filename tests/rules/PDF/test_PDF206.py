import tests.rule_helpers as rule_helpers
import tests.rules.PDF.statement_spacing_helpers as statement_spacing_helpers
from pydocformatter.rules.definitions.PDF.PDF206_no_blank_line_after_function_docstring import PDF206NoBlankLineAfterFunctionDocstring


def test_removes_blank_lines_after_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n\n\n    return None\n'
    _, context = statement_spacing_helpers.contexts(source, rule_code="PDF206")
    findings = rule_helpers.rule_findings(PDF206NoBlankLineAfterFunctionDocstring, context)
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Docstring."""\n    return None\n'
    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert result.fixed_findings[PDF206NoBlankLineAfterFunctionDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF206").modified


def test_removes_adjacent_blank_before_body_comment() -> None:
    source = 'def function():\n    """Docstring."""\n\n    # Body comment.\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Docstring."""\n    # Body comment.\n    return None\n'


def test_ignores_function_with_only_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings


def test_ignores_classes() -> None:
    source = 'class Client:\n    """Docstring."""\n\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings


def test_collapses_whitespace_only_blank_lines_after_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n    \t  \n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Docstring."""\n    return None\n'
    assert result.fixed_findings[PDF206NoBlankLineAfterFunctionDocstring.meta] == 1


def test_suppression_on_docstring_line_suppresses_after_finding() -> None:
    source = 'def function():\n    """Docstring."""  # noqa: PDF206\n\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_trailing_body_comment_without_following_statement() -> None:
    source = 'def function():\n    """Docstring."""\n\n    # Body comment.\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings


def test_removes_blank_lines_after_multiline_function_docstring() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n    """\n\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n    return None\n'
    assert result.fixed_findings[PDF206NoBlankLineAfterFunctionDocstring.meta] == 1
