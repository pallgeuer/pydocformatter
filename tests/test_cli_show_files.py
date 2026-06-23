import collections
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path
from typing import Callable, TextIO, cast

import pytest

import pydocformatter.cli.check as check_command
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.cli.settings_check as settings_check
import pydocformatter.file_selection as file_selection
import pydocformatter.rules_selection as rules_selection
import pydocformatter.settings as settings_core
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.formatter import FormatterResult
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata
from pydocformatter.rules_selection import RuleSelection

PDF101_RULE = RuleMetadata(
    code=RuleCode("PDF101"), name="docstring-reflow", message="Docstring chunk needs reflow", fix_availability=FixAvailability.ALWAYS, stable_since="1.0.0", setting_effects=(), incompatible_with=()
)
PCF001_RULE = RuleMetadata(
    code=RuleCode("PCF001"),
    name="comment-formatting-needed",
    message="Comment needs formatting",
    fix_availability=FixAvailability.ALWAYS,
    stable_since="1.0.0",
    setting_effects=(),
    incompatible_with=(),
)


@pytest.mark.isolated_cwd
class TestCLIShowFiles(unittest.TestCase):
    @staticmethod
    def _profile(settings: CheckSettings) -> settings_core.SettingsProfile[CheckSettings]:
        """Return a minimal settings profile for CLI orchestration tests."""
        return settings_core.SettingsProfile(settings=settings, field_bases={}, field_priorities={})

    @staticmethod
    def _make_sample_tree() -> tempfile.TemporaryDirectory[str]:
        """Create a temporary tree with included, ignored, and non-Python files."""
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / "b.txt").write_text("not python\n", encoding="utf-8")
        (root / "skip.py").write_text("x = 2\n", encoding="utf-8")
        return temp_dir

    @staticmethod
    def _make_git_tree() -> tempfile.TemporaryDirectory[str]:
        """Create a temporary tree with a minimal git marker."""
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / "skip.py").write_text("x = 2\n", encoding="utf-8")
        return temp_dir

    @staticmethod
    def _fake_git_check_ignore_for_root(root: Path, ignored_paths: set[str]) -> Callable[..., subprocess.CompletedProcess[bytes]]:
        """Return a fake git check-ignore runner for a temporary root."""

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            expected_command = [
                "git",
                "-C",
                str(root),
                "check-ignore",
                "--stdin",
                "--no-index",
                "-z",
            ]
            assert args[0] == expected_command
            stdin_bytes = kwargs["input"]
            assert isinstance(stdin_bytes, bytes)
            provided_paths = [path for path in stdin_bytes.decode("utf-8").split("\0") if path]
            ignored = [path for path in provided_paths if path in ignored_paths]
            stdout = ("\0".join(ignored) + ("\0" if ignored else "")).encode("utf-8")
            return subprocess.CompletedProcess(expected_command, 0, stdout=stdout, stderr=b"")

        return fake_run

    def test_pydocfmt_show_files_lists_included_and_ignored_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                "check",
                str(root),
                "--show-files",
                "--include",
                "*.py",
                "--exclude",
                "skip.py",
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            expected_lines = [
                f"{root / 'a.py'} INCLUDED",
                f"{root / 'b.txt'} IGNORED: does not match include patterns",
                f"{root / 'skip.py'} IGNORED: matches exclude patterns",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [])

    def test_pydocfmt_defaults_to_current_directory_without_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            called_paths: list[str] = []

            def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix
                self.assertTrue(write)
                called_paths.append(os.path.abspath(path))
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                argv = ["pydocfmt", "check", "--fix", "--no-respect-gitignore", "--parallelism", "1"]
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.formatter.format_file",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(
                [Path(path) for path in called_paths],
                [root / "a.py", root / "skip.py"],
            )

    def test_pydocfmt_show_files_lists_pruned_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / ".venv").mkdir()
            (root / ".venv" / "ignored.py").write_text("x = 2\n", encoding="utf-8")
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", str(root), "--show-files"]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            expected_lines = [
                f"{root / '.venv'} IGNORED: matches exclude patterns",
                f"{root / 'a.py'} INCLUDED",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [])

    def test_pydocfmt_comma_separated_globs_per_include_and_exclude_option(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                "check",
                str(root),
                "--show-files",
                "--include",
                "*.py,*.txt",
                "--exclude",
                "skip.py,b.txt",
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            expected_lines = [
                f"{root / 'a.py'} INCLUDED",
                f"{root / 'b.txt'} IGNORED: matches exclude patterns",
                f"{root / 'skip.py'} IGNORED: matches exclude patterns",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [])

    def test_pydocfmt_multiple_globs_before_positional_path_after_separator(
        self,
    ) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                "check",
                "--show-files",
                "--include",
                "*.py,*.txt",
                "--exclude",
                "skip.py",
                "--",
                str(root),
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            expected_lines = [
                f"{root / 'a.py'} INCLUDED",
                f"{root / 'b.txt'} INCLUDED",
                f"{root / 'skip.py'} IGNORED: matches exclude patterns",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [])

    def test_pydocfmt_default_respects_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", "--show-files", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            expected_lines = [
                f"{root / 'a.py'} INCLUDED",
                f"{root / 'skip.py'} IGNORED: matches .gitignore",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [])

    def test_pydocfmt_no_respect_gitignore_disables_gitignore_filtering(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", "--show-files", "--no-respect-gitignore", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            self.assertFalse(run_mock.called)
            expected_lines = [
                f"{root / 'a.py'} INCLUDED",
                f"{root / 'skip.py'} INCLUDED",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [])

    def test_pydocfmt_show_files_with_rule_formatter_does_not_format(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            format_file = unittest.mock.Mock(
                return_value=FormatterResult(path=str(root / "a.py"), old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
            )
            argv = ["pydocfmt", "check", "--show-files", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    format_file,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            format_file.assert_not_called()
            self.assertIn(f"{root / 'a.py'} INCLUDED", stdout.getvalue().splitlines())

    def test_pydocfmt_show_files_reports_duplicate_paths_without_formatting(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            format_file = unittest.mock.Mock(return_value=False)
            argv = ["pydocfmt", "check", "--show-files", "a.py", str(root / "a.py")]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.formatter.format_file",
                        format_file,
                    ),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(exit_code, 0)
            format_file.assert_not_called()
            self.assertEqual(
                stdout.getvalue().splitlines(),
                [
                    f"{root / 'a.py'} INCLUDED",
                    f"{root / 'a.py'} IGNORED: duplicate path to already selected file",
                ],
            )

    def test_pydocfmt_removed_file_listing_option_is_rejected(self) -> None:
        stderr = StringIO()
        old_option = "--" + "ver" + "bose"
        argv = ["pydocfmt", "check", old_option]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            pydocfmt_cli.main()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn(f"unrecognized arguments: {old_option}", stderr.getvalue())

    def test_pydocfmt_hyphenated_pyproject_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 72\nrespect-gitignore = false\n",
                encoding="utf-8",
            )
            called_args: list[tuple[str, int, bool, str]] = []

            def fake_rule_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, rule_selection
                called_args.append((path, settings.line_length, fix, settings.output_format))
                self.assertTrue(write)
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            argv = ["pydocfmt", "check", "--fix", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                    unittest.mock.patch(
                        "pydocformatter.formatter.format_file",
                        side_effect=fake_rule_format,
                    ),
                ):
                    pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

            self.assertFalse(run_mock.called)
            self.assertEqual(called_args, [(str(root / "a.py"), 72, True, "grouped")])

    def test_pydocfmt_indent_cli_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            called_settings: list[tuple[str, int]] = []

            def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, rule_selection, fix
                self.assertTrue(write)
                called_settings.append((settings.indent_style, settings.indent_width))
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            argv = [
                "pydocfmt",
                "check",
                "--fix",
                "--indent-style",
                "tab",
                "--indent-width",
                "2",
                str(root / "a.py"),
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
            ):
                pydocfmt_cli.main()

            self.assertEqual(
                called_settings,
                [("tab", 2)],
            )

    def test_line_ending_cli_setting_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_settings: list[str] = []

            def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, rule_selection, fix
                self.assertTrue(write)
                called_settings.append(settings.line_ending)
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            argv = ["pydocfmt", "check", "--fix", "--line-ending", "cr-lf", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
            ):
                pydocfmt_cli.main()

            self.assertEqual(called_settings, ["cr-lf"])

    def test_rule_cli_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_settings: list[CheckSettings] = []

            def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, rule_selection, fix, write
                called_settings.append(settings)
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            argv = [
                "pydocfmt",
                "check",
                str(target),
                "--output-format",
                "grouped",
                "--select",
                "PCF,PDF",
                "--ignore",
                "PCF002,PDF101",
                "--fixable",
                "ALL",
                "--unfixable",
                "PCF001",
                "--per-file-ignores",
                '{"tests/*.py" = ["PCF001"]}',
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.rules_selection.select_rules", return_value=unittest.mock.Mock(errors=())),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(called_settings[0].select, ("PCF", "PDF"))
            self.assertEqual(called_settings[0].ignore, ("PCF002", "PDF101"))
            self.assertEqual(called_settings[0].fixable, ("ALL",))
            self.assertEqual(called_settings[0].unfixable, ("PCF001",))
            self.assertEqual(called_settings[0].per_file_ignores, (("tests/*.py", ("PCF001",)),))
            self.assertEqual(called_settings[0].output_format, "grouped")

    def test_invalid_rule_cli_selector_reports_operational_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(target), "--select", "BAD"]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: rule selection contains unknown selector: BAD", stdout.getvalue())
        self.assertNotIn("Traceback", stdout.getvalue())

    def test_invalid_rule_config_selector_reports_operational_error_once_for_equivalent_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\nselect = ["BAD999"]\n', encoding="utf-8")
            (root / "a").mkdir()
            (root / "b").mkdir()
            (root / "a" / "one.py").write_text("x = 1\n", encoding="utf-8")
            (root / "b" / "two.py").write_text("x = 2\n", encoding="utf-8")
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(root / "a"), str(root / "b"), "--no-respect-gitignore"]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue().count("ERROR: rule selection contains unknown selector: BAD999"), 1)
        self.assertNotIn("Traceback", stdout.getvalue())

    def test_force_exclude_filters_explicit_file_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                "check",
                str(target),
                "--show-files",
                "--force-exclude",
                "--exclude",
                "skip.py",
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            self.assertEqual(
                stdout.getvalue().splitlines(),
                [f"{target} IGNORED: matches exclude patterns"],
            )
            self.assertEqual(called_paths, [])

    def test_force_exclude_does_not_filter_explicit_file_by_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            target = root / "skip.py"
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", "--show-files", "--force-exclude", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ) as run_mock,
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            self.assertEqual(
                stdout.getvalue().splitlines(),
                [f"{target} INCLUDED"],
            )
            self.assertEqual(called_paths, [])
            run_mock.assert_not_called()

    def test_command_line_extend_exclude_overrides_config_extend_exclude(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.py"
            target.write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\n" 'include = ["*.py"]\n' "exclude = []\n" 'extend-exclude = ["skip.py"]\n',
                encoding="utf-8",
            )
            called_paths: list[str] = []

            def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix
                self.assertTrue(write)
                called_paths.append(path)
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            argv = [
                "pydocfmt",
                "check",
                "--fix",
                str(target),
                "--force-exclude",
                "--extend-exclude",
                "other.py",
            ]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.formatter.format_file",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(called_paths, [str(target)])

    def _assert_help_ignores_invalid_config(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
        """Assert that help output is available despite invalid local config."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            argv = [program, "--help"]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as cm,
                ):
                    main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(cm.exception.code, 0)
        self.assertIn("Usage:", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_pydocfmt_help_ignores_invalid_config(self) -> None:
        self._assert_help_ignores_invalid_config(pydocfmt_cli.main, "pydocfmt")

    def test_pydocfmt_check_help_ignores_invalid_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            argv = ["pydocfmt", "check", "--help"]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as cm,
                ):
                    pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(cm.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("Formatting:", output)
        self.assertIn("Rule selection:", output)
        self.assertIn("File selection:", output)
        options = output[output.index("Options:") : output.index("Formatting:")]
        formatting = output[output.index("Formatting:") : output.index("Rule selection:")]
        self.assertLess(options.index("--fix"), options.index("--diff"))
        self.assertLess(options.index("--diff"), options.index("--show-settings"))
        self.assertLess(options.index("--show-settings"), options.index("--show-rules"))
        self.assertLess(options.index("--show-rules"), options.index("--show-files"))
        self.assertLess(options.index("--show-files"), options.index("--output-file"))
        self.assertLess(formatting.index("--output-format"), formatting.index("--line-length"))
        self.assertLess(output.index("File selection:"), output.index("Miscellaneous:"))
        self.assertLess(output.index("Miscellaneous:"), output.index("Global options:"))
        self.assertIn("--output-file FILE", output)
        self.assertIn("--diff", output)
        self.assertIn("--stdin-filename FILENAME", output)
        self.assertIn("--config CONFIG", output)
        self.assertIn("--line-length LENGTH", output)
        self.assertIn("--indent-width WIDTH", output)
        self.assertIn("--per-file-ignores RULE_TOML", output)
        self.assertEqual(stderr.getvalue(), "")

    def test_pydocfmt_help_check_prints_check_help(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "help", "check"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: pydocfmt check", stdout.getvalue())

    def test_pydocfmt_config_lists_available_keys(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "config"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().splitlines(), [definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml])

    def test_pydocfmt_config_prints_option_details(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "config", "line-length"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Maximum line length for docstrings and comments.", output)
        self.assertIn("Default value: 88", output)
        self.assertIn("Type: int", output)
        self.assertIn("Example usage:\n```toml\nline-length = 88\n```", output)

    def test_pydocfmt_config_prints_option_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "config", "--output-format", "json", "line-ending"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["doc"], 'Line ending to use when rewriting files; one of "auto", "lf", "cr-lf", or "native".')
        self.assertEqual(output["default"], '"auto"')
        self.assertEqual(output["value_type"], '"auto" | "lf" | "cr-lf" | "native"')
        self.assertEqual(output["example"], 'line-ending = "auto"')
        self.assertNotIn("scope", output)
        self.assertNotIn("deprecated", output)

    def test_pydocfmt_config_prints_all_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "config", "--output-format", "json"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(tuple(output), tuple(definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml))
        self.assertEqual(output["line-length"]["default"], "88")
        self.assertEqual(output["docstring-convention"]["default"], '"pep257"')
        self.assertEqual(output["select"]["value_type"], "list[str]")
        self.assertEqual(output["per-file-ignores"]["value_type"], "dict[str, list[str]]")

    def test_pydocfmt_config_rejects_unknown_option(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["pydocfmt", "config", "unknown-key"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Invalid value 'unknown-key'", stderr.getvalue())

    def test_pydocfmt_config_rejects_invalid_output_format(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "config", "--output-format", "yaml"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            pydocfmt_cli.main()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("invalid choice: 'yaml'", stderr.getvalue())

    def test_pydocfmt_config_help_and_help_config_print_config_help(self) -> None:
        for argv in (["pydocfmt", "config", "--help"], ["pydocfmt", "help", "config"]):
            stdout = StringIO()
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                if argv[-1] == "--help":
                    with self.assertRaises(SystemExit) as cm:
                        pydocfmt_cli.main()
                    self.assertEqual(cm.exception.code, 0)
                else:
                    exit_code = pydocfmt_cli.main()
                    self.assertEqual(exit_code, 0)
            self.assertIn("Usage: pydocfmt config", stdout.getvalue())
            self.assertIn("--output-format {text,json}", stdout.getvalue())

    def test_pydocfmt_config_ignores_invalid_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            argv = ["pydocfmt", "config", "line-length"]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIn("Default value: 88", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_pydocfmt_version_flag_and_command_print_version(self) -> None:
        outputs = []
        for argv in (["pydocfmt", "--version"], ["pydocfmt", "version"]):
            stdout = StringIO()
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()
            self.assertEqual(exit_code, 0)
            outputs.append(stdout.getvalue())

        self.assertEqual(outputs[0], outputs[1])
        self.assertRegex(outputs[0], r"^pydocfmt \d+\.\d+\.\d+\n$")

    def test_pydocfmt_without_command_exits_with_usage_error(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Usage: pydocfmt", stderr.getvalue())

    def test_pydocfmt_top_level_check_flag_is_rejected(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "--check"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            pydocfmt_cli.main()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("unrecognized arguments: --check", stderr.getvalue())

    def test_pydocfmt_check_show_settings_prints_resolved_settings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 72\nrespect-gitignore = false\n",
                encoding="utf-8",
            )
            stdout = StringIO()
            argv = ["pydocfmt", "check", "--show-settings", "--line-ending", "lf"]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("[tool.pydocfmt]", output)
        self.assertLess(output.index("output-format"), output.index("line-length"))
        self.assertLess(output.index("line-length"), output.index("select"))
        self.assertLess(output.index("extend-fixable"), output.index("include"))
        self.assertIn("line-length = 72", output)
        self.assertIn('line-ending = "lf"', output)
        self.assertIn('convention = "pep257"', output)
        self.assertIn("respect-gitignore = false", output)

    def test_pydocfmt_check_show_rules_applies_conventions_and_manual_reenablements(self) -> None:
        def show_convention_rules(*args: str) -> tuple[int, tuple[str, ...], str]:
            stdout = StringIO()
            argv = ["pydocfmt", "--isolated", "check", "--show-rules", *args]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()
            output = stdout.getvalue()
            rules = tuple(line.split(maxsplit=1)[0].removesuffix("*") for line in output.splitlines() if line.startswith(("PDF201", "PDF106", "PDF107", "PDF108", "PDF109")))
            return exit_code, rules, output

        broad_expectations = {
            "none": (0, ("PDF106", "PDF109", "PDF201")),
            "google": (0, ("PDF106", "PDF109", "PDF201")),
            "numpy": (0, ("PDF109", "PDF201")),
            "rest": (0, ("PDF106", "PDF109", "PDF201")),
            "pep257": (0, ("PDF109", "PDF201")),
        }
        for convention, (expected_exit_code, expected_rules) in broad_expectations.items():
            with self.subTest(variation="broad", convention=convention):
                exit_code, rules, output = show_convention_rules("--docstring-convention", convention)
                self.assertEqual((exit_code, rules), (expected_exit_code, expected_rules))
                self.assertNotIn("has been disabled", output)

        for convention in broad_expectations:
            with self.subTest(variation="exact-extend-select", convention=convention):
                exit_code, rules, output = show_convention_rules("--docstring-convention", convention, "--extend-select", "PDF106,PDF107,PDF108,PDF109")
                self.assertEqual((exit_code, rules, output.count("has been disabled")), (1, ("PDF106", "PDF108", "PDF201"), 2))

        self.assertEqual(show_convention_rules("--docstring-convention", "google", "--extend-select", "PDF10")[:2], (0, ("PDF106", "PDF109", "PDF201")))
        self.assertEqual(show_convention_rules("--docstring-convention", "numpy", "--extend-select", "PDF10")[:2], (0, ("PDF109", "PDF201")))
        self.assertEqual(show_convention_rules("--docstring-convention", "google", "--select", "PDF107")[:2], (0, ("PDF107",)))
        exit_code, rules, output = show_convention_rules("--docstring-convention", "google", "--extend-select", "PDF107,PDF108", "--ignore", "PDF107")
        self.assertEqual((exit_code, rules, output.count("has been disabled")), (1, ("PDF106", "PDF108", "PDF201"), 1))

    def test_pydocfmt_check_config_file_prints_resolved_settings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            config_path.write_text(
                "line-length = 97\nrespect-gitignore = false\n",
                encoding="utf-8",
            )
            stdout = StringIO()
            argv = ["pydocfmt", "check", "--show-settings", "--config", str(config_path)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("line-length = 97", output)
        self.assertIn("respect-gitignore = false", output)

    def test_pydocfmt_check_config_options_work_before_and_after_command(self) -> None:
        stdout = StringIO()
        argv = [
            "pydocfmt",
            "--config",
            "line-length = 99",
            "check",
            "--show-settings",
            "--config",
            'line-ending = "lf"',
            "--line-length",
            "100",
        ]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("line-length = 100", output)
        self.assertIn('line-ending = "lf"', output)

    def test_pydocfmt_check_isolated_ignores_auto_discovered_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 72\n",
                encoding="utf-8",
            )
            stdout = StringIO()
            argv = ["pydocfmt", "check", "--show-settings", "--isolated", "--config", "line-length = 106"]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("line-length = 106", output)
        self.assertNotIn("line-length = 72", output)

    def test_pydocfmt_check_isolated_rejects_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            config_path.write_text("line-length = 97\n", encoding="utf-8")
            stderr = StringIO()
            argv = ["pydocfmt", "check", "--show-settings", "--isolated", "--config", str(config_path)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("--config=PATH", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_check_show_files_and_show_settings_are_mutually_exclusive(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "check", "--show-files", "--show-settings"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Cannot use more than one of {--show-settings, --show-rules, --show-files} together", stderr.getvalue())

    def test_pydocfmt_check_exit_flags_are_mutually_exclusive(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "check", "--exit-zero", "--exit-non-zero-on-fix"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            pydocfmt_cli.main()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("--exit-zero", stderr.getvalue())
        self.assertIn("--exit-non-zero-on-fix", stderr.getvalue())

    def _assert_invalid_command_line_include_reports_argument_error(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
        """Assert that an empty include CLI value reports an argument error."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            stderr = StringIO()
            argv = [program, "check", str(root), "--include", ""]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 2)
        self.assertIn("<argparse>.include must not contain empty strings", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_command_line_exclude_reports_argument_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            stderr = StringIO()
            argv = ["pydocfmt", "check", str(root), "--exclude", ""]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 2)
        self.assertIn("<argparse>.exclude must not contain empty strings", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_command_line_include_reports_argument_error(
        self,
    ) -> None:
        self._assert_invalid_command_line_include_reports_argument_error(
            pydocfmt_cli.main,
            "pydocfmt",
        )

    def _assert_directory_config_include_is_allowed(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
        """Assert that a Ruff-style directory include config value is accepted."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            stderr = StringIO()
            stdout = StringIO()
            argv = [program, "check", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "All checks passed!\n")
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_directory_config_include_is_allowed(self) -> None:
        self._assert_directory_config_include_is_allowed(
            pydocfmt_cli.main,
            "pydocfmt",
        )

    def test_pydocfmt_invalid_toml_reports_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt\n",
                encoding="utf-8",
            )
            stderr = StringIO()
            argv = ["pydocfmt", "check", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 2)
        self.assertIn("pydocfmt check: Configuration error", stderr.getvalue())
        self.assertIn("Failed to decode", stderr.getvalue())
        self.assertIn("pyproject.toml", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_nested_config_reports_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package = root / "package"
            package.mkdir()
            (package / "module.py").write_text("x = 1\n", encoding="utf-8")
            (package / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 0\n",
                encoding="utf-8",
            )
            stderr = StringIO()
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("pydocfmt check: Configuration error", stderr.getvalue())
        self.assertIn("line-length", stderr.getvalue())
        self.assertIn("greater than or equal to 1", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_show_files_invalid_nested_config_reports_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package = root / "package"
            package.mkdir()
            (package / "module.py").write_text("x = 1\n", encoding="utf-8")
            (package / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 0\n",
                encoding="utf-8",
            )
            stderr = StringIO()
            stdout = StringIO()
            argv = ["pydocfmt", "check", "--show-files", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("pydocfmt check: Configuration error", stderr.getvalue())
        self.assertIn("line-length", stderr.getvalue())
        self.assertIn("greater than or equal to 1", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_missing_explicit_file_reports_operational_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "missing.py"
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

        self.assertIn(f"ERROR: Failed to read file {target}", stdout.getvalue())
        self.assertNotIn("Traceback", stdout.getvalue())

    def test_pydocfmt_aborts_when_gitignore_check_fails(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            stderr = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: CheckSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", "--show-files", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    return_value=subprocess.CompletedProcess(["git"], 128, stdout=b"", stderr=b"fatal: broken git"),
                ),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn(f"pydocfmt check: File selection error: {root}: Unable to apply gitignore filtering: fatal: broken git", stderr.getvalue())
            self.assertEqual(called_paths, [])

    @staticmethod
    def _make_tree_with_invalid_utf8() -> tempfile.TemporaryDirectory[str]:
        """Create a temporary tree containing one valid file and one invalid UTF-8 file."""
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / "good.py").write_text("x = 1\n", encoding="utf-8")
        (root / "bad.py").write_bytes(b"\xff")
        return temp_dir

    def test_pydocfmt_skips_undecodable_utf8_file_with_operational_error(self) -> None:
        with self._make_tree_with_invalid_utf8() as td:
            root = Path(td)
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_cli.main()

            output = stdout.getvalue()
            self.assertIn(f"ERROR: Failed to decode {root / 'bad.py'} as UTF-8", output)

    def test_pydocfmt_check_mode_still_exits_nonzero_with_mixed_decode_inputs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "needs_fix.py").write_text(
                'def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n',
                encoding="utf-8",
            )
            (root / "bad.py").write_bytes(b"\xff")

            stdout = StringIO()
            argv = ["pydocfmt", "check", "--line-length", "72", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 1)
            output = stdout.getvalue()
            self.assertIn(f"ERROR: Failed to decode {root / 'bad.py'} as UTF-8", output)
            self.assertIn(f"{root / 'needs_fix.py'}:", output)
            self.assertIn("PDF101* Docstring chunk needs reflow. Line 2", output)

    def test_pydocfmt_check_prints_success_message_for_clean_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text('def foo():\n    """Do something."""\n    pass\n', encoding="utf-8")
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(target)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "All checks passed!\n")

    def test_pydocfmt_diff_prints_unified_diff_without_writing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            original_source = "x = 1\n"
            formatted_source = "x = 2\n"
            target.write_text(original_source, encoding="utf-8")
            stdout = StringIO()
            rule = RuleMetadata(
                code=RuleCode("PDF110"),
                name="summary-too-long",
                message="Docstring summary does not fit on one line",
                fix_availability=FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
            )
            called_args: list[tuple[bool, bool]] = []

            def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del path, file, settings, rule_selection
                called_args.append((fix, write))
                return FormatterResult(
                    path=str(target),
                    old_source=original_source,
                    new_source=formatted_source,
                    modified=True,
                    fixed_findings=collections.Counter({PDF101_RULE: 1}),
                    unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,)),),
                    errors=(),
                )

            argv = ["pydocfmt", "check", "--diff", str(target)]

            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 1)
            self.assertEqual(called_args, [(True, False)])
            self.assertEqual(target.read_text(encoding="utf-8"), original_source)
            output = stdout.getvalue()
            self.assertTrue(output.startswith("Would fix 1 rule check error and leave 1 more unfixed (0 fixable).\n\n"))
            self.assertIn(f"\n--- {target}", output)
            self.assertIn(f"+++ {target}", output)
            self.assertIn("-x = 1", output)
            self.assertIn("+x = 2", output)
            self.assertNotIn("PDF110", output)

    def test_parallelism_resolution_uses_cpu_count(self) -> None:
        with unittest.mock.patch("pydocformatter.cli.check.os.cpu_count", return_value=8):
            self.assertEqual(check_command.resolve_parallelism(0.0), 8)
            self.assertEqual(check_command.resolve_parallelism(0.25), 2)
            self.assertEqual(check_command.resolve_parallelism(2.0), 2)

    def test_parallelism_resolution_rejects_non_whole_values_above_one(self) -> None:
        with self.assertRaisesRegex(settings_core.SettingsError, "whole number"):
            check_command.resolve_parallelism(1.5)

    def test_format_selected_files_caps_windows_workers_at_process_pool_limit(self) -> None:
        profile = self._profile(CheckSettings(parallelism=0.0))
        selected_files = tuple(file_selection.SelectedFile(path=f"{index}.py", profile=profile) for index in range(62))
        rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}
        created_max_workers: list[int | None] = []

        class FakeFuture:
            def __init__(self, result: FormatterResult) -> None:
                self._result = result

            def result(self) -> FormatterResult:
                return self._result

        class FakeExecutor:
            def __init__(self, max_workers: int | None = None) -> None:
                created_max_workers.append(max_workers)

            def __enter__(self) -> "FakeExecutor":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def submit(self, fn: object, request: check_command._SelectedFileFormatRequest, **kwargs: object) -> FakeFuture:
                del fn, kwargs
                return FakeFuture(FormatterResult(path=request.selected_file.path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=()))

        with (
            unittest.mock.patch("pydocformatter.cli.check.os.cpu_count", return_value=128),
            unittest.mock.patch("pydocformatter.cli.check.sys.platform", "win32"),
            unittest.mock.patch("pydocformatter.cli.check.concurrent.futures.as_completed", side_effect=lambda futures: tuple(futures)),
        ):
            check_command.format_selected_files(
                selected_files,
                rule_selections=rule_selections,
                use_stdin=False,
                fix=False,
                write=True,
                parallelism=0.0,
                executor_factory=cast(check_command._ExecutorFactory, FakeExecutor),
            )

        self.assertEqual(created_max_workers, [61])

    def test_format_selected_files_preserves_selected_order_when_parallel_results_complete_out_of_order(self) -> None:
        profile = self._profile(CheckSettings(parallelism=2.0))
        selected_files = (
            file_selection.SelectedFile(path="a.py", profile=profile),
            file_selection.SelectedFile(path="b.py", profile=profile),
            file_selection.SelectedFile(path="c.py", profile=profile),
        )
        rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}
        completion_order: list[str] = []

        class FakeFuture:
            def __init__(self, result: FormatterResult) -> None:
                self._result = result

            def result(self) -> FormatterResult:
                completion_order.append(self._result.path)
                return self._result

        class FakeExecutor:
            def __init__(self, max_workers: int | None = None) -> None:
                self.max_workers = max_workers

            def __enter__(self) -> "FakeExecutor":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def submit(self, fn: object, request: check_command._SelectedFileFormatRequest, **kwargs: object) -> FakeFuture:
                del fn, kwargs
                return FakeFuture(FormatterResult(path=request.selected_file.path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=()))

        with unittest.mock.patch("pydocformatter.cli.check.concurrent.futures.as_completed", side_effect=lambda futures: reversed(tuple(futures))):
            results = check_command.format_selected_files(
                selected_files,
                rule_selections=rule_selections,
                use_stdin=False,
                fix=False,
                write=True,
                parallelism=2.0,
                executor_factory=cast(check_command._ExecutorFactory, FakeExecutor),
            )

        self.assertEqual(completion_order, ["c.py", "b.py", "a.py"])
        self.assertEqual([result.path for result in results], ["a.py", "b.py", "c.py"])

    def test_format_selected_files_runs_real_process_pool_for_disk_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / "a.py"
            second = root / "b.py"
            first.write_text("x = 1\n", encoding="utf-8")
            second.write_text("y = 2\n", encoding="utf-8")
            profile = self._profile(CheckSettings(parallelism=2.0))
            selected_files = (
                file_selection.SelectedFile(path=str(first), profile=profile),
                file_selection.SelectedFile(path=str(second), profile=profile),
            )
            rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}

            results = check_command.format_selected_files(
                selected_files,
                rule_selections=rule_selections,
                use_stdin=False,
                fix=False,
                write=True,
                parallelism=2.0,
            )

        self.assertEqual([result.path for result in results], [str(first), str(second)])
        self.assertEqual([result.errors for result in results], [(), ()])

    def test_format_selected_files_keeps_single_disk_file_sequential(self) -> None:
        profile = self._profile(CheckSettings(parallelism=2.0))
        selected_files = (file_selection.SelectedFile(path="a.py", profile=profile),)
        rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}

        with (
            unittest.mock.patch("pydocformatter.cli.check.concurrent.futures.ProcessPoolExecutor", side_effect=AssertionError("single file must not use executor")),
            unittest.mock.patch(
                "pydocformatter.formatter.format_file",
                return_value=FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=()),
            ) as format_file,
        ):
            results = check_command.format_selected_files(
                selected_files,
                rule_selections=rule_selections,
                use_stdin=False,
                fix=False,
                write=True,
                parallelism=2.0,
            )

        self.assertEqual([result.path for result in results], ["a.py"])
        format_file.assert_called_once()

    def test_format_selected_files_keeps_stdin_sequential(self) -> None:
        profile = self._profile(CheckSettings(parallelism=2.0))
        selected_files = (file_selection.SelectedFile(path="-", profile=profile),)
        rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}

        with (
            unittest.mock.patch("pydocformatter.cli.check.concurrent.futures.ProcessPoolExecutor", side_effect=AssertionError("stdin must not use executor")),
            unittest.mock.patch(
                "pydocformatter.formatter.format_file",
                return_value=FormatterResult(path="-", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=()),
            ) as format_file,
        ):
            results = check_command.format_selected_files(
                selected_files,
                rule_selections=rule_selections,
                use_stdin=True,
                fix=False,
                write=True,
                parallelism=2.0,
            )

        self.assertEqual([result.path for result in results], ["-"])
        self.assertIs(format_file.call_args.kwargs["file"], sys.stdin)

    def test_pydocfmt_diff_exit_zero_suppresses_diff_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()

            def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

            argv = ["pydocfmt", "check", "--diff", "--exit-zero", str(target)]

            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue(stdout.getvalue().startswith("Would fix 1 rule check error.\n\n"))

    def test_pydocfmt_clean_diff_prints_success_message(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()

            argv = ["pydocfmt", "check", "--diff", str(target)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "All checks passed!\n")

    def test_pydocfmt_diff_output_file_writes_summary_without_diff(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            output_file = root / "reports" / "errors.txt"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()

            def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(
                    path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1, PCF001_RULE: 2}), unfixed_findings=(), errors=()
                )

            argv = ["pydocfmt", "check", "--diff", "--output-file", str(output_file), str(target)]

            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 1)
            self.assertTrue(stdout.getvalue().startswith(f"\n--- {target}"))
            self.assertNotIn("Would fix", stdout.getvalue())
            self.assertEqual(output_file.read_text(encoding="utf-8"), "Would fix 3 rule check errors.\n")

    def test_pydocfmt_clean_diff_output_file_writes_success_message(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            output_file = root / "reports" / "errors.txt"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()

            argv = ["pydocfmt", "check", "--diff", "--output-file", str(output_file), str(target)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(output_file.read_text(encoding="utf-8"), "All checks passed!\n")

    def test_pydocfmt_diff_stdin_uses_stdin_filename_in_diff_headers(self) -> None:
        source = "x = 1\n"
        stdout = StringIO()

        def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del settings, rule_selection, fix, write
            assert file is not None
            assert file.read() == source
            return FormatterResult(path=path, old_source=source, new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", "--diff", "--stdin-filename", "virtual.py"]

        with (
            unittest.mock.patch("sys.argv", argv),
            unittest.mock.patch("sys.stdin", StringIO(source)),
            unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("--- virtual.py", stdout.getvalue())
        self.assertIn("+++ virtual.py", stdout.getvalue())

    def test_pydocfmt_stdin_filename_sets_display_path_and_ignores_paths(self) -> None:
        source = 'def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n'
        stdout = StringIO()
        stderr = StringIO()
        called_paths: list[str] = []

        def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del settings, rule_selection, fix, write
            called_paths.append(path)
            assert file is not None
            assert file.read() == source
            return FormatterResult(path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "ignored.py", "--stdin-filename", "virtual.py", "--line-length", "72"]

        with (
            unittest.mock.patch("sys.argv", argv),
            unittest.mock.patch("sys.stdin", StringIO(source)),
            unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(called_paths, ["virtual.py"])
        self.assertIn("ERROR: Using standard input instead of input path: ignored.py", stdout.getvalue())
        self.assertNotIn("All checks passed!", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_pydocfmt_stdin_filename_force_exclude_filters_by_exclude(self) -> None:
        stdout = StringIO()
        argv = [
            "pydocfmt",
            "check",
            "--show-files",
            "--stdin-filename",
            "skip.py",
            "--force-exclude",
            "--exclude",
            "skip.py",
        ]

        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().splitlines(), ["skip.py IGNORED: matches exclude patterns"])

    def test_pydocfmt_stdin_filename_force_exclude_does_not_format_excluded_path(self) -> None:
        source = "def foo():\n    pass\n"
        stdout = StringIO()
        stderr = StringIO()
        format_file = unittest.mock.Mock(
            return_value=FormatterResult(path="skip.py", old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
        )
        argv = [
            "pydocfmt",
            "check",
            "--stdin-filename",
            "skip.py",
            "--force-exclude",
            "--exclude",
            "skip.py",
        ]

        with (
            unittest.mock.patch("sys.argv", argv),
            unittest.mock.patch("sys.stdin", StringIO(source)),
            unittest.mock.patch("pydocformatter.formatter.format_file", format_file),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        format_file.assert_not_called()
        self.assertEqual(stdout.getvalue(), "All checks passed!\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_pydocfmt_stdin_filename_force_exclude_filters_by_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            argv = ["pydocfmt", "check", "--show-files", "--stdin-filename", "skip.py", "--force-exclude"]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.file_selection.subprocess.run",
                        side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                    ),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = pydocfmt_cli.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().splitlines(), [f"{root / 'skip.py'} INCLUDED"])

    def test_pydocfmt_fix_stdin_writes_formatted_source_to_stdout(self) -> None:
        source = 'def foo():\n    """Does something.\n\nArgs:\n    x (int): some parameter.\n    """\n    pass\n'
        formatted_source = 'def foo():\n    """Does something.\n\n    Args:\n        x (int): some parameter.\n    """\n    pass\n'
        stdout = StringIO()
        stderr = StringIO()

        def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del path, settings, rule_selection
            assert fix
            assert write
            assert file is not None
            assert file.read() == source
            return FormatterResult(path="-", old_source=source, new_source=formatted_source, modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", "-", "--line-length", "72"]

        with (
            unittest.mock.patch("sys.argv", argv),
            unittest.mock.patch("sys.stdin", StringIO(source)),
            unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), formatted_source)
        self.assertEqual(stderr.getvalue(), "-:\n  PDF101* Docstring chunk needs reflow. Fixed 1 time.\n\nFixed 1 rule check error.\n")

    def test_pydocfmt_fix_stdin_with_output_file_writes_diagnostics_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_file = root / "reports" / "errors.txt"
            source = 'def foo():\n    """Does something."""\n    pass\n'
            formatted_source = 'def foo():\n    """Does something better."""\n    pass\n'
            stdout = StringIO()
            stderr = StringIO()

            def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del path, settings, rule_selection
                assert fix
                assert write
                assert file is not None
                assert file.read() == source
                return FormatterResult(path="-", old_source=source, new_source=formatted_source, modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

            argv = ["pydocfmt", "check", "--fix", "-", "--line-length", "72", "--output-file", str(output_file)]

            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("sys.stdin", StringIO(source)),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), formatted_source)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(output_file.read_text(encoding="utf-8"), "-:\n  PDF101* Docstring chunk needs reflow. Fixed 1 time.\n\nFixed 1 rule check error.\n")

    def test_pydocfmt_output_file_redirects_check_errors_and_creates_parent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text('def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n', encoding="utf-8")
            output_file = root / "reports" / "errors.txt"
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(target), "--line-length", "72", "--select", "PDF101", "--output-file", str(output_file)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            output = output_file.read_text(encoding="utf-8")
            self.assertIn(f"{target}:", output)
            self.assertIn("PDF101* Docstring chunk needs reflow. Line 2", output)
            self.assertIn("Found 1 rule check error (1 fixable).", output)

    def test_pydocfmt_output_file_redirects_operational_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "missing.py"
            output_file = root / "reports" / "errors.txt"
            stdout = StringIO()
            stderr = StringIO()
            argv = ["pydocfmt", "check", str(target), "--output-file", str(output_file)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "")
            output = output_file.read_text(encoding="utf-8")
            self.assertIn(f"ERROR: Failed to read file {target}", output)
            self.assertIn("Found 1 operational error.", output)

    def test_pydocfmt_output_file_redirects_clean_check_success_message(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text('def foo():\n    """Do something."""\n    pass\n', encoding="utf-8")
            output_file = root / "reports" / "errors.txt"
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(target), "--output-file", str(output_file)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(output_file.read_text(encoding="utf-8"), "All checks passed!\n")

    def test_pydocfmt_output_file_does_not_create_nested_parents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text('def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n', encoding="utf-8")
            output_file = root / "reports" / "nested" / "errors.txt"
            stderr = StringIO()
            argv = ["pydocfmt", "check", str(target), "--line-length", "72", "--output-file", str(output_file)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 2)
            self.assertFalse((root / "reports").exists())
            self.assertIn("pydocfmt check: Output error:", stderr.getvalue())

    def test_pydocfmt_output_file_redirects_show_output(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            output_file = root / "reports" / "show-files.txt"
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(root), "--show-files", "--include", "*.py", "--exclude", "skip.py", "--output-file", str(output_file)]

            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(
                output_file.read_text(encoding="utf-8").splitlines(),
                [
                    f"{root / 'a.py'} INCLUDED",
                    f"{root / 'b.txt'} IGNORED: does not match include patterns",
                    f"{root / 'skip.py'} IGNORED: matches exclude patterns",
                ],
            )

    def test_pydocfmt_stdin_filename_is_allowed_with_show_files(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "check", "--show-files", "--stdin-filename", "virtual.py"]

        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().splitlines(), ["virtual.py INCLUDED"])

    def test_pydocfmt_stdin_filename_is_allowed_with_show_settings(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "check", "--show-settings", "--stdin-filename", "virtual.py"]

        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("[tool.pydocfmt]", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
