# Future imports
from __future__ import annotations

# Standard library imports
import argparse
import tempfile
import contextlib
import subprocess
import dataclasses
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
from tests import git_helpers


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture

    # First-party imports
    import pydocformatter.settings as settings_core


def _selected_relative_paths(selection: file_selection.SelectionResult, root: Path) -> tuple[str, ...]:
    """Return accepted paths relative to a temporary root."""
    return tuple(Path(path).relative_to(root).as_posix() for path in selection.accepted_paths)


def _resolver(settings: CheckSettings) -> settings_core.SettingsResolver[CheckSettings]:
    """Return a resolver with static test settings applied as overrides."""
    return SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True), field_overrides=dataclasses.asdict(settings))


def test_ruff_spec_deterministic_directory_order() -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "z_dir").mkdir()
        (root / "a_dir").mkdir()
        (root / "b.py").write_text("", encoding="utf-8")
        (root / "a.py").write_text("", encoding="utf-8")
        (root / "z_dir" / "c.py").write_text("", encoding="utf-8")
        (root / "a_dir" / "d.py").write_text("", encoding="utf-8")

        selection = file_selection.select_files([str(root)], _resolver(settings))

    collected = [Path(decision.path).relative_to(root).as_posix() for decision in selection.decisions]
    assert collected == ["a.py", "b.py", "a_dir/d.py", "z_dir/c.py"]


