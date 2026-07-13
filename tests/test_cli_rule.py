# Future imports
from __future__ import annotations

# Standard library imports
import json

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.rules.collection as rule_collection
from tests import cli_helpers


def test_pydocfmt_rule_prints_rule_markdown() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule", "PDF101"])

    output = result.stdout
    assert result.exit_code == 0
    assert output.startswith("# docstring-reflow (PDF101)\n\nFix is usually available.\n\n## What it does\n")
    assert "## Ruff compatibility\n" in output
    assert "Derived from" not in output


def test_pydocfmt_rule_prints_rule_json() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule", "--output-format", "json", "PDF203"])

    output = json.loads(result.stdout)
    assert result.exit_code == 0
    assert output["name"] == "summary-too-long"
    assert output["code"] == "PDF203"
    assert output["linter"] == "pydocformatter"
    assert output["url"] == "https://pallgeuer.github.io/pydocformatter/rules/summary-too-long/"
    assert output["fix"] == "Fix is not available."
    assert output["fix_availability"] == "Never"
    assert output["status"] == {"Stable": {"since": "v1.0.0"}}
    assert output["explanation"].startswith("## What it does\n")
    assert "# summary-too-long (PDF203)" not in output["explanation"]
    assert "Fix is not available." not in output["explanation"]
    assert "## Ruff compatibility\n" in output["explanation"]
    assert output["source_location"]["file"].endswith("PDF203_summary_too_long.py")


def test_pydocfmt_rule_prints_usually_fixable_rule_json() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule", "--output-format", "json", "PDF101"])

    output = json.loads(result.stdout)
    assert result.exit_code == 0
    assert output["fix"] == "Fix is usually available."
    assert output["fix_availability"] == "Usually"


def test_pydocfmt_rule_prints_all_rules() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule", "--all"])

    output = result.stdout
    assert result.exit_code == 0
    assert "# standalone-comment-formatting (PCF001)\n" in output
    assert "# one-line-docstring (PDF110)\n" in output
    assert output.index("# standalone-comment-formatting (PCF001)") < output.index("# docstring-reflow (PDF101)")


def test_pydocfmt_rule_prints_all_rules_json() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule", "--output-format", "json", "--all"])

    output = json.loads(result.stdout)
    expected_codes = tuple(str(rule_class.meta.code) for rule_class in rule_collection.RULE_COLLECTION.rules)

    assert result.exit_code == 0
    assert tuple(rule["code"] for rule in output) == expected_codes
    assert all(rule["url"].startswith("https://pallgeuer.github.io/pydocformatter/rules/") for rule in output)
    assert all(rule["url"].endswith("/") for rule in output)


def test_pydocfmt_rule_rejects_missing_rule() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Must specify RULE or --all" in result.stderr


def test_pydocfmt_rule_rejects_unknown_rule() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule", "BAD999"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Invalid value 'BAD999'" in result.stderr


def test_pydocfmt_rule_rejects_rule_with_all() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "rule", "PDF101", "--all"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "RULE cannot be used with --all" in result.stderr
