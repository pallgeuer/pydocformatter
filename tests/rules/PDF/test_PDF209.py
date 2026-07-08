# First-party imports
from pydocformatter.rules.definitions.PDF.PDF209_blank_line_before_class_docstring import PDF209BlankLineBeforeClassDocstring
from tests.rules.PDF import statement_spacing_helpers


def test_inserts_blank_line_before_class_docstring() -> None:
    source = 'class Client:\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF209")

    assert result.new_source == 'class Client:\n\n    """Docstring."""\n    value = 1\n'
    assert result.fixed_findings[PDF209BlankLineBeforeClassDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF209").modified


def test_collapses_excess_blank_lines_before_class_docstring() -> None:
    source = 'class Client:\n\n\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF209")

    assert result.new_source == 'class Client:\n\n    """Docstring."""\n    value = 1\n'
    assert result.fixed_findings[PDF209BlankLineBeforeClassDocstring.meta] == 1


def test_inserts_blank_after_leading_comment_before_class_docstring() -> None:
    source = 'class Client:\n    # Leading comment.\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF209")

    assert result.new_source == 'class Client:\n    # Leading comment.\n\n    """Docstring."""\n    value = 1\n'


def test_ignores_functions() -> None:
    source = 'def function():\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF209")

    assert result.new_source == source
    assert not result.fixed_findings


def test_inserts_blank_line_before_decorated_class_docstring() -> None:
    source = '@decorator\nclass Client:\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF209")

    assert result.new_source == '@decorator\nclass Client:\n\n    """Docstring."""\n    value = 1\n'
    assert result.fixed_findings[PDF209BlankLineBeforeClassDocstring.meta] == 1
