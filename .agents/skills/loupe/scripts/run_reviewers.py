#!/usr/bin/env python3
"""Run external Claude and Codex review processes with bounded concurrency."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_SCOPE = "uncommitted changes"
DEFAULT_TIMEOUT_SECONDS = 30 * 60
REVIEW_POLICY = "Review only. Do not modify repository files, stage changes, commit, install dependencies, or use external network access except normal web search. You may inspect files and run local validation, including manual tests; incidental temp/cache artifacts are okay."


@dataclass(frozen=True)
class ReviewerSpec:
    """Shell command metadata for one external reviewer."""

    name: str
    command: str


@dataclass
class RunningReviewer:
    """Subprocess state tracked while a reviewer is running."""

    spec: ReviewerSpec
    process: subprocess.Popen[str] | None
    started_at: float
    launch_error: str | None = None


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Run external Loupe reviewers and emit structured JSON.")
    parser.add_argument("scope", nargs="*", help=f"Review scope text. Defaults to {DEFAULT_SCOPE!r}.")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Per-reviewer timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Print the commands that would run without launching reviewers.")
    return parser.parse_args()


def build_specs(scope: str) -> list[ReviewerSpec]:
    """Build the exact reviewer shell commands for the requested scope."""
    claude_prompt = f"{REVIEW_POLICY} /code-review {scope}"
    codex_prompt = f"{REVIEW_POLICY} /review {scope}"
    claude_command = (
        '( set -o pipefail; cd "$(git rev-parse --show-toplevel)" && claude -p --no-session-persistence --permission-mode auto --effort high --output-format json '
        + shlex.quote(claude_prompt)
        + " | jq -er '.result' )"
    )
    codex_command = (
        '( set -o pipefail; codex exec --cd "$(git rev-parse --show-toplevel)" --ephemeral --sandbox workspace-write -c model_reasoning_effort=\'"high"\' --json '
        + shlex.quote(codex_prompt)
        + ' | jq -ser \'map(select(.type == "item.completed" and .item.type == "agent_message") | .item.text) | last // empty\' )'
    )
    return [
        ReviewerSpec(name="Claude", command=claude_command),
        ReviewerSpec(name="Codex", command=codex_command),
    ]


def get_repo_root() -> str | None:
    """Return the current Git repository root, if available."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def launch_reviewer(spec: ReviewerSpec) -> RunningReviewer:
    """Launch one reviewer in its own process group."""
    started_at = time.monotonic()
    try:
        process = subprocess.Popen(
            ["bash", "-lc", spec.command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        return RunningReviewer(spec=spec, process=None, started_at=started_at, launch_error=str(exc))
    return RunningReviewer(spec=spec, process=process, started_at=started_at)


def terminate_process_group(process: subprocess.Popen[str]) -> None:
    """Terminate a launched reviewer process group."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return


def collect_reviewer(running: RunningReviewer, timeout_seconds: float) -> dict[str, Any]:
    """Collect one reviewer result while respecting the per-reviewer timeout."""
    if running.process is None:
        return {
            "name": running.spec.name,
            "status": "launch_failed",
            "timed_out": False,
            "returncode": None,
            "elapsed_seconds": round(time.monotonic() - running.started_at, 3),
            "stdout": "",
            "stderr": running.launch_error or "",
            "command": running.spec.command,
        }

    remaining = max(0.0, timeout_seconds - (time.monotonic() - running.started_at))
    timed_out = False
    try:
        stdout, stderr = running.process.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_process_group(running.process)
        stdout, stderr = running.process.communicate()

    elapsed_seconds = round(time.monotonic() - running.started_at, 3)
    returncode = running.process.returncode
    if timed_out:
        status = "timed_out"
    elif returncode == 0:
        status = "succeeded"
    else:
        status = "failed"
    return {
        "name": running.spec.name,
        "status": status,
        "timed_out": timed_out,
        "returncode": returncode,
        "elapsed_seconds": elapsed_seconds,
        "stdout": stdout,
        "stderr": stderr,
        "command": running.spec.command,
    }


def main() -> int:
    """Run both external reviewers and emit combined JSON."""
    args = parse_args()
    scope = " ".join(args.scope).strip() or DEFAULT_SCOPE
    specs = build_specs(scope)
    repo_root = get_repo_root()
    if args.dry_run:
        print(json.dumps({"scope": scope, "repo_root": repo_root, "reviewers": [{"name": spec.name, "command": spec.command} for spec in specs]}, indent=2))
        return 0

    started_at = time.monotonic()
    running_reviewers = [launch_reviewer(spec) for spec in specs]
    results = [collect_reviewer(running, args.timeout_seconds) for running in running_reviewers]
    output = {
        "scope": scope,
        "repo_root": repo_root,
        "timeout_seconds": args.timeout_seconds,
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
        "reviewers": results,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
