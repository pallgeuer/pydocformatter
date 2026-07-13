# pydocformatter

pydocformatter is a Ruff-style Python linter and formatter for docstrings and comments.

Install it as a standalone tool:

```bash
uv tool install pydocformatter
```

Check a project:

```bash
pydocfmt check
```

Apply fixes:

```bash
pydocfmt check --fix
```

## Start here

- [Tutorial](tutorial.md) for a first end-to-end run.
- [Installation](installation.md) for pip, uv, pipx, and pre-commit setup.
- [Checking](checking.md) for diagnostics, exit codes, diffs, suppressions, and file previews.
- [Formatting](formatting.md) for automatic fixes and formatting scope.
- [Configuration](configuration.md) for `pyproject.toml`, discovery, and overrides.
- [Rules](rules.md) for generated rule documentation.
- [Settings](settings.md) for generated configuration reference.

## What it covers

pydocformatter formats Python docstrings and comments while leaving ordinary Python expression formatting to tools such as Ruff. It understands docstring conventions, file selection, rule selection, suppressions, line endings, indentation, protected code examples, and structured comment regions.

## Rule families

- [PCF comment formatting rules](rules/pcf.md) cover standalone comments, trailing comments, directives, suppressions, and comment source text.
- [PDF docstring formatting rules](rules/pdf.md) cover docstring literals, source layout, semantic sections, documentation consistency, missing documentation, and typed entries.

## Project resources

- [PyPI](https://pypi.org/project/pydocformatter/)
- [Source](https://github.com/pallgeuer/pydocformatter)
- [Issues](https://github.com/pallgeuer/pydocformatter/issues)
- [Changelog](project/changelog.md)
- [Contributing](project/contributing.md)
- [License](project/license.md)