def test_selection_displays_real_explicit_paths_as_absolute(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("", encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["a.py"], _resolver(settings))

    assert selection.accepted_paths == (str(root / "a.py"),)
    assert selection.decisions[0].path == str(root / "a.py")


def test_virtual_file_is_not_walked_when_path_exists_as_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False, force_exclude=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pkg.py").mkdir()
        (root / "pkg.py" / "child.py").write_text("", encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_virtual_file("pkg.py", _resolver(settings))

    assert selection.accepted_paths == (str(root / "pkg.py"),)
    assert [decision.path for decision in selection.decisions] == [str(root / "pkg.py")]


def test_selection_deduplicates_equivalent_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text("", encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["a.py", str(target)], _resolver(settings))

    assert selection.accepted_paths == (str(root / "a.py"),)
    assert selection.decisions[0].reason == DecisionReason.EXPLICIT_INCLUDED
    assert selection.decisions[1].reason == DecisionReason.DUPLICATE
    assert not selection.decisions[1].accepted


def test_selection_canonicalizes_lexical_path_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pkg").mkdir()
        (root / "a.py").write_text("", encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["./a.py", "pkg/../a.py"], _resolver(settings))

    assert selection.accepted_paths == (str(root / "a.py"),)
    assert [decision.path for decision in selection.decisions] == [str(root / "a.py"), str(root / "a.py")]
    assert selection.decisions[1].reason == DecisionReason.DUPLICATE


def test_selection_displays_absolute_paths_inside_current_directory_as_absolute(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text("", encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files([str(target)], _resolver(settings))

    assert selection.accepted_paths == (str(target),)
    assert selection.decisions[0].path == str(target)


def test_selection_preserves_absolute_paths_outside_current_directory() -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text("", encoding="utf-8")

        selection = file_selection.select_files([str(target)], _resolver(settings))

    assert selection.accepted_paths == (str(target),)
    assert selection.decisions[0].path == str(target)


def test_selection_deduplicates_symlink_aliases_by_physical_target(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        alias = root / "alias.py"
        target.write_text("", encoding="utf-8")
        try:
            alias.symlink_to(target)
        except OSError as error:
            pytest.skip(f"symlinks are not available: {error}")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["a.py", "alias.py"], _resolver(settings))

    assert selection.accepted_paths == (str(root / "a.py"),)
    assert selection.decisions[1].reason == DecisionReason.DUPLICATE


def test_ruff_spec_explicit_file_bypasses_filters_without_force() -> None:
    settings = CheckSettings(respect_gitignore=True, force_exclude=False, include=("*.py",), exclude=("skip.py",))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "skip.txt"
        target.write_text("", encoding="utf-8")

        selection = file_selection.select_files([str(target)], _resolver(settings))

    assert selection.accepted_paths == (str(target),)
    assert selection.decisions[0].reason == DecisionReason.EXPLICIT_INCLUDED


def test_ruff_spec_force_exclude_filters_explicit_file() -> None:
    settings = CheckSettings(respect_gitignore=False, force_exclude=True, include=("*.py",), exclude=("skip.py",))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "skip.py"
        target.write_text("", encoding="utf-8")

        selection = file_selection.select_files([str(target)], _resolver(settings))

    assert selection.accepted_paths == ()
    assert selection.decisions[0].reason == DecisionReason.EXCLUDED


def test_ruff_spec_gitignore_can_be_disabled(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "a.py").write_text("", encoding="utf-8")
        run_mock = mocker.patch("pydocformatter.file_selection.subprocess.run", autospec=True)
        selection = file_selection.select_files([str(root)], _resolver(settings))

    assert not run_mock.called
    assert selection.accepted_paths == (str(root / "a.py"),)


def test_ruff_spec_gitignore_filters_discovered_files(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "keep.py").write_text("", encoding="utf-8")
        (root / "skip.py").write_text("", encoding="utf-8")
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=git_helpers.fake_git_check_ignore_for_root(root, {"skip.py"}), autospec=True)
        selection = file_selection.select_files([str(root)], _resolver(settings))

    decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
    assert selection.accepted_paths == (str(root / "keep.py"),)
    assert decisions_by_name["skip.py"].reason == DecisionReason.GITIGNORED


def test_ruff_spec_non_git_directory_does_not_warn(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("", encoding="utf-8")
        stdout = StringIO()
        run_mock = mocker.patch("pydocformatter.file_selection.subprocess.run", autospec=True)

        with contextlib.redirect_stdout(stdout):
            selection = file_selection.select_files([str(root)], _resolver(settings))

    assert not run_mock.called
    assert stdout.getvalue() == ""
    assert selection.accepted_paths == (str(root / "a.py"),)


def test_ruff_spec_gitignore_check_failure_aborts_file_selection(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "a.py").write_text("", encoding="utf-8")
        (root / "b.py").write_text("", encoding="utf-8")
        mocker.patch("pydocformatter.file_selection.subprocess.run", return_value=subprocess.CompletedProcess(["git"], 128, stdout=b"", stderr=b"fatal: no such command"), autospec=True)

        with pytest.raises(file_selection.FileSelectionError, match=rf"{root}: Unable to apply gitignore filtering: fatal: no such command"):
            file_selection.select_files([str(root)], _resolver(settings))


def test_ruff_spec_gitignore_setting_comes_from_cwd_not_child_config(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "src" / "pkg").mkdir(parents=True)
        ignored = root / "src" / "pkg" / "ignored.py"
        keep = root / "src" / "pkg" / "keep.py"
        ignored.write_text("", encoding="utf-8")
        keep.write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\n', encoding="utf-8")
        (root / "src" / "pkg" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=git_helpers.fake_git_check_ignore_for_root(root, {"src/pkg/ignored.py"}), autospec=True)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())

    assert selection.accepted_paths == (str(keep),)
    decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
    assert decisions_by_name["ignored.py"].reason == DecisionReason.GITIGNORED


def test_ruff_spec_disabled_gitignore_from_cwd_ignores_child_config_enabling_it(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "src" / "pkg").mkdir(parents=True)
        ignored = root / "src" / "pkg" / "ignored.py"
        keep = root / "src" / "pkg" / "keep.py"
        ignored.write_text("", encoding="utf-8")
        keep.write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        (root / "src" / "pkg" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = true\n', encoding="utf-8")
        monkeypatch.chdir(root)
        run_mock = mocker.patch("pydocformatter.file_selection.subprocess.run", autospec=True)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())

    assert not run_mock.called
    assert selection.accepted_paths == (str(ignored), str(keep))


def test_ruff_spec_gitignore_setting_is_not_taken_from_each_positional_directory(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "left").mkdir()
        (root / "right").mkdir()
        (root / "left" / "ignored.py").write_text("", encoding="utf-8")
        (root / "left" / "keep.py").write_text("", encoding="utf-8")
        (root / "right" / "ignored.py").write_text("", encoding="utf-8")
        (root / "right" / "keep.py").write_text("", encoding="utf-8")
        (root / "left" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = true\n', encoding="utf-8")
        (root / "right" / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=git_helpers.fake_git_check_ignore_for_root(root, {"left/ignored.py", "right/ignored.py"}), autospec=True)
        selection = file_selection.select_files(["left", "right"], SETTINGS_SCHEMA.resolver())

    assert selection.accepted_paths == (str(root / "left" / "keep.py"), str(root / "right" / "keep.py"))


def test_ruff_spec_slash_patterns_are_not_git_root_relative_for_cwd_based_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False, exclude=("src/pkg/*.py",))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "src" / "pkg").mkdir(parents=True)
        target = root / "src" / "pkg" / "a.py"
        target.write_text("", encoding="utf-8")
        monkeypatch.chdir(root / "src")
        selection = file_selection.select_files([str(root / "src")], _resolver(settings))

    assert selection.accepted_paths == (str(target),)
    assert selection.decisions[0].reason == DecisionReason.INCLUDED


def test_ruff_spec_auto_config_patterns_are_config_directory_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "src" / "pkg").mkdir(parents=True)
        target = root / "src" / "pkg" / "a.py"
        target.write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["src/pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root / "src")
        selection = file_selection.select_files([str(root / "src")], SETTINGS_SCHEMA.resolver())

    assert selection.accepted_paths == ()
    assert selection.decisions[0].reason == DecisionReason.EXCLUDED


def test_ruff_spec_inline_config_patterns_are_current_directory_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "src" / "pkg").mkdir(parents=True)
        target = root / "src" / "pkg" / "a.py"
        target.write_text("", encoding="utf-8")
        monkeypatch.chdir(root / "src")
        excluding_resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True, config_options=('include = ["*.py"]\nexclude = ["pkg/*.py"]',)))
        included_resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True, config_options=('include = ["*.py"]\nexclude = ["src/pkg/*.py"]',)))
        excluded = file_selection.select_files(["."], excluding_resolver)
        included = file_selection.select_files(["."], included_resolver)

    assert excluded.accepted_paths == ()
    assert included.accepted_paths == (str(target),)


