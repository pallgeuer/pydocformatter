# Integrations

pydocformatter is designed to run in the same places as other Python quality tools, namely local terminals, Git pre-commit, and CI.

The published hooks check the built-in Python and Markdown filename forms case-insensitively with `types_or: [python, pyi, markdown]` and `files: (?i)\.(?:py|pyi|pyw|md)$`. This combination requires pre-commit 2.9.0 or newer.

## Git pre-commit

Use `pydocfmt-check` when commits should fail on findings:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v1.2.0
    hooks:
      - id: pydocfmt-check
```

Use the fixing hook in a local workflow where automatic edits are expected:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v1.2.0
    hooks:
      - id: pydocfmt-fix
```

## Custom extensions

A project that maps extra extensions must override the hook's `files` regex so pre-commit passes those filenames to pydocfmt. If [identify](https://github.com/pre-commit/identify) already classifies every extra extension as Python or Markdown, changing `files` is sufficient:

```yaml
- id: pydocfmt-check
  files: (?i)\.(?:py|pyi|pyw|md|rpy|mdx)$
```

If identify does not assign an applicable language type, override `types_or` as well. Use a broad file type and let `files` be the actual extension filter:

```yaml
- id: pydocfmt-check
  types_or: [file]
  files: (?i)\.(?:py|pyi|pyw|md|rpy|mdx)$
```

These hook overrides affect only which explicit paths pre-commit supplies. Configure pydocfmt's language assignment separately:

```toml
[tool.pydocfmt.extension]
rpy = "python"
mdx = "markdown"
```

An explicit pre-commit path bypasses pydocfmt's include patterns. Add `extend-include = ["*.rpy", "*.mdx"]` under `[tool.pydocfmt]` only when direct `pydocfmt check DIRECTORY` discovery should find the custom extensions. Every extension assigned to Markdown receives the automatic fragment-oriented Markdown defaults without another per-file pattern.

## GitHub Actions

Install dependencies, then run pydocformatter in check mode (e.g. `.github/workflows/pydocfmt_checks.yml`):

```yaml
name: pydocformatter checks
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  check:
    name: Run pydocfmt checks
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v7
      - name: Install uv
        uses: astral-sh/setup-uv@v8.3.2
        with:
          enable-cache: true
          cache-suffix: dev
      - name: Sync dev dependencies
        run: uv sync --locked --no-default-groups --group dev
      - name: Run pydocfmt checks
        run: uv run --no-sync pydocfmt check
```

## Editors

Run pydocformatter through an editor task, save hook, or pre-commit integration. A dedicated editor protocol is not required for this workflow.
