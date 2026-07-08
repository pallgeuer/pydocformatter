# First-party imports
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PDF.PDF204_no_blank_line_before_function_docstring import PDF204NoBlankLineBeforeFunctionDocstring
from tests import rule_helpers
from tests.rules.PDF import statement_spacing_helpers


def test_removes_blank_lines_before_function_docstring() -> None:
    source = 'def function():\n\n\n    """Docstring."""\n    return None\n'
    _, context = statement_spacing_helpers.contexts(source, rule_code="PDF204")
    findings = rule_helpers.rule_findings(PDF204NoBlankLineBeforeFunctionDocstring, context)
    result = statement_spacing_helpers.format_source(source, rule_code="PDF204")

    assert result.new_source == 'def function():\n    """Docstring."""\n    return None\n'
    assert tuple(finding.line_numbers for finding in findings) == ((4,),)
    assert result.fixed_findings[PDF204NoBlankLineBeforeFunctionDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF204").modified


def test_removes_adjacent_blank_after_leading_comment() -> None:
    source = 'def function():\n    # Leading comment.\n\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF204")

    assert result.new_source == 'def function():\n    # Leading comment.\n    """Docstring."""\n    return None\n'


def test_ignores_classes_and_already_compact_function_docstrings() -> None:
    source = 'def function():\n    """Docstring."""\n    return None\n\nclass Client:\n\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF204")

    assert result.new_source == source
    assert not result.fixed_findings


def test_suppression_on_docstring_line_suppresses_finding() -> None:
    source = 'def function():\n\n    """Docstring."""  # noqa: PDF204\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF204")

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_broad_selection_keeps_pdf204_over_incompatible_pdf205() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF204",), extend_select=("PDF205",)))

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF204",)
    assert selection.errors == ("Selected rule PDF205 is incompatible with earlier selected rule PDF204; PDF205 has been disabled",)


def test_removes_blank_lines_before_nested_function_docstrings_without_touching_other_owners() -> None:
    source = (
        "class Client:\n"
        "\n"
        '    """Class docstring."""\n'
        "\n"
        "    def method(self):\n"
        "\n"
        '        """Method docstring."""\n'
        "\n"
        "        def nested():\n"
        "\n"
        '            """Nested docstring."""\n'
        "            return None\n"
        "\n"
        "        return nested()\n"
    )
    result = statement_spacing_helpers.format_source(source, rule_code="PDF204")

    assert result.new_source == (
        "class Client:\n"
        "\n"
        '    """Class docstring."""\n'
        "\n"
        "    def method(self):\n"
        '        """Method docstring."""\n'
        "\n"
        "        def nested():\n"
        '            """Nested docstring."""\n'
        "            return None\n"
        "\n"
        "        return nested()\n"
    )
    assert result.fixed_findings[PDF204NoBlankLineBeforeFunctionDocstring.meta] == 2


def test_ignores_simple_suite_docstring() -> None:
    source = 'def function(): """Docstring."""; return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF204")

    assert result.new_source == source
    assert not result.fixed_findings


def test_removes_blank_line_before_decorated_async_function_docstring() -> None:
    source = '@decorator\nasync def function():\n\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF204")

    assert result.new_source == '@decorator\nasync def function():\n    """Docstring."""\n    return None\n'
    assert result.fixed_findings[PDF204NoBlankLineBeforeFunctionDocstring.meta] == 1
