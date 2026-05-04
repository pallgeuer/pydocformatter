import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
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
                f"WARNING: {root / 'bad.py'} ignored: failed to decode as UTF-8",
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
                f"WARNING: {root / 'bad.py'} ignored: failed to decode as UTF-8",
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
                f"WARNING: {root / 'bad.py'} ignored: failed to decode as UTF-8",
                output,
            )
            self.assertIn(
                f"{root / 'needs_fix.py'}: Needs docstring formatting on line 2",
                output,
            )


if __name__ == "__main__":
    unittest.main()
