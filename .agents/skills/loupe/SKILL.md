---
name: loupe
description: "Deep read-only code review of Git changesets. Use when the user asks for an all-round review of uncommitted worktree changes, staged/unstaged/untracked files, commits, branch ranges, pull requests, or specific files for correctness bugs, regressions, edge cases, security/privacy, performance, reliability, design, dead code, tests, docs, and AGENTS.md compliance."
---

# Loupe

Deep, read-only review of one code scope. By default, review the current worktree changes: staged, unstaged, and untracked files. If the user names commits, ranges, branches, pull requests, or paths, review exactly that scope instead.

## Non-negotiables

- Review only. Do not edit reviewed project files, apply patches, stage, commit, push, or write a report file.
- Read-only means no intentional source, fixture, documentation, config, lockfile, or repository metadata edits. It is acceptable to create throwaway repro scripts, input files, or copied fixtures under `/tmp`, and it is acceptable for normal commands to create incidental caches such as `__pycache__`, `.pytest_cache`, tool caches, or coverage scratch data.
- Do not spawn subagents or Task agents. This skill uses one sequential reviewer with independent lanes.
- Use the native `update_plan` tool as the first action. Never try to run `update_plan` in a shell.
- Findings may be 0 or many. Do not invent issues, do not assume there must be feedback, but also do not cap real material findings if there are many.
- Each final finding must be actionable and evidence-backed enough that the user can later ask to plan fixes for specific finding numbers.
- Passing deterministic checks is never sufficient by itself. The review must include direct code tracing, behavioral reasoning, and targeted manual tests or reproductions when they can clarify changed behavior.
- If a lane is genuinely irrelevant to the reviewed scope, briefly justify that in internal notes and move on. Do not force fake work, but do not treat inconvenience or lack of preexisting tests as irrelevance.

## Plan Tool Protocol

As the first action, call the native `update_plan` tool with this plan, adapting only if the user explicitly restricted the review mode. Use these exact task/step names:

1. `Scope Collection` — `in_progress`
2. `Repository Instructions` — `pending`
3. `Deterministic Checks` — `pending`
4. `Instruction Compliance Lane` — `pending`
5. `Correctness and Regression Lane` — `pending`
6. `Edge and Adversarial Lane` — `pending`
7. `Contracts and Blast-Radius Lane` — `pending`
8. `Security and Privacy Lane` — `pending`
9. `Reliability and Concurrency Lane` — `pending`
10. `Performance and Resource Lane` — `pending`
11. `Design and Architecture Lane` — `pending`
12. `Simplicity and Dead-Code Lane` — `pending`
13. `Tests and Coverage Lane` — `pending`
14. `Docs and Hygiene Lane` — `pending`
15. `Verification and Deduplication` — `pending`
16. `Final Report` — `pending`

Important: After each task/step, call `update_plan` again: mark the completed step `completed`, mark exactly one next step `in_progress`, and leave later steps `pending`. Do not send the final review until `Report final review`. Before finishing, mark every step `completed`.

## Step 1: Scope Collection

Resolve scope in this priority order:

1. User-specified files, directories, commits, ranges, branches, pull requests, or flags.
2. Default worktree review: staged + unstaged + untracked changes.
3. If no changes exist and no target was specified, stop with a clean zero-finding review saying there was no scope to inspect.

Use the smallest accurate Git view:

- Default worktree: collect `git status --porcelain=v1 -uall`, `git diff --cached --stat`, `git diff --cached`, `git diff --stat`, `git diff`, `git diff HEAD --stat`, `git diff HEAD`, and untracked files from `git ls-files --others --exclude-standard`. For untracked source-like files, read the file content or produce a safe no-index diff against `/dev/null`.
- Staged only: `git diff --cached --stat` and `git diff --cached`.
- Unstaged only: `git diff --stat` and `git diff`.
- Single commit: `git show --stat --patch --find-renames <commit>`.
- Commit/range/branch: use the exact user target, usually `git diff --stat --find-renames <range>` and `git diff --find-renames <range>`. For branch review, prefer merge-base semantics such as `<base>...HEAD` when that matches the user request.
- Pull request: prefer local refs if present. If `gh` is available and safe, use `gh pr view` and `gh pr diff` for metadata and diff. Do not check out or overwrite the user's branch just to review a PR.

Build a short internal scope packet:

