import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from pydocformatter.utils import (
    classify_file,
    collect_file_decisions,
    format_line_ranges,
)


class TestUtils(unittest.TestCase):
    def test_classify_file_reasoning(self) -> None:
        include = re.compile(r"\.py$")
        exclude = re.compile(r"skip\.py$")

        accepted = classify_file("pkg/module.py", include, exclude)
        self.assertTrue(accepted.accepted)
        self.assertEqual(accepted.reason, "included")

        rejected_include = classify_file("pkg/module.txt", include, exclude)
        self.assertFalse(rejected_include.accepted)
        self.assertEqual(
            rejected_include.reason,
            "does not match the --include regular expression",
        )

        rejected_exclude = classify_file("pkg/skip.py", include, exclude)
        self.assertFalse(rejected_exclude.accepted)
        self.assertEqual(
            rejected_exclude.reason,
            "matches the --exclude regular expression",
        )

    def test_collect_file_decisions_is_deterministic(self) -> None:
        include = re.compile(r"\.py$")
        exclude = None

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "z_dir").mkdir()
            (root / "a_dir").mkdir()
            (root / "b.py").write_text("", encoding="utf-8")
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "z_dir" / "c.py").write_text("", encoding="utf-8")
            (root / "a_dir" / "d.py").write_text("", encoding="utf-8")

            decisions = collect_file_decisions([str(root)], include, exclude)

        collected = [
            Path(decision.path).relative_to(root).as_posix() for decision in decisions
        ]
        self.assertEqual(collected, ["a.py", "b.py", "a_dir/d.py", "z_dir/c.py"])

    def test_format_line_ranges(self) -> None:
        self.assertEqual(format_line_ranges([7]), "7")
        self.assertEqual(format_line_ranges([3, 4, 5]), "3-5")
        self.assertEqual(format_line_ranges([1, 2, 4, 6, 7, 8, 10]), "1-2, 4, 6-8, 10")

    def test_collect_file_decisions_respects_gitignore(self) -> None:
        include = re.compile(r"\.py$")
        exclude = None

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "keep.py").write_text("", encoding="utf-8")
            (root / "skip.py").write_text("", encoding="utf-8")

            def fake_run(
                *args: object, **kwargs: object
            ) -> subprocess.CompletedProcess[bytes]:
                command = cast(list[str], args[0])
                self.assertEqual(
                    command,
                    [
                        "git",
                        "-C",
                        str(root),
                        "check-ignore",
                        "--stdin",
                        "--no-index",
                        "-z",
                    ],
                )
                stdin_bytes = cast(bytes, kwargs["input"])
                self.assertIn(b"keep.py", stdin_bytes)
                self.assertIn(b"skip.py", stdin_bytes)
                return subprocess.CompletedProcess(
                    cast(Any, command), 0, stdout=b"skip.py\0", stderr=b""
                )

            with patch("pydocformatter.utils.subprocess.run", side_effect=fake_run):
                decisions = collect_file_decisions([str(root)], include, exclude)

        decisions_by_name = {
            Path(decision.path).name: decision for decision in decisions
        }
        self.assertTrue(decisions_by_name["keep.py"].accepted)
        self.assertEqual(decisions_by_name["keep.py"].reason, "included")
        self.assertFalse(decisions_by_name["skip.py"].accepted)
        self.assertEqual(decisions_by_name["skip.py"].reason, "matches .gitignore")

    def test_collect_file_decisions_can_disable_gitignore(self) -> None:
        include = re.compile(r"\.py$")
        exclude = None

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "keep.py").write_text("", encoding="utf-8")

            with patch("pydocformatter.utils.subprocess.run") as run_mock:
                decisions = collect_file_decisions(
                    [str(root)], include, exclude, respect_gitignore=False
                )

        self.assertFalse(run_mock.called)
        self.assertEqual(len(decisions), 1)
        self.assertTrue(decisions[0].accepted)
        self.assertEqual(decisions[0].reason, "included")

    def test_collect_file_decisions_warns_once_per_root_on_git_failure(self) -> None:
        include = re.compile(r"\.py$")
        exclude = None

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "b.py").write_text("", encoding="utf-8")

            with (
                patch(
                    "pydocformatter.utils.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        ["git"], 128, stdout=b"", stderr=b"fatal: no such command"
                    ),
                ),
                patch("builtins.print") as print_mock,
            ):
                decisions = collect_file_decisions([str(root)], include, exclude)

        self.assertEqual(len(decisions), 2)
        self.assertTrue(all(decision.accepted for decision in decisions))
        print_mock.assert_called_once_with(
            f"{root} WARNING: unable to apply gitignore filtering (fatal: no such command); "
            "continuing without gitignore filtering for this repository root"
        )


if __name__ == "__main__":
    unittest.main()
