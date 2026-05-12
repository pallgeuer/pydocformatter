import contextlib
import os
import subprocess
import tempfile
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path
from typing import Callable

import pydocformatter.cli.pydocfmt_main as pydocfmt_main
from pydocformatter.config import FormatterSettings
from pydocformatter.formatter import FormatterResult


class TestCliShowFiles(unittest.TestCase):
    @staticmethod
    def _make_sample_tree() -> tempfile.TemporaryDirectory[str]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / "b.txt").write_text("not python\n", encoding="utf-8")
        (root / "skip.py").write_text("x = 2\n", encoding="utf-8")
        return temp_dir

    @staticmethod
    def _make_git_tree() -> tempfile.TemporaryDirectory[str]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / "skip.py").write_text("x = 2\n", encoding="utf-8")
        return temp_dir

    @staticmethod
    def _fake_git_check_ignore_for_root(root: Path, ignored_paths: set[str]) -> Callable[..., subprocess.CompletedProcess[bytes]]:
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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
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
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(os.path.abspath(path))
                return False

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                argv = ["pydocfmt", "check", "--fix", "--no-respect-gitignore"]
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.cli.check.pydocfmt.format_file",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_main.main()
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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", str(root), "--show-files"]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
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
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
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
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
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
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", "--show-files", "--no-respect-gitignore", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                unittest.mock.patch(
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            self.assertFalse(run_mock.called)
            expected_lines = [
                f"{root / 'a.py'} INCLUDED",
                f"{root / 'skip.py'} INCLUDED",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [])

    def test_pydocfmt_show_files_with_check_does_not_format(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            format_file = unittest.mock.Mock(return_value=True)
            argv = ["pydocfmt", "check", "--show-files", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    format_file,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_main.main()

            self.assertEqual(exit_code, 0)
            format_file.assert_not_called()
            self.assertIn(f"{root / 'a.py'} INCLUDED", stdout.getvalue().splitlines())

    def test_pydocfmt_show_files_with_experimental_does_not_format(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            format_file_exp = unittest.mock.Mock(return_value=FormatterResult(path=str(root / "a.py"), modified=False, findings=()))
            argv = ["pydocfmt", "check", "--show-files", "--experimental", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file_exp",
                    format_file_exp,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_main.main()

            self.assertEqual(exit_code, 0)
            format_file_exp.assert_not_called()
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
                        "pydocformatter.cli.check.pydocfmt.format_file",
                        format_file,
                    ),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(exit_code, 0)
            format_file.assert_not_called()
            self.assertEqual(
                stdout.getvalue().splitlines(),
                [
                    "a.py INCLUDED",
                    "a.py IGNORED: duplicate path to already selected file",
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
            pydocfmt_main.main()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn(f"unrecognized arguments: {old_option}", stderr.getvalue())

    def test_pydocfmt_hyphenated_pyproject_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 72\nrespect-gitignore = false\nexperimental = true\n",
                encoding="utf-8",
            )
            legacy_called = False
            called_args: list[tuple[str, int, bool, bool, str]] = []

            def fake_format(path: str, settings: FormatterSettings, fix: bool) -> bool:
                nonlocal legacy_called
                legacy_called = True
                return False

            def fake_exp_format(path: str, settings: FormatterSettings, fix: bool) -> FormatterResult:
                called_args.append((path, settings.line_length, fix, settings.experimental, settings.output_format))
                return FormatterResult(path=path, modified=False, findings=())

            argv = ["pydocfmt", "check", "--fix", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                    unittest.mock.patch(
                        "pydocformatter.cli.check.pydocfmt.format_file",
                        side_effect=fake_format,
                    ),
                    unittest.mock.patch(
                        "pydocformatter.formatter.format_file_exp",
                        side_effect=fake_exp_format,
                    ),
                ):
                    pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertFalse(run_mock.called)
            self.assertFalse(legacy_called)
            self.assertEqual(called_args, [("a.py", 72, True, True, "grouped")])

    def test_pydocfmt_indent_cli_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            called_settings: list[tuple[str, int]] = []

            def fake_format(path: str, settings: FormatterSettings, fix: bool) -> bool:
                called_settings.append((settings.indent_style, settings.indent_width))
                return False

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
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
            ):
                pydocfmt_main.main()

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

            def fake_format(path: str, settings: FormatterSettings, fix: bool) -> bool:
                called_settings.append(settings.line_ending)
                return False

            argv = ["pydocfmt", "check", "--fix", "--line-ending", "cr-lf", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
            ):
                pydocfmt_main.main()

            self.assertEqual(called_settings, ["cr-lf"])

    def test_rule_cli_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_settings: list[FormatterSettings] = []

            def fake_format(path: str, settings: FormatterSettings, fix: bool) -> FormatterResult:
                called_settings.append(settings)
                return FormatterResult(path=path, modified=False, findings=())

            argv = [
                "pydocfmt",
                "check",
                str(target),
                "--experimental",
                "--output-format",
                "grouped",
                "--select",
                "PCF,PDF",
                "--ignore",
                "PCF002,PDF001",
                "--fixable",
                "ALL",
                "--unfixable",
                "PCF001",
                "--per-file-ignores",
                '{"tests/*.py" = ["PCF001"]}',
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.formatter.format_file_exp",
                    side_effect=fake_format,
                ),
            ):
                exit_code = pydocfmt_main.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(called_settings[0].select, ("PCF", "PDF"))
            self.assertEqual(called_settings[0].ignore, ("PCF002", "PDF001"))
            self.assertEqual(called_settings[0].fixable, ("ALL",))
            self.assertEqual(called_settings[0].unfixable, ("PCF001",))
            self.assertEqual(called_settings[0].per_file_ignores, (("tests/*.py", ("PCF001",)),))
            self.assertTrue(called_settings[0].experimental)
            self.assertEqual(called_settings[0].output_format, "grouped")

    def test_invalid_rule_cli_selector_reports_configuration_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stderr = StringIO()
            argv = ["pydocfmt", "check", str(target), "--select", "BAD"]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = pydocfmt_main.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("unknown selector: BAD", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_force_exclude_filters_explicit_file_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
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
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            self.assertEqual(
                stdout.getvalue().splitlines(),
                [f"{target} IGNORED: matches exclude patterns"],
            )
            self.assertEqual(called_paths, [])

    def test_force_exclude_filters_explicit_file_by_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            target = root / "skip.py"
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "check", "--show-files", "--force-exclude", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ),
                unittest.mock.patch(
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            self.assertEqual(
                stdout.getvalue().splitlines(),
                [f"{target} IGNORED: matches .gitignore"],
            )
            self.assertEqual(called_paths, [])

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

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

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
                        "pydocformatter.cli.check.pydocfmt.format_file",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(called_paths, ["skip.py"])

    def _assert_help_ignores_invalid_config(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
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
        self.assertIn("usage:", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_pydocfmt_help_ignores_invalid_config(self) -> None:
        self._assert_help_ignores_invalid_config(pydocfmt_main.main, "pydocfmt")

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
                    pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(cm.exception.code, 0)
        self.assertIn("Rule selection:", stdout.getvalue())
        self.assertIn("File selection:", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_pydocfmt_help_check_prints_check_help(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "help", "check"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = pydocfmt_main.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("usage: pydocfmt check", stdout.getvalue())

    def test_pydocfmt_version_flag_and_command_print_version(self) -> None:
        outputs = []
        for argv in (["pydocfmt", "--version"], ["pydocfmt", "version"]):
            stdout = StringIO()
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_main.main()
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
            exit_code = pydocfmt_main.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("usage: pydocfmt", stderr.getvalue())

    def test_pydocfmt_legacy_top_level_check_flag_is_rejected(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "--check"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            pydocfmt_main.main()

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
                    exit_code = pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("[tool.pydocfmt]", output)
        self.assertIn("line-length = 72", output)
        self.assertIn('line-ending = "lf"', output)
        self.assertIn("respect-gitignore = false", output)

    def test_pydocfmt_check_show_files_and_show_settings_are_mutually_exclusive(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "check", "--show-files", "--show-settings"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = pydocfmt_main.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("--show-files and --show-settings cannot be used together", stderr.getvalue())

    def test_pydocfmt_check_exit_flags_are_mutually_exclusive(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "check", "--exit-zero", "--exit-non-zero-on-fix"]
        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            pydocfmt_main.main()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("--exit-zero", stderr.getvalue())
        self.assertIn("--exit-non-zero-on-fix", stderr.getvalue())

    def _assert_invalid_command_line_include_reports_argument_error(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
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
        self.assertIn("command line.include must not contain empty strings", stderr.getvalue())
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
                    exit_code = pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 2)
        self.assertIn("command line.exclude must not contain empty strings", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_command_line_include_reports_argument_error(
        self,
    ) -> None:
        self._assert_invalid_command_line_include_reports_argument_error(
            pydocfmt_main.main,
            "pydocfmt",
        )

    def _assert_invalid_config_include_reports_config_error(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            stderr = StringIO()
            argv = [program, "check", str(root)]
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
        self.assertIn(f"{program} check: file selection error", stderr.getvalue())
        self.assertIn("include pattern must target files", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_config_include_reports_config_error(self) -> None:
        self._assert_invalid_config_include_reports_config_error(
            pydocfmt_main.main,
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
                    exit_code = pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 2)
        self.assertIn("pydocfmt check: configuration error", stderr.getvalue())
        self.assertIn("failed to decode pyproject.toml", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_missing_explicit_file_reports_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "missing.py"
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

        self.assertIn(
            f"{target} ignored WARNING: failed to read or write file",
            stdout.getvalue(),
        )
        self.assertNotIn("Traceback", stdout.getvalue())

    def test_pydocfmt_warns_once_when_gitignore_check_fails(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            def fake_format(path: str, settings: FormatterSettings, fix: bool, **kwargs: object) -> bool:
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
                    "pydocformatter.cli.check.pydocfmt.format_file",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            output_lines = stdout.getvalue().splitlines()
            warning = f"{root} WARNING: unable to apply gitignore filtering (fatal: broken git); continuing without gitignore filtering for this repository root"
            self.assertIn(warning, output_lines)
            self.assertEqual(output_lines.count(warning), 1)
            self.assertEqual(called_paths, [])

    @staticmethod
    def _make_tree_with_invalid_utf8() -> tempfile.TemporaryDirectory[str]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / "good.py").write_text("x = 1\n", encoding="utf-8")
        (root / "bad.py").write_bytes(b"\xff")
        return temp_dir

    def test_pydocfmt_skips_undecodable_utf8_file_with_stdout_warning(self) -> None:
        with self._make_tree_with_invalid_utf8() as td:
            root = Path(td)
            stdout = StringIO()
            argv = ["pydocfmt", "check", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            output = stdout.getvalue()
            self.assertIn(
                f"{root / 'bad.py'} ignored WARNING: failed to decode as UTF-8",
                output,
            )

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
                exit_code = pydocfmt_main.main()

            self.assertEqual(exit_code, 1)
            output = stdout.getvalue()
            self.assertIn(
                f"{root / 'bad.py'} ignored WARNING: failed to decode as UTF-8",
                output,
            )
            self.assertIn(
                f"{root / 'needs_fix.py'}: Needs docstring formatting on line 2",
                output,
            )


if __name__ == "__main__":
    unittest.main()
