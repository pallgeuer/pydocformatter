"""Evaluation and adoption documentation tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import json
import difflib
import pathlib
import tomllib

# Third-party imports
from tools.docs import generate_zensical

# First-party imports
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter import formatter
from tests import markdown_example_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPARISON_PATH = ROOT / "docs_site" / "comparison.md"
DEMONSTRATION_PATH = ROOT / "docs_site" / "demonstration.md"
INTEGRATIONS_PATH = ROOT / "docs_site" / "integrations.md"


def test_comparison_identifies_reviewed_versions_and_primary_sources() -> None:
    """The comparison must bound claims to exact versions and first-party references."""
    comparison = COMPARISON_PATH.read_text(encoding="utf-8")
    reviewed_versions = {"pydocformatter": "1.2.0", "Ruff": "0.16.6", "pydocstyle": "6.3.0", "docformatter": "1.7.8", "Black": "26.5.1", "pydoclint": "0.9.1"}

    for project, version in reviewed_versions.items():
        assert f"[{project} {version}](https://pypi.org/project/{project.lower()}/{version}/)" in comparison

    for source in (
        "https://docs.astral.sh/ruff/formatter/",
        "https://docs.astral.sh/ruff/rules/#pydocstyle-d",
        "https://pydocstyle.readthedocs.io/en/latest/error_codes.html",
        "https://pydocstyle.readthedocs.io/en/latest/usage.html",
        "https://docformatter.readthedocs.io/en/stable/usage.html",
        "https://docformatter.readthedocs.io/en/stable/configuration.html",
        "https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#strings",
        "https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#comments",
        "https://jsh9.github.io/pydoclint/config_options.html",
    ):
        assert source in comparison

    for heading in ("## Ruff", "## pydocstyle", "## docformatter", "## Black", "## pydoclint", "## Choosing a toolchain"):
        assert heading in comparison


def test_canonical_demonstration_matches_formatter_and_complete_diff() -> None:
    """The canonical example must remain executable, complete, and idempotent."""
    demonstration = DEMONSTRATION_PATH.read_text(encoding="utf-8")
    examples = rule_documentation.parse_rule_markdown_examples(demonstration, rule_code="DEMONSTRATION")

    assert len(examples) == 1
    outcome = markdown_example_helpers.execute_markdown_example(examples[0], label="canonical demonstration", fallback_path="demo.py")
    fixable_codes = {finding.rule.code.tag for finding in outcome.check_result.unfixed_findings if finding.fixable}
    fix_result = formatter.format_source(outcome.example.input_source, outcome.path, settings=outcome.settings, rule_selection=outcome.selection, fix=True)
    remaining_codes = {finding.rule.code.tag for finding in fix_result.unfixed_findings}

    assert fixable_codes == {"PCF000", "PCF002", "PDF101"}
    assert remaining_codes == {"PDF203", "PDF500"}
    second_result = formatter.format_source(outcome.example.output_source, outcome.path, settings=outcome.settings, rule_selection=outcome.selection, fix=True)
    assert second_result.errors == ()
    assert not second_result.modified
    assert second_result.new_source == outcome.example.output_source
    protected_fragments = (
        '>>> render_report(["alpha"], "https://example.com/reports", 2)',
        "'https://example.com/reports/latest'",
        '```python\n        result=render_report(["alpha"],"https://example.com/reports",2)\n        ```',
        ".. math::\n\n            total = successful + failed",
        "[the deployment guide](https://example.com/docs/deployment?region=eu&mode=preview)",
    )
    for fragment in protected_fragments:
        assert fragment in outcome.example.input_source
        assert fragment in outcome.example.output_source

    expected_diff = "".join(
        difflib.unified_diff(outcome.example.input_source.splitlines(keepends=True), outcome.example.output_source.splitlines(keepends=True), fromfile="before/demo.py", tofile="after/demo.py", n=0)
    )
    documented_diff = markdown_example_helpers.marked_fence(demonstration, "canonical-demo-diff", "diff")
    assert documented_diff == expected_diff
    assert not tuple(line for line in documented_diff.splitlines() if line.endswith((" ", "\t")))


def test_canonical_demonstration_config_keeps_tool_boundaries_aligned() -> None:
    """The documented Ruff-first and Black-alternative settings must stay coherent."""
    demonstration = DEMONSTRATION_PATH.read_text(encoding="utf-8")
    config = tomllib.loads(markdown_example_helpers.marked_fence(demonstration, "canonical-demo-config", "toml"))
    black_config = tomllib.loads(markdown_example_helpers.marked_fence(demonstration, "canonical-demo-black", "toml"))

    assert config["tool"]["ruff"]["line-length"] == config["tool"]["pydocfmt"]["line-length"] == 88
    assert config["tool"]["ruff"]["format"]["docstring-code-format"] is True
    assert config["tool"]["ruff"]["lint"]["select"] == ["E4", "E7", "E9", "F"]
    assert config["tool"]["pydocfmt"]["select"] == ["PDF101", "PDF203", "PDF500", "PCF000", "PCF001", "PCF002"]
    assert config["tool"]["pydocfmt"]["docstring"]["convention"] == "google"
    assert config["tool"]["pydocfmt"]["comment"]["join-standalone-lines"] is True
    assert black_config["tool"]["black"]["line-length"] == 88
    for command in ("uv run ruff check .", "uv run ruff format --check .", "uv run pydocfmt check --diff", "uv run pydocfmt check --fix"):
        assert command in demonstration


def test_editor_tasks_are_manual_read_only_and_fix_workflows() -> None:
    """Editor recipes must expose explicit current-file checks and fixes."""
    integrations = INTEGRATIONS_PATH.read_text(encoding="utf-8")
    tasks = json.loads(markdown_example_helpers.marked_fence(integrations, "vscode-tasks", "json"))["tasks"]

    assert [task["label"] for task in tasks] == ["pydocfmt: check current file", "pydocfmt: fix current file"]
    assert all(task["type"] == "process" for task in tasks)
    assert all(task["command"] == "uv" for task in tasks)
    assert all(task["options"]["cwd"] == "${workspaceFolder}" for task in tasks)
    assert all(task["problemMatcher"] == [] for task in tasks)
    assert tasks[0]["args"] == ["run", "pydocfmt", "check", "--force-exclude", "${file}"]
    assert tasks[1]["args"] == ["run", "pydocfmt", "check", "--fix", "--force-exclude", "${file}"]
    for required in (
        "https://code.visualstudio.com/docs/editor/tasks",
        "https://www.jetbrains.com/help/pycharm/configuring-third-party-tools.html",
        'run pydocfmt check --force-exclude "$FilePath$"',
        'run pydocfmt check --fix --force-exclude "$FilePath$"',
        "$ProjectFileDir$",
        "The read-only action is the recommended default",
        "intentionally manual rather than save-time fixers",
    ):
        assert required in integrations


def test_evaluation_pages_are_discoverable_and_metadata_is_consistent() -> None:
    """Navigation and primary entry points must expose the evaluation pages."""
    nav = generate_zensical._nav()
    tutorial_index = nav.index({"Tutorial": "tutorial.md"})

    assert nav[tutorial_index + 1] == {"Evaluation": [{"Comparison": "comparison.md"}, {"Demonstration": "demonstration.md"}]}
    assert (
        tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["description"]
        == tomllib.loads((ROOT / "zensical.template.toml").read_text(encoding="utf-8"))["project"]["site_description"]
    )
    for path in (ROOT / "README.md", ROOT / "docs_site" / "index.md"):
        entry_point = path.read_text(encoding="utf-8")
        assert "comparison" in entry_point.casefold()
        assert "demonstration" in entry_point.casefold()
    faq = (ROOT / "docs_site" / "faq.md").read_text(encoding="utf-8")
    for anchor in ("#ruff", "#pydocstyle", "#docformatter", "#black", "#pydoclint"):
        assert f"comparison.md{anchor}" in faq
