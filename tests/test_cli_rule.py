# Standard library imports
import json
import unittest
import contextlib
import unittest.mock
from io import StringIO

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.rules.collection as rule_collection


class TestCLIRule(unittest.TestCase):
    def test_pydocfmt_rule_prints_rule_markdown(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "PDF101"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
            exit_code = pydocfmt_cli.main()

        output = stdout.getvalue()
        assert exit_code == 0
        assert output.startswith("# docstring-reflow (PDF101)\n\nFix is usually available.\n\n## What it does\n")
        assert "## Ruff compatibility\n" in output
        assert "Derived from" not in output

    def test_pydocfmt_rule_prints_rule_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "--output-format", "json", "PDF203"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
            exit_code = pydocfmt_cli.main()

        output = json.loads(stdout.getvalue())
        assert exit_code == 0
        assert output["name"] == "summary-too-long"
        assert output["code"] == "PDF203"
        assert output["linter"] == "pydocformatter"
        assert output["fix"] == "Fix is not available."
        assert output["fix_availability"] == "Never"
        assert output["status"] == {"Stable": {"since": "v1.0.0"}}
        assert output["explanation"].startswith("## What it does\n")
        assert "# summary-too-long (PDF203)" not in output["explanation"]
        assert "Fix is not available." not in output["explanation"]
        assert "## Ruff compatibility\n" in output["explanation"]
        assert output["source_location"]["file"].endswith("PDF203_summary_too_long.py")

    def test_pydocfmt_rule_prints_usually_fixable_rule_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "--output-format", "json", "PDF101"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
            exit_code = pydocfmt_cli.main()

        output = json.loads(stdout.getvalue())
        assert exit_code == 0
        assert output["fix"] == "Fix is usually available."
        assert output["fix_availability"] == "Usually"

    def test_pydocfmt_rule_prints_all_rules(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "--all"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
            exit_code = pydocfmt_cli.main()

        output = stdout.getvalue()
        assert exit_code == 0
        assert "# standalone-comment-formatting (PCF001)\n" in output
        assert "# one-line-docstring (PDF110)\n" in output
        assert output.index("# standalone-comment-formatting (PCF001)") < output.index("# docstring-reflow (PDF101)")

    def test_pydocfmt_rule_prints_all_rules_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "--output-format", "json", "--all"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
            exit_code = pydocfmt_cli.main()

        output = json.loads(stdout.getvalue())
        expected_codes = tuple(str(rule_class.meta.code) for rule_class in rule_collection.RULE_COLLECTION.rules)

        assert exit_code == 0
        assert tuple(rule["code"] for rule in output) == expected_codes

    def test_pydocfmt_rule_rejects_missing_rule(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["pydocfmt", "rule"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = pydocfmt_cli.main()

        assert exit_code == 2
        assert stdout.getvalue() == ""
        assert "Must specify RULE or --all" in stderr.getvalue()

    def test_pydocfmt_rule_rejects_unknown_rule(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["pydocfmt", "rule", "BAD999"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = pydocfmt_cli.main()

        assert exit_code == 2
        assert stdout.getvalue() == ""
        assert "Invalid value 'BAD999'" in stderr.getvalue()

    def test_pydocfmt_rule_rejects_rule_with_all(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["pydocfmt", "rule", "PDF101", "--all"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = pydocfmt_cli.main()

        assert exit_code == 2
        assert stdout.getvalue() == ""
        assert "RULE cannot be used with --all" in stderr.getvalue()


if __name__ == "__main__":
    unittest.main()