def test_ruff_spec_explicit_config_file_patterns_are_current_directory_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config = root / "config" / "pydocfmt.toml"
        repo = root / "repo"
        (repo / "src" / "pkg").mkdir(parents=True)
        target = repo / "src" / "pkg" / "a.py"
        target.write_text("", encoding="utf-8")
        config.parent.mkdir()
        config.write_text('include = ["*.py"]\nexclude = ["src/pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")

        with monkeypatch.context() as patch:
            patch.chdir(repo)
            resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),)))
            from_repo = file_selection.select_files(["."], resolver)

        with monkeypatch.context() as patch:
            patch.chdir(repo / "src")
            resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),)))
            from_src = file_selection.select_files(["."], resolver)

        config.write_text('include = ["*.py"]\nexclude = ["pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        with monkeypatch.context() as patch:
            patch.chdir(repo / "src")
            resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),)))
            changed_pattern = file_selection.select_files(["."], resolver)

    assert from_repo.accepted_paths == ()
    assert from_src.accepted_paths == (str(target),)
    assert changed_pattern.accepted_paths == ()


def test_ruff_spec_explicit_config_file_ignores_auto_discovered_config(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config = root / "config" / "pydocfmt.toml"
        (root / "auto_skip.py").write_text("", encoding="utf-8")
        (root / "keep.py").write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["auto_skip.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        config.parent.mkdir()
        config.write_text('include = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config),))))

    assert _selected_relative_paths(selection, root) == ("auto_skip.py", "keep.py")


def test_ruff_spec_multiple_explicit_config_files_are_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_a = root / "a.toml"
        config_b = root / "b.toml"
        config_a.write_text('include = ["*.py"]\n', encoding="utf-8")
        config_b.write_text('include = ["*.py"]\n', encoding="utf-8")

        with pytest.raises(ValueError, match="Only one --config=PATH"):
            SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(config_options=(str(config_a), str(config_b)))).profile_for_path(str(root))


def test_ruff_spec_cli_exclude_patterns_are_current_directory_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "src" / "pkg").mkdir(parents=True)
        target = root / "src" / "pkg" / "a.py"
        target.write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root / "src")
        excluding_resolver = SETTINGS_SCHEMA.resolver(args=argparse.Namespace(exclude=["pkg/*.py"]))
        included_resolver = SETTINGS_SCHEMA.resolver(args=argparse.Namespace(exclude=["src/pkg/*.py"]))
        excluded = file_selection.select_files(["."], excluding_resolver)
        included = file_selection.select_files(["."], included_resolver)

    assert excluded.accepted_paths == ()
    assert included.accepted_paths == (str(target),)


