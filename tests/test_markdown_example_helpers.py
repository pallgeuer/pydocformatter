"""Structured Markdown example helper tests."""

# Standard library imports
import ast
import pathlib

# Third-party imports
import pytest

# First-party imports
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter.cli import settings_check
from tests import assertion_rewriting, markdown_example_helpers


TESTS_ROOT = pathlib.Path(__file__).resolve().parent


@pytest.mark.parametrize(("documented_path", "expected_path"), [("package/module.py", "package/module.py"), (None, "fallback.py")])
def test_execute_markdown_example_resolves_documented_path_before_fallback(documented_path: str | None, expected_path: str) -> None:
    """Documented paths must take precedence over test-owned fallback paths."""
    example = rule_documentation.RuleMarkdownExample(path=documented_path, settings_text="", input_source="value = 1\n", output_source="value = 1\n", findings=())

    outcome = markdown_example_helpers.execute_markdown_example(example, label="path example", fallback_path="fallback.py", field_overrides=settings_check.CheckSettingsOverrides(select=()))

    assert outcome.path == expected_path


def test_assertion_bearing_helpers_are_registered_for_rewriting() -> None:
    """Every non-test helper with plain assertions must have pytest introspection."""
    assertion_modules: set[str] = set()
    for path in TESTS_ROOT.rglob("*.py"):
        if path.name == "conftest.py" or path.name.startswith("test_"):
            continue
        syntax = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(isinstance(node, ast.Assert) for node in ast.walk(syntax)):
            assertion_modules.add(".".join(path.relative_to(TESTS_ROOT.parent).with_suffix("").parts))

    assert assertion_modules == set(assertion_rewriting.ASSERT_REWRITE_MODULES)


def test_execute_markdown_example_failure_shows_rewritten_values() -> None:
    """Markdown helper failures must include pytest's actual and expected values."""
    example = rule_documentation.RuleMarkdownExample(path=None, settings_text="", input_source="value = 1\n", output_source="value = 2\n", findings=())

    with pytest.raises(AssertionError) as error_info:
        markdown_example_helpers.execute_markdown_example(example, label="rewritten example", fallback_path="fallback.py", field_overrides=settings_check.CheckSettingsOverrides(select=()))

    message = str(error_info.value)
    assert "value = 1" in message
    assert "value = 2" in message
