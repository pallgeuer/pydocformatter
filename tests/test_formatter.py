import contextlib
import os
import tempfile
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path

import pydocformatter.cli.pydocfmt_main as pydocfmt_main
import pydocformatter.formatter as formatter
from pydocformatter.config import FormatterSettings
from pydocformatter.formatter import FormatterResult, Rule, RuleFinding


class TestFormatterResults(unittest.TestCase):
    def test_formatter_result_tracks_modified_and_findings_explicitly(self) -> None:
        clean = FormatterResult(path="a.py", modified=False, findings=())
        modified = FormatterResult(path="a.py", modified=True, findings=())
        finding = RuleFinding(
            rule=Rule(
                rule_code="PDF105",
                rule_name="summary-too-long",
                message="Docstring summary does not fit on one line",
                fixable=False,
            ),
            line_numbers=(3,),
        )
        with_findings = FormatterResult(path="a.py", modified=False, findings=(finding,))

        self.assertFalse(clean.modified)
        self.assertEqual(clean.findings, ())
        self.assertTrue(modified.modified)
        self.assertEqual(with_findings.findings, (finding,))

    def test_rule_finding_uses_rule_defaults_with_per_finding_overrides(self) -> None:
        rule = Rule(
            rule_code="PDF001",
            rule_name="reflow-required",
            message="Docstring chunk needs reflow",
            fixable=True,
        )

        default_finding = RuleFinding(rule=rule, line_numbers=(2,))
        overridden_finding = RuleFinding(
            rule=rule,
            line_numbers=(3,),
            instance_message="Custom message",
            instance_fixable=False,
        )

        self.assertEqual(default_finding.message, "Docstring chunk needs reflow")
        self.assertTrue(default_finding.fixable)
        self.assertEqual(overridden_finding.message, "Custom message")
        self.assertFalse(overridden_finding.fixable)

    def test_grouped_output_merges_matching_findings_and_prints_summary(self) -> None:
        reflow_rule = Rule(
            rule_code="PDF001",
            rule_name="reflow-required",
            message="Docstring chunk needs reflow",
            fixable=True,
        )
        summary_rule = Rule(
            rule_code="PDF105",
            rule_name="summary-too-long",
            message="Docstring summary does not fit on one line",
            fixable=False,
        )
        result = FormatterResult(
            path="a.py",
            modified=False,
            findings=(
                RuleFinding(rule=reflow_rule, line_numbers=(2, 2, 3)),
                RuleFinding(rule=summary_rule, line_numbers=(5,)),
                RuleFinding(rule=reflow_rule, line_numbers=(8,)),
            ),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            pydocfmt_main.print_results_grouped([result])

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PDF001* Docstring chunk needs reflow. Lines 2-3, 8",
                "  PDF105 Docstring summary does not fit on one line. Line 5",
                "",
                "Found 3 errors (2 fixable).",
            ],
        )

    def test_experimental_formatter_interface_is_noop_and_preserves_display_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                result = formatter.format_file_exp("a.py", FormatterSettings(experimental=True), check=False)
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(result.path, "a.py")
            self.assertFalse(result.modified)
            self.assertEqual(result.findings, ())
            self.assertEqual(target.read_text(encoding="utf-8"), "x = 1\n")

    def test_format_files_exp_deduplicates_by_physical_path_and_preserves_first_display_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_paths: list[str] = []

            def fake_format_file_exp(path: str, settings: FormatterSettings, check: bool) -> FormatterResult:
                called_paths.append(path)
                return FormatterResult(path=path, modified=False, findings=())

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with unittest.mock.patch("pydocformatter.formatter.format_file_exp", side_effect=fake_format_file_exp):
                    results = pydocfmt_main.format_files_exp(
                        ("a.py", str(target)),
                        FormatterSettings(experimental=True),
                        check=False,
                    )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(called_paths, ["a.py"])
        self.assertEqual([result.path for result in results], ["a.py"])

    def test_check_exit_status_depends_on_remaining_findings_not_modified_results(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file_exp(path: str, settings: FormatterSettings, check: bool) -> FormatterResult:
                return FormatterResult(path=path, modified=True, findings=())

            argv = ["pydocfmt", "--experimental", "--check", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file_exp", side_effect=fake_format_file_exp),
            ):
                exit_code = pydocfmt_main.main()

        self.assertEqual(exit_code, 0)

    def test_legacy_check_result_uses_synthetic_finding_for_needed_formatting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            with unittest.mock.patch("pydocformatter.cli.pydocfmt_main.pydocfmt.format_file", return_value=True):
                results = pydocfmt_main.format_files(
                    (str(target),),
                    FormatterSettings(),
                    check=True,
                )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].modified)
        self.assertEqual(len(results[0].findings), 1)
        self.assertEqual(results[0].findings[0].rule.rule_code, "000")
        self.assertEqual(results[0].findings[0].line_numbers, (0,))

    def test_legacy_format_result_uses_modified_for_actual_writes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            with unittest.mock.patch("pydocformatter.cli.pydocfmt_main.pydocfmt.format_file", return_value=True):
                results = pydocfmt_main.format_files(
                    (str(target),),
                    FormatterSettings(),
                    check=False,
                )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].modified)
        self.assertEqual(results[0].findings, ())
