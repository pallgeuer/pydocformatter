# Future imports
from __future__ import annotations

# Standard library imports
import os
import re
import sys
import json
import tempfile
import subprocess
import collections
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Self, TextIO, cast

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.settings as settings_core
import pydocformatter.cli.check as check_command
import pydocformatter.rules.collection as rule_collection
from pydocformatter import file_selection, formatter, rules_selection
from pydocformatter.cli import settings_check
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.formatter import FormatterResult
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleFinding, RuleMetadata
from tests import cli_helpers, git_helpers


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture

    # First-party imports
    from pydocformatter.rules_selection import RuleSelection


PDF101_RULE = RuleMetadata(
    code=RuleCode("PDF101"),
    name="docstring-reflow",
    message="Docstring chunk needs reflow",
    fix_availability=FixAvailability.ALWAYS,
    stable_since="1.0.0",
    setting_effects=(),
    incompatible_with=(),
    check_kind=RuleCheckKind.STANDARD,
)
PCF000_RULE = RuleMetadata(
    code=RuleCode("PCF000"),
    name="comment-formatting-needed",
    message="Comment needs formatting",
    fix_availability=FixAvailability.ALWAYS,
    stable_since="1.0.0",
    setting_effects=(),
    incompatible_with=(),
    check_kind=RuleCheckKind.STANDARD,
)

SHOW_RULES_CASES = (
    [
        pytest.param(("--docstring-convention", convention), CheckSettings(docstring_convention=settings_check.DocstringConvention(convention)), id=f"broad-{convention}")
        for convention in ("none", "google", "numpy", "rest", "pep257")
    ]
    + [
        pytest.param(
            ("--docstring-convention", convention, "--extend-select", "PDF106,PDF107,PDF108,PDF109"),
            CheckSettings(docstring_convention=settings_check.DocstringConvention(convention), extend_select=("PDF106", "PDF107", "PDF108", "PDF109")),
            id=f"exact-extend-select-{convention}",
        )
        for convention in ("none", "google", "numpy", "rest", "pep257")
    ]
    + [
        pytest.param(
            ("--docstring-convention", "google", "--extend-select", "PDF10"),
            CheckSettings(docstring_convention=settings_check.DocstringConvention.GOOGLE, extend_select=("PDF10",)),
            id="google-extend-prefix",
        ),
        pytest.param(
            ("--docstring-convention", "numpy", "--extend-select", "PDF10"),
            CheckSettings(docstring_convention=settings_check.DocstringConvention.NUMPY, extend_select=("PDF10",)),
            id="numpy-extend-prefix",
        ),
        pytest.param(
            ("--docstring-convention", "google", "--select", "PDF107"), CheckSettings(docstring_convention=settings_check.DocstringConvention.GOOGLE, select=("PDF107",)), id="google-exact-select"
        ),
        pytest.param(
            ("--docstring-convention", "google", "--extend-select", "PDF107,PDF108", "--ignore", "PDF107"),
            CheckSettings(docstring_convention=settings_check.DocstringConvention.GOOGLE, extend_select=("PDF107", "PDF108"), ignore=("PDF107",)),
            id="google-extend-ignore",
        ),
        pytest.param(
            ("--docstring-convention", "rest", "--extend-select", "PDF301"),
            CheckSettings(docstring_convention=settings_check.DocstringConvention.REST, extend_select=("PDF301",)),
            id="rest-exact-incompatibility-override",
        ),
        pytest.param(("--select", "docstring-reflow"), CheckSettings(select=("docstring-reflow",)), id="exact-name-select"),
    ]
)


pytestmark = pytest.mark.isolated_cwd


def _profile(settings: CheckSettings) -> settings_core.SettingsProfile[CheckSettings]:
    """Return a minimal settings profile for CLI orchestration tests."""
    return settings_core.SettingsProfile(settings=settings, field_bases={}, field_priorities={}, project_root=os.getcwd())


def _patch_disk_formatter(mocker: MockerFixture, side_effect: Callable[..., FormatterResult]) -> None:
    """Patch the evidence-producing disk formatter around a result-only test fake."""

    def adapter(request: formatter.DiskFormatRequest) -> formatter.DiskFormatResult:
        rule_selection = rules_selection.RuleSelection(rules=request.execution_plan.selected_rules, per_file_ignores=(), errors=(), collection=request.execution_plan.collection)
        result = side_effect(request.path, file=None, settings=request.settings, rule_selection=rule_selection, fix=request.fix, write=request.write)
        return formatter.DiskFormatResult(result=result, clean_snapshot=None)

    mocker.patch("pydocformatter.formatter.format_disk_file", side_effect=adapter, autospec=True)


def _make_sample_tree() -> tempfile.TemporaryDirectory[str]:
    """Create a temporary tree with included, ignored, and non-Python files."""
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "b.txt").write_text("not python\n", encoding="utf-8")
    (root / "skip.py").write_text("x = 2\n", encoding="utf-8")
    return temp_dir


def _make_git_tree() -> tempfile.TemporaryDirectory[str]:
    """Create a temporary tree with a minimal git marker."""
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    git_helpers.write_git_marker(root)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "skip.py").write_text("x = 2\n", encoding="utf-8")
    return temp_dir


def test_pydocfmt_show_files_lists_included_and_ignored_files(mocker: MockerFixture) -> None:
    with _make_sample_tree() as td:
        root = Path(td)

        argv = ["pydocfmt", "check", str(root), "--show-files", "--include", "*.py", "--exclude", "skip.py"]
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        expected_lines = [f"{root / 'a.py'} INCLUDED", f"{root / 'b.txt'} IGNORED: does not match include patterns", f"{root / 'skip.py'} IGNORED: matches exclude patterns"]
        assert result.stdout.splitlines() == expected_lines
        format_file.assert_not_called()


def test_pydocfmt_defaults_to_current_directory_without_files(mocker: MockerFixture) -> None:
    with _make_sample_tree() as td:
        root = Path(td)
        called_paths: list[str] = []

        def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, settings, rule_selection, fix
            assert write
            called_paths.append(os.path.abspath(path))
            return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", "--no-respect-gitignore", "--parallelism", "1"]
        _patch_disk_formatter(mocker, fake_format)
        cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

        assert [Path(path) for path in called_paths] == [root / "a.py", root / "skip.py"]


