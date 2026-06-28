import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, List, Sequence

import pytest

RUNNER_PATH = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "loupe" / "scripts" / "run_reviewers.py"


def load_loupe_runner() -> ModuleType:
    """Load the Loupe runner script as an importable module."""
    spec = importlib.util.spec_from_file_location("loupe_run_reviewers", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def executable_availability(*available_executables: str) -> Callable[[str], bool]:
    """Return an availability probe for selected executable names."""
    return lambda executable: executable in available_executables


def test_parse_args_requires_review_scope() -> None:
    """Require callers to pass explicit review scope text."""
    runner = load_loupe_runner()

    with pytest.raises(SystemExit) as exc_info:
        runner.parse_args([])

    assert exc_info.value.code == 2


def test_parse_args_rejects_blank_review_scope() -> None:
    """Reject blank scope values instead of substituting a default."""
    runner = load_loupe_runner()

    for scope in ("", "   "):
        with pytest.raises(SystemExit) as exc_info:
            runner.parse_args([scope])

        assert exc_info.value.code == 2


def test_parse_args_rejects_multiple_review_scope_arguments() -> None:
    """Require the review scope to be passed as one shell-quoted argument."""
    runner = load_loupe_runner()

    with pytest.raises(SystemExit) as exc_info:
        runner.parse_args(["uncommitted", "changes"])

    assert exc_info.value.code == 2


def test_dry_run_uses_expected_json_shape_and_reviewer_commands(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Emit dry-run reviewer names and commands using the public JSON keys."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("claude", "codex", "jq"))

    exit_code = runner.main(["--dry-run", "uncommitted changes"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert list(payload) == ["review_scope", "git_root", "timeout_seconds", "reviewers"]
    assert payload["review_scope"] == "uncommitted changes"
    assert payload["timeout_seconds"] == 1800
    assert [list(reviewer) for reviewer in payload["reviewers"]] == [
        ["reviewer_name", "launched_command"],
        ["reviewer_name", "launched_command"],
        ["reviewer_name", "launched_command"],
        ["reviewer_name", "launched_command"],
    ]
    assert payload["reviewers"] == [
        {
            "reviewer_name": "Claude Code Review",
            "launched_command": runner.CLAUDE_COMMAND_TEMPLATE.format(
                prompt=runner.shlex.quote(
                    runner.CODE_REVIEW_COMMAND_PROMPT_TEMPLATE.format(
                        review_scope="uncommitted changes", review_policy=runner.REVIEW_POLICY, review_skill_prohibition=runner.REVIEW_SKILL_PROHIBITION, review_note=runner.REVIEW_NOTE
                    )
                )
            ),
        },
        {
            "reviewer_name": "Codex Review",
            "launched_command": runner.CODEX_COMMAND_TEMPLATE.format(
                prompt=runner.shlex.quote(
                    runner.REVIEW_COMMAND_PROMPT_TEMPLATE.format(
                        review_scope="uncommitted changes", review_policy=runner.REVIEW_POLICY, review_skill_prohibition=runner.REVIEW_SKILL_PROHIBITION, review_note=runner.REVIEW_NOTE
                    )
                )
            ),
        },
        {
            "reviewer_name": "Codex Correctness",
            "launched_command": runner.CODEX_COMMAND_TEMPLATE.format(
                prompt=runner.shlex.quote(
                    runner.CORRECTNESS_REVIEW_PROMPT_TEMPLATE.format(
                        review_scope="uncommitted changes", review_policy=runner.REVIEW_POLICY, review_skill_prohibition=runner.REVIEW_SKILL_PROHIBITION, review_note=runner.REVIEW_NOTE
                    )
                )
            ),
        },
        {
            "reviewer_name": "Codex Design",
            "launched_command": runner.CODEX_COMMAND_TEMPLATE.format(
                prompt=runner.shlex.quote(
                    runner.DESIGN_REVIEW_PROMPT_TEMPLATE.format(
                        review_scope="uncommitted changes", review_policy=runner.REVIEW_POLICY, review_skill_prohibition=runner.REVIEW_SKILL_PROHIBITION, review_note=runner.REVIEW_NOTE
                    )
                )
            ),
        },
    ]
    assert "\nTask: It is very important to me that the code now works completely correctly" in payload["reviewers"][2]["launched_command"]
    assert "\nTask: It is very important to me that the code is well-structured" in payload["reviewers"][3]["launched_command"]
    assert runner.REVIEW_SKILL_PROHIBITION in payload["reviewers"][2]["launched_command"]
    assert runner.REVIEW_SKILL_PROHIBITION in payload["reviewers"][3]["launched_command"]


def test_dry_run_skips_claude_reviewers_when_claude_is_missing(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Omit Claude reviewers from dry-run output when the Claude CLI is unavailable."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("codex", "jq"))

    exit_code = runner.main(["--dry-run", "uncommitted changes"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert list(payload) == ["review_scope", "git_root", "timeout_seconds", "reviewers"]
    reviewer_names = [reviewer["reviewer_name"] for reviewer in payload["reviewers"]]
    assert reviewer_names == ["Codex Review", "Codex Correctness", "Codex Design"]
    assert all(not reviewer_name.startswith("Claude ") for reviewer_name in reviewer_names)


def test_dry_run_skips_codex_reviewers_when_codex_is_missing(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Omit Codex reviewers from dry-run output when the Codex CLI is unavailable."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("claude", "jq"))

    exit_code = runner.main(["--dry-run", "uncommitted changes"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert list(payload) == ["review_scope", "git_root", "timeout_seconds", "reviewers"]
    reviewer_names = [reviewer["reviewer_name"] for reviewer in payload["reviewers"]]
    assert reviewer_names == ["Claude Code Review"]


def test_dry_run_output_file_matches_stdout(capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Write the exact emitted dry-run JSON to the requested output file."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("claude", "codex", "jq"))
    output_path = tmp_path / "reviewers.json"

    exit_code = runner.main(["--dry-run", "--output", str(output_path), "uncommitted changes"])

    stdout = capsys.readouterr().out
    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == stdout
    assert json.loads(stdout)["review_scope"] == "uncommitted changes"


def test_reviewer_launch_plan_uses_required_executable_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Filter reviewer runs by executable metadata instead of display name."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", lambda executable: False)
    reviewers = (
        runner.Reviewer("Claude Local", "printf keep", "{review_scope}"),
        runner.Reviewer("Anthropic Review", "printf skip", "{review_scope}", required_executable="claude"),
    )

    runs = runner.reviewer_launch_plan(reviewers, "metadata scope")

    assert [run.reviewer.reviewer_name for run in runs] == ["Claude Local"]
    assert [run.launch_error for run in runs] == [None]


def test_reviewer_launch_plan_shares_executable_availability_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Probe each executable only once across primary and helper dependencies."""
    runner = load_loupe_runner()
    checked_executables: List[str] = []

    def executable_is_available(executable: str) -> bool:
        checked_executables.append(executable)
        return True

    monkeypatch.setattr(runner, "executable_is_available", executable_is_available)
    reviewers = (
        runner.Reviewer("Primary Shared", "printf primary", "{review_scope}", required_executable="shared-tool"),
        runner.Reviewer("Helper Shared", "printf helper", "{review_scope}", additional_required_executables=("shared-tool",)),
    )

    runs = runner.reviewer_launch_plan(reviewers, "shared cache scope")

    assert [run.reviewer.reviewer_name for run in runs] == ["Primary Shared", "Helper Shared"]
    assert [run.launch_error for run in runs] == [None, None]
    assert checked_executables == ["shared-tool"]


def test_reviewer_launch_plan_attaches_missing_helper_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Store helper dependency failures on the planned reviewer run."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("codex"))
    reviewers = (runner.Reviewer("Codex Local", "printf should-not-run", "{review_scope}", required_executable="codex", additional_required_executables=("jq",)),)

    runs = runner.reviewer_launch_plan(reviewers, "helper-missing scope")

    assert len(runs) == 1
    assert runs[0].launch_error == "Missing additional executable 'jq' for Codex Local. Please install jq and rerun Loupe."


def test_executable_availability_uses_reviewer_launch_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """Probe executable availability through bash login-shell command resolution."""
    runner = load_loupe_runner()
    launched_commands: List[Sequence[str]] = []

    class CompletedProcess:
        returncode = 0

    def run(command: Sequence[str], **kwargs: Any) -> CompletedProcess:
        launched_commands.append(command)
        return CompletedProcess()

    monkeypatch.setattr(runner.subprocess, "run", run)

    assert runner.executable_is_available("claude") is True
    assert launched_commands == [["bash", "-lc", "command -v claude"]]


def test_missing_claude_skips_claude_reviewers_before_launch(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not launch Claude reviewers when the Claude CLI is unavailable."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("codex", "jq"))
    reviewers = (
        runner.Reviewer("Claude Missing", "printf should-not-run; exit 9", "{review_scope}", required_executable="claude"),
        runner.Reviewer("Codex Local", "printf ok", "{review_scope}", required_executable="codex", additional_required_executables=("jq",)),
    )

    exit_code = runner.main(["filtered scope"], reviewers=reviewers)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [reviewer["reviewer_name"] for reviewer in payload["reviewers"]] == ["Codex Local"]
    assert payload["reviewers"][0]["stdout"] == "ok"


def test_all_filtered_reviewers_return_nonzero_and_empty_payload(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail clearly when no configured reviewer can be launched."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", lambda executable: False)
    reviewers = (runner.Reviewer("Anthropic Review", "printf should-not-run", "{review_scope}", required_executable="claude"),)

    exit_code = runner.main(["filtered scope"], reviewers=reviewers)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert runner.NO_LAUNCHABLE_REVIEWERS_MESSAGE in captured.err
    payload = json.loads(captured.out)
    assert list(payload) == ["review_scope", "git_root", "timeout_seconds", "elapsed_seconds", "reviewers"]
    assert payload["reviewers"] == []


def test_dry_run_all_filtered_reviewers_return_nonzero_and_empty_payload(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail dry runs clearly when no configured reviewer can be launched."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", lambda executable: False)
    reviewers = (runner.Reviewer("Anthropic Review", "printf should-not-run", "{review_scope}", required_executable="claude"),)

    exit_code = runner.main(["--dry-run", "filtered scope"], reviewers=reviewers)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert runner.NO_LAUNCHABLE_REVIEWERS_MESSAGE in captured.err
    payload = json.loads(captured.out)
    assert list(payload) == ["review_scope", "git_root", "timeout_seconds", "reviewers"]
    assert payload["reviewers"] == []


def test_missing_additional_executable_produces_launch_failed_without_launch(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail a launchable reviewer clearly when a helper executable is unavailable."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("codex"))
    reviewers = (runner.Reviewer("Codex Local", "printf should-not-run", "{review_scope}", required_executable="codex", additional_required_executables=("jq",)),)

    exit_code = runner.main(["helper-missing scope"], reviewers=reviewers)

    captured = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(captured.out)
    result = payload["reviewers"][0]
    assert result["reviewer_name"] == "Codex Local"
    assert result["status"] == "launch_failed"
    assert result["return_code"] is None
    assert result["stdout"] == ""
    assert result["stderr"] == "Missing additional executable 'jq' for Codex Local. Please install jq and rerun Loupe."


def test_dry_run_reports_missing_additional_executable(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Return dry-run commands while warning about missing helper executables."""
    runner = load_loupe_runner()
    monkeypatch.setattr(runner, "executable_is_available", executable_availability("codex"))
    reviewers = (runner.Reviewer("Codex Local", "printf would-run", "{review_scope}", required_executable="codex", additional_required_executables=("jq",)),)

    exit_code = runner.main(["--dry-run", "helper-missing scope"], reviewers=reviewers)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing additional executable 'jq' for Codex Local. Please install jq and rerun Loupe." in captured.err
    payload = json.loads(captured.out)
    assert [reviewer["reviewer_name"] for reviewer in payload["reviewers"]] == ["Codex Local"]
    assert payload["reviewers"][0]["launched_command"] == "printf would-run"


def test_failed_reviewer_produces_failed_status_and_nonzero_exit(capsys: pytest.CaptureFixture[str]) -> None:
    """Return nonzero when any reviewer command fails."""
    runner = load_loupe_runner()
    reviewers = (
        runner.Reviewer("success", "printf ok", "{review_scope}"),
        runner.Reviewer("failure", "printf problem >&2; exit 4", "{review_scope}"),
    )

    exit_code = runner.main(["failing scope"], reviewers=reviewers)

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    success, failure = payload["reviewers"]
    assert success["status"] == "succeeded"
    assert success["return_code"] == 0
    assert failure["status"] == "failed"
    assert failure["return_code"] == 4
    assert failure["stderr"] == "problem"


def test_review_output_file_matches_stdout(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Write the exact emitted reviewer JSON to the requested output file."""
    runner = load_loupe_runner()
    output_path = tmp_path / "reviewers.json"
    reviewers = (runner.Reviewer("only", "printf result", "{review_scope}"),)

    exit_code = runner.main(["--output", str(output_path), "artifact scope"], reviewers=reviewers)

    stdout = capsys.readouterr().out
    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == stdout
    payload = json.loads(stdout)
    assert payload["review_scope"] == "artifact scope"
    assert payload["reviewers"][0]["stdout"] == "result"


def test_reviewer_elapsed_timer_starts_at_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start reviewer elapsed timing at process launch instead of run construction."""
    runner = load_loupe_runner()
    run = runner.ReviewerRun(runner.Reviewer("timed", "printf ok", "{review_scope}"), "printf ok")
    times = iter((100.0, 100.25))

    class FakePopen:
        returncode = 0

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(runner.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: FakePopen())

    assert run.started_at is None
    assert run.elapsed_seconds() == 0.0

    run.launch()
    assert run.thread is not None
    run.thread.join()
    run.close()

    assert run.started_at == 100.0
    assert run.elapsed_seconds() == 0.25