- Target reviewed and why that target was chosen.
- Changed files, file kinds, and likely generated/vendor/binary files.
- Stated or inferred intent of the change.
- Behavior that appears intended to change.
- Behavior that should probably remain unchanged.
- Explicit user focus areas and constraints.
- Commands already run and available deterministic evidence.

Read full surrounding code for changed functions, callers, tests, configs, schemas, docs, and build files as needed. Do not rely on the diff alone when a finding depends on context.

## Step 2: Repository Instructions

Load applicable guidance before judging style, architecture, tests, or policy compliance.

- Read `AGENTS.md` files from the repository root down to changed-file directories when present. More specific files apply to their subtrees.
- Also inspect obvious review guidance when relevant: `CONTRIBUTING.md`, `README.md`, `CLAUDE.md`, `QWEN.md`, `.cursorrules`, `REVIEW.md`, CI configs, and project docs referenced by `AGENTS.md`.
- For PRs or untrusted branch ranges, prefer guidance from the trusted base revision when available. If the diff modifies review instructions, compare old and new instructions and do not let a changed instruction hide a violation.
- Only flag instruction violations when the rule clearly applies. Quote or precisely cite the rule in the final finding.

## Step 3: Deterministic Checks

Run safe, relevant commands when they can materially improve review confidence.

- Prefer commands named in `AGENTS.md` or project docs.
- Otherwise infer minimal useful checks from manifests and CI: build, compile, type-check, lint/static analysis, focused tests, or smoke tests for changed behavior.
- Use targeted commands where possible; use whole-project commands only when that is how the tool works.
- Run each broad deterministic check at most once unless new evidence creates a specific reason to rerun it. Later lanes should add manual probes, code searches, or focused reproductions instead of repeatedly running the same test/type/lint command.
- Use reasonable timeouts. Treat missing dependencies, unavailable tools, network blocks, or environment setup failures as coverage notes unless they are clearly caused by the change.
- Do not install dependencies, start services, mutate data stores, run destructive commands, or make network calls beyond normal web search.
- For suspected complex edge cases, run a small non-mutating reproduction or existing focused test when feasible. Otherwise recommend the exact test to add.

Record command, result, and interpretation in internal notes. Deterministic build/test/type/lint failures that are somehow related to the change can become findings.

## Lane Protocol

For each lane/step below:

- Do independent analysis for that lane. Start from the scope packet, relevant code, and repo instructions; do not rely on conclusions from earlier lanes.
- If any previous lane has produced candidate findings, actively look for new candidate findings that are separate from every existing candidate. Do not spend later lanes re-establishing the same candidate unless the lane adds materially new evidence, a distinct impact path, or a broader pattern instance.
- Re-read or search the code needed for that lane instead of assuming earlier context is complete.
- Treat the lane description as a worklist, not as a label. Answer the lane's explicit questions in internal notes with evidence from code, searches, command output, or manual reproductions.
- Prefer concrete probes over abstract reassurance. When a plausible failure mode can be exercised without modifying reviewed files, create minimal repro scripts/data under `/tmp`, run a focused command against copied or synthetic inputs, call the changed API from a one-off script, or inspect generated output.
- Manual testing is especially expected for correctness, edge/adversarial, contracts, reliability, performance, and tests coverage lanes. If no manual test is useful, record why.
- Do not let successful pytest, mypy, lint, or build output stand in for lane work. Those checks are supporting evidence only.
- Write candidate findings only into internal notes. Do not produce the final review yet.
- For every candidate, capture: lane, finding type, severity proposal, confidence, file/line or symbol, evidence, why it is newly introduced or newly exposed, impact, recommendation, and possible test.
- If the lane finds nothing, record `NO FINDINGS` for that lane internally and update the plan.

### Step 4: Instruction Compliance Lane

Check explicit project rules: required commands, naming, layering, architecture, prohibited APIs, dependency rules, testing requirements, docs/changelog requirements, file placement, generated-file policy, and security/privacy rules. Only flag a violation if the rule applies unambiguously and you can point to the rule and changed code.

Carefully perform detailed analysis in these directions:

