import collections
import contextlib
import dataclasses
import inspect
import os
import tempfile
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path

import pydocformatter.cli.check as check_command
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.formatter as formatter
import pydocformatter.formatters.pydocfmt as pydocfmt
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.formatter import FormatterResult, RuleFinding
from pydocformatter.rules.base import RuleCode, RuleMetadata

PDF001_RULE = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fixable=True, stable_since="0.3.0")
PDF105_RULE = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fixable=False, stable_since="0.3.0")
PCF100_RULE = RuleMetadata(code=RuleCode("PCF100"), name="comment-formatting-needed", message="Comment needs formatting", fixable=True, stable_since="0.3.0")


class TestFormatterResults(unittest.TestCase):
    def test_formatter_result_field_order_has_no_defaults(self) -> None:
        fields = dataclasses.fields(FormatterResult)

        self.assertEqual(tuple(field.name for field in fields), ("path", "old_source", "new_source", "modified", "fixed_findings", "unfixed_findings", "errors"))
        self.assertTrue(all(field.default is dataclasses.MISSING for field in fields))
        self.assertTrue(all(field.default_factory is dataclasses.MISSING for field in fields))

    def test_experimental_file_formatter_write_has_no_default(self) -> None:
        signature = inspect.signature(formatter.format_file_exp)

        self.assertIs(signature.parameters["write"].default, inspect.Parameter.empty)

    def test_formatter_result_tracks_modified_and_findings_explicitly(self) -> None:
        clean = FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
        modified = FormatterResult(path="a.py", old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())
        finding = RuleFinding(
            rule=RuleMetadata(
                code=RuleCode("PDF105"),
                name="summary-too-long",
                message="Docstring summary does not fit on one line",
                fixable=False,
                stable_since="0.3.0",
            ),
            line_numbers=(3,),
        )
        with_findings = FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(finding,), errors=())

        self.assertFalse(clean.modified)
        self.assertEqual(clean.unfixed_findings, ())
        self.assertEqual(clean.old_source, "")
        self.assertEqual(clean.new_source, "")
        self.assertEqual(clean.fixed_findings, collections.Counter())
        self.assertTrue(modified.modified)
        self.assertEqual(modified.fixed_findings, collections.Counter({PDF001_RULE: 1}))
        self.assertEqual(with_findings.unfixed_findings, (finding,))

    def test_rule_finding_uses_rule_defaults_with_per_finding_overrides(self) -> None:
        rule = RuleMetadata(
            code=RuleCode("PDF001"),
            name="reflow-required",
            message="Docstring chunk needs reflow",
            fixable=True,
            stable_since="0.3.0",
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

    def test_rule_metadata_and_finding_keys_are_sortable(self) -> None:
        later_rule = RuleMetadata(code=RuleCode("PDF999"), name="later", message="Later", fixable=True, stable_since="0.3.0")

        self.assertEqual(sorted((later_rule, PDF001_RULE)), [PDF001_RULE, later_rule])
        self.assertTrue(dataclasses.is_dataclass(RuleFinding.Key))
        self.assertEqual(
            sorted((RuleFinding.Key(rule=later_rule, message="Later", fixable=True), RuleFinding.Key(rule=PDF001_RULE, message="Docstring chunk needs reflow", fixable=True))),
            [RuleFinding.Key(rule=PDF001_RULE, message="Docstring chunk needs reflow", fixable=True), RuleFinding.Key(rule=later_rule, message="Later", fixable=True)],
        )

    def test_grouped_output_merges_matching_findings_and_prints_summary(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(
                RuleFinding(rule=PDF001_RULE, line_numbers=(2, 2, 3)),
                RuleFinding(rule=PDF105_RULE, line_numbers=(5,)),
                RuleFinding(rule=PDF001_RULE, line_numbers=(8,)),
            ),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PDF001* Docstring chunk needs reflow. Lines 2-3, 8",
                "  PDF105 Docstring summary does not fit on one line. Line 5",
                "",
                "Found 3 rule check errors (2 fixable).",
            ],
        )

    def test_grouped_output_prints_fixed_findings_before_unfixed_findings(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=True,
            fixed_findings=collections.Counter({PDF001_RULE: 50, PCF100_RULE: 1}),
            unfixed_findings=(RuleFinding(rule=PDF105_RULE, line_numbers=(5,)),),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PCF100* Comment needs formatting. Fixed 1 time.",
                "  PDF001* Docstring chunk needs reflow. Fixed 50 times.",
                "  PDF105 Docstring summary does not fit on one line. Line 5",
                "",
                "Fixed 51 rule check errors and left 1 more unfixed (0 fixable).",
            ],
        )

    def test_grouped_output_reports_fixed_findings_for_clean_results(self) -> None:
        result = FormatterResult(path="a.py", old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PDF001* Docstring chunk needs reflow. Fixed 1 time.",
                "",
                "Fixed 1 rule check error.",
            ],
        )

    def test_grouped_output_prints_success_message_for_clean_results(self) -> None:
        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped(
                [], [FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())], output=None
            )

        self.assertEqual(output.getvalue(), "All checks passed!\n")

    def test_grouped_output_prints_errors_without_success_message(self) -> None:
        result = FormatterResult(path="a.py", old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=("Failed to read file a.py",))

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped(["Using standard input instead of input path: b.py"], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "ERROR: Using standard input instead of input path: b.py",
                "ERROR: Failed to read file a.py",
                "",
                "Found 2 operational errors.",
            ],
        )

    def test_grouped_output_summary_counts_findings_and_operational_errors(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source=None,
            new_source=None,
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(RuleFinding(rule=PDF001_RULE, line_numbers=(2,)),),
            errors=("Failed to read file a.py",),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped(["Using standard input instead of input path: b.py"], [result], output=None)

        self.assertEqual(output.getvalue().splitlines()[-3:], ["", "Found 2 operational errors.", "Found 1 rule check error (1 fixable)."])

    def test_diff_summary_reports_fixed_and_remaining_findings(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=True,
            fixed_findings=collections.Counter({PDF001_RULE: 2}),
            unfixed_findings=(RuleFinding(rule=PDF105_RULE, line_numbers=(1,)),),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_diff_summary([], [result], output=None)

        self.assertEqual(output.getvalue(), "Would fix 2 rule check errors and leave 1 more unfixed (0 fixable).\n")

    def test_diff_summary_reports_remaining_findings_without_fixes(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(RuleFinding(rule=PDF001_RULE, line_numbers=(1,)), RuleFinding(rule=PDF105_RULE, line_numbers=(2,))),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_diff_summary([], [result], output=None)

        self.assertEqual(output.getvalue(), "Would leave 2 rule check errors unfixed (1 fixable).\n")

    def test_diff_summary_reports_operational_errors_separately(self) -> None:
        result = FormatterResult(path="a.py", old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=("Failed to read file a.py",))

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_diff_summary(["Using standard input instead of input path: b.py"], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "ERROR: Using standard input instead of input path: b.py",
                "ERROR: Failed to read file a.py",
                "",
                "Found 2 operational errors.",
            ],
        )

    def test_output_stream_does_not_convert_body_os_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_file = str(Path(td) / "errors.txt")

            with self.assertRaisesRegex(OSError, "Body failed"):
                with check_command.output_stream(output_file):
                    raise OSError("Body failed")

    def test_experimental_formatter_interface_is_noop_and_preserves_display_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                result = formatter.format_file_exp("a.py", settings=CheckSettings(experimental=True), fix=True, write=True)
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(result.path, "a.py")
            self.assertEqual(result.old_source, "x = 1\n")
            self.assertEqual(result.new_source, "x = 1\n")
            self.assertFalse(result.modified)
            self.assertEqual(result.unfixed_findings, ())
            self.assertEqual(target.read_text(encoding="utf-8"), "x = 1\n")

    def test_experimental_file_formatter_delegates_to_source_formatter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_args: list[tuple[str, str, bool]] = []

            def fake_format_source_exp(source: str, path: str, settings: CheckSettings, fix: bool) -> FormatterResult:
                called_args.append((source, path, fix))
                return FormatterResult(path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            with unittest.mock.patch("pydocformatter.formatter.format_source_exp", side_effect=fake_format_source_exp):
                result = formatter.format_file_exp(str(target), settings=CheckSettings(experimental=True), fix=False, write=True)

        self.assertEqual(called_args, [("x = 1\n", str(target), False)])
        self.assertEqual(result.path, str(target))
        self.assertEqual(result.new_source, "x = 1\n")
        self.assertFalse(result.modified)

    def test_experimental_file_formatter_writes_modified_fix_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_source_exp(source: str, path: str, settings: CheckSettings, fix: bool) -> FormatterResult:
                del source
                return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

            with unittest.mock.patch("pydocformatter.formatter.format_source_exp", side_effect=fake_format_source_exp):
                result = formatter.format_file_exp(str(target), settings=CheckSettings(experimental=True), fix=True, write=True)

            self.assertEqual(result.new_source, "x = 2\n")
            self.assertEqual(result.old_source, "x = 1\n")
            self.assertTrue(result.modified)
            self.assertEqual(target.read_text(encoding="utf-8"), "x = 2\n")

    def test_experimental_file_formatter_can_skip_modified_fix_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_source_exp(source: str, path: str, settings: CheckSettings, fix: bool) -> FormatterResult:
                del source, settings, fix
                return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

            with unittest.mock.patch("pydocformatter.formatter.format_source_exp", side_effect=fake_format_source_exp):
                result = formatter.format_file_exp(str(target), settings=CheckSettings(experimental=True), fix=True, write=False)

            self.assertEqual(result.new_source, "x = 2\n")
            self.assertEqual(result.old_source, "x = 1\n")
            self.assertTrue(result.modified)
            self.assertEqual(target.read_text(encoding="utf-8"), "x = 1\n")

    def test_experimental_file_formatter_reports_file_io_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = str(Path(td) / "missing.py")
            result = formatter.format_file_exp(missing, settings=CheckSettings(experimental=True), fix=False, write=True)

        self.assertIsNone(result.new_source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())
        self.assertEqual(len(result.errors), 1)
        self.assertIn(f"Failed to read file {missing}", result.errors[0])

    def test_format_files_exp_formats_each_received_path_without_deduplicating(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_paths: list[str] = []

            def fake_format_source_exp(source: str, path: str, settings: CheckSettings, fix: bool) -> FormatterResult:
                del source, settings, fix
                called_paths.append(path)
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with unittest.mock.patch("pydocformatter.formatter.format_source_exp", side_effect=fake_format_source_exp):
                    results = [formatter.format_file_exp(path, settings=CheckSettings(experimental=True), fix=True, write=True) for path in ("a.py", str(target))]
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(called_paths, ["a.py", str(target)])
        self.assertEqual([result.path for result in results], ["a.py", str(target)])

    def test_check_exit_status_depends_on_remaining_findings_not_modified_results(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file_exp(path: str, *, file: object = None, settings: CheckSettings, fix: bool, write: bool) -> FormatterResult:
                del file, settings, fix, write
                return FormatterResult(path=path, old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

            argv = ["pydocfmt", "check", "--experimental", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file_exp", side_effect=fake_format_file_exp),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)

    def test_exit_zero_suppresses_remaining_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            rule = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fixable=False, stable_since="0.3.0")

            def fake_format_file_exp(path: str, *, file: object = None, settings: CheckSettings, fix: bool, write: bool) -> FormatterResult:
                del file, settings, fix, write
                return FormatterResult(
                    path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,)),), errors=()
                )

            argv = ["pydocfmt", "check", "--experimental", "--exit-zero", str(target)]
            stdout = StringIO()
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file_exp", side_effect=fake_format_file_exp),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)

    def test_errors_affect_exit_status_without_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file_exp(path: str, *, file: object = None, settings: CheckSettings, fix: bool, write: bool) -> FormatterResult:
                del file, settings, fix, write
                return FormatterResult(path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=("Failed to read file",))

            for extra_args, expected_exit_code in (([], 1), (["--exit-zero"], 0)):
                argv = ["pydocfmt", "check", "--experimental", *extra_args, str(target)]
                stdout = StringIO()
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch("pydocformatter.formatter.format_file_exp", side_effect=fake_format_file_exp),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = pydocfmt_cli.main()

                self.assertEqual(exit_code, expected_exit_code)
                self.assertNotIn("All checks passed!", stdout.getvalue())

    def test_fix_mode_exits_nonzero_for_remaining_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            rule = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fixable=False, stable_since="0.3.0")

            def fake_format_file_exp(path: str, *, file: object = None, settings: CheckSettings, fix: bool, write: bool) -> FormatterResult:
                del file, settings, fix, write
                return FormatterResult(
                    path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,)),), errors=()
                )

            argv = ["pydocfmt", "check", "--experimental", "--fix", str(target)]
            stdout = StringIO()
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file_exp", side_effect=fake_format_file_exp),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 1)

    def test_exit_non_zero_on_fix_reports_modified_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file_exp(path: str, *, file: object = None, settings: CheckSettings, fix: bool, write: bool) -> FormatterResult:
                del file, settings, fix, write
                return FormatterResult(path=path, old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

            for extra_args, expected_exit_code in ((["--fix"], 0), (["--fix", "--exit-non-zero-on-fix"], 1)):
                argv = ["pydocfmt", "check", "--experimental", *extra_args, str(target)]
                with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("pydocformatter.formatter.format_file_exp", side_effect=fake_format_file_exp):
                    exit_code = pydocfmt_cli.main()

                self.assertEqual(exit_code, expected_exit_code)

    def test_legacy_check_result_uses_synthetic_finding_for_needed_formatting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            source_result = pydocfmt.SourceFormatResult(source="x = 1\n", docstring_changed_lines=(3, 1), comment_changed_lines=(5, 3))
            with unittest.mock.patch("pydocformatter.cli.check.pydocfmt.format_file_source", return_value=source_result):
                results = check_command.format_files((str(target),), settings=CheckSettings(), fix=False, write=True)

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].modified)
        self.assertEqual(len(results[0].unfixed_findings), 1)
        self.assertEqual(results[0].unfixed_findings[0].rule.code.tag, "PDF000")
        self.assertEqual(results[0].unfixed_findings[0].line_numbers, (1, 3, 5))

    def test_legacy_check_result_uses_zero_line_fallback_for_missing_changed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            source_result = pydocfmt.SourceFormatResult(source="x = 1\n", docstring_changed_lines=(), comment_changed_lines=())
            with unittest.mock.patch.object(type(source_result), "modified", new_callable=unittest.mock.PropertyMock, return_value=True):
                with unittest.mock.patch("pydocformatter.cli.check.pydocfmt.format_file_source", return_value=source_result):
                    results = check_command.format_files((str(target),), settings=CheckSettings(), fix=False, write=True)

        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0].unfixed_findings), 1)
        self.assertEqual(results[0].unfixed_findings[0].line_numbers, (0,))

    def test_legacy_format_result_uses_modified_for_actual_writes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            source_result = pydocfmt.SourceFormatResult(source="x = 1\n", docstring_changed_lines=(1,), comment_changed_lines=())
            with unittest.mock.patch("pydocformatter.cli.check.pydocfmt.format_file_source", return_value=source_result):
                results = check_command.format_files((str(target),), settings=CheckSettings(), fix=True, write=True)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].modified)
        self.assertEqual(results[0].fixed_findings, collections.Counter({check_command.LEGACY_FORMAT_RULE_META: 1}))
        self.assertEqual(results[0].unfixed_findings, ())