def test_pydocfmt_show_files_lists_pruned_directories(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / ".venv").mkdir()
        (root / ".venv" / "ignored.py").write_text("x = 2\n", encoding="utf-8")

        argv = ["pydocfmt", "check", str(root), "--show-files"]
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        expected_lines = [f"{root / '.venv'} IGNORED: matches exclude patterns", f"{root / 'a.py'} INCLUDED"]
        assert result.stdout.splitlines() == expected_lines
        format_file.assert_not_called()


def test_pydocfmt_comma_separated_globs_per_include_and_exclude_option(mocker: MockerFixture) -> None:
    with _make_sample_tree() as td:
        root = Path(td)

        argv = ["pydocfmt", "check", str(root), "--show-files", "--include", "*.py,*.txt", "--exclude", "skip.py,b.txt"]
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        expected_lines = [f"{root / 'a.py'} INCLUDED", f"{root / 'b.txt'} IGNORED: matches exclude patterns", f"{root / 'skip.py'} IGNORED: matches exclude patterns"]
        assert result.stdout.splitlines() == expected_lines
        format_file.assert_not_called()


def test_pydocfmt_multiple_globs_before_positional_path_after_separator(mocker: MockerFixture) -> None:
    with _make_sample_tree() as td:
        root = Path(td)

        argv = ["pydocfmt", "check", "--show-files", "--include", "*.py,*.txt", "--exclude", "skip.py", "--", str(root)]
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        expected_lines = [f"{root / 'a.py'} INCLUDED", f"{root / 'b.txt'} INCLUDED", f"{root / 'skip.py'} IGNORED: matches exclude patterns"]
        assert result.stdout.splitlines() == expected_lines
        format_file.assert_not_called()


def test_pydocfmt_default_respects_gitignore(mocker: MockerFixture) -> None:
    with _make_git_tree() as td:
        root = Path(td)

        argv = ["pydocfmt", "check", "--show-files", str(root)]
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=git_helpers.fake_git_check_ignore_for_root(root, {"skip.py"}), autospec=True)
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        expected_lines = [f"{root / 'a.py'} INCLUDED", f"{root / 'skip.py'} IGNORED: matches .gitignore"]
        assert result.stdout.splitlines() == expected_lines
        format_file.assert_not_called()


def test_pydocfmt_no_respect_gitignore_disables_gitignore_filtering(mocker: MockerFixture) -> None:
    with _make_git_tree() as td:
        root = Path(td)

        argv = ["pydocfmt", "check", "--show-files", "--no-respect-gitignore", str(root)]
        run_mock = mocker.patch("pydocformatter.file_selection.subprocess.run", autospec=True)
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert not run_mock.called
        expected_lines = [f"{root / 'a.py'} INCLUDED", f"{root / 'skip.py'} INCLUDED"]
        assert result.stdout.splitlines() == expected_lines
        format_file.assert_not_called()


def test_pydocfmt_show_files_with_rule_formatter_does_not_format(mocker: MockerFixture) -> None:
    with _make_sample_tree() as td:
        root = Path(td)
        format_file = mocker.Mock(
            return_value=FormatterResult(path=str(root / "a.py"), old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
        )
        argv = ["pydocfmt", "check", "--show-files", str(root)]
        mocker.patch("pydocformatter.formatter.format_disk_file", format_file)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        format_file.assert_not_called()
        assert f"{root / 'a.py'} INCLUDED" in result.stdout.splitlines()


def test_pydocfmt_show_files_reports_duplicate_paths_without_formatting(mocker: MockerFixture) -> None:
    with _make_sample_tree() as td:
        root = Path(td)
        format_file = mocker.Mock(return_value=False)
        argv = ["pydocfmt", "check", "--show-files", "a.py", str(root / "a.py")]
        mocker.patch("pydocformatter.formatter.format_disk_file", format_file)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

        assert result.exit_code == 0
        format_file.assert_not_called()
        assert result.stdout.splitlines() == [f"{root / 'a.py'} INCLUDED", f"{root / 'a.py'} IGNORED: duplicate path to already selected file"]


def test_pydocfmt_removed_file_listing_option_is_rejected() -> None:
    old_option = "--" + "ver" + "bose"
    argv = ["pydocfmt", "check", old_option]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=True)

    assert result.exit_code == 2
    assert f"unrecognized arguments: {old_option}" in result.stderr


