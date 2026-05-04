import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from pydocformatter.cli.pycommentfmt_main import main as pycommentfmt_main
from pydocformatter.cli.pydocfmt_main import main as pydocfmt_main


class TestCliVerbose(unittest.TestCase):
    def _make_sample_tree(self) -> tempfile.TemporaryDirectory[str]:
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


if __name__ == "__main__":
    unittest.main()
