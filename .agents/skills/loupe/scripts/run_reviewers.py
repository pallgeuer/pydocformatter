#!/usr/bin/env python3
"""Run configured Loupe reviewer commands and emit structured JSON.

This Python script must support Python 3.6+.
"""

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, BinaryIO, Dict, List, Optional, Sequence

DEFAULT_TIMEOUT_SECONDS = 30 * 60
PROCESS_TERMINATION_SECONDS = 5
NO_LAUNCHABLE_REVIEWERS_MESSAGE = "No launchable reviewers are available."
MISSING_ADDITIONAL_EXECUTABLE_MESSAGE_TEMPLATE = "Missing additional executable '{}' for {}. Please install {} and rerun Loupe."

CODEX_COMMAND_TEMPLATE = """( set -o pipefail; codex exec --cd "$(git rev-parse --show-toplevel)" --ephemeral --sandbox workspace-write -c model_reasoning_effort='"high"' --json {prompt} | jq -ser 'map(select(.type == "item.completed" and .item.type == "agent_message") | .item.text) | last // empty' )"""
CLAUDE_COMMAND_TEMPLATE = """( set -o pipefail; cd "$(git rev-parse --show-toplevel)" && claude -p --no-session-persistence --permission-mode auto --effort high --output-format json {prompt} | jq -er ".result" )"""  # fmt: skip

REVIEW_SKILL_PROHIBITION = "Do not launch any kind of review skill."
REVIEW_POLICY = "Review only. Do not modify repository files, stage changes, commit, install dependencies, or use external network access except normal web search. You may inspect files and run local validation, including manual tests; incidental temp/cache artifacts are okay."
REVIEW_NOTE = "{} {}".format(REVIEW_SKILL_PROHIBITION, REVIEW_POLICY)

CODE_REVIEW_COMMAND_PROMPT_TEMPLATE = "{review_policy} /code-review {review_scope}"
REVIEW_COMMAND_PROMPT_TEMPLATE = "{review_policy} /review {review_scope}"
CORRECTNESS_REVIEW_PROMPT_TEMPLATE = """Review scope: {review_scope}
Task: It is very important to me that the code now works completely correctly and as intended, and robustly performs the exact required actions in all cases without the risk of unintended side-effects. Carefully analyze the code in detail to ensure this. Construct and run a large number of manual tests to test all conceivable unusual/complex/mixed situations, as well as special/edge cases, and on purposely try to find (in an adversarial manner) manual tests that make the current implementation fail or do the wrong thing. Explicitly consider measured test code coverage, if possible. If a manual test fails, then think critically whether the expectation of the test is truly correct or the current implementation behavior is actually truly correct.
Note: {review_note}"""
DESIGN_REVIEW_PROMPT_TEMPLATE = """Review scope: {review_scope}
Task: It is very important to me that the code is well-structured, well-organized, maintainable long-term, has clean/meaningful interfaces/contracts/abstraction boundaries throughout, and exhibits good design patterns/architectural choices. Carefully analyze the code in detail to ensure this, and identify any code smells/recommended refactoring opportunities. Search also explicitly for any duplicated logic, unnecessary thin wrappers, dead code, old compatibility code that is no longer needed, and unnecessarily inefficient code.
Note: {review_note}"""


class Reviewer:
    """Command and prompt template for one external reviewer."""

    def __init__(self, reviewer_name: str, command_template: str, prompt_template: str, required_executable: Optional[str] = None, additional_required_executables: Sequence[str] = ()) -> None:
        """Store the display name, command template, prompt template, fundamental executable, and helper executables."""
        self.reviewer_name = reviewer_name
        self.command_template = command_template
        self.prompt_template = prompt_template
        self.required_executable = required_executable
        self.additional_required_executables = tuple(additional_required_executables)

    def build_prompt(self, review_scope: str) -> str:
        """Return the complete prompt passed to this reviewer for a scope."""
        return self.prompt_template.format(review_scope=review_scope, review_policy=REVIEW_POLICY, review_skill_prohibition=REVIEW_SKILL_PROHIBITION, review_note=REVIEW_NOTE)

    def build_command(self, review_scope: str) -> str:
        """Return the launched shell command for this reviewer and scope."""
        return self.command_template.format(prompt=shlex.quote(self.build_prompt(review_scope)))


