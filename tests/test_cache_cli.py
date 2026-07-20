"""Tests for persistent-cache settings, lifecycle UI, and CLI parity."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import typing
import dataclasses
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.cli.check as check_command
import pydocformatter.cache.store as cache_store
import pydocformatter.cache.directory as cache_directory
import pydocformatter.rules.collection as rule_collection
import pydocformatter.cache.coordinator as cache_coordinator
from pydocformatter.cli import settings_check
from pydocformatter.cli.global_args import GlobalArgs
from tests import cli_helpers


if typing.TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


@dataclasses.dataclass(frozen=True)
class _ParityScenario:
    """One cached-versus-uncached CLI scenario."""

    name: str
    source: bytes
    arguments: tuple[str, ...] = ()
    output_file: bool = False


_PARITY_SCENARIOS = (
    _ParityScenario(name="clean-check", source=b'"""Module."""\n'),
    _ParityScenario(name="fixable-check", source=b'"""Summary"""\n', arguments=("--select", "PDF300")),
    _ParityScenario(name="nonfixable-check", source=b'"""This summary is too long."""\n', arguments=("--select", "PDF203", "--line-length", "10")),
    _ParityScenario(name="clean-fix", source=b'"""Module."""\n', arguments=("--fix",)),
    _ParityScenario(name="successful-fix", source=b'"""Summary"""\n', arguments=("--fix", "--select", "PDF300")),
    _ParityScenario(name="fix-leaving-findings", source=b'"""This summary is too long"""\n', arguments=("--fix", "--select", "PDF203", "--extend-select", "PDF300", "--line-length", "10")),
    _ParityScenario(name="clean-diff", source=b'"""Module."""\n', arguments=("--diff",)),
    _ParityScenario(name="changed-diff", source=b'"""Summary"""\n', arguments=("--diff", "--select", "PDF300")),
    _ParityScenario(name="exit-zero", source=b'"""Summary"""\n', arguments=("--exit-zero", "--select", "PDF300")),
    _ParityScenario(name="exit-non-zero-on-fix", source=b'"""Summary"""\n', arguments=("--fix", "--exit-non-zero-on-fix", "--select", "PDF300")),
    _ParityScenario(name="output-file", source=b'"""Summary"""\n', arguments=("--select", "PDF300"), output_file=True),
    _ParityScenario(name="empty-selection-valid", source=b"value = 1\n", arguments=("--ignore", "ALL")),
    _ParityScenario(name="empty-selection-invalid", source=b"def broken(:\n", arguments=("--ignore", "ALL")),
    _ParityScenario(name="suppressed", source=b'"""Summary"""  # pydocfmt: ignore[PDF300]\n', arguments=("--select", "PDF300")),
    _ParityScenario(name="utf8-bom", source=b'\xef\xbb\xbf"""Module."""\n'),
    _ParityScenario(name="crlf", source=b'"""Module."""\r\n'),
    _ParityScenario(name="cr", source=b'"""Module."""\r'),
    _ParityScenario(name="invalid-utf8", source=b"\xff"),
)


def _run_scenario(root: Path, scenario: _ParityScenario, *, cache_arguments: tuple[str, ...]) -> tuple[cli_helpers.CliRunResult, bytes, bytes | None]:
    """Run one scenario and capture source plus optional output-file state."""
    target = root / "module.py"
    output_file = root / "report.txt"
    argv = ["pydocfmt", "check", *cache_arguments, *scenario.arguments]
    if scenario.output_file:
        argv.extend(("--output-file", str(output_file)))
    argv.append(str(target))
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)
    output = output_file.read_bytes() if output_file.exists() else None
    return result, target.read_bytes(), output


def _reset_scenario(root: Path, source: bytes) -> None:
    """Restore source and remove transient output before another invocation."""
    (root / "module.py").write_bytes(source)
    report = root / "report.txt"
    if report.exists():
        report.unlink()


@pytest.mark.parametrize("scenario", _PARITY_SCENARIOS, ids=lambda scenario: scenario.name)
def test_cached_and_uncached_cli_behavior_is_equivalent(tmp_path: Path, scenario: _ParityScenario) -> None:
    cache = tmp_path / "cache"
    _reset_scenario(tmp_path, scenario.source)
    uncached_cold = _run_scenario(tmp_path, scenario, cache_arguments=("--no-cache",))
    _reset_scenario(tmp_path, scenario.source)
    cached_cold = _run_scenario(tmp_path, scenario, cache_arguments=("--cache-dir", str(cache)))

    assert cached_cold == uncached_cold

    warm_start = cached_cold[1]
    _reset_scenario(tmp_path, warm_start)
    uncached_warm = _run_scenario(tmp_path, scenario, cache_arguments=("--no-cache",))
    _reset_scenario(tmp_path, warm_start)
    cached_warm = _run_scenario(tmp_path, scenario, cache_arguments=("--cache-dir", str(cache)))

    assert cached_warm == uncached_warm


@pytest.mark.parametrize("mode", [(), ("--fix",), ("--diff",), ("--fix", "--stdin-filename", "virtual.py")], ids=("check", "fix", "diff", "named-fix"))
def test_stdin_modes_are_equivalent_and_never_cached(tmp_path: Path, mode: tuple[str, ...]) -> None:
    cache = tmp_path / "cache"
    source = '"""Summary"""\n'
    base = ["pydocfmt", "check", *mode, "--select", "PDF300", "-"]

    uncached = cli_helpers.run_cli(pydocfmt_cli.main, [*base[:2], "--no-cache", *base[2:]], cwd=tmp_path, stdin=source)
    cached = cli_helpers.run_cli(pydocfmt_cli.main, [*base[:2], "--cache-dir", str(cache), *base[2:]], cwd=tmp_path, stdin=source)

    assert cached == uncached
    assert not cache.exists()


def test_nested_profiles_per_file_settings_and_ignores_retain_cli_parity(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    cache = tmp_path / "cache"
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pydocfmt]\nselect = ["PDF203", "PDF300"]\nline-length = 20\nrespect-gitignore = false\n[tool.pydocfmt.per-file-ignores]\n"ignored.py" = ["PDF300"]\n[tool.pydocfmt.per-file-settings]\n"wide.py" = { line-length = 100 }\n',
        encoding="utf-8",
    )
    (nested / "pyproject.toml").write_text('[tool.pydocfmt]\nselect = ["PDF300"]\nrespect-gitignore = false\n', encoding="utf-8")
    sources = {
        tmp_path / "clean.py": '"""Module."""\n',
        tmp_path / "ignored.py": '"""Summary"""\n',
        tmp_path / "wide.py": '"""This summary fits only the per-file line length."""\n',
        nested / "module.py": '"""Nested module."""\n',
    }
    for path, source in sources.items():
        path.write_text(source, encoding="utf-8")
    uncached_argv = ["pydocfmt", "check", "--no-cache", str(tmp_path)]
    cached_argv = ["pydocfmt", "check", "--cache-dir", str(cache), str(tmp_path)]

    uncached = cli_helpers.run_cli(pydocfmt_cli.main, uncached_argv, cwd=tmp_path)
    cold = cli_helpers.run_cli(pydocfmt_cli.main, cached_argv, cwd=tmp_path)
    warm = cli_helpers.run_cli(pydocfmt_cli.main, cached_argv, cwd=tmp_path)

    assert cold == uncached
    assert warm == uncached
    assert all(path.read_text(encoding="utf-8") == source for path, source in sources.items())


def test_default_settings_and_cli_flags_are_publicly_visible(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")

    shown = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--show-settings"], cwd=tmp_path)
    help_result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--help"], cwd=tmp_path, expect_system_exit=True)

    assert "cache = true\n" in shown.stdout
    assert 'cache-dir = ".pydocfmt_cache"\n' in shown.stdout
    assert "--cache, --no-cache" in help_result.stdout
    assert "--cache-dir PATH" in help_result.stdout
    assert "--cache-stats" in help_result.stdout


@pytest.mark.parametrize("value", ["", 1, False])
def test_cache_directory_configuration_must_be_a_nonempty_string(tmp_path: Path, value: object) -> None:
    rendered = '""' if value == "" else str(value).lower()
    (tmp_path / "pyproject.toml").write_text(f"[tool.pydocfmt]\ncache-dir = {rendered}\n", encoding="utf-8")

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--show-settings"], cwd=tmp_path)

    assert result.exit_code == 2
    assert "cache_dir" in result.stderr or "cache-dir" in result.stderr


@pytest.mark.parametrize("command", ["check", "clean"])
def test_cli_cache_directory_rejects_embedded_nul_with_status_two(command: str, tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    if command == "check":
        arguments = ["pydocfmt", command, "--cache-dir", "state\0cache"]
        arguments.append(str(target))
    else:
        arguments = ["pydocfmt", command, "--config", 'cache-dir="\\u0000"']

    result = cli_helpers.run_cli(pydocfmt_cli.main, arguments, cwd=tmp_path)

    assert result.exit_code == 2
    assert "Configuration error" in result.stderr
    assert "NUL" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "state").exists()


@pytest.mark.parametrize("key", ["cache", "cache-dir"])
def test_cache_settings_are_rejected_in_per_file_settings(tmp_path: Path, key: str) -> None:
    value = "false" if key == "cache" else '"other-cache"'
    (tmp_path / "pyproject.toml").write_text(f'[tool.pydocfmt]\nper-file-settings = {{"*.py" = {{{key} = {value}}}}}\n', encoding="utf-8")

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--show-settings"], cwd=tmp_path)

    assert result.exit_code == 2
    assert f"{key} cannot be configured in per-file-settings" in result.stderr


def test_default_cache_directory_resolves_against_auto_discovered_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    nested = project / "nested"
    nested.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[tool.pydocfmt]\n", encoding="utf-8")
    monkeypatch.chdir(nested)

    profile = settings_check.SETTINGS_SCHEMA.load_profile(path=str(nested))

    assert profile.project_root == str(project)
    assert cache_directory.cache_directory_for_profile(profile) == project / ".pydocfmt_cache"


def test_auto_discovered_cache_directory_value_is_config_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    nested = project / "nested"
    nested.mkdir(parents=True)
    (project / "pyproject.toml").write_text('[tool.pydocfmt]\ncache-dir = "state/cache"\n', encoding="utf-8")
    monkeypatch.chdir(nested)

    profile = settings_check.SETTINGS_SCHEMA.load_profile(path=str(nested))

    assert cache_directory.cache_directory_for_profile(profile) == project / "state" / "cache"


@pytest.mark.parametrize("config_option", ['cache-dir="inline-cache"', "config.toml"])
def test_explicit_configuration_cache_directory_is_cwd_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config_option: str) -> None:
    monkeypatch.chdir(tmp_path)
    if config_option.endswith(".toml"):
        (tmp_path / config_option).write_text('cache-dir = "explicit-cache"\n', encoding="utf-8")
        expected = tmp_path / "explicit-cache"
    else:
        expected = tmp_path / "inline-cache"

    profile = settings_check.SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(config_option,)))

    assert cache_directory.cache_directory_for_profile(profile) == expected


def test_cli_cache_directory_is_cwd_relative(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", "cli-cache", str(target)], cwd=tmp_path)

    assert result.exit_code == 0
    assert (tmp_path / "cli-cache" / "v1" / "cache.sqlite3").is_file()


def test_missing_cache_parent_warns_once_and_preserves_uncached_findings_and_status(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    cache = tmp_path / "missing" / "cache"
    warning = f"pydocfmt check: Cache warning: Cache directory parent does not exist or is not a directory; running without persistent cache: {cache.parent}"
    base = ["pydocfmt", "check", "--select", "PDF300", str(target)]

    uncached = cli_helpers.run_cli(pydocfmt_cli.main, [*base[:2], "--no-cache", *base[2:]], cwd=tmp_path)
    first = cli_helpers.run_cli(pydocfmt_cli.main, [*base[:2], "--cache-dir", str(cache), "--cache-stats", *base[2:]], cwd=tmp_path)
    second = cli_helpers.run_cli(pydocfmt_cli.main, [*base[:2], "--cache-dir", str(cache), "--cache-stats", *base[2:]], cwd=tmp_path)

    assert first.exit_code == second.exit_code == uncached.exit_code == 1
    assert first.stdout == second.stdout == uncached.stdout
    assert first.stderr.splitlines().count(warning) == 1
    assert second.stderr.splitlines().count(warning) == 1
    assert first.stderr.splitlines()[-1] == "Cache: candidates=0 hits=0 metadata-rejected=0 digest-rejected=0 misses=0 uncacheable=1 read-errors=0 writes=0 store-errors=1"
    assert first.stderr.splitlines().index(warning) < len(first.stderr.splitlines()) - 1
    assert target.read_text(encoding="utf-8") == '"""Summary"""\n'
    assert not cache.parent.exists()


def test_missing_cache_parent_warning_does_not_change_successful_fix_behavior(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    cache = tmp_path / "missing" / "cache"

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--select", "PDF300", "--fix", str(target)], cwd=tmp_path)

    assert result.exit_code == 0
    assert result.stdout.endswith("Fixed 1 rule check error.\n")
    assert "PDF300" in result.stdout
    assert result.stderr.count("Cache directory parent does not exist or is not a directory") == 1
    assert target.read_text(encoding="utf-8") == '"""Summary."""\n'
    assert not cache.parent.exists()


def test_missing_cache_parent_warning_is_suppressed_when_cache_work_is_not_attempted(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    cache = tmp_path / "missing" / "cache"
    cases = (
        (["pydocfmt", "check", "--no-cache", "--cache-dir", str(cache), str(target)], None),
        (["pydocfmt", "check", "--cache-dir", str(cache), "-"], '"""Module."""\n'),
        (["pydocfmt", "check", "--cache-dir", str(cache), str(empty)], None),
    )

    for arguments, stdin in cases:
        result = cli_helpers.run_cli(pydocfmt_cli.main, arguments, cwd=tmp_path, stdin=stdin)
        assert result.exit_code == 0
        assert "Cache warning" not in result.stderr
    assert not cache.parent.exists()


def test_existing_cache_parent_allows_root_creation_without_warning(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    cache = tmp_path / "state" / "cache"
    cache.parent.mkdir()

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), str(target)], cwd=tmp_path)

    assert result.exit_code == 0
    assert "Cache warning" not in result.stderr
    assert cache.is_dir()


def test_non_directory_cache_parent_warns_while_clean_retains_strict_error(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    parent = tmp_path / "state"
    parent.write_text("not a directory", encoding="utf-8")
    cache = parent / "cache"

    check = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), str(target)], cwd=tmp_path)
    clean = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"'], cwd=tmp_path)

    assert check.exit_code == 0
    assert check.stderr == f"pydocfmt check: Cache warning: Cache directory parent does not exist or is not a directory; running without persistent cache: {parent}\n"
    assert clean.exit_code == 2
    assert "Cache cleanup error" in clean.stderr
    assert "Cache warning" not in clean.stderr


def test_clean_keeps_no_data_behavior_when_cache_root_and_parent_are_absent(tmp_path: Path) -> None:
    cache = tmp_path / "missing" / "cache"

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"'], cwd=tmp_path)

    assert result.exit_code == 0
    assert result.stdout == f"No pydocfmt cache data found at {cache}.\n"
    assert result.stderr == ""


def test_no_cache_show_only_stdin_and_dirty_runs_create_no_cache_directory(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    cases = (
        (["pydocfmt", "check", "--show-settings"], None),
        (["pydocfmt", "check", "--show-rules"], None),
        (["pydocfmt", "check", "--show-files", str(target)], None),
        (["pydocfmt", "check", "--no-cache", str(target)], None),
        (["pydocfmt", "check", "--select", "PDF300", str(target)], None),
        (["pydocfmt", "check", "-"], '"""Module."""\n'),
    )
    for index, (arguments, stdin) in enumerate(cases):
        cache = tmp_path / f"cache-{index}"
        result = cli_helpers.run_cli(pydocfmt_cli.main, [*arguments[:2], "--cache-dir", str(cache), *arguments[2:]], cwd=tmp_path, stdin=stdin)
        assert result.exit_code in {0, 1}
        assert not cache.exists()


def test_custom_cache_directory_is_self_pruned_with_distinct_reason(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "state" / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    cache.parent.mkdir()
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache))
    (cache / "ignored.py").write_text("broken syntax(", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.pydocfmt]\ncache-dir = "state/cache"\nexclude = []\nrespect-gitignore = false\n', encoding="utf-8")

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--show-files", str(tmp_path)], cwd=tmp_path)

    assert result.exit_code == 0
    assert f"{cache} IGNORED: internal pydocfmt cache directory" in result.stdout.splitlines()
    assert f"{cache / 'ignored.py'} INCLUDED" not in result.stdout.splitlines()


def test_cache_directory_equal_to_traversal_root_does_not_prune_inputs(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text('"""Module."""\n', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.pydocfmt]\ncache-dir = "."\n', encoding="utf-8")

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--show-files", "."], cwd=tmp_path)

    assert result.exit_code == 0
    assert f"{target} INCLUDED" in result.stdout.splitlines()
    assert "internal pydocfmt cache directory" not in result.stdout

    check_result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-stats", "."], cwd=tmp_path)

    assert check_result.exit_code == 0
    assert check_result.stdout == "All checks passed!\n"
    assert "candidates=1" in check_result.stderr
    assert "misses=1" in check_result.stderr
    assert "store-errors=1" in check_result.stderr
    assert not (tmp_path / "CACHEDIR.TAG").exists()


def test_clean_command_is_precise_idempotent_and_keeps_shared_root(tmp_path: Path) -> None:
    cache = tmp_path / "shared-cache"
    layout = cache_directory.cache_layout(cache)
    cache_directory.ensure_cache_layout(layout)
    layout.database.write_bytes(b"database")
    unknown = cache / "keep.txt"
    unknown.write_text("user data", encoding="utf-8")
    config = f'cache-dir="{cache}"'

    first = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", config], cwd=tmp_path)
    second = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", config], cwd=tmp_path)

    assert first.exit_code == 0
    assert first.stdout == f"Removed pydocfmt cache data from {cache}.\n"
    assert second.exit_code == 0
    assert second.stdout == f"No pydocfmt cache data found at {cache}.\n"
    assert cache.is_dir()
    assert unknown.read_text(encoding="utf-8") == "user data"


def test_clean_command_cache_dir_option_overrides_configuration(tmp_path: Path) -> None:
    configured_cache = tmp_path / "configured-cache"
    override_cache = tmp_path / "override-cache"
    configured_layout = cache_directory.cache_layout(configured_cache)
    override_layout = cache_directory.cache_layout(override_cache)
    cache_directory.ensure_cache_layout(configured_layout)
    cache_directory.ensure_cache_layout(override_layout)

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{configured_cache}"', "--cache-dir", str(override_cache)], cwd=tmp_path)

    assert result.exit_code == 0
    assert not override_layout.version_dir.exists()
    assert configured_layout.version_dir.exists()


def test_clean_command_explains_that_an_empty_untagged_directory_is_unowned(tmp_path: Path) -> None:
    cache = tmp_path / "empty-unowned"
    cache.mkdir()

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--cache-dir", str(cache)], cwd=tmp_path)

    assert result.exit_code == 2
    assert "untagged empty cache directory" in result.stderr
    assert "exact pydocfmt ownership" in result.stderr


def test_clean_command_refuses_an_untagged_directory(tmp_path: Path) -> None:
    cache = tmp_path / "unowned"
    cache.mkdir()
    (cache / "keep.txt").write_text("user data", encoding="utf-8")

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"'], cwd=tmp_path)

    assert result.exit_code == 2
    assert "Cache cleanup error" in result.stderr
    assert (cache / "keep.txt").read_text(encoding="utf-8") == "user data"


def test_clean_command_reports_cache_enumeration_errors_without_traceback(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache))
    real_iterdir = Path.iterdir

    def failing_iterdir(path: Path) -> typing.Iterator[Path]:
        if path == cache:
            raise OSError("enumeration failed")
        return real_iterdir(path)

    mocker.patch("pathlib.Path.iterdir", side_effect=failing_iterdir, autospec=True)

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"'], cwd=tmp_path)

    assert result.exit_code == 2
    assert f"Unable to enumerate cache root {cache}" in result.stderr
    assert "Traceback" not in result.stderr


def test_clean_command_reports_cache_inspection_errors_without_traceback(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache))
    real_lstat = Path.lstat

    def failing_lstat(path: Path) -> os.stat_result:
        if path == cache:
            raise OSError("inspection failed")
        return real_lstat(path)

    mocker.patch("pathlib.Path.lstat", side_effect=failing_lstat, autospec=True)

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"'], cwd=tmp_path)

    assert result.exit_code == 2
    assert f"Unable to inspect cache root {cache}" in result.stderr
    assert "Traceback" not in result.stderr


def test_clean_command_reports_directory_removal_errors_without_traceback(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache))
    mocker.patch("pydocformatter.cache.directory.shutil.rmtree", side_effect=OSError("removal failed"), autospec=True)

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"'], cwd=tmp_path)

    assert result.exit_code == 2
    assert f"Unable to remove owned cache directory {cache / 'v1'}" in result.stderr
    assert "Traceback" not in result.stderr


def test_clean_command_preserves_root_level_quarantine_shaped_files(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache_directory.ensure_cache_layout(cache_directory.cache_layout(cache))
    quarantine = cache / "cache.sqlite3.corrupt-1-1"
    quarantine.write_bytes(b"broken")

    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"'], cwd=tmp_path)

    assert result.exit_code == 0
    assert quarantine.read_bytes() == b"broken"


def test_clean_command_reports_partial_cleanup_and_can_be_retried(tmp_path: Path, mocker: MockerFixture) -> None:
    cache = tmp_path / "cache"
    layout = cache_directory.cache_layout(cache)
    cache_directory.ensure_cache_layout(layout)
    second_version = cache / "v2"
    second_version.mkdir()
    real_rmtree = cache_directory.shutil.rmtree
    failed = False

    def fail_once(path: str | os.PathLike[str]) -> None:
        nonlocal failed
        if Path(path) == second_version and not failed:
            failed = True
            raise OSError("removal failed")
        real_rmtree(path)

    mocker.patch("pydocformatter.cache.directory.shutil.rmtree", side_effect=fail_once)
    arguments = ["pydocfmt", "clean", "--config", f'cache-dir="{cache}"']

    first = cli_helpers.run_cli(pydocfmt_cli.main, arguments, cwd=tmp_path)

    assert first.exit_code == 2
    assert "already removed 1 owned path" in first.stderr
    assert not layout.version_dir.exists()
    assert second_version.exists()

    second = cli_helpers.run_cli(pydocfmt_cli.main, arguments, cwd=tmp_path)

    assert second.exit_code == 0
    assert not second_version.exists()


def test_top_level_help_lists_clean_command() -> None:
    result = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "--help"], expect_system_exit=True)

    assert result.exit_code == 0
    assert "clean" in result.stdout


@pytest.mark.parametrize("warm_parallelism", ["2", "4", None], ids=("two", "four", "default"))
def test_clean_proof_reuses_across_parallelism_and_current_value_controls_coordinator(tmp_path: Path, mocker: MockerFixture, warm_parallelism: str | None) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    cold = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats", "--parallelism", "1", str(target)], cwd=tmp_path)
    received_parallelism = []
    real_coordinator = cache_coordinator.CacheCoordinator

    class RecordingCoordinator(real_coordinator):
        def __init__(self, store: cache_store.CacheStore, *, engine_key: bytes, parallelism: int) -> None:
            received_parallelism.append(parallelism)
            super().__init__(store, engine_key=engine_key, parallelism=parallelism)

    mocker.patch("pydocformatter.cache.coordinator.CacheCoordinator", new=RecordingCoordinator)
    parser = mocker.patch("pydocformatter.formatter.cst.parse_module", side_effect=AssertionError("cache hit must not parse"), autospec=True)
    rule_pipeline = mocker.patch("pydocformatter.rules.runner.run_rule_plan", side_effect=AssertionError("cache hit must not run rules"), autospec=True)
    analysis_worker = mocker.patch("pydocformatter.formatter.format_disk_file", side_effect=AssertionError("cache hit must not execute analysis"), autospec=True)
    warm_arguments = ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats"]
    if warm_parallelism is not None:
        warm_arguments.extend(("--parallelism", warm_parallelism))
    warm_arguments.append(str(target))

    warm = cli_helpers.run_cli(pydocfmt_cli.main, warm_arguments, cwd=tmp_path)

    expected_parallelism = check_command.resolve_parallelism(float(warm_parallelism) if warm_parallelism is not None else 0.0)
    assert cold.exit_code == 0
    assert "hits=0" in cold.stderr
    assert "misses=1" in cold.stderr
    assert "writes=1" in cold.stderr
    assert warm.exit_code == 0
    assert "hits=1" in warm.stderr
    assert "misses=0" in warm.stderr
    assert "writes=0" in warm.stderr
    assert received_parallelism == [expected_parallelism]
    parser.assert_not_called()
    rule_pipeline.assert_not_called()
    analysis_worker.assert_not_called()


def test_clean_check_proof_reuses_across_fixability_and_fix_mode(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    cold = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats", "--parallelism", "1", "--select", "PDF300", str(target)], cwd=tmp_path)
    warm = cli_helpers.run_cli(
        pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats", "--parallelism", "1", "--select", "PDF300", "--unfixable", "PDF300", "--fix", str(target)], cwd=tmp_path
    )

    assert cold.exit_code == warm.exit_code == 0
    assert "hits=0" in cold.stderr
    assert "misses=1" in cold.stderr
    assert "writes=1" in cold.stderr
    assert "hits=1" in warm.stderr
    assert "misses=0" in warm.stderr
    assert "writes=0" in warm.stderr


def test_clean_proof_reuses_across_equivalent_selector_syntax_priority_and_specificity(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    other_pdf3_codes = tuple(rule.meta.code.tag for rule in rule_collection.RULE_COLLECTION.rules if rule.meta.code.tag.startswith("PDF3") and rule.meta.code.tag != "PDF300")
    equivalent_inline_config = f'select = ["PDF3"]\nignore = [{", ".join(f"{code!r}" for code in other_pdf3_codes)}]\nrequire-explicit = []'
    cold = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats", "--parallelism", "1", "--select", "PDF300", str(target)], cwd=tmp_path)
    warm = cli_helpers.run_cli(
        pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats", "--parallelism", "1", "--config", equivalent_inline_config, str(target)], cwd=tmp_path
    )

    assert cold.exit_code == warm.exit_code == 0
    assert "hits=0" in cold.stderr
    assert "misses=1" in cold.stderr
    assert "writes=1" in cold.stderr
    assert "hits=1" in warm.stderr
    assert "misses=0" in warm.stderr
    assert "writes=0" in warm.stderr


def test_effective_direct_setting_change_misses_and_produces_new_finding(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    config = tmp_path / "pyproject.toml"
    target.write_text('"""This module summary is deliberately longer than twenty columns."""\n', encoding="utf-8")
    config.write_text('[tool.pydocfmt]\nselect = ["PDF101"]\nline-length = 120\n', encoding="utf-8")
    argv = ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats", str(target)]
    first = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)
    config.write_text('[tool.pydocfmt]\nselect = ["PDF101"]\nline-length = 20\n', encoding="utf-8")
    second = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)

    assert first.exit_code == 0
    assert "hits=0" in first.stderr
    assert "misses=1" in first.stderr
    assert "writes=1" in first.stderr
    assert second.exit_code == 1
    assert "PDF101" in second.stdout
    assert "hits=0" in second.stderr
    assert "misses=1" in second.stderr
    assert "writes=0" in second.stderr


def test_pdf212_parser_setting_change_invalidates_clean_proof(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    config = tmp_path / "pyproject.toml"
    target.write_text('"""- item"""\n', encoding="utf-8")
    config.write_text('[tool.pydocfmt]\nselect = ["PDF212"]\ndocstring-parse-list-items = false\n', encoding="utf-8")
    argv = ["pydocfmt", "check", "--cache-dir", str(cache), "--cache-stats", str(target)]
    first = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)
    config.write_text('[tool.pydocfmt]\nselect = ["PDF212"]\ndocstring-parse-list-items = true\n', encoding="utf-8")
    second = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=tmp_path)

    assert first.exit_code == 0
    assert "hits=0" in first.stderr
    assert "misses=1" in first.stderr
    assert "writes=1" in first.stderr
    assert second.exit_code == 1
    assert "PDF212" in second.stdout
    assert "hits=0" in second.stderr
    assert "misses=1" in second.stderr
    assert "writes=0" in second.stderr


def test_selector_errors_bypass_cache_and_remain_equivalent(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Module."""\n', encoding="utf-8")
    uncached = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--no-cache", "--select", "BAD", str(target)], cwd=tmp_path)
    cached = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--select", "BAD", str(target)], cwd=tmp_path)

    assert cached == uncached
    assert not cache.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX source write permission semantics")
def test_write_failure_is_equivalent_and_never_populates(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    cache = tmp_path / "cache"
    target.write_text('"""Summary"""\n', encoding="utf-8")
    real_open = typing.cast("typing.Callable[..., typing.IO[typing.Any]]", open)

    def failing_open(path: str, mode: str = "r", **kwargs: object) -> typing.IO[typing.Any]:
        if os.fspath(path) == str(target) and mode == "w":
            raise PermissionError("write denied")
        return real_open(path, mode, **kwargs)

    mocker.patch("pydocformatter.formatter.open", side_effect=failing_open)
    uncached = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--no-cache", "--fix", "--select", "PDF300", str(target)], cwd=tmp_path)
    cached = cli_helpers.run_cli(pydocfmt_cli.main, ["pydocfmt", "check", "--cache-dir", str(cache), "--fix", "--select", "PDF300", str(target)], cwd=tmp_path)

    assert cached == uncached
    assert not cache.exists()
