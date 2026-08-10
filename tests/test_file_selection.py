# Future imports
from __future__ import annotations

# Standard library imports
import os
import typing
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
import pydocformatter.cache.directory as cache_directory
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


def test_directory_walk_resolves_profiles_per_directory_without_file_lookups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (tmp_path / "root.py").write_text("", encoding="utf-8")
    (first / "first.py").write_text("", encoding="utf-8")
    (second / "second.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(isolated=True), field_overrides={"respect_gitignore": False})

    class CountingResolver:
        def __init__(self) -> None:
            self.calls: list[str | None] = []

        def profile_for_path(self, path: str | None = None) -> settings_core.SettingsProfile[CheckSettings]:
            self.calls.append(path)
            return profile

    counting_resolver = CountingResolver()
    resolver = typing.cast("settings_core.SettingsResolver[CheckSettings]", counting_resolver)

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert _selected_relative_paths(selection, tmp_path) == ("root.py", "first/first.py", "second/second.py")
    assert counting_resolver.calls == [str(tmp_path), str(tmp_path), str(tmp_path), str(first), str(second)]
    assert all(path is None or not path.endswith(".py") for path in counting_resolver.calls)


def test_walked_files_receive_their_exact_walk_root_profile_with_nested_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child = tmp_path / "child"
    child.mkdir()
    root_file = tmp_path / "root.py"
    child_file = child / "child.py"
    root_file.write_text("", encoding="utf-8")
    child_file.write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
    (child / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nline-length = 91\nrespect-gitignore = false\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = SETTINGS_SCHEMA.resolver()

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert selection.profile_for_path(str(root_file)) is resolver.profile_for_path(str(tmp_path))
    assert selection.profile_for_path(str(child_file)) is resolver.profile_for_path(str(child))
    assert selection.profile_for_path(str(root_file)) is not selection.profile_for_path(str(child_file))
    assert selection.profile_for_path(str(child_file)).settings.line_length == 91


def test_multiple_walked_children_share_root_profile_without_changing_decision_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a_dir = tmp_path / "a_dir"
    z_dir = tmp_path / "z_dir"
    a_dir.mkdir()
    z_dir.mkdir()
    (tmp_path / "root.py").write_text("", encoding="utf-8")
    (a_dir / "a.py").write_text("", encoding="utf-8")
    (z_dir / "z.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = _resolver(CheckSettings(respect_gitignore=False))

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert _selected_relative_paths(selection, tmp_path) == ("root.py", "a_dir/a.py", "z_dir/z.py")
    profiles = tuple(selected.profile for selected in selection.selected_files)
    assert all(profile is profiles[0] for profile in profiles)


def test_internal_cache_directory_is_resolved_once_from_run_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    for name in ("a", "b", "c"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / f"{name}.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = _resolver(CheckSettings(respect_gitignore=False))
    cache_directory_for_profile = mocker.spy(file_selection.cache_directory, "cache_directory_for_profile")

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert len(selection.accepted_paths) == 3
    assert cache_directory_for_profile.call_count == 1


@pytest.mark.parametrize("source", ["auto", "cli"])
def test_owned_custom_relative_cache_directories_preserve_source_base_pruning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    cache_root = tmp_path / "runtime" / "cache"
    cache_root.parent.mkdir()
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache_root))
    skipped = cache_root / "skipped.py"
    kept = tmp_path / "kept.py"
    skipped.write_text("", encoding="utf-8")
    kept.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    if source == "auto":
        (tmp_path / "pyproject.toml").write_text('[tool.pydocfmt]\ncache-dir = "runtime/cache"\ninclude = ["*.py"]\nrespect-gitignore = false\n', encoding="utf-8")
        resolver = SETTINGS_SCHEMA.resolver()
    else:
        resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True), args=argparse.Namespace(cache_dir="runtime/cache"), field_overrides={"respect_gitignore": False})

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert selection.accepted_paths == (str(kept),)
    cache_decisions = tuple(decision for decision in selection.decisions if decision.reason is DecisionReason.CACHE_DIRECTORY)
    assert tuple(decision.path for decision in cache_decisions) == (str(cache_root),)
    assert str(skipped) not in tuple(decision.path for decision in selection.decisions)