class ReviewerRun:
    """Mutable execution state for one launched reviewer process."""

    def __init__(self, reviewer: Reviewer, launched_command: str, launch_error: Optional[str] = None) -> None:
        """Initialize process, timing, and captured output fields."""
        self.reviewer = reviewer
        self.launched_command = launched_command
        self.process = None  # type: Optional[subprocess.Popen[Any]]
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.stdout = ""
        self.stderr = ""
        self.launch_error = launch_error
        self.collection_error: Optional[str] = None
        self.thread: Optional[threading.Thread] = None
        self.stdout_file: Optional[BinaryIO] = None
        self.stderr_file: Optional[BinaryIO] = None
        self.timed_out = False

    def launch(self) -> None:
        """Start the reviewer process and begin collecting its output."""
        try:
            self.stdout_file = tempfile.TemporaryFile(mode="w+b")
            self.stderr_file = tempfile.TemporaryFile(mode="w+b")
            self.started_at = time.monotonic()
            self.process = subprocess.Popen(
                ["bash", "-lc", self.launched_command],
                stdout=self.stdout_file,
                stderr=self.stderr_file,
                universal_newlines=True,
                start_new_session=True,
            )
        except OSError as exc:
            self.launch_error = str(exc)
            self.finished_at = time.monotonic()
            self.close()
            return

        self.thread = threading.Thread(target=self._collect_output)
        self.thread.daemon = True
        self.thread.start()

    def _collect_output(self) -> None:
        """Wait for the process to finish and capture stdout and stderr."""
        if self.process is None:
            self.finished_at = time.monotonic()
            return
        try:
            self.process.wait()
            self._refresh_output()
        except OSError as exc:
            self.collection_error = str(exc)
        self.finished_at = time.monotonic()

    def _read_output_file(self, output_file: BinaryIO) -> str:
        """Return current text from a temporary output file."""
        output_file.flush()
        output_file.seek(0)
        return output_file.read().decode("utf-8", errors="replace")

    def _refresh_output(self) -> None:
        """Read any output captured so far from temporary files."""
        if self.stdout_file is not None:
            self.stdout = self._read_output_file(self.stdout_file)
        if self.stderr_file is not None:
            self.stderr = self._read_output_file(self.stderr_file)

    def close(self) -> None:
        """Close temporary output files."""
        for output_file in (self.stdout_file, self.stderr_file):
            if output_file is not None:
                output_file.close()
        self.stdout_file = None
        self.stderr_file = None

    def is_running(self) -> bool:
        """Return whether the reviewer process is still being collected."""
        return self.thread is not None and self.thread.is_alive()

    def elapsed_seconds(self) -> float:
        """Return elapsed reviewer runtime in seconds."""
        if self.started_at is None:
            return 0.0
        finished_at = self.finished_at
        if finished_at is None:
            finished_at = time.monotonic()
        return round(finished_at - self.started_at, 3)

    def return_code(self) -> Optional[int]:
        """Return the subprocess return code when a process was launched."""
        if self.process is None:
            return None
        return self.process.returncode

    def status(self) -> str:
        """Return the normalized status string for this reviewer run."""
        if self.launch_error is not None:
            return "launch_failed"
        if self.timed_out:
            return "timed_out"
        if self.collection_error is not None:
            return "failed"
        if self.return_code() == 0:
            return "succeeded"
        return "failed"

    def result(self) -> Dict[str, Any]:
        """Return the JSON-serializable reviewer result."""
        stderr_parts: List[str] = []
        try:
            self._refresh_output()
        except OSError as exc:
            self.collection_error = str(exc)
        if self.stderr:
            stderr_parts.append(self.stderr)
        if self.launch_error is not None:
            stderr_parts.append(self.launch_error)
        if self.collection_error is not None:
            stderr_parts.append(self.collection_error)
        return {
            "reviewer_name": self.reviewer.reviewer_name,
            "launched_command": self.launched_command,
            "status": self.status(),
            "timed_out": self.timed_out,
            "return_code": self.return_code(),
            "elapsed_seconds": self.elapsed_seconds(),
            "stdout": self.stdout,
            "stderr": "\n".join(stderr_parts),
        }


