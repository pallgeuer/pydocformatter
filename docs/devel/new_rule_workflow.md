# New rule development workflow

This maintainer playbook describes the Codex-assisted workflow for planning, implementing, polishing, reviewing, and publishing a new pydocformatter rule. The [rule implementation specification](rule_implementation_spec.md) remains the normative contract for rule behavior, metadata, implementation, documentation, and tests.

The workflow starts with rule planning. General development setup, issue agreement, and branch preparation are covered by [Contributing to pydocformatter](../../CONTRIBUTING.md).

## Plan and implement

1. Start in Plan mode at high reasoning effort. Produce a decision-complete plan that addresses the new rule's intended behavior, identity and category, fix availability, settings and incompatibilities, cache behavior, implementation approach, documentation, audits, and test coverage required by the rule implementation specification.
2. Resolve every material design question before implementation. Preserve this chat because it contains the originating requirements and decisions needed by the later completeness audit.
3. Switch the same chat to Default mode at high reasoning effort and implement the approved plan.
4. Run focused tests and checks while implementing. Use the verification guidance in the rule implementation specification, expanding to category, selection, settings, formatter, CLI, and documentation coverage when the rule crosses those boundaries.

## Polish tests and documentation

1. In the original implementation chat, remain in Default mode, select medium reasoning effort, and run:

   ```text
   $toolkit:perform polish-rule-tests
   ```

2. Always perform a second, independent test-polishing pass. Open a separate fresh chat in Default mode at high reasoning effort and run the same action:

   ```text
   $toolkit:perform polish-rule-tests
   ```

   Do not clear the original implementation chat. If an existing secondary chat must be reused instead of opening a new one, run `/clear` there before invoking the action. The fresh context should independently challenge the implementation and tests rather than inherit the first pass's assumptions.

3. Return to the original implementation chat. In Default mode at medium reasoning effort, run:

   ```text
   $toolkit:perform polish-rule-docs
   ```

4. Optionally, but preferably, select high reasoning effort in the original implementation chat and run:

   ```text
   $toolkit:perform check-work-complete
   ```

   This action is read-only. It works best in the original chat because that chat retains the initial request, plan, clarifications, and implementation decisions.

5. **Important:** Manually read every new or changed rule and category Markdown source. Confirm that it follows the applicable template, describes the implemented behavior and fix availability exactly, identifies pertinent settings and compatibility constraints, uses exact diagnostic messages, leads with a canonical example, and includes varied examples for the rule's important behavior. Automated documentation checks complement rather than replace this review.

## Review and fix

1. In Default mode at medium reasoning effort, run Loupe over the complete uncommitted worktree:

   ```text
   $la-review:loupe
   ```

2. Read and understand every numbered Loupe finding. Decide which findings should be fixed, which should be ignored with a reason, and which require more explanation, examples, or analysis before a decision.
3. Enter Plan mode and manually submit those dispositions in one prompt. Include any extra implementation direction needed to disambiguate a selected fix. For example:

   ```text
   /plan Fix #1 (use the shared parser), Ignore #2 (intentional compatibility behavior), Explain #3 with examples and ask me.
   ```

4. Switch to Default mode at high reasoning effort, implement the approved fix plan, and run the affected automated checks. Manually recheck any rule documentation changed by the fixes.
5. Rerun Loupe if the review found significant problems or the fixes caused significant code, test, or documentation changes. Repeat the plan, implement, check, and Loupe cycle until no significant actionable findings or subsequent significant changes remain.

## Verify, commit, and push

1. Review the complete diff and Git status. Remove unintended changes and ensure generated documentation artifacts are not included.
2. Run the complete fix-stage suite, inspect any automatic edits, and rerun it until it passes without further changes:

   ```bash
   uv run pre-commit run --all-files
   ```

3. Run the non-mutating CI-equivalent manual stage:

   ```bash
   uv run pre-commit run --all-files --hook-stage manual
   ```

4. Generate and build the documentation site (do not run these commands in parallel):

   ```bash
   uv run python tools/docs/generate_zensical.py
   uv run zensical build --strict -f zensical.generated.toml
   ```

5. Commit the verified rule work with a meaningful message (e.g. the `Diff summary:` from Loupe), then push the current branch.
