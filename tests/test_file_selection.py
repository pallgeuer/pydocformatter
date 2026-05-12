import contextlib
import os
import subprocess
import tempfile
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path
from typing import Callable

import pydocformatter.file_selection as file_selection
from pydocformatter.config import FormatterSettings
from pydocformatter.file_selection import DecisionReason


class TestFileSelection(unittest.TestCase):
    @staticmethod
    def _write_git_marker(root: Path) -> None:
        (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")

    @staticmethod
    def _fake_git_check_ignore_for_root(
        root: Path,
        ignored_paths: set[str],
    ) -> Callable[..., subprocess.CompletedProcess[bytes]]:
        def fake_run(
            *args: object,
            **kwargs: object,
        ) -> subprocess.CompletedProcess[bytes]:
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

    def test_ruff_spec_deterministic_directory_order(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "z_dir").mkdir()
            (root / "a_dir").mkdir()
            (root / "b.py").write_text("", encoding="utf-8")
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "z_dir" / "c.py").write_text("", encoding="utf-8")
            (root / "a_dir" / "d.py").write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(root)], settings)

        collected = [Path(decision.path).relative_to(root).as_posix() for decision in selection.decisions]
        self.assertEqual(collected, ["a.py", "b.py", "a_dir/d.py", "z_dir/c.py"])

    def test_selection_preserves_relative_explicit_paths(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["a.py"], settings)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(selection.accepted_paths, ("a.py",))
        self.assertEqual(selection.decisions[0].path, "a.py")

    def test_selection_deduplicates_equivalent_paths(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["a.py", str(target)], settings)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(selection.accepted_paths, ("a.py",))
        self.assertEqual(selection.decisions[0].reason, DecisionReason.EXPLICIT_INCLUDED)
        self.assertEqual(selection.decisions[1].reason, DecisionReason.DUPLICATE)
        self.assertFalse(selection.decisions[1].accepted)

    def test_selection_canonicalizes_lexical_path_aliases(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pkg").mkdir()
            (root / "a.py").write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["./a.py", "pkg/../a.py"], settings)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(selection.accepted_paths, ("a.py",))
        self.assertEqual([decision.path for decision in selection.decisions], ["a.py", "a.py"])
        self.assertEqual(selection.decisions[1].reason, DecisionReason.DUPLICATE)

    def test_selection_converts_absolute_paths_inside_current_directory_to_relative_paths(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files([str(target)], settings)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(selection.accepted_paths, ("a.py",))
        self.assertEqual(selection.decisions[0].path, "a.py")

    def test_selection_preserves_absolute_paths_outside_current_directory(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(target)], settings)

        self.assertEqual(selection.accepted_paths, (str(target),))
        self.assertEqual(selection.decisions[0].path, str(target))

    def test_selection_deduplicates_symlink_aliases_by_physical_target(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            alias = root / "alias.py"
            target.write_text("", encoding="utf-8")
            try:
                alias.symlink_to(target)
            except OSError as error:
                self.skipTest(f"symlinks are not available: {error}")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["a.py", "alias.py"], settings)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(selection.accepted_paths, ("a.py",))
        self.assertEqual(selection.decisions[1].reason, DecisionReason.DUPLICATE)

    def test_ruff_spec_explicit_file_bypasses_filters_without_force(
        self,
    ) -> None:
        settings = FormatterSettings(
            respect_gitignore=True,
            force_exclude=False,
            include=("*.py",),
            exclude=("skip.py",),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.txt"
            target.write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(target)], settings)

        self.assertEqual(selection.accepted_paths, (str(target),))
        self.assertEqual(selection.decisions[0].reason, DecisionReason.EXPLICIT_INCLUDED)

    def test_ruff_spec_force_exclude_filters_explicit_file(self) -> None:
        settings = FormatterSettings(
            respect_gitignore=False,
            force_exclude=True,
            include=("*.py",),
            exclude=("skip.py",),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.py"
            target.write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(target)], settings)

        self.assertEqual(selection.accepted_paths, ())
        self.assertEqual(selection.decisions[0].reason, DecisionReason.EXCLUDED)

    def test_ruff_spec_gitignore_can_be_disabled(self) -> None:
        settings = FormatterSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "a.py").write_text("", encoding="utf-8")

            with unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock:
                selection = file_selection.select_files([str(root)], settings)

        self.assertFalse(run_mock.called)
        self.assertEqual(selection.accepted_paths, (str(root / "a.py"),))

    def test_ruff_spec_gitignore_filters_discovered_files(self) -> None:
        settings = FormatterSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "keep.py").write_text("", encoding="utf-8")
            (root / "skip.py").write_text("", encoding="utf-8")

            with unittest.mock.patch(
                "pydocformatter.file_selection.subprocess.run",
                side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"}),
            ):
                selection = file_selection.select_files([str(root)], settings)

        decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
        self.assertEqual(selection.accepted_paths, (str(root / "keep.py"),))
        self.assertEqual(decisions_by_name["skip.py"].reason, DecisionReason.GITIGNORED)

    def test_ruff_spec_non_git_directory_does_not_warn(self) -> None:
        settings = FormatterSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("", encoding="utf-8")
            stdout = StringIO()

            with (
                unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock,
                contextlib.redirect_stdout(stdout),
            ):
                selection = file_selection.select_files([str(root)], settings)

        self.assertFalse(run_mock.called)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(selection.accepted_paths, (str(root / "a.py"),))

    def test_ruff_spec_warns_once_per_git_root_on_check_failure(self) -> None:
        settings = FormatterSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "b.py").write_text("", encoding="utf-8")
            stdout = StringIO()

            with (
                unittest.mock.patch(
                    "pydocformatter.file_selection.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        ["git"],
                        128,
                        stdout=b"",
                        stderr=b"fatal: no such command",
                    ),
                ),
                contextlib.redirect_stdout(stdout),
            ):
                selection = file_selection.select_files([str(root)], settings)

        warning = f"{root} WARNING: unable to apply gitignore filtering (fatal: no such command); continuing without gitignore filtering for this repository root"
        self.assertEqual(stdout.getvalue().splitlines(), [warning])
        self.assertEqual(
            selection.accepted_paths,
            (str(root / "a.py"), str(root / "b.py")),
        )

    def test_ruff_spec_slash_patterns_are_git_root_relative(self) -> None:
        settings = FormatterSettings(
            respect_gitignore=False,
            exclude=("src/pkg/*.py",),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "pkg").mkdir(parents=True)
            target = root / "src" / "pkg" / "a.py"
            target.write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                selection = file_selection.select_files([str(root / "src")], settings)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(selection.accepted_paths, ())
        self.assertEqual(selection.decisions[0].reason, DecisionReason.EXCLUDED)

    def test_ruff_spec_direct_excluded_directory_is_skipped(self) -> None:
        settings = FormatterSettings(
            respect_gitignore=False,
            exclude=("src/generated",),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "generated").mkdir(parents=True)
            (root / "src" / "generated" / "a.py").write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(root / "src" / "generated")], settings)

        self.assertEqual(selection.accepted_paths, ())
        self.assertEqual(selection.decisions[0].path, str(root / "src" / "generated"))
        self.assertEqual(selection.decisions[0].reason, DecisionReason.EXCLUDED)

    def test_pruned_excluded_directory_is_reported_as_decision(self) -> None:
        settings = FormatterSettings(
            respect_gitignore=False,
            exclude=("generated",),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "generated").mkdir()
            (root / "generated" / "ignored.py").write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(root)], settings)

        decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
        self.assertEqual(selection.accepted_paths, (str(root / "a.py"),))
        self.assertEqual(decisions_by_name["generated"].reason, DecisionReason.EXCLUDED)
        self.assertNotIn("ignored.py", decisions_by_name)

    def test_ruff_spec_slash_directory_exclude_filters_descendant_file(
        self,
    ) -> None:
        settings = FormatterSettings(
            respect_gitignore=False,
            force_exclude=True,
            exclude=("src/generated",),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "generated").mkdir(parents=True)
            target = root / "src" / "generated" / "a.py"
            target.write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(target)], settings)

        self.assertEqual(selection.accepted_paths, ())
        self.assertEqual(selection.decisions[0].reason, DecisionReason.EXCLUDED)

    def test_gitignore_query_encodes_surrogate_paths(self) -> None:
        settings = FormatterSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            surrogate_path = "bad_\udcff.py"
            target = root / surrogate_path
            target.write_text("", encoding="utf-8")
            expected_command = [
                "git",
                "-C",
                str(root),
                "check-ignore",
                "--stdin",
                "--no-index",
                "-z",
            ]

            def fake_run(
                *args: object,
                **kwargs: object,
            ) -> subprocess.CompletedProcess[bytes]:
                assert args[0] == expected_command
                stdin_bytes = kwargs["input"]
                assert stdin_bytes == b"bad_\xff.py\0"
                return subprocess.CompletedProcess(
                    expected_command,
                    0,
                    stdout=b"bad_\xff.py\0",
                    stderr=b"",
                )

            with unittest.mock.patch("pydocformatter.file_selection.subprocess.run", side_effect=fake_run):
                selection = file_selection.select_files([str(root)], settings)

        self.assertEqual(selection.accepted_paths, ())
        self.assertEqual(selection.decisions[0].reason, DecisionReason.GITIGNORED)


if __name__ == "__main__":
    unittest.main()