def test_nonempty_unowned_run_cache_directory_is_selected_normally(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_root = tmp_path / "runtime" / "cache"
    cache_root.mkdir(parents=True)
    source = cache_root / "source.py"
    source.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = _resolver(CheckSettings(cache_dir=str(cache_root), exclude=(), respect_gitignore=False))

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert selection.accepted_paths == (str(source),)
    assert all(decision.reason is not DecisionReason.CACHE_DIRECTORY for decision in selection.decisions)


def test_empty_unowned_run_cache_directory_is_pruned_only_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    monkeypatch.chdir(tmp_path)

    enabled = file_selection.select_files([str(tmp_path)], _resolver(CheckSettings(cache=True, cache_dir=str(cache_root), exclude=(), respect_gitignore=False)))
    disabled = file_selection.select_files([str(tmp_path)], _resolver(CheckSettings(cache=False, cache_dir=str(cache_root), exclude=(), respect_gitignore=False)))

    assert tuple(decision.reason for decision in enabled.decisions) == (DecisionReason.CACHE_DIRECTORY,)
    assert not disabled.decisions


def test_owned_run_cache_directory_is_pruned_when_cache_is_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_root = tmp_path / "cache"
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache_root))
    hidden = cache_root / "hidden.py"
    hidden.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = _resolver(CheckSettings(cache=False, cache_dir=str(cache_root), exclude=(), respect_gitignore=False))

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert tuple(decision.reason for decision in selection.decisions if decision.path == str(cache_root)) == (DecisionReason.CACHE_DIRECTORY,)
    assert str(hidden) not in tuple(decision.path for decision in selection.decisions)


def test_symlinked_run_cache_directory_is_not_internal_cache_pruned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "cache-target"
    target.mkdir()
    cache_root = tmp_path / "cache"
    try:
        cache_root.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    monkeypatch.chdir(tmp_path)
    resolver = _resolver(CheckSettings(cache_dir=str(cache_root), exclude=(), respect_gitignore=False))

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert all(decision.reason is not DecisionReason.CACHE_DIRECTORY for decision in selection.decisions)


def test_owned_cache_directory_is_pruned_through_a_symlinked_parent_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = tmp_path / "real"
    cache_root = real / "cache"
    alias = tmp_path / "alias"
    real.mkdir()
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache_root))
    hidden = cache_root / "hidden.py"
    hidden.write_text("", encoding="utf-8")
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    monkeypatch.chdir(tmp_path)
    resolver = _resolver(CheckSettings(cache_dir=str(cache_root), exclude=(), respect_gitignore=False))

    selection = file_selection.select_files([str(alias)], resolver)

    alias_cache = alias / "cache"
    assert tuple(decision.path for decision in selection.decisions if decision.reason is DecisionReason.CACHE_DIRECTORY) == (str(alias_cache),)
    assert str(alias_cache / "hidden.py") not in tuple(decision.path for decision in selection.decisions)