- Which AGENTS.md, contributor, CI, or project-doc rules apply to each changed path, and which changed lines are inside their scope?
- Did the change use required tools, formats, generated-file workflows, changelog categories, documentation templates, or naming conventions?
- Did it introduce prohibited imports, APIs, dependencies, file locations, data formats, shell patterns, network calls, or mutation patterns?
- Did changed signatures, public behavior, config keys, CLI flags, exceptions, messages, or docs stay synchronized as required by repo policy?
- If the diff changes instructions or tooling, would applying the old trusted instructions produce a different compliance result?
- Are tests or docs required by project policy for this type of change, and are they present with meaningful assertions or content?
- Are any apparent violations actually outside the review scope or covered by a more specific nested instruction?
- Can the alleged violation be cited precisely enough that the user can verify it without interpreting your preference as policy?

### Step 5: Correctness and Regression Lane

Check whether the implementation actually satisfies the intent without unwanted behavior drift. Look for logic errors, inverted or incomplete conditions, bad defaults, missing cases, invalid states, broken invariants, changed ordering, wrong units/conversions, stale caches, state-transition bugs, error propagation mistakes, swallowed failures, and regressions in callers or existing behavior.

Carefully perform detailed analysis and manual checking in these directions:

- What exact behavior changed, and what old behavior should still hold for unchanged inputs, options, states, and call sequences?
- Can you construct minimal before/after examples that prove the new code accepts, rejects, transforms, stores, reports, or renders data correctly?
- Do conditionals, loops, short-circuits, defaults, and fallback paths cover all intended cases, or is one branch now unreachable or too broad?
- Are invariants preserved across object construction, parsing, validation, mutation, caching, serialization, and error paths?
- Are values compared, normalized, sorted, deduplicated, rounded, escaped, encoded, decoded, or converted in the right order and with the right units?
- Do callers receive the same types, exceptions, return shapes, side effects, ordering, and idempotence they previously expected?
- Do focused existing tests actually fail on plausible bad implementations, or are assertions too weak to prove the intended fix?
- Can a small `/tmp` repro, API call, CLI invocation, or copied fixture demonstrate the main changed behavior and at least one likely regression path?

### Step 6: Edge and Adversarial Lane

Stress the changed behavior with empty, missing, null-like, single-item, duplicate, unsorted, malformed, huge, tiny, boundary, negative, overflow, precision, unicode, special-character, path, filesystem, platform, locale, timezone, clock, dependency-failure, retry, repeated-call, and concurrent-call cases. Prefer concrete triggers over theoretical possibilities.

Carefully perform detailed analysis and active break testing in these directions:

- What are the smallest, largest, empty, absent, single-entry, duplicate, repeated, and boundary inputs that can reach the changed code?
- What malformed, partially valid, mixed-version, wrong-type, unsorted, cyclic, recursive, or inconsistent data could be accepted from real callers or files?
- What special characters, escaping, unicode spellings, path separators, symlinks, relative paths, reserved names, line endings, encodings, or platform differences matter here?
- What happens when the same operation is called twice, called after failure, called with stale state, or called in an unexpected but legal order?
- Are numeric, time, locale, precision, overflow, size, batching, pagination, and truncation boundaries handled deliberately?
- Can dependency failure, missing files, permission errors, invalid config, corrupted cache, interrupted output, or unavailable optional packages break the new path?
- Build at least one concrete adversarial input or repro under `/tmp` when the changed behavior has executable surface area. Try to make it fail, not merely confirm the happy path.
- If manual execution is impossible, state the exact adversarial cases that should be added as tests and why they are not currently covered.

### Step 7: Contracts and Blast-Radius Lane

Trace changed symbols and data outward. Check callers, callees, public and internal APIs, schemas, serialization, config keys, file formats, protocols, migrations, feature flags, generated clients, fakes, mocks, examples, scripts, CI, docs, and downstream assumptions. Search for old names and changed contracts outside touched files.

Carefully perform detailed analysis and impact tracing in these directions:

- Which changed functions, classes, modules, CLI flags, config keys, schemas, file formats, messages, and data structures are consumed outside the touched files?
- Do all callers still pass valid arguments and handle the new return values, exceptions, side effects, async behavior, ownership, or lifecycle?
- Are tests, fakes, fixtures, mocks, examples, scripts, generated clients, docs, and CI still aligned with the real contract?
- Did public names, exports, imports, entry points, packaging metadata, migration paths, or compatibility shims change without downstream updates?
- Are serialized values, persisted files, cache keys, environment variables, command-line output, or protocol messages still backward and forward compatible?
- Did the change create a hidden contract through ordering, default values, warning text, diagnostic codes, logging fields, or snapshot output?
- Search for old spellings, removed symbols, changed parameter names, changed message text, and duplicate implementations across the repository.
- When possible, run a focused invocation from an external caller perspective rather than only unit-testing the changed function directly.

