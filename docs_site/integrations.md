# Integrations

pydocformatter is designed to run in the same places as other Python quality tools, namely local terminals, Git pre-commit, and CI. Complete the [five-minute tutorial](tutorial.md) before enabling enforcement in an existing repository.

The published hooks check the built-in Python and Markdown filename forms case-insensitively with `types_or: [python, pyi, markdown]` and `files: (?i)\.(?:py|pyi|pyw|md)$`. This combination requires pre-commit 2.9.0 or newer.

## Git pre-commit

Use `pydocfmt-check` for the recommended read-only hook that fails commits on findings:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v1.2.0
    hooks:
      - id: pydocfmt-check
```

Use `pydocfmt-fix` instead in a local workflow where automatic edits are expected:

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

The final step is read-only and fails when findings remain. See [Exit codes and CI](checking.md#exit-codes-and-ci) for the exact status contract, diff previews, advisory runs, and fix-mode behavior.

## Editors

Use explicit editor actions for the current file. The read-only action is the recommended default; invoke fixes deliberately so prose changes can be reviewed. pydocformatter does not currently expose a dedicated editor protocol or machine-readable diagnostic format.

### Visual Studio Code

Add these [process tasks](https://code.visualstudio.com/docs/editor/tasks) to `.vscode/tasks.json`. They use the documented [`${file}` and `${workspaceFolder}` variables](https://code.visualstudio.com/docs/reference/variables-reference) and respect project exclusions.

<!-- vscode-tasks:start -->

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "pydocfmt: check current file",
      "type": "process",
      "command": "uv",
      "args": ["run", "pydocfmt", "check", "--force-exclude", "${file}"],
      "options": {
        "cwd": "${workspaceFolder}"
      },
      "problemMatcher": []
    },
    {
      "label": "pydocfmt: fix current file",
      "type": "process",
      "command": "uv",
      "args": ["run", "pydocfmt", "check", "--fix", "--force-exclude", "${file}"],
      "options": {
        "cwd": "${workspaceFolder}"
      },
      "problemMatcher": []
    }
  ]
}
```

<!-- vscode-tasks:end -->

Run either action from **Terminal > Run Task** or bind it to a keyboard shortcut. The empty problem matcher is intentional because grouped pydocfmt diagnostics do not currently implement an editor protocol.

### PyCharm

Follow PyCharm's [External Tools](https://www.jetbrains.com/help/pycharm/configuring-third-party-tools.html) workflow and add these two local tools. Set **Program** to the absolute path reported by `command -v uv`.

| Field                       | Check current file                                | Fix current file                                        |
|-----------------------------|---------------------------------------------------|---------------------------------------------------------|
| Name                        | `pydocfmt: check current file`                    | `pydocfmt: fix current file`                            |
| Program                     | `PATH/TO/uv`                                      | `PATH/TO/uv`                                            |
| Arguments                   | `run pydocfmt check --force-exclude "$FilePath$"` | `run pydocfmt check --fix --force-exclude "$FilePath$"` |
| Working directory           | `$ProjectFileDir$`                                | `$ProjectFileDir$`                                      |
| Synchronize after execution | Disabled                                          | Enabled                                                 |

Run the actions from **Tools > External Tools** or assign shortcuts. PyCharm's [built-in macro reference](https://www.jetbrains.com/help/pycharm/built-in-macros.html) documents `$FilePath$` and `$ProjectFileDir$`.

For a standalone pydocformatter installation, set the editor command or program to `pydocfmt` and remove the leading `uv run` arguments. These actions are intentionally manual rather than save-time fixers.
