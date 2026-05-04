import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Callable
from unittest.mock import patch

from pydocformatter.cli.pycommentfmt_main import main as pycommentfmt_main
from pydocformatter.cli.pydocfmt_main import main as pydocfmt_main


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
        (root / ".git").mkdir()
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / "skip.py").write_text("x = 2\n", encoding="utf-8")
        return temp_dir

    @staticmethod
    def _fake_git_check_ignore_for_root(
        root: Path, ignored_paths: set[str]
    ) -> Callable[..., subprocess.CompletedProcess[bytes]]:
        def fake_run(
            *args: object, **kwargs: object
        ) -> subprocess.CompletedProcess[bytes]:
            command = args[0]
            assert command == [
                "git",
                "-C",
                str(root),
                "check-ignore",
                "--stdin",
                "--no-index",
                "-z",
            ]
            stdin_bytes = kwargs["input"]
            assert isinstance(stdin_bytes, bytes)
            provided_paths = [
                path for path in stdin_bytes.decode("utf-8").split("\0") if path
            ]
            ignored = [path for path in provided_paths if path in ignored_paths]
            stdout = ("\0".join(ignored) + ("\0" if ignored else "")).encode("utf-8")
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

        return fake_run

    def test_pydocfmt_verbose_lists_included_and_ignored_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pydocfmt",
                "--verbose",
                "--include",
                r"\.py$",
                "--exclude",
                r"skip\.py$",
                str(root),
            ]
            with (
                patch("sys.argv", argv),
                patch(
                    "pydocformatter.cli.pydocfmt_main.format_docstrings",
                    side_effect=fake_format,
                ),
                redirect_stdout(stdout),
            ):
                pydocfmt_main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'b.txt'} ignored: does not match the --include regular expression",
                f"{root / 'skip.py'} ignored: matches the --exclude regular expression",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pycommentfmt_verbose_lists_included_and_ignored_files(self) -> None:
        with self._make_sample_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_paths.append(path)
                return False

            argv = [
                "pycommentfmt",
                "--verbose",
                "--include",
                r"\.py$",
                "--exclude",
                r"skip\.py$",
                str(root),
            ]
            with (
                patch("sys.argv", argv),
                patch(
                    "pydocformatter.cli.pycommentfmt_main.format_comments",
                    side_effect=fake_format,
                ),
                redirect_stdout(stdout),
            ):
                pycommentfmt_main()

            expected_lines = [
                f"{root / 'a.py'} included",
                f"{root / 'b.txt'} ignored: does not match the --include regular expression",
                f"{root / 'skip.py'} ignored: matches the --exclude regular expression",
            ]
            self.assertEqual(stdout.getvalue().splitlines(), expected_lines)
            self.assertEqual(called_paths, [str(root / "a.py")])

    def test_pydocfmt_default_respects_gitignore(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "--verbose", str(root)]
            with (
                patch("sys.argv", argv),
                patch(
                    "pydocformatter.utils.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ),
                patch(
                    "pydocformatter.cli.pydocfmt_main.format_docstrings",
                    side_effect=fake_format,
                ),
                redirect_stdout(stdout),
            ):
                pydocfmt_main()

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
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "--verbose", "--no-respect-gitignore", str(root)]
            with (
                patch("sys.argv", argv),
                patch("pydocformatter.utils.subprocess.run") as run_mock,
                patch(
                    "pydocformatter.cli.pydocfmt_main.format_docstrings",
                    side_effect=fake_format,
                ),
                redirect_stdout(stdout),
            ):
                pydocfmt_main()

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
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_paths.append(path)
                return False

            argv = ["pycommentfmt", "--verbose", str(root)]
            with (
                patch("sys.argv", argv),
                patch(
                    "pydocformatter.utils.subprocess.run",
                    side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
                ),
                patch(
                    "pydocformatter.cli.pycommentfmt_main.format_comments",
                    side_effect=fake_format,
                ),
                redirect_stdout(stdout),
            ):
                pycommentfmt_main()

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
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_paths.append(path)
                return False

            argv = ["pycommentfmt", "--verbose", "--no-respect-gitignore", str(root)]
            with (
                patch("sys.argv", argv),
                patch("pydocformatter.utils.subprocess.run") as run_mock,
                patch(
                    "pydocformatter.cli.pycommentfmt_main.format_comments",
                    side_effect=fake_format,
                ),
                redirect_stdout(stdout),
            ):
                pycommentfmt_main()

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
                "[tool.pydocfmt]\nline-length = 72\nrespect-gitignore = false\n",
                encoding="utf-8",
            )
            called_args: list[tuple[str, int, bool]] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_args.append((path, line_length, check))
                return False

            argv = ["pydocfmt", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    patch("sys.argv", argv),
                    patch("pydocformatter.utils.subprocess.run") as run_mock,
                    patch(
                        "pydocformatter.cli.pydocfmt_main.format_docstrings",
                        side_effect=fake_format,
                    ),
                ):
                    pydocfmt_main()
            finally:
                os.chdir(previous_cwd)

            self.assertFalse(run_mock.called)
            self.assertEqual(called_args, [(str(root / "a.py"), 72, False)])

    def test_pycommentfmt_hyphenated_pyproject_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.pycommentfmt]\nline-length = 72\nrespect-gitignore = false\n",
                encoding="utf-8",
            )
            called_args: list[tuple[str, int, bool]] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_args.append((path, line_length, check))
                return False

            argv = ["pycommentfmt", str(root)]
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with (
                    patch("sys.argv", argv),
                    patch("pydocformatter.utils.subprocess.run") as run_mock,
                    patch(
                        "pydocformatter.cli.pycommentfmt_main.format_comments",
                        side_effect=fake_format,
                    ),
                ):
                    pycommentfmt_main()
            finally:
                os.chdir(previous_cwd)

            self.assertFalse(run_mock.called)
            self.assertEqual(called_args, [(str(root / "a.py"), 72, False)])

    def test_pydocfmt_warns_once_when_gitignore_check_fails(self) -> None:
        with self._make_git_tree() as td:
            root = Path(td)
            stdout = StringIO()
            called_paths: list[str] = []

            # noinspection PyUnusedLocal
            def fake_format(path: str, line_length: int, check: bool) -> bool:
                called_paths.append(path)
                return False

            argv = ["pydocfmt", "--verbose", str(root)]
            with (
                patch("sys.argv", argv),
                patch(
                    "pydocformatter.utils.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        ["git"], 128, stdout=b"", stderr=b"fatal: broken git"
                    ),
                ),
                patch(
                    "pydocformatter.cli.pydocfmt_main.format_docstrings",
                    side_effect=fake_format,
                ),
                redirect_stdout(stdout),
            ):
                pydocfmt_main()

            output_lines = stdout.getvalue().splitlines()
            warning = (
                f"{root} WARNING: unable to apply gitignore filtering (fatal: broken git); "
                "continuing without gitignore filtering for this repository root"
            )
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
            with patch("sys.argv", argv), redirect_stdout(stdout):
                pydocfmt_main()

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
            with patch("sys.argv", argv), redirect_stdout(stdout):
                pycommentfmt_main()

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
            with patch("sys.argv", argv), redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as cm:
                    pydocfmt_main()

            self.assertEqual(cm.exception.code, 1)
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