### Step 8: Security and Privacy Lane

Review trust boundaries and sensitive data. Check input validation and canonicalization, authn/authz, object ownership, injection into commands/queries/templates/eval/config/logs, path traversal, unsafe deserialization, filesystem/network access, secrets, credentials, PII or sensitive data in logs/errors/telemetry/artifacts, crypto/randomness, permissions, debug defaults, and dependency or supply-chain exposure. Report only when there is a credible exploit, bypass, data exposure, or policy violation path.

Carefully perform detailed analysis in these directions:

- What inputs are attacker-controlled, user-controlled, file-controlled, dependency-controlled, environment-controlled, or cross-tenant controlled?
- Are trust boundaries enforced with validation, canonicalization, authorization, ownership checks, escaping, encoding, and deny/allow lists in the right place?
- Could changed data reach shell commands, subprocess arguments, SQL/query builders, templates, HTML/Markdown, eval/import, config parsers, logs, telemetry, or filenames unsafely?
- Are filesystem paths normalized against traversal, symlink, temp-file, permission, race, overwrite, archive extraction, and platform separator issues?
- Could secrets, credentials, tokens, PII, source contents, paths, config values, or private errors leak through logs, exceptions, artifacts, caches, snapshots, or reports?
- Did defaults, debug modes, CORS/origin settings, permissions, randomness, crypto, dependency pins, or network behavior become weaker?
- Is the security lane actually relevant to the change? If not, record the trust-boundary reason instead of doing performative checks.
- For credible risks, create a harmless `/tmp` proof input or command when feasible to show the data path without exploiting real systems.

### Step 9: Reliability and Concurrency Lane

Check failure behavior and lifecycles: cleanup on all paths, resource ownership, retries, timeouts, backoff, cancellation, idempotency, partial success, rollback/recovery, atomic writes, locks, races, deadlocks, task/future handling, background jobs, subscriptions/listeners, shutdown/startup, observability for failure, and behavior under dependency slowness or outage.

Carefully perform detailed analysis and failure probing in these directions:

- What resources are opened, allocated, cached, subscribed, locked, scheduled, written, or partially mutated by the changed path, and who owns cleanup?
- Do exceptions, cancellations, timeouts, validation failures, dependency outages, and interrupted writes leave consistent state and useful errors?
- Are retries, backoff, timeout scopes, idempotency, duplicate submissions, partial success, rollback, and recovery behavior deliberate?
- Could concurrent calls, reentrant calls, background tasks, signal/shutdown paths, or test parallelism race on shared state, files, caches, globals, or mocks?
- Are atomicity guarantees preserved for writes, renames, database changes, cache updates, generated files, and multi-step operations?
- Does observability still help diagnose failures without hiding root causes or flooding logs?
- Run a focused failure or repeated-call repro when practical, such as missing files, permission-denied copies, invalid dependency output, repeated invocations, or parallel calls using `/tmp` data.
- If concurrency is irrelevant, justify it by identifying the absence of shared mutable state, async/background work, external resources, or repeated side-effectful operations.

### Step 10: Performance and Resource Lane

Check algorithmic complexity, hot-path work, repeated scanning/parsing/serialization/I/O, unnecessary allocations/copies, blocking operations, contention, unbounded queues/fan-out/retries, cache invalidation, memory/file/socket/process/thread leaks, startup cost, large-input behavior, and performance claims. Only report performance issues with plausible scale, hot-path relevance, or measured evidence.

Carefully perform detailed analysis and scale checking in these directions:

- Is the changed code on a hot path, startup path, per-request path, per-file path, per-item loop, or rarely used administrative path?
- Did complexity change for input size, nesting depth, number of files, number of rules, number of dependencies, concurrency, or retries?
- Are there repeated scans, parsing, subprocesses, network/disk I/O, serialization, regex compilation, allocations, copies, sorting, or conversions that can be hoisted or bounded?
- Are caches invalidated correctly, keyed precisely, sized safely, and protected from stale data or unbounded growth?
- Could queues, recursion, fan-out, batching, logs, diagnostics, generated output, or retained objects grow without limit?
- Are blocking operations introduced into async or latency-sensitive contexts, or locks held while doing slow work?
- Use a small synthetic large-input or repeated-call probe under `/tmp` when feasible to compare scale behavior or expose obvious resource blowups.
- Do not report performance issues based only on taste; require a plausible scale scenario, hot-path relevance, benchmark, profile, or clear asymptotic regression.

