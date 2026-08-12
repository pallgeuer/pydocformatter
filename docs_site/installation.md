# Installation

pydocformatter requires Python 3.11 or newer.

## Python implementation support

pydocformatter officially supports CPython 3.11 or newer. Compatibility with PyPy and GraalPy is intended but is not currently verified or guaranteed. LibCST's native parser does not publish binary wheels for these implementations, so installation may require an unverified source build. Jython and IronPython are unsupported.

## Platform support

Ubuntu 20.04 and newer and macOS 14 and newer are supported. Other POSIX Linux systems, including musl-based distributions, receive best-effort support. Native Windows and WSL are unsupported.

The current stable Python 3.11 through 3.14 releases are exercised across the supported operating-system matrix. Ubuntu 18.04 and Python prereleases are not part of that matrix.

Git is conditionally required when the default gitignore-aware recursive file discovery processes files inside a Git worktree. Install Git or use `--no-respect-gitignore` when gitignore filtering is not needed. Explicit file arguments and files outside Git worktrees do not require Git.

## Project dependency

Add pydocformatter to a project environment as a development dependency using `uv` (or manually edit the `pyproject.toml`):

```bash
uv add --dev pydocformatter
```

Then ideally run it through uv (or otherwise run it in the suitable project `.venv`):

```bash
uv run pydocfmt check
```

## uv tool

Install the command as a standalone tool:

```bash
uv tool install pydocformatter
```

## pip

Install with pip:

```bash
python -m pip install pydocformatter
```

## pipx

Install with pipx:

```bash
pipx install pydocformatter
```

## Git pre-commit

Use one published repository hook when pre-commit should manage the pydocformatter environment. Choose `pydocfmt-check` for read-only validation, or `pydocfmt-fix` when commits should apply fixes before reporting remaining findings:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v1.1.0
    hooks:
      - id: pydocfmt-check
      # - id: pydocfmt-fix
```

Update `rev` when you intentionally adopt a newer pydocformatter release.

Use a local hook instead when the project already installs pydocformatter, for example in a uv-managed development environment. Choose one hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: pydocfmt-check
        name: pydocfmt (check)
        entry: uv run pydocfmt check --force-exclude
        language: system
        types: [python]
      # - id: pydocfmt-fix
      #   name: pydocfmt (fix)
      #   entry: uv run pydocfmt check --fix --force-exclude
      #   language: system
      #   types: [python]
```
