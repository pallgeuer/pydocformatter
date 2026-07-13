# Tutorial

This walkthrough installs pydocformatter, checks a small project, applies fixes, and inspects the settings, files, and rules involved.

## Install

Install the command as a standalone tool:

```bash
uv tool install pydocformatter
```

Or for a project-local environment, install it through your normal dependency manager instead, for example use `uv` to add it to your `pyproject.toml`:

```bash
uv add --dev pydocformatter
```

## Configure

Add settings to `pyproject.toml`, like (just an example):

```toml
[tool.pydocfmt]
line-length = 120
indent-style = "space"
docstring-convention = "google"
respect-gitignore = true
extend-select = ["PDF107"]
ignore = ["PDF106"]

[tool.pydocfmt.per-file-ignores]
"tests/**/test_*.py" = ["PDF6"]
```

Use [Configuration](configuration.md) for discovery and precedence details, and [Settings](settings.md) to see what settings are available.

## Inspect settings and rules

List the active settings to ensure they are being picked up:

```bash
pydocfmt check --show-settings
```

List the discovered files that will be checked by `pydocfmt` (`INCLUDED`), as well as the reason why each individual other file is `IGNORED`:

```bash
pydocfmt check --show-files
```

List the active rules (`*` means a rule is fixable):

```bash
pydocfmt check --show-rules
```

Explain a specific rule on the command line:

```bash
pydocfmt rule PDF101
```

Usually it is easier to browse and understand the available rules using the [Rules](rules.md) documentation pages.

## Check code

Run pydocformatter from the project root to actually have it check the discovered source code (read-only):

```bash
pydocfmt check
```

If paths are supplied, pydocformatter checks only those files or directories:

```bash
pydocfmt check src tests
```

## Fix code

Allow safe automatic fixes to be applied (source edits) by specifying `--fix`:

```bash
pydocfmt check --fix
```

Preview the exact edits that would be made, without actually editing the corresponding files, using `--diff`:

```bash
pydocfmt check --diff
```
