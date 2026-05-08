import contextlib
import os
import subprocess
import tempfile
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path
from typing import Callable

import pydocformatter.cli.pycommentfmt_main as pycommentfmt_main
import pydocformatter.cli.pydocfmt_main as pydocfmt_main
from pydocformatter.config import FormatterSettings


class TestCliVerbose(unittest.TestCase):
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

    def test_pydocfmt_verbose_lists_included_and_ignored_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                str(root),
                "--verbose",
                "--include",
                "*.py",
                "--exclude",
                "skip.py",
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'b.txt'} ignored: does not match include patterns",
                f"{root / 'skip.py'} ignored: matches exclude patterns",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pydocfmt_defaults_to_current_directory_without_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(os.path.abspath(path))
                return False

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                argv = ["pydocfmt", "--no-respect-gitignore"]
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
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

    def test_pydocfmt_verbose_lists_pruned_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / ".venv").mkdir()
            (root / ".venv" / "ignored.py").write_text("x = 2\n", encoding="utf-8")
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", str(root), "--verbose"]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            expected_lines = [
                f"{root / '.venv'} ignored: matches exclude patterns",
                f"{root / 'a.py'} included",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pycommentfmt_verbose_lists_included_and_ignored_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pycommentfmt",
                str(root),
                "--verbose",
                "--include",
                "*.py",
                "--exclude",
                "skip.py",
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pycommentfmt_main.pycommentfmt.format_comments",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pycommentfmt_main.main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'b.txt'} ignored: does not match include patterns",
                f"{root / 'skip.py'} ignored: matches exclude patterns",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pycommentfmt_defaults_to_current_directory_without_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(os.path.abspath(path))
                return False

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                argv = ["pycommentfmt", "--no-respect-gitignore"]
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.cli.pycommentfmt_main.pycommentfmt.format_comments",
                        side_effect=fake_format,
                    ),
                ):
                    pycommentfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(
                [Path(path) for path in called_paths],
                [root / "a.py", root / "skip.py"],
            )

    def test_pydocfmt_multiple_globs_per_include_and_exclude_option(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                str(root),
                "--verbose",
                "--include",
                "*.py",
                "*.txt",
                "--exclude",
                "skip.py",
                "b.txt",
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'b.txt'} ignored: matches exclude patterns",
                f"{root / 'skip.py'} ignored: matches exclude patterns",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pydocfmt_multiple_globs_before_positional_path_after_separator(
        self,
    ) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                "--verbose",
                "--include",
                "*.py",
                "*.txt",
                "--exclude",
                "skip.py",
                "--",
                str(root),
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'b.txt'} included",
                f"{root / 'skip.py'} ignored: matches exclude patterns",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py"), str(root / "b.txt")])

    def test_pydocfmt_default_respects_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "--verbose", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'skip.py'} ignored: matches .gitignore",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pydocfmt_no_respect_gitignore_disables_gitignore_filtering(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "--verbose", "--no-respect-gitignore", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            self.assertFalse(run_mock.called)
            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'skip.py'} included",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py"), str(root / "skip.py")])

    def test_pycommentfmt_default_respects_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pycommentfmt", "--verbose", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ),
                unittest.mock.patch(
                    "pydocformatter.cli.pycommentfmt_main.pycommentfmt.format_comments",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pycommentfmt_main.main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'skip.py'} ignored: matches .gitignore",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pycommentfmt_no_respect_gitignore_disables_gitignore_filtering(
        self,
    ) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pycommentfmt", "--verbose", "--no-respect-gitignore", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                unittest.mock.patch(
                    "pydocformatter.cli.pycommentfmt_main.pycommentfmt.format_comments",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pycommentfmt_main.main()

            self.assertFalse(run_mock.called)
            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'skip.py'} included",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py"), str(root / "skip.py")])

    def test_pydocfmt_hyphenated_pyproject_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pydocfmt]\nline-length = 72\nrespect-gitignore = false\nexperimental = true\n",
                encoding="utf-8",
            )
            called_args: list[tuple[str, int, bool, bool]] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool) -> bool:
                called_args.append((path, settings.line_length, check, settings.experimental))
                return False

            argv = ["pydocfmt", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                    unittest.mock.patch(
                        "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertFalse(run_mock.called)
            self.assertEqual(called_args, [(str(root / "a.py"), 72, False, True)])

    def test_pydocfmt_indent_cli_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            called_settings: list[tuple[str, int]] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool) -> bool:
                called_settings.append((settings.indent_style, settings.indent_width))
                return False

            argv = [
                "pydocfmt",
                "--indent-style",
                "tab",
                "--indent-width",
                "2",
                str(root / "a.py"),
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
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

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool) -> bool:
                called_settings.append(settings.line_ending)
                return False

            argv = ["pycommentfmt", "--line-ending", "cr-lf", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pycommentfmt_main.pycommentfmt.format_comments",
                    side_effect=fake_format,
                ),
            ):
                pycommentfmt_main.main()

            self.assertEqual(called_settings, ["cr-lf"])

    def test_pycommentfmt_rejects_unused_indent_cli_settings(self) -> None:
        stderr = StringIO()
        argv = ["pycommentfmt", "--indent-style", "tab", "a.py"]

        with (
            unittest.mock.patch("sys.argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            pycommentfmt_main.main()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("unrecognized arguments: --indent-style", stderr.getvalue())

    def test_pycommentfmt_hyphenated_pyproject_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pycommentfmt]\nline-length = 72\nrespect-gitignore = false\n",
                encoding="utf-8",
            )
            called_args: list[tuple[str, int, bool]] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool) -> bool:
                called_args.append((path, settings.line_length, check))
                return False

            argv = ["pycommentfmt", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                    unittest.mock.patch(
                        "pydocformatter.cli.pycommentfmt_main.pycommentfmt.format_comments",
                        side_effect=fake_format,
                    ),
                ):
                    pycommentfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertFalse(run_mock.called)
            self.assertEqual(called_args, [(str(root / "a.py"), 72, False)])

    def test_shared_settings_are_overridden_by_tool_specific_settings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\nline-length = 70\n[tool.pydocformatter.pydocfmt]\nline-length = 72\n",
                encoding="utf-8",
            )
            called_args: list[tuple[str, int, bool]] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool) -> bool:
                called_args.append((path, settings.line_length, check))
                return False

            argv = ["pydocfmt", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch(
                        "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(called_args, [(str(root / "a.py"), 72, False)])

    def test_rule_cli_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_settings: list[FormatterSettings] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool) -> bool:
                called_settings.append(settings)
                return False

            argv = [
                "pycommentfmt",
                str(target),
                "--experimental",
                "--select",
                "PCF",
                "--ignore",
                "PCF002",
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
                    "pydocformatter.cli.pycommentfmt_main.pycommentfmt.format_comments",
                    side_effect=fake_format,
                ),
            ):
                exit_code = pycommentfmt_main.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(called_settings[0].select, ("PCF",))
            self.assertEqual(called_settings[0].ignore, ("PCF002",))
            self.assertEqual(called_settings[0].fixable, ("ALL",))
            self.assertEqual(called_settings[0].unfixable, ("PCF001",))
            self.assertEqual(called_settings[0].per_file_ignores, (("tests/*.py", ("PCF001",)),))
            self.assertTrue(called_settings[0].experimental)

    def test_invalid_rule_cli_selector_reports_configuration_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stderr = StringIO()
            argv = ["pycommentfmt", str(target), "--select", "RD"]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = pycommentfmt_main.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("unknown selector: RD", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_force_exclude_filters_explicit_file_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.py"
            target.write_text("x = 1\n", encoding="utf-8")
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                str(target),
                "--verbose",
                "--force-exclude",
                "--exclude",
                "skip.py",
            ]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            self.assertEqual(
                stdout.getvalue().splitlines(),
                [f"{target} ignored: matches exclude patterns"],
            )
            self.assertEqual(called_paths, [])

    def test_force_exclude_filters_explicit_file_by_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            target = root / "skip.py"
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "--verbose", "--force-exclude", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            self.assertEqual(
                stdout.getvalue().splitlines(),
                [f"{target} ignored: matches .gitignore"],
            )
            self.assertEqual(called_paths, [])

    def test_command_line_extend_exclude_overrides_config_extend_exclude(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.py"
            target.write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pydocfmt]\n" 'include = ["*.py"]\n' "exclude = []\n" 'extend-exclude = ["skip.py"]\n',
                encoding="utf-8",
            )
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
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
                        "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_main.main()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(called_paths, [str(target)])

    def _assert_help_ignores_invalid_config(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocformatter]\ninclude = ["src/"]\n',
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

    def test_pycommentfmt_help_ignores_invalid_config(self) -> None:
        self._assert_help_ignores_invalid_config(pycommentfmt_main.main, "pycommentfmt")

    def _assert_invalid_command_line_include_reports_argument_error(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            stderr = StringIO()
            argv = [program, str(root), "--include", ""]
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
        self.assertIn("include patterns must not be empty", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_command_line_exclude_reports_argument_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            stderr = StringIO()
            argv = ["pydocfmt", str(root), "--exclude", ""]
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
        self.assertIn("exclude patterns must not be empty", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_command_line_include_reports_argument_error(
        self,
    ) -> None:
        self._assert_invalid_command_line_include_reports_argument_error(
            pydocfmt_main.main,
            "pydocfmt",
        )

    def test_pycommentfmt_invalid_command_line_include_reports_argument_error(
        self,
    ) -> None:
        self._assert_invalid_command_line_include_reports_argument_error(
            pycommentfmt_main.main,
            "pycommentfmt",
        )

    def _assert_invalid_config_include_reports_config_error(
        self,
        main: Callable[[], int],
        program: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocformatter]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            stderr = StringIO()
            argv = [program, str(root)]
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
        self.assertIn(f"{program}: configuration error", stderr.getvalue())
        self.assertIn("include pattern must target files", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_invalid_config_include_reports_config_error(self) -> None:
        self._assert_invalid_config_include_reports_config_error(
            pydocfmt_main.main,
            "pydocfmt",
        )

    def test_pycommentfmt_invalid_config_include_reports_config_error(self) -> None:
        self._assert_invalid_config_include_reports_config_error(
            pycommentfmt_main.main,
            "pycommentfmt",
        )

    def test_pydocfmt_invalid_toml_reports_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter\n",
                encoding="utf-8",
            )
            stderr = StringIO()
            argv = ["pydocfmt", str(root)]
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
        self.assertIn("pydocfmt: configuration error", stderr.getvalue())
        self.assertIn("failed to decode pyproject.toml", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_pydocfmt_missing_explicit_file_reports_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "missing.py"
            stdout = StringIO()
            argv = ["pydocfmt", str(target)]
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

            # noinspection PyUnusedLocal
            def fake_format(path: str, settings: FormatterSettings, check: bool, **kwargs: object) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "--verbose", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    return_value=subprocess.CompletedProcess(["git"], 128, stdout=b"", stderr=b"fatal: broken git"),
                ),
                unittest.mock.patch(
                    "pydocformatter.cli.pydocfmt_main.pydocfmt.format_docstrings",
                    side_effect=fake_format,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                pydocfmt_main.main()

            output_lines = stdout.getvalue().splitlines()
            warning = f"{root} WARNING: unable to apply gitignore filtering (fatal: broken git); continuing without gitignore filtering for this repository root"
            self.assertIn(warning, output_lines)
            self.assertEqual(output_lines.count(warning), 1)
            self.assertEqual(called_paths, [str(root / "a.py"), str(root / "skip.py")])

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
            argv = ["pydocfmt", str(root)]
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

    def test_pycommentfmt_skips_undecodable_utf8_file_with_stdout_warning(self) -> None:
        with self._make_tree_with_invalid_utf8() as td:
            root = Path(td)
            stdout = StringIO()
            argv = ["pycommentfmt", str(root)]
            with (
                unittest.mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(stdout),
            ):
                pycommentfmt_main.main()

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
            argv = ["pydocfmt", "--check", "--line-length", "72", str(root)]
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