def test_pydocfmt_hyphenated_pyproject_settings_are_applied(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 72\nrespect-gitignore = false\n", encoding="utf-8")
        called_args: list[tuple[str, int, bool, str]] = []

        def fake_rule_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, rule_selection
            called_args.append((path, settings.line_length, fix, settings.output_format))
            assert write
            return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", "--no-cache", str(root)]
        run_mock = mocker.patch("pydocformatter.file_selection.subprocess.run", autospec=True)
        _patch_disk_formatter(mocker, fake_rule_format)
        cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

        assert not run_mock.called
        assert called_args == [(str(root / "a.py"), 72, True, "grouped")]


def test_pydocfmt_indent_cli_settings_are_applied(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        called_settings: list[tuple[str, int]] = []

        def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, rule_selection, fix
            assert write
            called_settings.append((settings.indent_style, settings.indent_width))
            return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", "--indent-style", "tab", "--indent-width", "2", str(root / "a.py")]
        _patch_disk_formatter(mocker, fake_format)
        cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert called_settings == [("tab", 2)]


def test_line_ending_cli_setting_is_applied(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text('"""Module."""\n\nx = 1\n', encoding="utf-8")
        called_settings: list[str] = []

        def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, rule_selection, fix
            assert write
            called_settings.append(settings.line_ending)
            return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", "--line-ending", "cr-lf", str(target)]
        _patch_disk_formatter(mocker, fake_format)
        cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert called_settings == ["cr-lf"]


def test_rule_cli_settings_are_applied(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text("x = 1\n", encoding="utf-8")
        called_settings: list[CheckSettings] = []

        def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, rule_selection, fix, write
            called_settings.append(settings)
            return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

        argv = [
            "pydocfmt",
            "check",
            "--no-cache",
            str(target),
            "--output-format",
            "grouped",
            "--select",
            "standalone-comment-formatting,PDF",
            "--ignore",
            "trailing-comment-spacing,docstring-reflow",
            "--extend-select",
            "summary-too-long",
            "--require-explicit",
            "docstring-reflow",
            "--fixable",
            "ALL",
            "--unfixable",
            "standalone-comment-formatting",
            "--extend-fixable",
            "docstring-reflow",
            "--per-file-ignores",
            '{"tests/*.py" = ["standalone-comment-formatting"]}',
            "--extend-per-file-ignores",
            '{"generated/*.py" = ["docstring-reflow"]}',
        ]
        mocker.patch("pydocformatter.rules_selection.select_rules", return_value=mocker.Mock(errors=()), autospec=True)
        _patch_disk_formatter(mocker, fake_format)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        assert called_settings[0].select == ("standalone-comment-formatting", "PDF")
        assert called_settings[0].ignore == ("trailing-comment-spacing", "docstring-reflow")
        assert called_settings[0].extend_select == ("summary-too-long",)
        assert called_settings[0].require_explicit == ("docstring-reflow",)
        assert called_settings[0].fixable == ("ALL",)
        assert called_settings[0].unfixable == ("standalone-comment-formatting",)
        assert called_settings[0].extend_fixable == ("docstring-reflow",)
        assert called_settings[0].per_file_ignores == (("tests/*.py", ("standalone-comment-formatting",)),)
        assert called_settings[0].extend_per_file_ignores == (("generated/*.py", ("docstring-reflow",)),)
        assert called_settings[0].output_format == "grouped"


def test_invalid_rule_cli_selector_reports_operational_error() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text("x = 1\n", encoding="utf-8")
        argv = ["pydocfmt", "check", str(target), "--select", "BAD"]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 1
    assert "ERROR: rule selection contains unknown selector: BAD" in result.stdout
    assert "Traceback" not in result.stdout


def test_invalid_rule_config_selector_reports_operational_error_once_for_equivalent_profiles() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\nselect = ["BAD999"]\n', encoding="utf-8")
        (root / "a").mkdir()
        (root / "b").mkdir()
        (root / "a" / "one.py").write_text("x = 1\n", encoding="utf-8")
        (root / "b" / "two.py").write_text("x = 2\n", encoding="utf-8")
        argv = ["pydocfmt", "check", str(root / "a"), str(root / "b"), "--no-respect-gitignore"]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 1
    assert result.stdout.count("ERROR: rule selection contains unknown selector: BAD999") == 1
    assert "Traceback" not in result.stdout


def test_force_exclude_filters_explicit_file_when_enabled(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "skip.py"
        target.write_text("x = 1\n", encoding="utf-8")

        argv = ["pydocfmt", "check", str(target), "--show-files", "--force-exclude", "--exclude", "skip.py"]
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.stdout.splitlines() == [f"{target} IGNORED: matches exclude patterns"]
        format_file.assert_not_called()


def test_force_exclude_does_not_filter_explicit_file_by_gitignore(mocker: MockerFixture) -> None:
    with _make_git_tree() as td:
        root = Path(td)
        target = root / "skip.py"

        argv = ["pydocfmt", "check", "--show-files", "--force-exclude", str(target)]
        run_mock = mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=git_helpers.fake_git_check_ignore_for_root(root, {"skip.py"}), autospec=True)
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.stdout.splitlines() == [f"{target} INCLUDED"]
        format_file.assert_not_called()
        run_mock.assert_not_called()


def test_command_line_extend_exclude_overrides_config_extend_exclude(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "skip.py"
        target.write_text("x = 1\n", encoding="utf-8")
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["*.py"]\nexclude = []\nextend-exclude = ["skip.py"]\n', encoding="utf-8")
        called_paths: list[str] = []

        def fake_format(path: str, *, file: object = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, settings, rule_selection, fix
            assert write
            called_paths.append(path)
            return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", str(target), "--force-exclude", "--extend-exclude", "other.py"]
        _patch_disk_formatter(mocker, fake_format)
        cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

        assert called_paths == [str(target)]


def _assert_help_ignores_invalid_config(main: Callable[[], int], program: str) -> None:
    """Assert that help output is available despite invalid local config."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["src/"]\n', encoding="utf-8")
        argv = [program, "--help"]
        result = cli_helpers.run_cli(main, argv, cwd=root, expect_system_exit=True)

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert result.stderr == ""


def test_pydocfmt_help_ignores_invalid_config() -> None:
    _assert_help_ignores_invalid_config(pydocfmt_cli.main, "pydocfmt")


def test_pydocfmt_check_help_ignores_invalid_config() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["src/"]\n', encoding="utf-8")
        argv = ["pydocfmt", "check", "--help"]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root, expect_system_exit=True)

    assert result.exit_code == 0
    output = result.stdout
    assert "Run:" in output
    assert "Formatting:" in output
    assert "Rule selection:" in output
    assert "File selection:" in output
    options = output[output.index("Options:") : output.index("Run:")]
    run_options = output[output.index("Run:") : output.index("Formatting:")]
    formatting = output[output.index("Formatting:") : output.index("Rule selection:")]
    assert options.index("--fix") < options.index("--diff")
    assert options.index("--diff") < options.index("--show-settings")
    assert options.index("--show-settings") < options.index("--show-rules")
    assert options.index("--show-rules") < options.index("--show-files")
    assert options.index("--show-files") < options.index("--output-file")
    assert run_options.index("--output-format") < run_options.index("--parallelism")
    assert "--line-length" in formatting
    assert output.index("Run:") < output.index("Formatting:")
    assert output.index("File selection:") < output.index("Miscellaneous:")
    assert output.index("Miscellaneous:") < output.index("Global options:")
    assert "--output-file FILE" in output
    assert "--diff" in output
    assert "--stdin-filename FILENAME" in output
    assert "--config CONFIG" in output
    assert "--line-length LENGTH" in output
    assert "--indent-width WIDTH" in output
    assert "--per-file-ignores RULE_TOML" in output
    assert result.stderr == ""


def test_pydocfmt_help_check_prints_check_help() -> None:
    argv = ["pydocfmt", "help", "check"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert "Usage: pydocfmt check" in result.stdout


def test_pydocfmt_config_lists_available_keys() -> None:
    argv = ["pydocfmt", "config"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml]


def test_pydocfmt_config_prints_option_details() -> None:
    argv = ["pydocfmt", "config", "line-length"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = result.stdout
    assert "Maximum line length for docstrings and comments." in output
    assert "Default value: 88" in output
    assert "Type: int" in output
    assert "Example usage:\n```toml\nline-length = 88\n```" in output


def test_pydocfmt_config_prints_option_json() -> None:
    argv = ["pydocfmt", "config", "--output-format", "json", "line-ending"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["doc"] == 'Line ending to use when rewriting files; one of "auto", "lf", "cr-lf", or "native".'
    assert output["default"] == '"auto"'
    assert output["value_type"] == '"auto" | "lf" | "cr-lf" | "native"'
    assert output["example"] == 'line-ending = "auto"'
    assert "scope" not in output
    assert "deprecated" not in output


def test_pydocfmt_config_prints_all_json() -> None:
    argv = ["pydocfmt", "config", "--output-format", "json"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert tuple(output) == tuple(definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml)
    assert output["line-length"]["default"] == "88"
    assert output["docstring-convention"]["default"] == '"pep257"'
    assert output["select"]["value_type"] == "list[str]"
    assert output["per-file-ignores"]["value_type"] == "dict[str, list[str]]"


def test_pydocfmt_config_rejects_unknown_option() -> None:
    argv = ["pydocfmt", "config", "unknown-key"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Invalid value 'unknown-key'" in result.stderr


def test_pydocfmt_config_rejects_invalid_output_format() -> None:
    argv = ["pydocfmt", "config", "--output-format", "yaml"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=True)

    assert result.exit_code == 2
    assert "invalid choice: 'yaml'" in result.stderr


def test_pydocfmt_config_help_and_help_config_print_config_help() -> None:
    for argv in (["pydocfmt", "config", "--help"], ["pydocfmt", "help", "config"]):
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=argv[-1] == "--help")
        assert result.exit_code == 0
        assert "Usage: pydocfmt config" in result.stdout
        assert "--output-format {text,json}" in result.stdout


def test_pydocfmt_config_ignores_invalid_config_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["src/"]\n', encoding="utf-8")
        argv = ["pydocfmt", "config", "line-length"]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 0
    assert "Default value: 88" in result.stdout
    assert result.stderr == ""


def test_pydocfmt_version_flag_and_command_print_version() -> None:
    outputs = []
    for argv in (["pydocfmt", "--version"], ["pydocfmt", "version"]):
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)
        assert result.exit_code == 0
        outputs.append(result.stdout)

    assert outputs[0] == outputs[1]
    assert re.search(r"^pydocfmt \d+\.\d+\.\d+\n$", outputs[0])


def test_pydocfmt_without_command_exits_with_usage_error() -> None:
    argv = ["pydocfmt"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 2
    assert "Usage: pydocfmt" in result.stderr


def test_pydocfmt_top_level_check_flag_is_rejected() -> None:
    argv = ["pydocfmt", "--check"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=True)

    assert result.exit_code == 2
    assert "unrecognized arguments: --check" in result.stderr


def test_pydocfmt_check_show_settings_prints_resolved_settings() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 72\nrespect-gitignore = false\n", encoding="utf-8")
        argv = ["pydocfmt", "check", "--show-settings", "--line-ending", "lf"]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 0
    output = result.stdout
    assert "[tool.pydocfmt]" in output
    assert output.index("output-format") < output.index("line-length")
    assert output.index("line-length") < output.index("select")
    assert output.index("extend-fixable") < output.index("\ninclude =")
    assert "line-length = 72" in output
    assert 'line-ending = "lf"' in output
    assert 'convention = "pep257"' in output
    assert "respect-gitignore = false" in output


@pytest.mark.parametrize(
    ("flag", "expected"), [("--docstring-include-assertion-errors", "include-assertion-errors = true"), ("--no-docstring-include-assertion-errors", "include-assertion-errors = false")]
)
def test_pydocfmt_check_assertion_error_flags_round_trip_through_show_settings(flag: str, expected: str) -> None:
    argv = ["pydocfmt", "check", "--show-settings", "--isolated", flag]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert expected in result.stdout


@pytest.mark.parametrize(("args", "settings"), SHOW_RULES_CASES)
def test_pydocfmt_check_show_rules_applies_conventions_and_manual_reenablements(args: tuple[str, ...], settings: CheckSettings) -> None:
    known_rule_codes = frozenset(rule_class.meta.code.tag for rule_class in rule_collection.RULE_COLLECTION.rules)

    def show_convention_rules(*args: str) -> tuple[int, tuple[str, ...], str]:
        argv = ["pydocfmt", "--isolated", "check", "--show-rules", *args]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)
        output = result.stdout
        rules: list[str] = []
        for line in output.splitlines():
            fields = line.split(maxsplit=1)
            if fields:
                rule_code = fields[0].removesuffix("*")
                if rule_code in known_rule_codes:
                    rules.append(rule_code)
        return result.exit_code, tuple(rules), output

    def assert_show_rules(args: tuple[str, ...], settings: CheckSettings) -> None:
        exit_code, rules, output = show_convention_rules(*args)
        selection = rules_selection.select_rules(settings)
        expected_exit_code = 1 if selection.errors else 0

        assert exit_code == expected_exit_code
        assert rules == tuple(rule.rule.code.tag for rule in selection.rules)
        for error in selection.errors:
            assert error in output
        if not selection.errors:
            assert "ERROR:" not in output

    assert_show_rules(args, settings)


def test_pydocfmt_check_config_file_prints_resolved_settings() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pydocfmt.toml"
        config_path.write_text("line-length = 97\nrespect-gitignore = false\n", encoding="utf-8")
        argv = ["pydocfmt", "check", "--show-settings", "--config", str(config_path)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = result.stdout
    assert "line-length = 97" in output
    assert "respect-gitignore = false" in output


def test_pydocfmt_check_config_options_work_before_and_after_command() -> None:
    argv = ["pydocfmt", "--config", "line-length = 99", "check", "--show-settings", "--config", 'line-ending = "lf"', "--line-length", "100"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    output = result.stdout
    assert "line-length = 100" in output
    assert 'line-ending = "lf"' in output


def test_pydocfmt_check_isolated_ignores_auto_discovered_pyproject() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 72\n", encoding="utf-8")
        argv = ["pydocfmt", "check", "--show-settings", "--isolated", "--config", "line-length = 106"]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 0
    output = result.stdout
    assert "line-length = 106" in output
    assert "line-length = 72" not in output


def test_pydocfmt_check_isolated_rejects_config_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config_path = root / "pydocfmt.toml"
        config_path.write_text("line-length = 97\n", encoding="utf-8")
        argv = ["pydocfmt", "check", "--show-settings", "--isolated", "--config", str(config_path)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 2
    assert "--config=PATH" in result.stderr
    assert "Traceback" not in result.stderr


def test_pydocfmt_check_show_files_and_show_settings_are_mutually_exclusive() -> None:
    argv = ["pydocfmt", "check", "--show-files", "--show-settings"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 2
    assert "Cannot use more than one of {--show-settings, --show-rules, --show-files} together" in result.stderr


def test_pydocfmt_check_exit_flags_are_mutually_exclusive() -> None:
    argv = ["pydocfmt", "check", "--exit-zero", "--exit-non-zero-on-fix"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, expect_system_exit=True)

    assert result.exit_code == 2
    assert "--exit-zero" in result.stderr
    assert "--exit-non-zero-on-fix" in result.stderr


def _assert_invalid_command_line_include_reports_argument_error(main: Callable[[], int], program: str) -> None:
    """Assert that an empty include CLI value reports an argument error."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        argv = [program, "check", str(root), "--include", ""]
        result = cli_helpers.run_cli(main, argv, cwd=root)

    assert result.exit_code == 2
    assert "<argparse>.include must not contain empty strings" in result.stderr
    assert "Traceback" not in result.stderr


def test_pydocfmt_invalid_command_line_exclude_reports_argument_error() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        argv = ["pydocfmt", "check", str(root), "--exclude", ""]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 2
    assert "<argparse>.exclude must not contain empty strings" in result.stderr
    assert "Traceback" not in result.stderr


def test_pydocfmt_invalid_command_line_include_reports_argument_error() -> None:
    _assert_invalid_command_line_include_reports_argument_error(pydocfmt_cli.main, "pydocfmt")


def _assert_directory_config_include_is_allowed(main: Callable[[], int], program: str) -> None:
    """Assert that a Ruff-style directory include config value is accepted."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text('[tool.pydocfmt]\ninclude = ["src/"]\n', encoding="utf-8")
        argv = [program, "check", str(root)]
        result = cli_helpers.run_cli(main, argv, cwd=root)

    assert result.exit_code == 0
    assert result.stdout == "All checks passed!\n"
    assert result.stderr == ""
    assert "Traceback" not in result.stderr


def test_pydocfmt_directory_config_include_is_allowed() -> None:
    _assert_directory_config_include_is_allowed(pydocfmt_cli.main, "pydocfmt")


def test_pydocfmt_invalid_toml_reports_config_error() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[tool.pydocfmt\n", encoding="utf-8")
        argv = ["pydocfmt", "check", str(root)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 2
    assert "pydocfmt check: Configuration error" in result.stderr
    assert "Failed to decode" in result.stderr
    assert "pyproject.toml" in result.stderr
    assert "Traceback" not in result.stderr


def test_pydocfmt_invalid_nested_config_reports_config_error() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        package = root / "package"
        package.mkdir()
        (package / "module.py").write_text("x = 1\n", encoding="utf-8")
        (package / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 0\n", encoding="utf-8")
        argv = ["pydocfmt", "check", str(root)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "pydocfmt check: Configuration error" in result.stderr
    assert "line-length" in result.stderr
    assert "greater than or equal to 1" in result.stderr
    assert "Traceback" not in result.stderr


def test_pydocfmt_show_files_invalid_nested_config_reports_config_error() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        package = root / "package"
        package.mkdir()
        (package / "module.py").write_text("x = 1\n", encoding="utf-8")
        (package / "pyproject.toml").write_text("[tool.pydocfmt]\nline-length = 0\n", encoding="utf-8")
        argv = ["pydocfmt", "check", "--show-files", str(root)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "pydocfmt check: Configuration error" in result.stderr
    assert "line-length" in result.stderr
    assert "greater than or equal to 1" in result.stderr
    assert "Traceback" not in result.stderr


def test_pydocfmt_missing_explicit_file_reports_operational_error() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "missing.py"
        argv = ["pydocfmt", "check", str(target)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert f"ERROR: Failed to read file {target}" in result.stdout
    assert "Traceback" not in result.stdout


def test_pydocfmt_aborts_when_gitignore_check_fails(mocker: MockerFixture) -> None:
    with _make_git_tree() as td:
        root = Path(td)

        argv = ["pydocfmt", "check", "--show-files", str(root)]
        mocker.patch("pydocformatter.file_selection.subprocess.run", return_value=subprocess.CompletedProcess(["git"], 128, stdout=b"", stderr=b"fatal: broken git"), autospec=True)
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 2
        assert result.stdout == ""
        assert f"pydocfmt check: File selection error: {root}: Unable to apply gitignore filtering: fatal: broken git" in result.stderr
        format_file.assert_not_called()


def test_pydocfmt_missing_git_reports_actionable_error(mocker: MockerFixture) -> None:
    with _make_git_tree() as td:
        root = Path(td)
        argv = ["pydocfmt", "check", "--show-files", str(root)]
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=FileNotFoundError, autospec=True)
        format_file = mocker.patch("pydocformatter.formatter.format_disk_file", autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 2
        assert result.stdout == ""
        assert (
            f"pydocfmt check: File selection error: {root}: Unable to apply gitignore filtering: Git executable was not found; install Git or disable gitignore filtering with --no-respect-gitignore"
            in result.stderr
        )
        format_file.assert_not_called()


def _make_tree_with_invalid_utf8() -> tempfile.TemporaryDirectory[str]:
    """Create a temporary tree containing one valid file and one invalid UTF-8 file."""
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    (root / "good.py").write_text("x = 1\n", encoding="utf-8")
    (root / "bad.py").write_bytes(b"\xff")
    return temp_dir


def test_pydocfmt_skips_undecodable_utf8_file_with_operational_error() -> None:
    with _make_tree_with_invalid_utf8() as td:
        root = Path(td)
        argv = ["pydocfmt", "check", str(root)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        output = result.stdout
        assert f"ERROR: Failed to decode {root / 'bad.py'} as UTF-8" in output


def test_pydocfmt_check_mode_still_exits_nonzero_with_mixed_decode_inputs() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "needs_fix.py").write_text('def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n', encoding="utf-8")
        (root / "bad.py").write_bytes(b"\xff")

        argv = ["pydocfmt", "check", "--line-length", "72", str(root)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 1
        output = result.stdout
        assert f"ERROR: Failed to decode {root / 'bad.py'} as UTF-8" in output
        assert f"{root / 'needs_fix.py'}:" in output
        assert "PDF101* Docstring chunk needs reflow. Line 2" in output


def test_pydocfmt_check_prints_success_message_for_clean_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text('"""Module."""\n\n\ndef foo():\n    """Do something."""\n    pass\n', encoding="utf-8")
        argv = ["pydocfmt", "check", str(target)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        assert result.stdout == "All checks passed!\n"


def test_pydocfmt_check_reports_warning_specific_pdf410_message() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "warning.py"
        source = 'def function():\n    """Summary.\n\n    Warns:\n        RuntimeWarning | UserWarning: Bad warning.\n    """\n'
        target.write_text(source, encoding="utf-8")
        argv = ["pydocfmt", "check", "--isolated", "--no-cache", "--no-fix", "--select", "PDF410", "--docstring-convention", "google", str(target)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 1
        assert target.read_text(encoding="utf-8") == source
        assert f"{target}:" in result.stdout
        assert "PDF410* Docstring warning entry spelling should be normalized from 'RuntimeWarning | UserWarning' to 'RuntimeWarning, UserWarning'. Line 5" in result.stdout


def test_pydocfmt_diff_prints_unified_diff_without_writing_file(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        original_source = "x = 1\n"
        formatted_source = "x = 2\n"
        target.write_text(original_source, encoding="utf-8")
        rule = RuleMetadata(
            code=RuleCode("PDF110"),
            name="summary-too-long",
            message="Docstring summary does not fit on one line",
            fix_availability=FixAvailability.NEVER,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
        called_args: list[tuple[bool, bool]] = []

        def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del path, file, settings, rule_selection
            called_args.append((fix, write))
            return FormatterResult(
                path=str(target),
                old_source=original_source,
                new_source=formatted_source,
                modified=True,
                fixed_findings=collections.Counter({PDF101_RULE: 1}),
                unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,), instance_fixable=None),),
                errors=(),
            )

        argv = ["pydocfmt", "check", "--diff", str(target)]
        _patch_disk_formatter(mocker, fake_format)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 1
        assert called_args == [(True, False)]
        assert target.read_text(encoding="utf-8") == original_source
        output = result.stdout
        assert output.startswith("Would fix 1 rule check error and leave 1 more unfixed (0 fixable).\n\n")
        assert f"\n--- {target}" in output
        assert f"+++ {target}" in output
        assert "-x = 1" in output
        assert "+x = 2" in output
        assert "PDF110" not in output


def test_parallelism_resolution_uses_cpu_count(mocker: MockerFixture) -> None:
    mocker.patch("pydocformatter.cli.check.os.cpu_count", return_value=8, autospec=True)
    assert check_command.resolve_parallelism(0.0) == 8
    assert check_command.resolve_parallelism(0.25) == 2
    assert check_command.resolve_parallelism(2.0) == 2


def test_parallelism_resolution_rejects_non_whole_values_above_one() -> None:
    with pytest.raises(settings_core.SettingsError, match="whole number"):
        check_command.resolve_parallelism(1.5)


def test_format_selected_files_caps_windows_workers_at_process_pool_limit(mocker: MockerFixture) -> None:
    profile = _profile(CheckSettings(parallelism=0.0))
    selected_files = tuple(file_selection.SelectedFile(path=f"{index}.py", profile=profile) for index in range(62))
    rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}
    created_max_workers: list[int | None] = []

    class FakeFuture:
        def __init__(self, result: formatter.DiskFormatResult) -> None:
            self._result = result

        def result(self) -> formatter.DiskFormatResult:
            return self._result

    class FakeExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            created_max_workers.append(max_workers)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def submit(self, fn: object, request: formatter.DiskFormatRequest, **kwargs: object) -> FakeFuture:
            del self, fn, kwargs
            result = FormatterResult(path=request.path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
            return FakeFuture(formatter.DiskFormatResult(result=result, clean_snapshot=None))

    mocker.patch("pydocformatter.cli.check.os.cpu_count", return_value=128, autospec=True)
    mocker.patch("pydocformatter.cli.check.sys.platform", "win32")
    mocker.patch("pydocformatter.cli.check.concurrent.futures.as_completed", side_effect=tuple, autospec=True)
    check_command.format_selected_files(
        selected_files, rule_selections=rule_selections, use_stdin=False, fix=False, write=True, parallelism=0.0, executor_factory=cast("check_command._ExecutorFactory", FakeExecutor)
    )

    assert created_max_workers == [61]


def test_format_selected_files_preserves_selected_order_when_parallel_results_complete_out_of_order(mocker: MockerFixture) -> None:
    profile = _profile(CheckSettings(parallelism=2.0))
    selected_files = (file_selection.SelectedFile(path="a.py", profile=profile), file_selection.SelectedFile(path="b.py", profile=profile), file_selection.SelectedFile(path="c.py", profile=profile))
    rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}
    completion_order: list[str] = []

    class FakeFuture:
        def __init__(self, result: formatter.DiskFormatResult) -> None:
            self._result = result

        def result(self) -> formatter.DiskFormatResult:
            completion_order.append(self._result.result.path)
            return self._result

    class FakeExecutor:
        def __init__(self, max_workers: int | None = None) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def submit(self, fn: object, request: formatter.DiskFormatRequest, **kwargs: object) -> FakeFuture:
            del self, fn, kwargs
            result = FormatterResult(path=request.path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
            return FakeFuture(formatter.DiskFormatResult(result=result, clean_snapshot=None))

    mocker.patch("pydocformatter.cli.check.concurrent.futures.as_completed", side_effect=lambda futures: reversed(tuple(futures)), autospec=True)
    batch = check_command.format_selected_files(
        selected_files, rule_selections=rule_selections, use_stdin=False, fix=False, write=True, parallelism=2.0, executor_factory=cast("check_command._ExecutorFactory", FakeExecutor)
    )

    assert completion_order == ["c.py", "b.py", "a.py"]
    assert [result.path for result in batch.results] == ["a.py", "b.py", "c.py"]


def test_format_selected_files_runs_real_process_pool_for_disk_files() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        first = root / "a.py"
        second = root / "b.py"
        first.write_text("x = 1\n", encoding="utf-8")
        second.write_text("y = 2\n", encoding="utf-8")
        profile = _profile(CheckSettings(parallelism=2.0))
        selected_files = (file_selection.SelectedFile(path=str(first), profile=profile), file_selection.SelectedFile(path=str(second), profile=profile))
        rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}

        batch = check_command.format_selected_files(selected_files, rule_selections=rule_selections, use_stdin=False, fix=False, write=True, parallelism=2.0)

    assert [result.path for result in batch.results] == [str(first), str(second)]
    assert [result.errors for result in batch.results] == [(), ()]


def test_format_selected_files_keeps_single_disk_file_sequential(mocker: MockerFixture) -> None:
    profile = _profile(CheckSettings(parallelism=2.0))
    selected_files = (file_selection.SelectedFile(path="a.py", profile=profile),)
    rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}
    mocker.patch("pydocformatter.cli.check.concurrent.futures.ProcessPoolExecutor", side_effect=AssertionError("single file must not use executor"))
    result = FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
    format_file = mocker.patch("pydocformatter.formatter.format_disk_file", return_value=formatter.DiskFormatResult(result=result, clean_snapshot=None), autospec=True)
    batch = check_command.format_selected_files(selected_files, rule_selections=rule_selections, use_stdin=False, fix=False, write=True, parallelism=2.0)

    assert [result.path for result in batch.results] == ["a.py"]
    format_file.assert_called_once()


def test_format_selected_files_keeps_stdin_sequential(mocker: MockerFixture) -> None:
    profile = _profile(CheckSettings(parallelism=2.0))
    selected_files = (file_selection.SelectedFile(path="-", profile=profile),)
    rule_selections = {profile.key(): rules_selection.select_rules(profile.settings, profile=profile)}
    mocker.patch("pydocformatter.cli.check.concurrent.futures.ProcessPoolExecutor", side_effect=AssertionError("stdin must not use executor"))
    format_file = mocker.patch(
        "pydocformatter.formatter.format_stream",
        return_value=FormatterResult(path="-", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=()),
        autospec=True,
    )
    batch = check_command.format_selected_files(selected_files, rule_selections=rule_selections, use_stdin=True, fix=False, write=True, parallelism=2.0)

    assert [result.path for result in batch.results] == ["-"]
    assert format_file.call_args.kwargs["file"] is sys.stdin


def test_pydocfmt_diff_exit_zero_suppresses_diff_exit_status(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text('"""Module."""\n\nx = 1\n', encoding="utf-8")

        def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, settings, rule_selection, fix, write
            return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--diff", "--exit-zero", str(target)]
        _patch_disk_formatter(mocker, fake_format)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        assert result.stdout.startswith("Would fix 1 rule check error.\n\n")


def test_pydocfmt_clean_diff_prints_success_message() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text('"""Module."""\n\nx = 1\n', encoding="utf-8")

        argv = ["pydocfmt", "check", "--diff", str(target)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        assert result.stdout == "All checks passed!\n"


def test_pydocfmt_diff_output_file_writes_summary_without_diff(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        output_file = root / "reports" / "errors.txt"
        target.write_text("x = 1\n", encoding="utf-8")

        def fake_format(path: str, *, file: TextIO | None = None, settings: CheckSettings, rule_selection: RuleSelection, fix: bool, write: bool) -> FormatterResult:
            del file, settings, rule_selection, fix, write
            return FormatterResult(
                path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1, PCF000_RULE: 2}), unfixed_findings=(), errors=()
            )

        argv = ["pydocfmt", "check", "--diff", "--output-file", str(output_file), str(target)]
        _patch_disk_formatter(mocker, fake_format)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 1
        assert result.stdout.startswith(f"\n--- {target}")
        assert "Would fix" not in result.stdout
        assert output_file.read_text(encoding="utf-8") == "Would fix 3 rule check errors.\n"


def test_pydocfmt_clean_diff_output_file_writes_success_message() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        output_file = root / "reports" / "errors.txt"
        target.write_text('"""Module."""\n\nx = 1\n', encoding="utf-8")

        argv = ["pydocfmt", "check", "--diff", "--output-file", str(output_file), str(target)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        assert result.stdout == ""
        assert output_file.read_text(encoding="utf-8") == "All checks passed!\n"


def test_pydocfmt_diff_stdin_uses_stdin_filename_in_diff_headers(mocker: MockerFixture) -> None:
    source = "x = 1\n"

    def fake_format(path: str, *, file: TextIO, settings: CheckSettings, rule_selection: RuleSelection, fix: bool) -> FormatterResult:
        del settings, rule_selection, fix
        assert file.read() == source
        return FormatterResult(path=path, old_source=source, new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

    argv = ["pydocfmt", "check", "--fix", "--diff", "--stdin-filename", "virtual.py"]
    mocker.patch("pydocformatter.formatter.format_stream", side_effect=fake_format, autospec=True)
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, stdin=source)

    assert result.exit_code == 1
    assert "--- virtual.py" in result.stdout
    assert "+++ virtual.py" in result.stdout


def test_pydocfmt_stdin_filename_sets_display_path_and_ignores_paths(mocker: MockerFixture) -> None:
    source = 'def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n'
    called_paths: list[str] = []

    def fake_format(path: str, *, file: TextIO, settings: CheckSettings, rule_selection: RuleSelection, fix: bool) -> FormatterResult:
        del settings, rule_selection, fix
        called_paths.append(path)
        assert file.read() == source
        return FormatterResult(path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

    argv = ["pydocfmt", "check", "ignored.py", "--stdin-filename", "virtual.py", "--line-length", "72"]
    mocker.patch("pydocformatter.formatter.format_stream", side_effect=fake_format, autospec=True)
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, stdin=source)

    assert result.exit_code == 1
    assert called_paths == ["virtual.py"]
    assert "ERROR: Using standard input instead of input path: ignored.py" in result.stdout
    assert "All checks passed!" not in result.stdout
    assert result.stderr == ""


def test_pydocfmt_stdin_filename_force_exclude_filters_by_exclude() -> None:
    argv = ["pydocfmt", "check", "--show-files", "--stdin-filename", "skip.py", "--force-exclude", "--exclude", "skip.py"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["skip.py IGNORED: matches exclude patterns"]


def test_pydocfmt_stdin_filename_force_exclude_does_not_format_excluded_path(mocker: MockerFixture) -> None:
    source = "def foo():\n    pass\n"
    format_file = mocker.Mock(return_value=FormatterResult(path="skip.py", old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=()))
    argv = ["pydocfmt", "check", "--stdin-filename", "skip.py", "--force-exclude", "--exclude", "skip.py"]
    mocker.patch("pydocformatter.formatter.format_stream", format_file)
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, stdin=source)

    assert result.exit_code == 0
    format_file.assert_not_called()
    assert result.stdout == "All checks passed!\n"
    assert result.stderr == ""


def test_pydocfmt_stdin_filename_force_exclude_does_not_filter_by_gitignore(mocker: MockerFixture) -> None:
    with _make_git_tree() as td:
        root = Path(td)
        argv = ["pydocfmt", "check", "--show-files", "--stdin-filename", "skip.py", "--force-exclude"]
        mocker.patch("pydocformatter.file_selection.subprocess.run", side_effect=git_helpers.fake_git_check_ignore_for_root(root, {"skip.py"}), autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, cwd=root)

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [f"{root / 'skip.py'} INCLUDED"]


def test_pydocfmt_fix_stdin_writes_formatted_source_to_stdout(mocker: MockerFixture) -> None:
    source = 'def foo():\n    """Does something.\n\nArgs:\n    x (int): some parameter.\n    """\n    pass\n'
    formatted_source = 'def foo():\n    """Does something.\n\n    Args:\n        x (int): some parameter.\n    """\n    pass\n'

    def fake_format(path: str, *, file: TextIO, settings: CheckSettings, rule_selection: RuleSelection, fix: bool) -> FormatterResult:
        del path, settings, rule_selection
        assert fix
        assert file.read() == source
        return FormatterResult(path="-", old_source=source, new_source=formatted_source, modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

    argv = ["pydocfmt", "check", "--fix", "-", "--line-length", "72"]
    mocker.patch("pydocformatter.formatter.format_stream", side_effect=fake_format, autospec=True)
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv, stdin=source)

    assert result.exit_code == 0
    assert result.stdout == formatted_source
    assert result.stderr == "-:\n  PDF101* Docstring chunk needs reflow. Fixed 1 time.\n\nFixed 1 rule check error.\n"


def test_pydocfmt_fix_stdin_with_output_file_writes_diagnostics_to_file(mocker: MockerFixture) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        output_file = root / "reports" / "errors.txt"
        source = 'def foo():\n    """Does something."""\n    pass\n'
        formatted_source = 'def foo():\n    """Does something better."""\n    pass\n'

        def fake_format(path: str, *, file: TextIO, settings: CheckSettings, rule_selection: RuleSelection, fix: bool) -> FormatterResult:
            del path, settings, rule_selection
            assert fix
            assert file.read() == source
            return FormatterResult(path="-", old_source=source, new_source=formatted_source, modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

        argv = ["pydocfmt", "check", "--fix", "-", "--line-length", "72", "--output-file", str(output_file)]
        mocker.patch("pydocformatter.formatter.format_stream", side_effect=fake_format, autospec=True)
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv, stdin=source)

        assert result.exit_code == 0
        assert result.stdout == formatted_source
        assert result.stderr == ""
        assert output_file.read_text(encoding="utf-8") == "-:\n  PDF101* Docstring chunk needs reflow. Fixed 1 time.\n\nFixed 1 rule check error.\n"


def test_pydocfmt_output_file_redirects_check_errors_and_creates_parent() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text('def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n', encoding="utf-8")
        output_file = root / "reports" / "errors.txt"
        argv = ["pydocfmt", "check", str(target), "--line-length", "72", "--select", "PDF101", "--output-file", str(output_file)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 1
        assert result.stdout == ""
        output = output_file.read_text(encoding="utf-8")
        assert f"{target}:" in output
        assert "PDF101* Docstring chunk needs reflow. Line 2" in output
        assert "Found 1 rule check error (1 fixable)." in output


def test_pydocfmt_output_file_redirects_operational_errors() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "missing.py"
        output_file = root / "reports" / "errors.txt"
        argv = ["pydocfmt", "check", str(target), "--output-file", str(output_file)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 1
        assert result.stdout == ""
        assert result.stderr == ""
        output = output_file.read_text(encoding="utf-8")
        assert f"ERROR: Failed to read file {target}" in output
        assert "Found 1 operational error." in output


def test_pydocfmt_output_file_redirects_clean_check_success_message() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text('"""Module."""\n\n\ndef foo():\n    """Do something."""\n    pass\n', encoding="utf-8")
        output_file = root / "reports" / "errors.txt"
        argv = ["pydocfmt", "check", str(target), "--output-file", str(output_file)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        assert result.stdout == ""
        assert output_file.read_text(encoding="utf-8") == "All checks passed!\n"


def test_pydocfmt_output_file_does_not_create_nested_parents() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        target.write_text('def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n', encoding="utf-8")
        output_file = root / "reports" / "nested" / "errors.txt"
        argv = ["pydocfmt", "check", str(target), "--line-length", "72", "--output-file", str(output_file)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 2
        assert not (root / "reports").exists()
        assert "pydocfmt check: Output error:" in result.stderr


def test_pydocfmt_output_file_redirects_show_output() -> None:
    with _make_sample_tree() as td:
        root = Path(td)
        output_file = root / "reports" / "show-files.txt"
        argv = ["pydocfmt", "check", str(root), "--show-files", "--include", "*.py", "--exclude", "skip.py", "--output-file", str(output_file)]
        result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

        assert result.exit_code == 0
        assert result.stdout == ""
        assert output_file.read_text(encoding="utf-8").splitlines() == [
            f"{root / 'a.py'} INCLUDED",
            f"{root / 'b.txt'} IGNORED: does not match include patterns",
            f"{root / 'skip.py'} IGNORED: matches exclude patterns",
        ]


def test_pydocfmt_stdin_filename_is_allowed_with_show_files() -> None:
    argv = ["pydocfmt", "check", "--show-files", "--stdin-filename", "virtual.py"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["virtual.py INCLUDED"]


def test_pydocfmt_stdin_filename_is_allowed_with_show_settings() -> None:
    argv = ["pydocfmt", "check", "--show-settings", "--stdin-filename", "virtual.py"]
    result = cli_helpers.run_cli(pydocfmt_cli.main, argv)

    assert result.exit_code == 0
    assert "[tool.pydocfmt]" in result.stdout
