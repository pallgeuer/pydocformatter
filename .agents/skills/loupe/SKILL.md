---
name: loupe
description: Run multiple parallel external code reviews for a given scope, then independently verify the findings and organize them into one final review. Possible scopes include uncommitted changes (default) or specific commits, commit ranges, branches, pull requests, or other custom textual review scopes.
---

# Loupe Skill

Use this skill when explicitly invoked by the user. The skill runs multiple parallel external code reviews for a given code/diff scope, then independently verifies the findings and organizes them into one coherent final review.

Do not modify repository files, stage changes, commit, install dependencies, or use external network access except normal web search. As part of the finding verification process, you may inspect files and run local manual tests to confirm code behavior; incidental temp/cache artifacts are okay.

## Workflow

1. Based on the user's specific request, resolve what string you need to pass to `scripts/run_reviewers.py` in order to precisely specify the target review scope:
   - Use `uncommitted changes (staged + unstaged + untracked)` when the user does not provide a specific request.
   - Pass all user-provided scope text through to the script, for example `last two commits`, `HEAD~2..HEAD`, or `PR 123`.

2. Create a private temporary artifact directory and remember the exact path as `LOUPE_ARTIFACT_DIR` for future commands:

   ```bash
   mktemp -d "${TMPDIR:-/tmp}/loupe.XXXXXXXXXX"
   ```

   - Keep all Loupe artifacts in this directory: `review.diff` for the review-scope diff and `reviewers.json` for the exact reviewer JSON stdout.
   - If the review is completed successfully, clean up the directory at the end of the skill run after all needed information has been extracted by deleting only the known Loupe artifact files and then removing the now-empty directory:

     ```bash
     rm "$LOUPE_ARTIFACT_DIR/review.diff" "$LOUPE_ARTIFACT_DIR/reviewers.json"
     rmdir "$LOUPE_ARTIFACT_DIR"
     ```

     Do not use recursive force deletion. After running these commands, report the temporary artifact directory path to the user only if the directory or either known artifact file still exists.
   - If the review cannot be completed because of truncation, malformed JSON, verification blockers, or another unexpected issue, keep this directory and report its path to the user.

3. Snapshot the diff corresponding to the target review scope before running the reviewers script:

   - For the default scope, run the bundled script:

     ```bash
     <absolute path to>/scripts/collect_review_diff.py "uncommitted changes (staged + unstaged + untracked)" --output "$LOUPE_ARTIFACT_DIR/review.diff"
     ```

     The helper supports only that exact default scope. It writes to `review.diff` the concatenated diffs of the staged tracked changes, unstaged tracked changes, and untracked non-ignored files (meaning that files can appear more than once in `review.diff`). It does not request binary patch payloads; binary changes appear only as compact Git diff markers.

   - For any other custom review scope, choose the matching Git diff command yourself, write the result to `$LOUPE_ARTIFACT_DIR/review.diff`, and record its byte count with `wc -c`. Avoid `--binary` and `--text`. Include untracked non-ignored file diffs automatically when the user's custom scope simply asks for `unstaged changes`.

4. Run the `scripts/run_reviewers.py` script that is bundled with this skill exactly once, and with escalated sandbox permissions, writing a copy of the exact stdout to an artifact file via the script's `--output` option:

   ```bash
   <absolute path to>/scripts/run_reviewers.py "<target review scope>" --output "$LOUPE_ARTIFACT_DIR/reviewers.json"
   ```

   - The script accepts a single positional argument with text corresponding to the target review scope.
   - The `--output` option writes exactly the same JSON text that the script emits on stdout.
   - The script has a shebang that ensures it is automatically run with whichever `python3` has highest priority in the current environment's `PATH`.
   - Request `sandbox_permissions: "require_escalated"` for this command, using the justification that the launched child `codex` and `claude` processes need to read and write their normal state to their respective home directory locations (`~/.codex` and `~/.claude`).
   - Run the command and all polling reads with `max_output_tokens` set to `30000`.
   - The script may take a very long time to return (default timeout is 30 minutes). Never kill the script yourself; allow its own timeout to trigger if it takes too long.
   - The script emits JSON that includes both general and reviewer-specific information, including in particular each reviewer name (`reviewer_name`) and full response (`stdout`).
   - Do not do anything other than keep the session alive until the script returns. Just say `Continuing to wait for the external reviews...` whenever needed to keep the session alive.
   - If the script exits nonzero, continue with any reviewer output it produced. A timeout or failure of one reviewer must not block you from using the analysis of the remaining reviewers.
   - Never automatically rerun this reviewers script. If the tool output is truncated, malformed, or otherwise unusable, read `$LOUPE_ARTIFACT_DIR/reviewers.json` instead. If that artifact is missing or unreadable, stop and report the artifact directory path to the user.