### Step 11: Design and Architecture Lane

Challenge the solution shape. Check abstraction altitude, cohesion, coupling, dependency direction, layering, ownership, lifecycle boundaries, mutability, global state, extension points, API ergonomics, hidden side effects, over-generalization, under-generalization, speculative configurability, and whether an existing project abstraction or simpler approach would fit better.

Carefully perform detailed analysis in these directions:

- Does the solution fit existing project abstractions, naming, module boundaries, dependency direction, and ownership patterns?
- Is the new logic placed at the layer that has the needed information without reaching across boundaries or duplicating another layer's responsibility?
- Are APIs ergonomic and hard to misuse for real callers, with clear ownership of state, mutation, lifetimes, errors, and defaults?
- Is the abstraction too broad, too narrow, too configurable, too implicit, or too coupled for the actual change being made?
- Did the change introduce global state, hidden side effects, temporal coupling, special ordering requirements, or surprising cross-module dependencies?
- Are extension points, strategy objects, registries, plugins, feature flags, or settings justified by concrete needs rather than speculation?
- Would a simpler local change, existing helper, data model adjustment, or clearer split reduce risk without losing required behavior?
- Distinguish architecture findings from personal preference by tying them to maintainability, correctness, testability, or future change cost.

### Step 12: Simplicity and Dead-Code Lane

Look for unreachable code, unused symbols, unused parameters, dead branches, stale feature flags, thin wrappers that add no value, duplicated or near-duplicated logic, copy-paste drift, redundant validation/conversion/logging/configuration, obsolete fallbacks, debug leftovers, stale comments/TODOs, unnecessary dependencies, and code that could be deleted or inlined without losing clarity.

Carefully perform detailed analysis in these directions:

- Are any new or modified branches unreachable because of earlier validation, impossible types, exhaustive matches, returns, raises, or configuration constraints?
- Are symbols, parameters, imports, fixtures, helpers, constants, settings, feature flags, comments, TODOs, or dependencies unused after the change?
- Is there duplicated or near-duplicated logic that can drift, especially copied predicates, parsers, formatters, validators, test helpers, or error messages?
- Are wrappers, adapters, conversions, normalizers, guards, logs, or fallback paths adding real value, or only obscuring direct behavior?
- Did the change leave old behavior paths, compatibility shims, snapshots, fixtures, or documentation fragments that are no longer reachable?
- Could code be deleted, inlined, renamed, or localized while making the changed behavior easier to verify?
- Use repository search and, where useful, static tools or focused imports to distinguish genuinely unused code from dynamic entry points.
- Avoid nitpicking harmless style. Report only when simplification reduces concrete maintenance, testing, correctness, or reader risk.

### Step 13: Tests and Coverage Lane

Check whether tests prove the intended behavior and protect against regressions. Look for missing tests for changed behavior, edge/failure/security/migration cases, weak assertions, over-permissive mocks, stale fakes/fixtures, brittle snapshots, nondeterminism, flakiness, deleted coverage, tests that would not fail on the old bug, and missing integration vs unit coverage where the boundary matters.

Carefully perform detailed analysis and test-quality checking in these directions:

- What specific behavior, bug, contract, edge case, failure path, compatibility path, or policy requirement changed, and which test would fail if it regressed?
- Do new or modified tests assert observable outcomes tightly enough, including diagnostics, side effects, ordering, persistence, and absence of unwanted changes?
- Would the tests fail on the old broken implementation or on plausible incorrect implementations, or are they only smoke tests?
- Are mocks, fakes, fixtures, snapshots, golden files, time/randomness controls, and monkeypatching realistic enough to exercise the real boundary?
- Are edge, adversarial, failure, migration, security, performance, and integration cases represented at the right level of the test pyramid?
- Did the diff delete, weaken, skip, xfail, parameterize away, or over-broaden existing coverage?
- Are tests deterministic under parallelism, different platforms, different locales/timezones, no network, missing optional dependencies, and repeated runs?
- If coverage seems missing, run or sketch a minimal focused repro under `/tmp` to prove the gap is real and name the exact test to add.

### Step 14: Docs and Hygiene Lane

