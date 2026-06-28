import importlib.util
import json
from pathlib import Path
from types import ModuleType

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


def test_dry_run_uses_expected_json_shape_and_reviewer_commands(capsys: pytest.CaptureFixture[str]) -> None:
    """Emit dry-run reviewer names and commands using the public JSON keys."""
    runner = load_loupe_runner()

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


def test_dry_run_output_file_matches_stdout(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Write the exact emitted dry-run JSON to the requested output file."""
    runner = load_loupe_runner()
    output_path = tmp_path / "reviewers.json"

    exit_code = runner.main(["--dry-run", "--output", str(output_path), "uncommitted changes"])

    stdout = capsys.readouterr().out
    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == stdout
    assert json.loads(stdout)["review_scope"] == "uncommitted changes"


def test_reviewers_run_in_parallel_and_keep_separate_elapsed_times(capsys: pytest.CaptureFixture[str]) -> None:
    """Track global elapsed time independently from each reviewer runtime."""
    runner = load_loupe_runner()
    reviewers = (
        runner.Reviewer("fast", "sleep 0.05; printf fast", "{review_scope}"),
        runner.Reviewer("slow", "sleep 0.25; printf slow", "{review_scope}"),
    )

    exit_code = runner.main(["--timeout-seconds", "2", "parallel scope"], reviewers=reviewers)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    fast, slow = payload["reviewers"]
    assert list(payload) == ["review_scope", "git_root", "timeout_seconds", "elapsed_seconds", "reviewers"]
    assert [list(result) for result in payload["reviewers"]] == [
        ["reviewer_name", "launched_command", "status", "timed_out", "return_code", "elapsed_seconds", "stdout", "stderr"],
        ["reviewer_name", "launched_command", "status", "timed_out", "return_code", "elapsed_seconds", "stdout", "stderr"],
    ]
    assert fast["status"] == "succeeded"
    assert slow["status"] == "succeeded"
    assert fast["stdout"] == "fast"
    assert slow["stdout"] == "slow"
    assert fast["elapsed_seconds"] < slow["elapsed_seconds"]
    assert payload["elapsed_seconds"] >= slow["elapsed_seconds"]
    assert payload["elapsed_seconds"] < 0.5


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


def test_timed_out_reviewer_is_terminated(capsys: pytest.CaptureFixture[str]) -> None:
    """Terminate still-running reviewers at the global timeout."""
    runner = load_loupe_runner()
    reviewers = (runner.Reviewer("slow", "sleep 5; printf late", "{review_scope}"),)

    exit_code = runner.main(["--timeout-seconds", "0.15", "timeout scope"], reviewers=reviewers)

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    result = payload["reviewers"][0]
    assert result["status"] == "timed_out"
    assert result["timed_out"] is True
    assert result["stdout"] == ""
    assert result["elapsed_seconds"] < 1.0


def test_sigterm_resistant_timed_out_reviewer_is_killed(capsys: pytest.CaptureFixture[str]) -> None:
    """Kill timed-out reviewers that do not exit after SIGTERM."""
    runner = load_loupe_runner()
    setattr(runner, "PROCESS_TERMINATION_SECONDS", 0.1)
    reviewers = (runner.Reviewer("slow", "trap '' TERM; sleep 5; printf late", "{review_scope}"),)

    exit_code = runner.main(["--timeout-seconds", "0.15", "timeout scope"], reviewers=reviewers)

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    result = payload["reviewers"][0]
    assert result["status"] == "timed_out"
    assert result["timed_out"] is True
    assert result["stdout"] == ""
    assert result["elapsed_seconds"] < 1.0


def test_timed_out_reviewer_does_not_wait_for_detached_output_handles(capsys: pytest.CaptureFixture[str]) -> None:
    """Return promptly when descendants keep inherited output files open."""
    runner = load_loupe_runner()
    setattr(runner, "PROCESS_TERMINATION_SECONDS", 0.1)
    reviewers = (runner.Reviewer("pipe-holder", "setsid sh -c 'sleep 1' & printf parent; sleep 5", "{review_scope}"),)

    exit_code = runner.main(["--timeout-seconds", "0.1", "timeout scope"], reviewers=reviewers)

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    result = payload["reviewers"][0]
    assert result["status"] == "timed_out"
    assert result["timed_out"] is True
    assert result["stdout"] == "parent"
    assert result["elapsed_seconds"] < 0.5