@pytest.mark.parametrize(
    ("pattern", "expected_paths"),
    [
        pytest.param("*.py", ("pkg/a.py", "src/pkg/a.py"), id="basename-python"),
        pytest.param("pkg/*.py", ("pkg/a.py",), id="bare-directory-python"),
        pytest.param("src/pkg/*.py", ("src/pkg/a.py",), id="project-relative-python"),
        pytest.param("*.foo", ("src/pkg/named.foo",), id="basename-custom-extension"),
    ],
)
def test_ruff_spec_include_pattern_shapes(pattern: str, expected_paths: tuple[str, ...], monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pkg").mkdir()
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "pkg" / "a.py").write_text("", encoding="utf-8")
        (root / "src" / "pkg" / "a.py").write_text("", encoding="utf-8")
        (root / "src" / "pkg" / "named.foo").write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text(f'[tool.pydocfmt]\ninclude = ["{pattern}"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())

        assert _selected_relative_paths(selection, root) == expected_paths


@pytest.mark.parametrize(
    ("pattern", "expected_paths"),
    [
        pytest.param("src", (), id="directory-name"),
        pytest.param("src/", (), id="directory-with-slash"),
        pytest.param("src/**", ("src/a.py",), id="directory-descendants"),
        pytest.param("**", ("pyproject.toml", "src/a.py"), id="all-descendants"),
    ],
)
def test_ruff_spec_directory_shaped_include_patterns(pattern: str, expected_paths: tuple[str, ...], monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "src").mkdir()
        (root / "src" / "a.py").write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text(f'[tool.pydocfmt]\ninclude = ["{pattern}"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())

        assert _selected_relative_paths(selection, root) == expected_paths


@pytest.mark.parametrize(
    ("pattern", "expected_paths"),
    [
        pytest.param("pkg", ("src/generated/a.py",), id="bare-directory"),
        pytest.param("pkg/*.py", ("src/generated/a.py", "src/pkg/a.py"), id="bare-directory-file"),
        pytest.param("**/pkg/*.py", ("src/generated/a.py",), id="globstar-directory-file"),
        pytest.param("src/generated", ("pkg/a.py", "src/pkg/a.py"), id="project-relative-directory"),
        pytest.param("generated", ("pkg/a.py", "src/pkg/a.py"), id="bare-generated-directory"),
    ],
)
def test_ruff_spec_exclude_pattern_shapes(pattern: str, expected_paths: tuple[str, ...], monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pkg").mkdir()
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "generated").mkdir(parents=True)
        (root / "pkg" / "a.py").write_text("", encoding="utf-8")
        (root / "src" / "pkg" / "a.py").write_text("", encoding="utf-8")
        (root / "src" / "generated" / "a.py").write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text(f'[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["{pattern}"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())

        assert _selected_relative_paths(selection, root) == expected_paths


def test_ruff_spec_child_config_overrides_parent_file_exclude_but_not_parent_directory_prune(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        package = root / "src" / "pkg"
        package.mkdir(parents=True)
        target = package / "a.py"
        target.write_text("", encoding="utf-8")
        (package / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["src/pkg/*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())

    assert str(target) in selection.accepted_paths

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        package = root / "src" / "pkg"
        package.mkdir(parents=True)
        target = package / "a.py"
        target.write_text("", encoding="utf-8")
        (package / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["src/pkg"]\nrespect-gitignore = false\n', encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["."], SETTINGS_SCHEMA.resolver())

    assert str(target) not in selection.accepted_paths
    assert DecisionReason.EXCLUDED in {decision.reason for decision in selection.decisions}


def test_ruff_spec_direct_excluded_directory_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False, exclude=("src/generated",))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "src" / "generated").mkdir(parents=True)
        (root / "src" / "generated" / "a.py").write_text("", encoding="utf-8")

        monkeypatch.chdir(root)
        selection = file_selection.select_files(["src/generated"], _resolver(settings))

    assert selection.accepted_paths == ()
    assert selection.decisions[0].path == str(root / "src" / "generated")
    assert selection.decisions[0].reason == DecisionReason.EXCLUDED


def test_ruff_spec_force_exclude_filters_explicit_directory_by_cli_path(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        package = root / "pkg"
        package.mkdir()
        (package / "a.py").write_text("", encoding="utf-8")
        (package / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["pkg"]\nrespect-gitignore = false\nforce-exclude = true\n', encoding="utf-8")
        monkeypatch.chdir(root)
        selection = file_selection.select_files(["pkg"], SETTINGS_SCHEMA.resolver())

    assert selection.accepted_paths == ()
    assert selection.decisions[0].path == str(package)
    assert selection.decisions[0].reason == DecisionReason.EXCLUDED


def test_pruned_excluded_directory_is_reported_as_decision() -> None:
    settings = CheckSettings(respect_gitignore=False, exclude=("generated",))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("", encoding="utf-8")
        (root / "generated").mkdir()
        (root / "generated" / "ignored.py").write_text("", encoding="utf-8")

        selection = file_selection.select_files([str(root)], _resolver(settings))

    decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
    assert selection.accepted_paths == (str(root / "a.py"),)
    assert decisions_by_name["generated"].reason == DecisionReason.EXCLUDED
    assert "ignored.py" not in decisions_by_name


def test_ruff_spec_slash_directory_exclude_filters_descendant_file(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False, force_exclude=True, exclude=("src/generated",))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "src" / "generated").mkdir(parents=True)
        target = root / "src" / "generated" / "a.py"
        target.write_text("", encoding="utf-8")

        monkeypatch.chdir(root)
        selection = file_selection.select_files([str(target)], _resolver(settings))

    assert selection.accepted_paths == ()
    assert selection.decisions[0].reason == DecisionReason.EXCLUDED


def test_gitignore_query_encodes_surrogate_paths(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        surrogate_path = "bad_\udcff.py"
        target = root / surrogate_path
        target.write_text("", encoding="utf-8")
        expected_command = ["git", "-C", str(root), "check-ignore", "--stdin", "--no-index", "-z"]

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            assert args[0] == expected_command
            stdin_bytes = kwargs["input"]
            assert stdin_bytes == b"bad_\xff.py\0"
            return subprocess.CompletedProcess(expected_command, 0, stdout=b"bad_\xff.py\0", stderr=b"")

        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=fake_run, autospec=True)
        selection = file_selection.select_files([str(root)], _resolver(settings))

    assert selection.accepted_paths == ()
    assert selection.decisions[0].reason == DecisionReason.GITIGNORED


def test_gitignore_query_uses_real_paths_for_symlinked_directory_traversal(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        real = root / "real"
        alias = root / "alias"
        real.mkdir()
        (real / "ignored.py").write_text("", encoding="utf-8")
        (real / "keep.py").write_text("", encoding="utf-8")
        try:
            alias.symlink_to(real, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"symlinks are not available: {error}")
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=git_helpers.fake_git_check_ignore_for_root(root, {"real/ignored.py"}), autospec=True)
        selection = file_selection.select_files([str(alias)], _resolver(settings))

    assert selection.accepted_paths == (str(alias / "keep.py"),)
    decisions_by_name = {Path(decision.path).name: decision for decision in selection.decisions}
    assert decisions_by_name["ignored.py"].reason == DecisionReason.GITIGNORED