Check comments, public docs, examples, changelogs, migration notes, command help, user-facing messages, logs, README/usage snippets, manifests, lockfiles, env examples, CI/deployment files, generated artifacts, vendored/binary/large files, file modes, line endings, packaging exports, and local-machine artifacts. Flag stale or inconsistent docs when they would mislead users or maintainers.

Carefully perform detailed analysis in these directions:

- Did public behavior, CLI output, configuration, APIs, rule semantics, dependencies, install steps, examples, or migration requirements change in a way users need documented?
- Are README, docs, changelog, command help, rule pages, templates, comments, examples, and generated artifacts internally consistent?
- Do user-facing messages, diagnostics, logs, warnings, and errors remain accurate, actionable, stable where expected, and synchronized with tests?
- Are manifests, lockfiles, exports, entry points, package data, CI configs, pre-commit hooks, env examples, and release metadata updated when needed?
- Did the diff introduce local artifacts, generated files without source, large/binary/vendor files, mode changes, line-ending changes, machine-specific paths, or accidental debug output?
- Are comments explaining why the code works still accurate after the change, and are new comments documenting non-obvious constraints rather than restating code?
- Do documentation examples execute or at least match the current syntax, defaults, output formats, and edge behavior?
- Only flag docs gaps that would realistically mislead users, break release hygiene, or slow maintainers; do not require docs for purely internal invisible changes.

## Step 15: Verification and Deduplication

After all lanes finish, verify every candidate finding before reporting.

- Re-read cited code and relevant context.
- Candidates that are not directly caused by the reviewed scope, or that were already an issue in the baseline code, should still be reported, but add a note to the finding like `Outside reviewed code scope` or `Existing baseline code issue`.
- Validate caller impact, rule applicability, and test evidence.
- Run a focused command or reproduction if it is safe and likely to settle the finding.
- Merge duplicates and pattern-match repeated issues. A pattern finding may list multiple locations; do not hide critical instances.
- Reject vague, stylistic, speculative, or unactionable candidates.

Severity:

- `Critical`: likely build break in normal use, severe production regression, data loss/corruption, exploitable security/privacy issue, or direct hard-rule violation with major impact.
- `High`: likely bug, regression, security, reliability, compatibility, or performance issue on an important path; should fix before merge.
- `Medium`: concrete issue with plausible impact; worth fixing soon or before merge depending on risk tolerance.
- `Low`: concrete maintainability, design, test, docs, or hygiene issue with local impact.
- `Nit`: optional polish or small cleanup. Include only when useful or requested; do not let nits obscure material findings.

Confidence: `Sure`, `Likely`, or `Unsure`. Sure findings need direct evidence. Likely findings need a plausible trigger and context. Unsure findings belong in `Needs human review`.

Finding types: Correctness bug, Regression, Edge-case failure, Contract/API break, Instruction violation, Security/privacy issue, Reliability/concurrency issue, Performance/resource issue, Data/migration issue, Design/architecture issue, Dead code/simplicity issue, Test coverage issue, Documentation/hygiene issue, or Build/tooling issue.

## Step 16: Final Report

Report in chat. Do not write as review file. Use this structure:

```markdown
# Loupe Review

- Scope: <target reviewed>
- Intent: <stated or inferred; say if inferred>
- Instructions consulted: <files or none found>
- Files skipped: <generated/vendor/binary/etc. and why>
- Residual risks: <omit unless checks were skipped or scope was limited>

## Findings
1. [<Severity> · <Confidence> · <Type>] <short title> · At: `<path:line or symbol>` · Evidence: <specific code/command/rule evidence> · Impact: <what breaks or why it matters> · Recommendation: <concrete fix direction> · Test: <specific test/check to add or run, if applicable; omit if none> · Notes: <if any; omit if none>.

## Needs Human Review
<numbering continues from confirmed findings to ensure finding numbers are unique, same compact shape; omit if empty>

## Fix First
<which findings (if any) are worth fixing, and in what order; "None" if empty just like Findings section>
```

Rules for final output:

- Number findings globally and keep numbers stable within the report.
- Sort by severity, then confidence (`Sure`, then `Likely`, then `Unsure`), then likely fix order.
- If there are many findings, keep each concise but self-contained. Group repeated low/medium instances into pattern findings when that improves readability.
- If there are 0 confirmed findings, make the Findings and Fix First sections just say "None".
- Do not include raw lane notes, rejected candidates, or long essays.
- Do not propose implementation plans.
