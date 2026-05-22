import contextlib
import json
import unittest
import unittest.mock
from io import StringIO

import pydocformatter.cli.main as pydocfmt_cli


class TestCLIRule(unittest.TestCase):
    def test_pydocfmt_rule_prints_rule_markdown(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "PDF001"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertTrue(output.startswith("# reflow-required (PDF001)\n\nFix is always available.\n\n## What it does\n"))
        self.assertIn("## Ruff compatibility\n", output)
        self.assertNotIn("Derived from", output)

    def test_pydocfmt_rule_prints_rule_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "--output-format", "json", "PDF105"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        output = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(output["name"], "summary-too-long")
        self.assertEqual(output["code"], "PDF105")
        self.assertEqual(output["linter"], "pydocformatter")
        self.assertEqual(output["fix"], "Fix is not available.")
        self.assertEqual(output["fix_availability"], "Never")
        self.assertEqual(output["status"], {"Stable": {"since": "v0.3.0"}})
        self.assertTrue(output["explanation"].startswith("## What it does\n"))
        self.assertNotIn("# summary-too-long (PDF105)", output["explanation"])
        self.assertNotIn("Fix is not available.", output["explanation"])
        self.assertIn("## Ruff compatibility\n", output["explanation"])
        self.assertTrue(output["source_location"]["file"].endswith("PDF105_summary_too_long.py"))

    def test_pydocfmt_rule_prints_all_rules(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "--all"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("# standalone-comment-too-long (PCF001)\n", output)
        self.assertIn("# docstring-should-be-one-line (PDF106)\n", output)
        self.assertLess(output.index("# standalone-comment-too-long (PCF001)"), output.index("# reflow-required (PDF001)"))

    def test_pydocfmt_rule_prints_all_rules_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "rule", "--output-format", "json", "--all"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        output = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(output[0]["code"], "PCF001")
        self.assertEqual(output[-1]["code"], "PDF106")

    def test_pydocfmt_rule_rejects_missing_rule(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["pydocfmt", "rule"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Must specify RULE or --all", stderr.getvalue())

    def test_pydocfmt_rule_rejects_unknown_rule(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["pydocfmt", "rule", "BAD999"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Invalid value 'BAD999'", stderr.getvalue())

    def test_pydocfmt_rule_rejects_rule_with_all(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["pydocfmt", "rule", "PDF001", "--all"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("RULE cannot be used with --all", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
