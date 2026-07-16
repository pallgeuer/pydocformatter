"""README source-contract tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import pathlib

# First-party imports
import pydocformatter.rules.documentation as rule_documentation
from tests import markdown_example_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_readme_examples_match_formatter() -> None:
    """Structured README examples must match fixes and remaining findings."""
    source = (ROOT / "README.md").read_text(encoding="utf-8")
    examples = rule_documentation.parse_rule_markdown_examples(source, rule_code="README")

    assert examples
    for index, example in enumerate(examples, start=1):
        markdown_example_helpers.execute_markdown_example(example, label=f"README example {index}", fallback_path=f"README_example_{index}.py")


def test_readme_configuration_links_to_detailed_documentation() -> None:
    """README configuration help must link to the detailed documentation."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "pydocfmt config" in readme
    assert "https://pallgeuer.github.io/pydocformatter/configuration/" in readme
    assert "https://pallgeuer.github.io/pydocformatter/settings/" in readme
    assert "https://pallgeuer.github.io/pydocformatter/reference/file-selection/" in readme
    assert "https://pallgeuer.github.io/pydocformatter/reference/rule-selection/" in readme
