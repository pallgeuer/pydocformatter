"""Tests for shared source-path semantics."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import typing
import pathlib
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cache.fingerprint as cache_fingerprint
from pydocformatter import formatter, rules_selection, source_path
from pydocformatter.cli.settings_check import CheckSettings, SourceLanguage
from pydocformatter.rules.definition_helpers import missing_documentation
from pydocformatter.source_path import SourcePathContext, SourcePathContextBuilder


if typing.TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


def _legacy_existing_parts(path: Path) -> tuple[str, ...]:
    """Return the module parts used before source contexts were introduced."""
    parts = [] if path.stem == "__init__" else [path.stem]
    parent = path.resolve().parent
    while (parent / "__init__.py").exists() or (parent / "__init__.pyi").exists():
        parts.append(parent.name)
        parent = parent.parent
    return tuple(reversed(parts))


def _legacy_synthetic_parts(path: str) -> tuple[str, ...]:
    """Return the former synthetic module-path derivation."""
    pure_path = pathlib.PurePath(path)
    parts = tuple(part for part in pure_path.parts if part not in {"", ".", "..", pure_path.anchor})
    module_parts = []
    for index, part in enumerate(parts):
        if index == len(parts) - 1:
            stem = pathlib.PurePath(part).stem
            if stem != "__init__":
                module_parts.append(stem)
        else:
            module_parts.append(part)
    return tuple(module_parts)


def test_existing_public_and_private_paths_retain_legacy_classification(tmp_path: Path) -> None:
    package = tmp_path / "_private_package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    target = package / "public_module.py"
    target.write_text("", encoding="utf-8")

    context = SourcePathContext.for_path(str(target))

    assert context.module_parts == _legacy_existing_parts(target)
    assert context.package_parts == ("_private_package",)
    assert not context.public
    assert missing_documentation.is_public_module_path(context) is context.public


@pytest.mark.parametrize("initializer", ["__init__.py", "__init__.pyi"])
def test_python_and_stub_package_initializers_have_equivalent_ancestry(tmp_path: Path, initializer: str) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / initializer).write_text("", encoding="utf-8")
    target = package / "module.py"
    target.write_text("", encoding="utf-8")

    context = SourcePathContext.for_path(str(target))

    assert context.package_parts == ("package",)
    assert context.module_parts == ("package", "module")
    assert context.public


def test_missing_initializer_stops_the_ancestor_walk(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    inner = outer / "inner"
    inner.mkdir(parents=True)
    (outer / "__init__.py").write_text("", encoding="utf-8")
    target = inner / "module.py"
    target.write_text("", encoding="utf-8")

    context = SourcePathContext.for_path(str(target))

    assert context.package_parts == ()
    assert context.module_parts == ("module",)


def test_filesystem_root_never_contributes_an_empty_package_part(mocker: MockerFixture) -> None:
    root = os.path.abspath(os.sep)
    mocker.patch("pydocformatter.source_path._package_initializer_exists", return_value=True, autospec=True)

    parts = SourcePathContextBuilder()._existing_package_parts(root)

    assert parts == ()


def test_package_initializer_paths_retain_package_semantics(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    target = package / "__init__.py"
    target.write_text("", encoding="utf-8")

    context = SourcePathContext.for_path(str(target))

    assert context.package_initializer
    assert context.package_parts == ("package",)
    assert context.module_parts == ("package",)


@pytest.mark.parametrize("path", ["virtual/package/module.py", "virtual/_private/module.py", "virtual/package/__init__.py", "-"])
def test_synthetic_paths_retain_legacy_module_parts(path: str) -> None:
    context = SourcePathContext.for_path(path)

    assert not context.existing
    assert context.module_parts == _legacy_synthetic_parts(path)
    assert context.public == (not any(part.startswith("_") for part in context.module_parts))


def test_private_filename_is_classified_private(tmp_path: Path) -> None:
    target = tmp_path / "_private.py"
    target.write_text("", encoding="utf-8")

    context = SourcePathContext.for_path(str(target))

    assert context.module_parts == ("_private",)
    assert not context.public


def test_package_marker_change_updates_parts_and_path_context_key(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    target = package / "module.py"
    target.write_text("", encoding="utf-8")
    before = SourcePathContext.for_path(str(target))
    before_key = cache_fingerprint.PathFingerprintBuilder(str(tmp_path)).fingerprints(before)[1]

    (package / "__init__.py").write_text("", encoding="utf-8")
    after = SourcePathContext.for_path(str(target))
    after_key = cache_fingerprint.PathFingerprintBuilder(str(tmp_path)).fingerprints(after)[1]

    assert before.package_parts == ()
    assert after.package_parts == ("package",)
    assert before_key != after_key


def test_symlink_spelling_and_resolved_target_are_both_recorded(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    target = real / "module.py"
    target.write_text("", encoding="utf-8")
    alias = tmp_path / "alias.py"
    try:
        alias.symlink_to(target)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    context = SourcePathContext.for_path(str(alias))

    assert context.lexical_path == os.path.normcase(os.path.abspath(alias))
    assert context.resolved_path == os.path.normcase(os.path.realpath(alias))
    assert context.lexical_path != context.resolved_path
    assert context.filename_stem == "alias"
    assert context.module_parts == ("alias",)


def test_path_sensitive_rules_match_with_implicit_and_precomputed_context(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("", encoding="utf-8")
    settings = CheckSettings(select=("PDF602",))
    selection = rules_selection.select_rules(settings)
    context = SourcePathContext.for_path(str(target))

    implicit = formatter.format_source("", str(target), settings=settings, rule_selection=selection, fix=False)
    precomputed = formatter._format_source_plan(
        "", str(target), settings=settings, source_language=SourceLanguage.PYTHON, execution_plan=selection.execution_plan_for_path(str(target)), fix=False, source_path=context
    )

    assert implicit == precomputed
    assert tuple(finding.rule.code.tag for finding in implicit.unfixed_findings) == ("PDF602",)


def test_builder_and_standalone_contexts_are_identical_for_existing_synthetic_and_broken_paths(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    existing = package / "module.py"
    existing.write_text("", encoding="utf-8")
    missing = package / "missing.py"
    broken = tmp_path / "broken.py"
    try:
        broken.symlink_to(tmp_path / "absent.py")
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    for path in (existing, missing, broken, Path(os.path.abspath(os.sep))):
        assert SourcePathContextBuilder().for_path(str(path)) == SourcePathContext.for_path(str(path))


def test_sibling_files_observe_each_shared_package_directory_once(tmp_path: Path, mocker: MockerFixture) -> None:
    package = tmp_path / "package"
    nested = package / "nested"
    nested.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (nested / "__init__.pyi").write_text("", encoding="utf-8")
    targets = (nested / "first.py", nested / "second.py")
    for target in targets:
        target.write_text("", encoding="utf-8")
    initializer_exists = mocker.spy(source_path, "_package_initializer_exists")
    builder = SourcePathContextBuilder()

    contexts = tuple(builder.for_path(str(target)) for target in targets)

    observed = tuple(Path(call.args[0]) for call in initializer_exists.call_args_list)
    assert contexts[0].package_parts == contexts[1].package_parts == ("package", "nested")
    assert set(observed) == {nested.resolve(), package.resolve(), tmp_path.resolve()}
    assert all(observed.count(directory) == 1 for directory in set(observed))


def test_distinct_package_subtrees_do_not_alias_shared_ancestry(tmp_path: Path, mocker: MockerFixture) -> None:
    package = tmp_path / "package"
    first = package / "first"
    second = package / "second"
    first.mkdir(parents=True)
    second.mkdir()
    for directory in (package, first, second):
        (directory / "__init__.py").write_text("", encoding="utf-8")
    targets = (first / "module.py", second / "module.py")
    for target in targets:
        target.write_text("", encoding="utf-8")
    initializer_exists = mocker.spy(source_path, "_package_initializer_exists")
    builder = SourcePathContextBuilder()

    contexts = tuple(builder.for_path(str(target)) for target in targets)

    observed = tuple(Path(call.args[0]) for call in initializer_exists.call_args_list)
    assert contexts[0].package_parts == ("package", "first")
    assert contexts[1].package_parts == ("package", "second")
    assert observed.count(package.resolve()) == 1
    assert observed.count(first.resolve()) == 1
    assert observed.count(second.resolve()) == 1


def test_lexical_aliases_share_resolved_package_ancestry(tmp_path: Path, mocker: MockerFixture) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "__init__.py").write_text("", encoding="utf-8")
    for name in ("first.py", "second.py"):
        (real / name).write_text("", encoding="utf-8")
    first_alias = tmp_path / "first_alias"
    second_alias = tmp_path / "second_alias"
    try:
        first_alias.symlink_to(real, target_is_directory=True)
        second_alias.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    initializer_exists = mocker.spy(source_path, "_package_initializer_exists")
    builder = SourcePathContextBuilder()

    first_context = builder.for_path(str(first_alias / "first.py"))
    second_context = builder.for_path(str(second_alias / "second.py"))

    observed = tuple(Path(call.args[0]) for call in initializer_exists.call_args_list)
    assert first_context.lexical_path != second_context.lexical_path
    assert Path(first_context.resolved_path).parent == Path(second_context.resolved_path).parent == real.resolve()
    assert first_context.package_parts == second_context.package_parts == ("real",)
    assert observed.count(real.resolve()) == 1


def test_negative_package_boundary_is_reused_for_siblings(tmp_path: Path, mocker: MockerFixture) -> None:
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text("", encoding="utf-8")
    initializer_exists = mocker.spy(source_path, "_package_initializer_exists")
    builder = SourcePathContextBuilder()

    contexts = tuple(builder.for_path(str(target)) for target in targets)

    assert contexts[0].package_parts == contexts[1].package_parts == ()
    assert initializer_exists.call_count == 1


def test_builder_reuses_first_marker_observation_and_fresh_builders_observe_changes(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    first = package / "first.py"
    second = package / "second.py"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    builder = SourcePathContextBuilder()

    before = builder.for_path(str(first))
    marker = package / "__init__.py"
    marker.write_text("", encoding="utf-8")
    same_invocation = builder.for_path(str(second))
    next_invocation = SourcePathContextBuilder().for_path(str(second))
    marker.unlink()
    later_invocation = SourcePathContextBuilder().for_path(str(second))

    assert before.package_parts == same_invocation.package_parts == later_invocation.package_parts == ()
    assert next_invocation.package_parts == ("package",)


def test_builder_computes_the_resolved_path_once_per_file(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("", encoding="utf-8")
    expected = os.path.normcase(os.path.realpath(target))
    realpath = mocker.spy(source_path.os.path, "realpath")

    context = SourcePathContextBuilder().for_path(str(target))

    assert context.resolved_path == expected
    realpath.assert_called_once_with(str(target))