5. Decide how to use the diff artifact:

   - If `$LOUPE_ARTIFACT_DIR/review.diff` is at most 200000 bytes, load the full file contents into chat once after the reviewers finish, using `cat` or explicit consecutive chunks that together cover the whole file. Do not use guessed line ranges such as `sed -n '1,220p'`; if any command output is truncated, keep reading non-overlapping later chunks until every byte of the diff has appeared in chat.
   - If it is above 200000 bytes, do not load it wholesale. Use targeted reads from the diff artifact together with direct source-file reads for verification of the findings.

6. Manually verify each candidate finding from each reviewer:
   - Confirm the cited code exists in the current working tree.
   - Confirm via analysis and manual testing that it is plausible that the stated issue exists.
   - Never reject findings simply because they are `cleanup only` or `performance only` or `not important/severe/impactful enough` (`Nit` and `Low` exist as severity categories for a reason).
   - Do not get rid of or omit rejected findings from the list; instead report them in the final review with a severity of `Unsure`.

7. Organize all returned external reviewer findings into a coherent final review in chat. Do not edit repository files or write a persistent report file. After a successful final review, clean up `LOUPE_ARTIFACT_DIR` with the targeted cleanup command from step 2 so the temporary artifacts are gone as if they were never there.

## Final Review

Use this structure for the final review in chat:

```markdown
**Diff summary:** <Suggested git commit message summary line if the analyzed diff is committed>

- <primary content or purpose of changed area>
- <secondary content or purpose of changed area>
- ...

**<Reviewer name>:** <status> in <elapsed_seconds>

1. [<Severity>] <Concise summary sentence>. · `<path:line or symbol>` · Description: <Evidence and impact>. · Recommendation: <Concrete fix direction>.

**<Reviewer name>:** <status> in <elapsed_seconds>

2. [<Severity>] <Concise summary sentence>. · `<path:line or symbol>` · Description: <Evidence and impact>. · Recommendation: <Concrete fix direction>.

...
```

Rules for final output:

- `<Severity>` is one of `Critical`, `High`, `Medium`, `Low`, `Nit`, `Unsure`.
- `<status>` should be the reviewer status exactly as per the script JSON output, only with the first letter capitalized and spaces instead of underscores, e.g. `Succeeded`, `Timed out`.
- `<elapsed_seconds>` should be the elapsed time of that specific reviewer exactly as per the script JSON output, only rounded to the nearest second, e.g. `174s`.
- Show all findings of all reviewers, whether they were rejected or not. Sort findings per reviewer by descending severity, then by likely fix order.
- Number findings with one continuous global counter across every reviewer section. The first structured finding in the final review is `1.`, and each later structured finding uses the next integer even when it appears under a different reviewer, so every finding can be uniquely referenced by number. Failed-reviewer descriptions and `No findings.` sections do not consume a finding number.
- Every finding must be self-contained and contain all information required for the user to understand the problem.
- If a reviewer failed then provide a detailed description of what went wrong in place of the structured findings list.
- If a reviewer succeeded but produced no findings then just say `No findings.` in place of the structured findings list.