def test_only_cwd_profile_cache_root_receives_internal_pruning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child = tmp_path / "child"
    run_cache = tmp_path / "run-cache"
    nested_cache = child / "nested-cache"
    child.mkdir()
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(run_cache))
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(nested_cache))
    run_hidden = run_cache / "hidden.py"
    nested_visible = nested_cache / "visible.py"
    run_hidden.write_text("", encoding="utf-8")
    nested_visible.write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.pydocfmt]\ncache-dir = "run-cache"\nexclude = []\nrespect-gitignore = false\n', encoding="utf-8")
    (child / "pyproject.toml").write_text('[tool.pydocfmt]\ncache-dir = "nested-cache"\nexclude = []\nrespect-gitignore = false\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    selection = file_selection.select_files([str(tmp_path)], SETTINGS_SCHEMA.resolver())

    assert str(nested_visible) in selection.accepted_paths
    assert str(run_hidden) not in tuple(decision.path for decision in selection.decisions)
    assert tuple(decision.path for decision in selection.decisions if decision.reason is DecisionReason.CACHE_DIRECTORY) == (str(run_cache),)


def test_traversal_root_equal_to_configured_cache_directory_remains_selectable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target.py"
    target.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolver = SETTINGS_SCHEMA.resolver(global_values=GlobalArgs(isolated=True), args=argparse.Namespace(cache_dir=str(tmp_path)), field_overrides={"respect_gitignore": False})

    selection = file_selection.select_files([str(tmp_path)], resolver)

    assert selection.accepted_paths == (str(target),)
    assert all(decision.reason is not DecisionReason.CACHE_DIRECTORY for decision in selection.decisions)


def test_parent_profile_can_still_prune_directory_before_nested_config_is_entered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child = tmp_path / "child"
    child.mkdir()
    target = child / "target.py"
    target.write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = ["child"]\nrespect-gitignore = false\n', encoding="utf-8")
    (child / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = []\nrespect-gitignore = false\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    selection = file_selection.select_files([str(tmp_path)], SETTINGS_SCHEMA.resolver())

    assert selection.accepted_paths == ()
    assert tuple((Path(decision.path).name, decision.reason) for decision in selection.decisions) == (("child", DecisionReason.EXCLUDED), ("pyproject.toml", DecisionReason.NOT_INCLUDED))
    assert str(target) not in tuple(decision.path for decision in selection.decisions)


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


def test_selection_deduplicates_mixed_case_hard_link_aliases_by_physical_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "Module.py"
        alias = root / "module.py"
        target.write_text("", encoding="utf-8")
        try:
            alias.hardlink_to(target)
        except OSError as error:
            pytest.skip(f"hard links with mixed-case names are not available: {error}")
        monkeypatch.chdir(root)
        selection = file_selection.select_files([target.name, alias.name], _resolver(settings))

    assert selection.accepted_paths == (str(target),)
    assert selection.decisions[0].reason == DecisionReason.EXPLICIT_INCLUDED
    assert selection.decisions[1].reason == DecisionReason.DUPLICATE


def test_selection_deduplicates_case_aliases_on_case_insensitive_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(respect_gitignore=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "MixedCase.py"
        alias = root / "mixedcase.py"
        target.write_text("", encoding="utf-8")
        if not alias.exists():
            pytest.skip("filesystem is case-sensitive")
        monkeypatch.chdir(root)
        selection = file_selection.select_files([target.name, alias.name], _resolver(settings))

    assert len(selection.accepted_paths) == 1
    assert tuple(decision.reason for decision in selection.decisions).count(DecisionReason.DUPLICATE) == 1


def test_path_identity_key_returns_none_for_zero_inode(mocker: MockerFixture) -> None:
    real_stat = os.stat
    zero_inode_stat = mocker.Mock(spec=os.stat_result, st_dev=11, st_ino=0)

    def selective_stat(path: str | bytes | int | os.PathLike[str] | os.PathLike[bytes], *, follow_symlinks: bool = True) -> os.stat_result:
        if path == "module.py":
            return typing.cast("os.stat_result", zero_inode_stat)
        return real_stat(path, follow_symlinks=follow_symlinks)

    mocker.patch("pydocformatter.file_selection.os.stat", side_effect=selective_stat, autospec=True)

    assert file_selection.path_identity_key("module.py") is None


def test_path_identity_key_returns_none_when_stat_fails(mocker: MockerFixture) -> None:
    real_stat = os.stat

    def selective_stat(path: str | bytes | int | os.PathLike[str] | os.PathLike[bytes], *, follow_symlinks: bool = True) -> os.stat_result:
        if path == "module.py":
            raise PermissionError("denied")
        return real_stat(path, follow_symlinks=follow_symlinks)

    mocker.patch("pydocformatter.file_selection.os.stat", side_effect=selective_stat, autospec=True)

    assert file_selection.path_identity_key("module.py") is None


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


def test_ruff_spec_missing_git_reports_actionable_file_selection_error(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "a.py").write_text("", encoding="utf-8")
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=FileNotFoundError, autospec=True)

        with pytest.raises(
            file_selection.FileSelectionError,
            match=rf"{root}: Unable to apply gitignore filtering: Git executable was not found; install Git or disable gitignore filtering with --no-respect-gitignore",
        ):
            file_selection.select_files([str(root)], _resolver(settings))


def test_ruff_spec_git_execution_oserror_reports_context(mocker: MockerFixture) -> None:
    settings = CheckSettings(respect_gitignore=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git_helpers.write_git_marker(root)
        (root / "a.py").write_text("", encoding="utf-8")
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=PermissionError("denied"), autospec=True)

        with pytest.raises(file_selection.FileSelectionError, match=rf"{root}: Unable to apply gitignore filtering: Unable to execute Git: denied"):
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
