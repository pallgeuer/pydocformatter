import tests.rules.PDF.statement_spacing_helpers as statement_spacing_helpers
from pydocformatter.rules.definitions.PDF.PDF205_blank_line_before_function_docstring import PDF205BlankLineBeforeFunctionDocstring


def test_inserts_blank_line_before_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF205")

    assert result.new_source == 'def function():\n\n    """Docstring."""\n    return None\n'
    assert result.fixed_findings[PDF205BlankLineBeforeFunctionDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF205").modified


def test_collapses_excess_blank_lines_before_function_docstring() -> None:
    source = 'def function():\n\n\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF205")

    assert result.new_source == 'def function():\n\n    """Docstring."""\n    return None\n'
    assert result.fixed_findings[PDF205BlankLineBeforeFunctionDocstring.meta] == 1


def test_inserts_blank_after_leading_comment_before_function_docstring() -> None:
    source = 'def function():\n    # Leading comment.\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF205")

    assert result.new_source == 'def function():\n    # Leading comment.\n\n    """Docstring."""\n    return None\n'


def test_ignores_classes() -> None:
    source = 'class Client:\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF205")

    assert result.new_source == source
    assert not result.fixed_findings


def test_ignores_attribute_docstrings() -> None:
    source = 'def function():\n    value = 1\n    """Attribute docstring."""\n    return value\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF205")

    assert result.new_source == source
    assert not result.fixed_findings


def test_inserts_blank_line_with_configured_crlf_line_ending() -> None:
    source = 'def function():\r\n    """Docstring."""\r\n    return None\r\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF205")

    assert result.new_source == 'def function():\r\n\r\n    """Docstring."""\r\n    return None\r\n'


def test_inserts_blank_line_before_decorated_async_function_docstring() -> None:
    source = '@decorator\nasync def function():\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF205")

    assert result.new_source == '@decorator\nasync def function():\n\n    """Docstring."""\n    return None\n'
    assert result.fixed_findings[PDF205BlankLineBeforeFunctionDocstring.meta] == 1
