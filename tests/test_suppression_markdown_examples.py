# Future imports
from __future__ import annotations

# Standard library imports
import pathlib
import tomllib

# First-party imports
import pydocformatter.rules.documentation as rule_documentation
from tests import markdown_example_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]
SUPPRESSIONS_PATH = ROOT / "docs" / "public" / "rule_suppressions.md"


def test_suppression_markdown_examples_match_formatter_behavior() -> None:
    """Execute structured suppression guide examples against the formatter."""
    markdown = SUPPRESSIONS_PATH.read_text(encoding="utf-8")
    examples = rule_documentation.parse_rule_markdown_examples(markdown, rule_code="SUPPRESSIONS")

    assert examples, "Expected at least one structured suppression guide example"
    for index, example in enumerate(examples, start=1):
        _validate_example_settings(index, example)
        markdown_example_helpers.execute_markdown_example(example, label=f"suppression example {index}", fallback_path=f"suppressions_example_{index}.py")


def _validate_example_settings(example_number: int, example: rule_documentation.RuleMarkdownExample) -> None:
    """Validate suppression guide examples declare explicit focused rule selection."""
    if not example.settings_text:
        raise AssertionError(f"suppression example {example_number}: expected [settings] with explicit select")
    try:
        settings = tomllib.loads(example.settings_text)
    except tomllib.TOMLDecodeError as error:
        raise AssertionError(f"suppression example {example_number}: invalid [settings] TOML: {error}") from error
    if "select" not in settings:
        raise AssertionError(f"suppression example {example_number}: expected explicit select setting")