REVIEWERS = (
    Reviewer(
        reviewer_name="Claude Code Review",
        command_template=CLAUDE_COMMAND_TEMPLATE,
        prompt_template=CODE_REVIEW_COMMAND_PROMPT_TEMPLATE,
        required_executable="claude",
        additional_required_executables=("jq",),
    ),
    Reviewer(
        reviewer_name="Codex Review",
        command_template=CODEX_COMMAND_TEMPLATE,
        prompt_template=REVIEW_COMMAND_PROMPT_TEMPLATE,
        required_executable="codex",
        additional_required_executables=("jq",),
    ),
    Reviewer(
        reviewer_name="Codex Correctness",
        command_template=CODEX_COMMAND_TEMPLATE,
        prompt_template=CORRECTNESS_REVIEW_PROMPT_TEMPLATE,
        required_executable="codex",
        additional_required_executables=("jq",),
    ),
    Reviewer(
        reviewer_name="Codex Design",
        command_template=CODEX_COMMAND_TEMPLATE,
        prompt_template=DESIGN_REVIEW_PROMPT_TEMPLATE,
        required_executable="codex",
        additional_required_executables=("jq",),
    ),
)


def executable_is_available(executable: str) -> bool:
    """Return whether the reviewer launch shell can resolve an executable."""
    try:
        completed = subprocess.run(
            ["bash", "-lc", "command -v {}".format(shlex.quote(executable))],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except OSError:
        return False
    return completed.returncode == 0


def reviewer_launch_plan(reviewers: Sequence[Reviewer], review_scope: str) -> List[ReviewerRun]:
    """Return reviewer runs that can launch or fail with a planned launch error."""
    availability_cache: Dict[str, bool] = {}
    runs: List[ReviewerRun] = []
    for reviewer in reviewers:
        required_executable = reviewer.required_executable
        if required_executable is not None and required_executable not in availability_cache:
            availability_cache[required_executable] = executable_is_available(required_executable)
        if required_executable is not None and not availability_cache[required_executable]:
            continue
        launch_errors = []
        for executable in reviewer.additional_required_executables:
            if executable not in availability_cache:
                availability_cache[executable] = executable_is_available(executable)
            if not availability_cache[executable]:
                launch_errors.append(MISSING_ADDITIONAL_EXECUTABLE_MESSAGE_TEMPLATE.format(executable, reviewer.reviewer_name, executable))
        launch_error = "\n".join(launch_errors) if launch_errors else None
        runs.append(ReviewerRun(reviewer=reviewer, launched_command=reviewer.build_command(review_scope), launch_error=launch_error))
    return runs


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    """Parse the runner command line and require explicit scope text."""
    parser = argparse.ArgumentParser(description="Run external Loupe reviewers and emit structured JSON.")
    parser.add_argument("scope", help="Review scope text.")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Global reviewer timeout in seconds.")
    parser.add_argument("--output", help="Path where the exact emitted JSON should also be written.")
    parser.add_argument("--dry-run", action="store_true", help="Print the commands that would run without launching reviewers.")
    args = parser.parse_args(argv)
    args.review_scope = args.scope.strip()
    if not args.review_scope:
        parser.error("review scope must not be empty")
    return args


def get_repo_root() -> Optional[str]:
    """Return the current Git repository root, if available."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def send_process_group_signal(process, signal_number):  # type: (subprocess.Popen[Any], signal.Signals) -> None
    """Send a signal to a launched reviewer process group."""
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        return


def launch_reviewer_runs(runs: Sequence[ReviewerRun]) -> None:
    """Launch every reviewer run."""
    for run in runs:
        if run.launch_error is not None:
            continue
        run.launch()


def wait_for_reviewer_runs(runs: Sequence[ReviewerRun], timeout_seconds: float) -> None:
    """Wait for reviewer runs until completion or the global timeout."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        running = [run for run in runs if run.is_running()]
        if not running:
            return
        if time.monotonic() >= deadline:
            for run in running:
                run.timed_out = True
                if run.process is not None:
                    send_process_group_signal(run.process, signal.SIGTERM)
            break
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

    termination_deadline = time.monotonic() + PROCESS_TERMINATION_SECONDS
    for run in running:
        if run.thread is not None:
            run.thread.join(max(0.0, termination_deadline - time.monotonic()))
    for run in running:
        if run.is_running() and run.process is not None:
            send_process_group_signal(run.process, signal.SIGKILL)
    kill_deadline = time.monotonic() + PROCESS_TERMINATION_SECONDS
    for run in runs:
        if run.thread is not None:
            run.thread.join(max(0.0, kill_deadline - time.monotonic()))


def result_exit_code(results: Sequence[Dict[str, Any]]) -> int:
    """Return zero only when every reviewer succeeded."""
    if results and all(result["status"] == "succeeded" for result in results):
        return 0
    return 1


def dry_run_output(review_scope: str, git_root: Optional[str], timeout_seconds: float, runs: Sequence[ReviewerRun]) -> Dict[str, Any]:
    """Return the dry-run JSON payload without reviewer result fields."""
    return {
        "review_scope": review_scope,
        "git_root": git_root,
        "timeout_seconds": timeout_seconds,
        "reviewers": [{"reviewer_name": run.reviewer.reviewer_name, "launched_command": run.launched_command} for run in runs],
    }


def review_output(review_scope: str, git_root: Optional[str], timeout_seconds: float, elapsed_seconds: float, results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the completed review JSON payload."""
    return {
        "review_scope": review_scope,
        "git_root": git_root,
        "timeout_seconds": timeout_seconds,
        "elapsed_seconds": elapsed_seconds,
        "reviewers": list(results),
    }


def emit_json_output(payload: Dict[str, Any], output_path: Optional[str]) -> None:
    """Write identical JSON text to stdout and an optional artifact path."""
    output = json.dumps(payload, indent=2) + "\n"
    sys.stdout.write(output)
    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(output)


def emit_no_launchable_reviewers_message() -> None:
    """Report that every configured reviewer was filtered out."""
    sys.stderr.write("{}\n".format(NO_LAUNCHABLE_REVIEWERS_MESSAGE))


def emit_launch_error_messages(runs: Sequence[ReviewerRun]) -> None:
    """Report missing helper executables for launchable reviewers."""
    for run in runs:
        if run.launch_error is not None:
            sys.stderr.write("{}\n".format(run.launch_error))


def main(argv: Optional[Sequence[str]] = None, reviewers: Sequence[Reviewer] = REVIEWERS) -> int:
    """Run configured external reviewers and emit combined JSON."""
    args = parse_args(argv)
    runs = reviewer_launch_plan(reviewers, args.review_scope)
    git_root = get_repo_root()
    if args.dry_run:
        emit_json_output(dry_run_output(args.review_scope, git_root, args.timeout_seconds, runs), args.output)
        if not runs:
            emit_no_launchable_reviewers_message()
            return 1
        if any(run.launch_error is not None for run in runs):
            emit_launch_error_messages(runs)
            return 1
        return 0
    if not runs:
        emit_json_output(review_output(args.review_scope, git_root, args.timeout_seconds, 0.0, []), args.output)
        emit_no_launchable_reviewers_message()
        return 1

    try:
        started_at = time.monotonic()
        launch_reviewer_runs(runs)
        wait_for_reviewer_runs(runs, args.timeout_seconds)
        elapsed_seconds = round(time.monotonic() - started_at, 3)
        results = [run.result() for run in runs]
        emit_json_output(review_output(args.review_scope, git_root, args.timeout_seconds, elapsed_seconds, results), args.output)
        return result_exit_code(results)
    finally:
        for run in runs:
            run.close()


if __name__ == "__main__":
    sys.exit(main())
