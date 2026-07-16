# Integrations

pydocformatter is designed to run in the same places as other Python quality tools, namely local terminals, Git pre-commit, and CI.

## Git pre-commit

Use `pydocfmt-check` when commits should fail on findings:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v1.0.0
    hooks:
      - id: pydocfmt-check
```

Use the fixing hook in a local workflow where automatic edits are expected:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v1.0.0
    hooks:
      - id: pydocfmt-fix
```

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
