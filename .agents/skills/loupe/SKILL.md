---
name: loupe
description: Run parallel external Claude Code and Codex CLI review passes for Git changes, then verify, deduplicate, and synthesize one actionable final review. Use only when the user explicitly invokes $loupe for uncommitted changes, commits, commit ranges, branches, pull requests, or another textual review scope.
---

# Loupe

Loupe runs two external reviewers in parallel through `scripts/run_reviewers.py` with a no-repository-edits policy, then requires Codex to verify and deduplicate their findings against the current repository before reporting.

## Workflow

1. Resolve the review scope text from the user request.
   - Use `uncommitted changes` when the user does not provide scope text.
   - Pass all user-provided scope text through to the script, for example `last two commits`, `HEAD~2..HEAD`, or `PR 123`.
2. Run the bundled script from the current repository:

   ```bash
   uv run python .agents/skills/loupe/scripts/run_reviewers.py <scope text>
   ```

3. If the script exits nonzero, continue with any reviewer output it produced. A timeout or failure from one reviewer must not block analysis of the other reviewer.
4. Independently inspect the current repository and the relevant diff before trusting any external finding.
5. Verify each candidate finding:
   - Confirm the cited code exists in the current working tree.
   - Reject obviously vague, stylistic, stale, duplicate, speculative, or non-actionable items.
   - Merge duplicates from Claude and Codex into one finding and mark the source as `Multiple`.
6. Produce a single final review in chat. Do not edit repository files, stage changes, commit, install dependencies, or write a report file.

## Script Contract

`scripts/run_reviewers.py` accepts the scope text as positional arguments. With no arguments it uses `uncommitted changes`.

The script launches these reviewer commands concurrently and waits up to 30 minutes for each (`<scope text>` is replaced with the actual required scope text, like `uncommitted changes`):

```bash
( set -o pipefail; cd "$(git rev-parse --show-toplevel)" && claude -p --no-session-persistence --permission-mode auto --effort high --output-format json 'Review only. Do not modify repository files, stage changes, commit, install dependencies, or use external network access except normal web search. You may inspect files and run local validation, including manual tests; incidental temp/cache artifacts are okay. /code-review <scope text>' | jq -er '.result' )
```

```bash
( set -o pipefail; codex exec --cd "$(git rev-parse --show-toplevel)" --ephemeral --sandbox workspace-write -c model_reasoning_effort='"high"' --json 'Review only. Do not modify repository files, stage changes, commit, install dependencies, or use external network access except normal web search. You may inspect files and run local validation, including manual tests; incidental temp/cache artifacts are okay. /review <scope text>' | jq -ser 'map(select(.type == "item.completed" and .item.type == "agent_message") | .item.text) | last // empty' )
```

The script emits JSON with `scope`, `repo_root`, and one result for each reviewer: `name`, `status`, `timed_out`, `returncode`, `elapsed_seconds`, `stdout`, `stderr`, and `command`. Treat `status` values of `failed`, `timed_out`, or `launch_failed` as reviewer coverage limitations, not as reasons to stop.

## Final Report

Produce a final report in chat, and not as a review file. Use this structure:

```markdown
Diff summary:
- <content or purpose of changed area>
- <additional content or purpose of changed area>

Findings:
1. [<Severity> · <Source>] <Concise summary sentence>. · `<path:line or symbol>` · Description: <Evidence and impact>. · Recommendation: <Concrete fix direction>.
```

Rules for final output:

- `<Severity>` is one of `Critical`, `High`, `Medium`, `Low`, `Nit`.
- `<Source>` is one of `Claude`, `Codex`, `Multiple`.
- Sort findings by descending severity, then likely fix order.
- Every finding must be self-contained and contain all information required for the user to understand the problem.
- If no actionable findings remain after verification, say that explicitly after the diff summary.
