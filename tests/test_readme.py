"""README source-contract tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import pathlib
import tomllib
import urllib.parse

# First-party imports
import pydocformatter.rules.documentation as rule_documentation
from tests import markdown_example_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_readme_first_screen_supports_package_evaluation() -> None:
    """The opening must provide the shortest useful package-evaluation path."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    try_position = readme.index("## Try it")
    rationale_position = readme.index("## Why pydocformatter?")
    evaluation = readme[:rationale_position]

    assert 0 < try_position < rationale_position
    assert "uv tool install pydocformatter" in evaluation
    assert "pydocfmt check\n" in evaluation
    assert "pydocfmt check --diff" in evaluation
    assert "https://pallgeuer.github.io/pydocformatter/" in evaluation
    assert "https://github.com/pallgeuer/pydocformatter" in evaluation


def test_project_metadata_supports_relevant_package_searches() -> None:
    """Package metadata must identify the formatter's accurate discovery terms."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    metadata = " ".join((project["description"], *project["keywords"])).casefold()

    for term in ("python docstring", "docstring formatter", "docstring linter", "comment formatter", "google-style docstrings", "numpy-style docstrings", "ruff integration", "pre-commit"):
        assert term in metadata


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
    assert "https://pallgeuer.github.io/pydocformatter/reference/cache/" in readme
    assert "https://pallgeuer.github.io/pydocformatter/reference/file-selection/" in readme
    assert "https://pallgeuer.github.io/pydocformatter/reference/rule-selection/" in readme


def test_readme_links_are_package_index_portable() -> None:
    """README links must resolve without a repository-relative base URL."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = [match.group("target") for match in re.finditer(r"\]\((?P<target>[^)]+)\)", readme)]
    invalid_targets = []

    for target in targets:
        parsed = urllib.parse.urlsplit(target)
        if target.startswith("#") or (parsed.scheme in {"http", "https"} and parsed.netloc):
            continue
        invalid_targets.append(target)

    assert not invalid_targets


def test_readme_links_to_the_compatibility_policy() -> None:
    """Evaluators must be able to find the compatibility policy from the README."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "https://pallgeuer.github.io/pydocformatter/versioning/" in readme
