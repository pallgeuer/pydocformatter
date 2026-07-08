# Future imports
from __future__ import annotations

# Standard library imports
import os
import argparse
import tempfile
import unittest
import contextlib
import subprocess
import dataclasses
import unittest.mock
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
from pydocformatter import file_selection
from pydocformatter.cli.global_args import GlobalArgs
from pydocformatter.cli.settings_check import SETTINGS_SCHEMA, CheckSettings
from pydocformatter.file_selection import DecisionReason


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.settings as settings_core


class TestFileSelection(unittest.TestCase):
    @staticmethod
    def _selected_relative_paths(selection: file_selection.SelectionResult, root: Path) -> tuple[str, ...]:
        """Return accepted paths relative to a temporary root."""
        return tuple(Path(path).relative_to(root).as_posix() for path in selection.accepted_paths)

    @staticmethod
    def _write_git_marker(root: Path) -> None:
        """Write a minimal git worktree marker in a temporary root."""
        (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")

    @staticmethod
    def _resolver(settings: CheckSettings) -> settings_core.SettingsResolver[CheckSettings]:
        """Return a resolver with static test settings applied as overrides."""
        return SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True), field_overrides=dataclasses.asdict(settings))

    @staticmethod
    def _fake_git_check_ignore_for_root(root: Path, ignored_paths: set[str]) -> Callable[..., subprocess.CompletedProcess[bytes]]:
        """Return a fake git check-ignore runner for a temporary root."""

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            expected_command = ["git", "-C", str(root), "check-ignore", "--stdin", "--no-index", "-z"]
            assert args[0] == expected_command
            stdin_bytes = kwargs["input"]
            assert isinstance(stdin_bytes, bytes)
            provided_paths = [path for path in stdin_bytes.decode("utf-8").split("\0") if path]
            ignored = [path for path in provided_paths if path in ignored_paths]
            stdout = ("\0".join(ignored) + ("\0" if ignored else "")).encode("utf-8")
            return subprocess.CompletedProcess(expected_command, 0, stdout=stdout, stderr=b"")

        return fake_run

    def test_ruff_spec_deterministic_directory_order(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "z_dir").mkdir()
            (root / "a_dir").mkdir()
            (root / "b.py").write_text("", encoding="utf-8")
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "z_dir" / "c.py").write_text("", encoding="utf-8")
            (root / "a_dir" / "d.py").write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(root)], self._resolver(settings))

        collected = [Path(decision.path).relative_to(root).as_posix() for decision in selection.decisions]
        assert collected == ["a.py", "b.py", "a_dir/d.py", "z_dir/c.py"]

    def test_selection_displays_real_explicit_paths_as_absolute(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["a.py"], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(root / "a.py"),)
        assert selection.decisions[0].path == str(root / "a.py")

    def test_virtual_file_is_not_walked_when_path_exists_as_directory(self) -> None:
        settings = CheckSettings(respect_gitignore=False, force_exclude=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pkg.py").mkdir()
            (root / "pkg.py" / "child.py").write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_virtual_file("pkg.py", self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(root / "pkg.py"),)
        assert [decision.path for decision in selection.decisions] == [str(root / "pkg.py")]

    def test_selection_deduplicates_equivalent_paths(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["a.py", str(target)], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(root / "a.py"),)
        assert selection.decisions[0].reason == DecisionReason.EXPLICIT_INCLUDED
        assert selection.decisions[1].reason == DecisionReason.DUPLICATE
        assert not selection.decisions[1].accepted

    def test_selection_canonicalizes_lexical_path_aliases(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pkg").mkdir()
            (root / "a.py").write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["./a.py", "pkg/../a.py"], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(root / "a.py"),)
        assert [decision.path for decision in selection.decisions] == [str(root / "a.py"), str(root / "a.py")]
        assert selection.decisions[1].reason == DecisionReason.DUPLICATE

    def test_selection_displays_absolute_paths_inside_current_directory_as_absolute(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files([str(target)], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(target),)
        assert selection.decisions[0].path == str(target)

    def test_selection_preserves_absolute_paths_outside_current_directory(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(target)], self._resolver(settings))

        assert selection.accepted_paths == (str(target),)
        assert selection.decisions[0].path == str(target)

    def test_selection_deduplicates_symlink_aliases_by_physical_target(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
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
                selection = file_selection.select_files(["a.py", "alias.py"], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(root / "a.py"),)
        assert selection.decisions[1].reason == DecisionReason.DUPLICATE

    def test_ruff_spec_explicit_file_bypasses_filters_without_force(self) -> None:
        settings = CheckSettings(respect_gitignore=True, force_exclude=False, include=("*.py",), exclude=("skip.py",))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.txt"
            target.write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(target)], self._resolver(settings))

        assert selection.accepted_paths == (str(target),)
        assert selection.decisions[0].reason == DecisionReason.EXPLICIT_INCLUDED

    def test_ruff_spec_force_exclude_filters_explicit_file(self) -> None:
        settings = CheckSettings(respect_gitignore=False, force_exclude=True, include=("*.py",), exclude=("skip.py",))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "skip.py"
            target.write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(target)], self._resolver(settings))

        assert selection.accepted_paths == ()
        assert selection.decisions[0].reason == DecisionReason.EXCLUDED

    def test_ruff_spec_gitignore_can_be_disabled(self) -> None:
        settings = CheckSettings(respect_gitignore=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "a.py").write_text("", encoding="utf-8")

            with unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock:
                selection = file_selection.select_files([str(root)], self._resolver(settings))

        assert not run_mock.called
        assert selection.accepted_paths == (str(root / "a.py"),)

    def test_ruff_spec_gitignore_filters_discovered_files(self) -> None:
        settings = CheckSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "keep.py").write_text("", encoding="utf-8")
            (root / "skip.py").write_text("", encoding="utf-8")

            with unittest.mock.patch("pydocformatter.file_selection.subprocess.run", side_effect=self._fake_git_check_ignore_for_root(root, {"skip.py"})):
                selection = file_selection.select_files([str(root)], self._resolver(settings))

        decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
        assert selection.accepted_paths == (str(root / "keep.py"),)
        assert decisions_by_name["skip.py"].reason == DecisionReason.GITIGNORED

    def test_ruff_spec_non_git_directory_does_not_warn(self) -> None:
        settings = CheckSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("", encoding="utf-8")
            stdout = StringIO()

            with unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock, contextlib.redirect_stdout(stdout):
                selection = file_selection.select_files([str(root)], self._resolver(settings))

        assert not run_mock.called
        assert stdout.getvalue() == ""
        assert selection.accepted_paths == (str(root / "a.py"),)

    def test_ruff_spec_gitignore_check_failure_aborts_file_selection(self) -> None:
        settings = CheckSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "b.py").write_text("", encoding="utf-8")

            with (
                unittest.mock.patch("pydocformatter.file_selection.subprocess.run", return_value=subprocess.CompletedProcess(["git"], 128, stdout=b"", stderr=b"fatal: no such command")),
                pytest.raises(file_selection.FileSelectionError, match=rf"{root}: Unable to apply gitignore filtering: fatal: no such command"),
            ):
                file_selection.select_files([str(root)], self._resolver(settings))

    def test_ruff_spec_gitignore_setting_comes_from_cwd_not_child_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "pkg").mkdir(parents=True)
            ignored = root / "src" / "pkg" / "ignored.py"
            keep = root / "src" / "pkg" / "keep.py"
            ignored.write_text("", encoding="utf-8")
            keep.write_text("", encoding="utf-8")
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\n', encoding="utf-8")
            (root / "src" / "pkg" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with unittest.mock.patch("pydocformatter.file_selection.subprocess.run", side_effect=self._fake_git_check_ignore_for_root(root, {"src/pkg/ignored.py"})):
                    selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(keep),)
        decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
        assert decisions_by_name["ignored.py"].reason == DecisionReason.GITIGNORED

    def test_ruff_spec_disabled_gitignore_from_cwd_ignores_child_config_enabling_it(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "pkg").mkdir(parents=True)
            ignored = root / "src" / "pkg" / "ignored.py"
            keep = root / "src" / "pkg" / "keep.py"
            ignored.write_text("", encoding="utf-8")
            keep.write_text("", encoding="utf-8")
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            (root / "src" / "pkg" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = true\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with unittest.mock.patch("pydocformatter.file_selection.subprocess.run") as run_mock:
                    selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        assert not run_mock.called
        assert selection.accepted_paths == (str(ignored), str(keep))

    def test_ruff_spec_gitignore_setting_is_not_taken_from_each_positional_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "left").mkdir()
            (root / "right").mkdir()
            (root / "left" / "ignored.py").write_text("", encoding="utf-8")
            (root / "left" / "keep.py").write_text("", encoding="utf-8")
            (root / "right" / "ignored.py").write_text("", encoding="utf-8")
            (root / "right" / "keep.py").write_text("", encoding="utf-8")
            (root / "left" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = true\n', encoding="utf-8")
            (root / "right" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with unittest.mock.patch("pydocformatter.file_selection.subprocess.run", side_effect=self._fake_git_check_ignore_for_root(root, {"left/ignored.py", "right/ignored.py"})):
                    selection = file_selection.select_files(["left", "right"], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(root / "left" / "keep.py"), str(root / "right" / "keep.py"))

    def test_ruff_spec_slash_patterns_are_not_git_root_relative_for_cwd_based_settings(self) -> None:
        settings = CheckSettings(respect_gitignore=False, exclude=("src/pkg/*.py",))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "pkg").mkdir(parents=True)
            target = root / "src" / "pkg" / "a.py"
            target.write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                selection = file_selection.select_files([str(root / "src")], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == (str(target),)
        assert selection.decisions[0].reason == DecisionReason.INCLUDED

    def test_ruff_spec_auto_config_patterns_are_config_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src" / "pkg").mkdir(parents=True)
            target = root / "src" / "pkg" / "a.py"
            target.write_text("", encoding="utf-8")
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["src/pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                selection = file_selection.select_files([str(root / "src")], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == ()
        assert selection.decisions[0].reason == DecisionReason.EXCLUDED

    def test_ruff_spec_inline_config_patterns_are_current_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src" / "pkg").mkdir(parents=True)
            target = root / "src" / "pkg" / "a.py"
            target.write_text("", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                excluding_resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True, config_options=('include = ["*.py"]\nexclude = ["pkg/*.py"]',)))
                included_resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True, config_options=('include = ["*.py"]\nexclude = ["src/pkg/*.py"]',)))
                excluded = file_selection.select_files(["."], excluding_resolver)
                included = file_selection.select_files(["."], included_resolver)
            finally:
                os.chdir(previous_cwd)

        assert excluded.accepted_paths == ()
        assert included.accepted_paths == (str(target),)

    def test_ruff_spec_explicit_config_file_patterns_are_current_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / "config" / "pydocfmt.toml"
            repo = root / "repo"
            (repo / "src" / "pkg").mkdir(parents=True)
            target = repo / "src" / "pkg" / "a.py"
            target.write_text("", encoding="utf-8")
            config.parent.mkdir()
            config.write_text('include = ["*.py"]\nexclude = ["src/pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")

            previous_cwd = os.getcwd()
            os.chdir(repo)
            try:
                resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),)))
                from_repo = file_selection.select_files(["."], resolver)
            finally:
                os.chdir(previous_cwd)

            os.chdir(repo / "src")
            try:
                resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),)))
                from_src = file_selection.select_files(["."], resolver)
            finally:
                os.chdir(previous_cwd)

            config.write_text('include = ["*.py"]\nexclude = ["pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            os.chdir(repo / "src")
            try:
                resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),)))
                changed_pattern = file_selection.select_files(["."], resolver)
            finally:
                os.chdir(previous_cwd)

        assert from_repo.accepted_paths == ()
        assert from_src.accepted_paths == (str(target),)
        assert changed_pattern.accepted_paths == ()

    def test_ruff_spec_explicit_config_file_ignores_auto_discovered_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / "config" / "pydocfmt.toml"
            (root / "auto_skip.py").write_text("", encoding="utf-8")
            (root / "keep.py").write_text("", encoding="utf-8")
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["auto_skip.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            config.parent.mkdir()
            config.write_text('include = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),))))
            finally:
                os.chdir(previous_cwd)

        assert self._selected_relative_paths(selection, root) == ("auto_skip.py", "keep.py")

    def test_ruff_spec_multiple_explicit_config_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_a = root / "a.toml"
            config_b = root / "b.toml"
            config_a.write_text('include = ["*.py"]\n', encoding="utf-8")
            config_b.write_text('include = ["*.py"]\n', encoding="utf-8")

            with pytest.raises(ValueError, match="Only one --config=PATH"):
                SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config_a), str(config_b)))).profile_for_path(str(root))

    def test_ruff_spec_cli_exclude_patterns_are_current_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src" / "pkg").mkdir(parents=True)
            target = root / "src" / "pkg" / "a.py"
            target.write_text("", encoding="utf-8")
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                excluding_resolver = SETTINGS_SCHEMA.resolver(args=argparse.Namespace(exclude=["pkg/*.py"]))
                included_resolver = SETTINGS_SCHEMA.resolver(args=argparse.Namespace(exclude=["src/pkg/*.py"]))
                excluded = file_selection.select_files(["."], excluding_resolver)
                included = file_selection.select_files(["."], included_resolver)
            finally:
                os.chdir(previous_cwd)

        assert excluded.accepted_paths == ()
        assert included.accepted_paths == (str(target),)

    def test_ruff_spec_include_pattern_shapes(self) -> None:
        cases = {"*.py": ("pkg/a.py", "src/pkg/a.py"), "pkg/*.py": ("pkg/a.py",), "src/pkg/*.py": ("src/pkg/a.py",), "*.foo": ("src/pkg/named.foo",)}
        for pattern, expected_paths in cases.items():
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / "pkg").mkdir()
                (root / "src" / "pkg").mkdir(parents=True)
                (root / "pkg" / "a.py").write_text("", encoding="utf-8")
                (root / "src" / "pkg" / "a.py").write_text("", encoding="utf-8")
                (root / "src" / "pkg" / "named.foo").write_text("", encoding="utf-8")
                (root / "pyproject.toml").write_text(f'[tool.pydocfmt]\ninclude = ["{pattern}"]\nrespect-gitignore = false\n', encoding="utf-8")
                previous_cwd = os.getcwd()
                os.chdir(root)
                try:
                    selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())
                finally:
                    os.chdir(previous_cwd)

                assert self._selected_relative_paths(selection, root) == expected_paths

    def test_ruff_spec_directory_shaped_include_patterns(self) -> None:
        cases = {"src": (), "src/": (), "src/**": ("src/a.py",), "**": ("pyproject.toml", "src/a.py")}
        for pattern, expected_paths in cases.items():
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / "src").mkdir()
                (root / "src" / "a.py").write_text("", encoding="utf-8")
                (root / "pyproject.toml").write_text(f'[tool.pydocfmt]\ninclude = ["{pattern}"]\nrespect-gitignore = false\n', encoding="utf-8")
                previous_cwd = os.getcwd()
                os.chdir(root)
                try:
                    selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())
                finally:
                    os.chdir(previous_cwd)

                assert self._selected_relative_paths(selection, root) == expected_paths

    def test_ruff_spec_exclude_pattern_shapes(self) -> None:
        cases = {
            "pkg": ("src/generated/a.py",),
            "pkg/*.py": ("src/generated/a.py", "src/pkg/a.py"),
            "**/pkg/*.py": ("src/generated/a.py",),
            "src/generated": ("pkg/a.py", "src/pkg/a.py"),
            "generated": ("pkg/a.py", "src/pkg/a.py"),
        }
        for pattern, expected_paths in cases.items():
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / "pkg").mkdir()
                (root / "src" / "pkg").mkdir(parents=True)
                (root / "src" / "generated").mkdir(parents=True)
                (root / "pkg" / "a.py").write_text("", encoding="utf-8")
                (root / "src" / "pkg" / "a.py").write_text("", encoding="utf-8")
                (root / "src" / "generated" / "a.py").write_text("", encoding="utf-8")
                (root / "pyproject.toml").write_text(f'[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["{pattern}"]\nrespect-gitignore = false\n', encoding="utf-8")
                previous_cwd = os.getcwd()
                os.chdir(root)
                try:
                    selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())
                finally:
                    os.chdir(previous_cwd)

                assert self._selected_relative_paths(selection, root) == expected_paths

    def test_ruff_spec_child_config_overrides_parent_file_exclude_but_not_parent_directory_prune(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package = root / "src" / "pkg"
            package.mkdir(parents=True)
            target = package / "a.py"
            target.write_text("", encoding="utf-8")
            (package / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["src/pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        assert str(target) in selection.accepted_paths

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package = root / "src" / "pkg"
            package.mkdir(parents=True)
            target = package / "a.py"
            target.write_text("", encoding="utf-8")
            (package / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
            (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["src/pkg"]\nrespect-gitignore = false\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        assert str(target) not in selection.accepted_paths
        assert DecisionReason.EXCLUDED in {decision.reason for decision in selection.decisions}

    def test_ruff_spec_direct_excluded_directory_is_skipped(self) -> None:
        settings = CheckSettings(respect_gitignore=False, exclude=("src/generated",))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "generated").mkdir(parents=True)
            (root / "src" / "generated" / "a.py").write_text("", encoding="utf-8")

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["src/generated"], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == ()
        assert selection.decisions[0].path == str(root / "src" / "generated")
        assert selection.decisions[0].reason == DecisionReason.EXCLUDED

    def test_ruff_spec_force_exclude_filters_explicit_directory_by_cli_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package = root / "pkg"
            package.mkdir()
            (package / "a.py").write_text("", encoding="utf-8")
            (package / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["pkg"]\nrespect-gitignore = false\nforce-exclude = true\n', encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files(["pkg"], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == ()
        assert selection.decisions[0].path == str(package)
        assert selection.decisions[0].reason == DecisionReason.EXCLUDED

    def test_pruned_excluded_directory_is_reported_as_decision(self) -> None:
        settings = CheckSettings(respect_gitignore=False, exclude=("generated",))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "generated").mkdir()
            (root / "generated" / "ignored.py").write_text("", encoding="utf-8")

            selection = file_selection.select_files([str(root)], self._resolver(settings))

        decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
        assert selection.accepted_paths == (str(root / "a.py"),)
        assert decisions_by_name["generated"].reason == DecisionReason.EXCLUDED
        assert "ignored.py" not in decisions_by_name

    def test_ruff_spec_slash_directory_exclude_filters_descendant_file(self) -> None:
        settings = CheckSettings(respect_gitignore=False, force_exclude=True, exclude=("src/generated",))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            (root / "src" / "generated").mkdir(parents=True)
            target = root / "src" / "generated" / "a.py"
            target.write_text("", encoding="utf-8")

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                selection = file_selection.select_files([str(target)], self._resolver(settings))
            finally:
                os.chdir(previous_cwd)

        assert selection.accepted_paths == ()
        assert selection.decisions[0].reason == DecisionReason.EXCLUDED

    def test_gitignore_query_encodes_surrogate_paths(self) -> None:
        settings = CheckSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            surrogate_path = "bad_\udcff.py"
            target = root / surrogate_path
            target.write_text("", encoding="utf-8")
            expected_command = ["git", "-C", str(root), "check-ignore", "--stdin", "--no-index", "-z"]

            def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
                assert args[0] == expected_command
                stdin_bytes = kwargs["input"]
                assert stdin_bytes == b"bad_\xff.py\0"
                return subprocess.CompletedProcess(expected_command, 0, stdout=b"bad_\xff.py\0", stderr=b"")

            with unittest.mock.patch("pydocformatter.file_selection.subprocess.run", side_effect=fake_run):
                selection = file_selection.select_files([str(root)], self._resolver(settings))

        assert selection.accepted_paths == ()
        assert selection.decisions[0].reason == DecisionReason.GITIGNORED

    def test_gitignore_query_uses_real_paths_for_symlinked_directory_traversal(self) -> None:
        settings = CheckSettings(respect_gitignore=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            real = root / "real"
            alias = root / "alias"
            real.mkdir()
            (real / "ignored.py").write_text("", encoding="utf-8")
            (real / "keep.py").write_text("", encoding="utf-8")
            try:
                alias.symlink_to(real, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks are not available: {error}")

            with unittest.mock.patch("pydocformatter.file_selection.subprocess.run", side_effect=self._fake_git_check_ignore_for_root(root, {"real/ignored.py"})):
                selection = file_selection.select_files([str(alias)], self._resolver(settings))

        assert selection.accepted_paths == (str(alias / "keep.py"),)
        decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
        assert decisions_by_name["ignored.py"].reason == DecisionReason.GITIGNORED


if __name__ == "__main__":
    unittest.main()
