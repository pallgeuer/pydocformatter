# First-party imports
from pydocformatter.rules.definitions.PDF.PDF207_blank_line_after_function_docstring import PDF207BlankLineAfterFunctionDocstring
from tests.rules.PDF import statement_spacing_helpers


def test_inserts_blank_line_after_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == 'def function():\n    """Docstring."""\n\n    return None\n'
    assert result.fixed_findings[PDF207BlankLineAfterFunctionDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF207").modified


def test_collapses_excess_blank_lines_after_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n\n\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == 'def function():\n    """Docstring."""\n\n    return None\n'
    assert result.fixed_findings[PDF207BlankLineAfterFunctionDocstring.meta] == 1


def test_inserts_blank_before_body_comment_after_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n    # Body comment.\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == 'def function():\n    """Docstring."""\n\n    # Body comment.\n    return None\n'


def test_ignores_function_with_only_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == source
    assert not result.fixed_findings


def test_inserts_blank_line_before_final_statement_without_final_newline() -> None:
    source = 'def function():\n    """Docstring."""\n    return None'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == 'def function():\n    """Docstring."""\n\n    return None'
    assert result.fixed_findings[PDF207BlankLineAfterFunctionDocstring.meta] == 1


def test_ignores_simple_suite_docstring() -> None:
    source = 'def function(): """Docstring."""; return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == source
    assert not result.fixed_findings


def test_ignores_trailing_body_comment_without_following_statement() -> None:
    source = 'def function():\n    """Docstring."""\n    # Body comment.\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == source
    assert not result.fixed_findings


def test_inserts_blank_line_after_multiline_function_docstring() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n    """\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF207")

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n\n    return None\n'
    assert result.fixed_findings[PDF207BlankLineAfterFunctionDocstring.meta] == 1
