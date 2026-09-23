# Tutorial

This five-minute path installs pydocformatter, checks an existing project without changing it, previews and applies safe fixes, adds a small configuration, and leads directly to pre-commit or CI enforcement.

## 1. Install

Install pydocformatter as a standalone command:

```bash
uv tool install pydocformatter
pydocfmt --version
```

Alternatively, add it to a project environment as a development dependency:

```bash
uv add --dev pydocformatter
uv run pydocfmt --version
```

The commands below use the standalone `pydocfmt` form. Prefix them with `uv run` when pydocformatter is installed in the project environment. See [Installation](installation.md) for pip, pipx, and Git pre-commit alternatives.

## 2. Check and inspect

From the project root, run a read-only check over discovered Python and Markdown files:

```bash
pydocfmt check
```

Limit the first run to selected paths when useful:

```bash
pydocfmt check src tests
```

Inspect the resolved configuration, discovered files, and active rules before changing source:

```bash
pydocfmt check --show-settings
pydocfmt check --show-files
pydocfmt check --show-rules
pydocfmt rule PDF101
```

An asterisk in `--show-rules` output marks a rule with an available automatic fix. The [Rules](rules.md) pages explain individual findings and fix availability.

## 3. Preview fixes

Preview the exact automatic changes as a unified diff without writing files:

```bash
pydocfmt check --diff
```

Review the proposed changes and the findings that remain. A nonzero status is expected when the diff is nonempty or findings still require attention; see [Exit codes and CI](checking.md#exit-codes-and-ci).

## 4. Configure and apply

Add a minimal project configuration to `pyproject.toml`. Usually the shared line length and the project's docstring convention are enough to begin:

```toml
[tool.pydocfmt]
line-length = 88

[tool.pydocfmt.docstring]
convention = "google"
```

Run `pydocfmt check --show-settings` and `pydocfmt check --show-rules` again to verify the resolved policy, then preview the updated result. Use [Configuration](configuration.md), [Settings](settings.md), and [Rule selection](reference/rule-selection.md) when actual findings show that the project needs a more specific policy.

Apply the reviewed fixes in place:

```bash
pydocfmt check --fix
git diff --check
git diff
```

pydocformatter applies fixes only for selected rules and fixable cases. Diagnostic-only findings and ambiguous cases remain for the author rather than being guessed.

## 5. Enforce

Use the read-only check in automated enforcement after the source and configuration are clean:

```bash
pydocfmt check
```

Copy a complete [pre-commit configuration](integrations.md#git-pre-commit) or [minimal GitHub Actions job](integrations.md#github-actions) from the integrations page. The checking command exits nonzero for findings, so the same command works locally, in pre-commit, and in CI.

## Adopting in an existing codebase

For a mature repository, keep the initial adoption separate from routine enforcement:

1. Run `pydocfmt check` without fixes to understand the baseline.
2. Use `--show-settings`, `--show-files`, and `--show-rules` to confirm the configuration, scope, and selected policy.
3. Preview automatic changes with `--diff` and inspect representative findings before changing rule selection.
4. Tune selectors, per-file ignores, or fixability only where the observed output establishes a project-specific need.
5. Apply safe fixes with `--fix` in a focused, reviewable change, then resolve or deliberately suppress findings that require human judgment.
6. Add the stable read-only command to pre-commit or CI and require it for later changes.

This sequence makes the size and character of the migration visible before source is rewritten and avoids combining policy selection with an unreviewed repository-wide formatting change.
