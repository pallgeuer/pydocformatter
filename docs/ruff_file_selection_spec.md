# Ruff File Selection Specification

This document summarizes Ruff file selection as observed in Ruff `0.15.14` via `uvx ruff` on 2026-05-21. Examples were run in temporary directories; paths shown as `$T/...` stand in for those real temporary roots.

The point of this document is not to restate every Ruff setting. It focuses on the path-resolution and pattern-matching behavior that matters when comparing Ruff to `pydocformatter.file_selection`.

## Compact Summary

Ruff does not resolve `include`, `exclude`, or per-file-ignore patterns relative to the nearest Git root. Git is relevant for ignore-file discovery, not as the base for Ruff's glob patterns.

Ruff resolves path patterns relative to a project root chosen from configuration context:

- For an auto-discovered config file, the base is the directory containing the closest Ruff config file for the file being analyzed.
- For an explicit `--config PATH` config file, the base is the current working directory.
- For individual command-line settings such as `--exclude`, `--extend-exclude`, `--per-file-ignores`, `--extend-per-file-ignores`, and inline `--config "key = value"` overrides, the base is the current working directory.
- With no discovered config, the base is the current working directory.

Ruff uses hierarchical config discovery. The closest config file applies to each file, and parent config files are not merged into child config files. Directory excludes in a parent config can still prune traversal before Ruff enters a child directory. File-specific parent excludes do not exclude a file that is governed by a closer child config.

Ruff's default discovery includes `*.py`, `*.pyi`, `*.ipynb`, and `pyproject.toml`. In preview mode, it also includes `*.pyw`.

`include` replaces the default include list. `extend-include` adds to the default include list. Include patterns identify files to discover; explicitly passed files are still analyzed even if they do not match `include`.

Bare include patterns such as `*.py` match basenames at any depth. Slash-containing include patterns are anchored to the pattern base, so `pkg/*.py` matches `$BASE/pkg/a.py` but not `$BASE/src/pkg/a.py`.

Bare exclude patterns such as `pkg` or `generated` match file or directory names at any depth. Slash-containing exclude patterns are anchored to the pattern base; `pkg/*.py` matches only `$BASE/pkg/a.py`, while `**/pkg/*.py` matches package directories at any depth. Directory excludes such as `src/generated` exclude descendants.

Explicit files bypass discovery and are analyzed regardless of include patterns. With `force-exclude`, Ruff applies configured exclude patterns to explicit files. In Ruff `0.15.14`, explicit files still bypass include patterns and gitignore filtering even when `force-exclude` is enabled.

`respect-gitignore = true` affects discovered files from directory traversal. It does not change the base used for `include`, `exclude`, or per-file-ignore patterns.

Per-file ignores are not file selection. They apply after a file is selected and suppress selected rules for matching files. Their pattern base follows the same config context rules: closest auto-discovered config directory, cwd for explicit `--config PATH`, and cwd for CLI per-file-ignore options.

## Comparison To Current pydocformatter

Current `pydocformatter.file_selection` normalizes candidate paths relative to the nearest containing Git root when one exists, otherwise relative to cwd. Ruff does not do that. Ruff uses the closest config directory, explicit-config cwd, or command cwd as described above.

Current `pydocformatter.file_selection` has one resolved config for a run. Ruff applies the closest config per file and does not merge parent configs into child configs.

Current `pydocformatter.file_selection` applies include, exclude, and gitignore checks to explicit files when `force_exclude=True`. Ruff applies exclude checks to explicit files when `force-exclude=True`, but explicit files still bypass include and gitignore checks in the tested Ruff version.

Current `pydocformatter.file_selection` defaults to `*.py`, `*.pyi`, and `*.pyw`. Ruff defaults to `*.py`, `*.pyi`, `*.ipynb`, and `pyproject.toml`, with `*.pyw` added only in preview mode.

## Tested Examples

In the examples below, `warning: No Python files found under the given path(s)` means Ruff selected no files for that invocation.

### E01: Default Includes

Setup:

```text
$T/a.py
$T/b.pyi
$T/c.pyw
$T/d.ipynb
$T/pyproject.toml
```

Command:

```bash
cd "$T"
uvx ruff check --show-files --no-cache .
```

Selected:

```text
$T/a.py
$T/b.pyi
$T/d.ipynb
$T/pyproject.toml
```

With preview mode:

```bash
uvx ruff check --show-files --no-cache --preview .
```

Selected:

```text
$T/a.py
$T/b.pyi
$T/c.pyw
$T/d.ipynb
$T/pyproject.toml
```

### E02: `include` Replaces Defaults, `extend-include` Adds To Defaults

Setup:

```text
$T/a.py
$T/b.foo
$T/pyproject.toml
```

Config:

```toml
[tool.ruff]
extend-include = ["*.foo"]
```

Selected:

```text
$T/a.py
$T/b.foo
$T/pyproject.toml
```

After changing the config to:

```toml
[tool.ruff]
include = ["*.foo"]
```

Selected:

```text
$T/b.foo
```

### E03: Auto-Discovered Config Patterns Are Config-Directory Relative, Not Cwd Relative

Setup:

```text
$T/repo/pyproject.toml
$T/repo/src/pkg/a.py
```

Config in `$T/repo/pyproject.toml`:

```toml
[tool.ruff]
exclude = ["src/pkg/*.py"]
```

Command:

```bash
cd "$T/repo/src"
uvx ruff check --show-files --no-cache .
```

Selected:

```text
warning: No Python files found under the given path(s)
```

Changing the config to `exclude = ["pkg/*.py"]` selected:

```text
$T/repo/src/pkg/a.py
```

So the base was `$T/repo`, the config directory, not `$T/repo/src`, the cwd.

The same `src/pkg/*.py` exclusion still applied with `--no-respect-gitignore`, showing that the gitignore toggle does not affect the glob base.

### E04: Inline `--config` Patterns Are Cwd Relative

Setup:

```text
$T/repo/src/pkg/a.py
```

Command from `$T/repo/src`:

```bash
uvx ruff check --show-files --no-cache --isolated --config 'exclude = ["pkg/*.py"]' .
```

Selected:

```text
warning: No Python files found under the given path(s)
```

Command from the same cwd:

```bash
uvx ruff check --show-files --no-cache --isolated --config 'exclude = ["src/pkg/*.py"]' .
```

Selected:

```text
$T/repo/src/pkg/a.py
```

### E05: Git Root Is Not The Pattern Base

Setup:

```text
$T/repo/.git/HEAD
$T/repo/src/pyproject.toml
$T/repo/src/pkg/a.py
```

Config in `$T/repo/src/pyproject.toml`:

```toml
[tool.ruff]
exclude = ["pkg/*.py"]
```

Command:

```bash
cd "$T/repo/src/pkg"
uvx ruff check --show-files --no-cache ..
```

Selected:

```text
$T/repo/src/pyproject.toml
```

Changing the config to `exclude = ["src/pkg/*.py"]` selected:

```text
$T/repo/src/pkg/a.py
$T/repo/src/pyproject.toml
```

The Git root was `$T/repo`, but Ruff resolved the exclude against `$T/repo/src`, the config directory.

### E06: Explicit `--config PATH` Config Files Use Cwd As The Pattern Base

Setup:

```text
$T/config/ruff.toml
$T/repo/src/pkg/a.py
```

Config in `$T/config/ruff.toml`:

```toml
include = ["*.py"]
exclude = ["src/pkg/*.py"]
```

Command from `$T/repo`:

```bash
uvx ruff check --show-files --no-cache --config "$T/config/ruff.toml" .
```

Selected:

```text
warning: No Python files found under the given path(s)
```

Command from `$T/repo/src` with the same explicit config file:

```bash
uvx ruff check --show-files --no-cache --config "$T/config/ruff.toml" .
```

Selected:

```text
$T/repo/src/pkg/a.py
```

Changing the explicit config file to `exclude = ["pkg/*.py"]` and running from `$T/repo/src` selected no files.

### E07: CLI `--exclude` Is Cwd Relative

Setup:

```text
$T/repo/pyproject.toml
$T/repo/src/pkg/a.py
```

Config:

```toml
[tool.ruff]
include = ["*.py"]
```

Command from `$T/repo/src`:

```bash
uvx ruff check --show-files --no-cache --exclude 'pkg/*.py' .
```

Selected:

```text
warning: No Python files found under the given path(s)
```

Command from the same cwd:

```bash
uvx ruff check --show-files --no-cache --exclude 'src/pkg/*.py' .
```

Selected:

```text
$T/repo/src/pkg/a.py
```

### E08: Include Pattern Shape

Setup:

```text
$T/repo/pkg/a.py
$T/repo/src/pkg/a.py
$T/repo/src/pkg/named.foo
```

With config in `$T/repo/pyproject.toml`:

```toml
[tool.ruff]
include = ["*.py"]
```

Selected:

```text
$T/repo/pkg/a.py
$T/repo/src/pkg/a.py
```

With `include = ["pkg/*.py"]`, selected:

```text
$T/repo/pkg/a.py
```

With `include = ["src/pkg/*.py"]`, selected:

```text
$T/repo/src/pkg/a.py
```

With `include = ["*.foo"]`, selected:

```text
$T/repo/src/pkg/named.foo
```

### E09: Directory-Shaped Include Patterns In Ruff 0.15.14

Setup:

```text
$T/repo/src/a.py
```

Observed results:

```text
include = ["src"]   -> warning: No Python files found under the given path(s)
include = ["src/"]  -> warning: No Python files found under the given path(s)
include = ["src/**"] -> $T/repo/src/a.py
include = ["**"]     -> $T/repo/pyproject.toml and $T/repo/src/a.py
```

### E10: Exclude Pattern Shape

Setup:

```text
$T/repo/pkg/a.py
$T/repo/src/pkg/a.py
$T/repo/src/generated/a.py
```

All cases used:

```toml
[tool.ruff]
include = ["*.py"]
```

Observed selected files:

| Extra config | Selected files |
| --- | --- |
| `exclude = ["pkg"]` | `$T/repo/src/generated/a.py` |
| `exclude = ["pkg/*.py"]` | `$T/repo/src/generated/a.py`, `$T/repo/src/pkg/a.py` |
| `exclude = ["**/pkg/*.py"]` | `$T/repo/src/generated/a.py` |
| `exclude = ["src/generated"]` | `$T/repo/pkg/a.py`, `$T/repo/src/pkg/a.py` |
| `exclude = ["generated"]` | `$T/repo/pkg/a.py`, `$T/repo/src/pkg/a.py` |

This shows the distinction between bare directory-name excludes, anchored slash patterns, recursive `**`, and directory-descendant exclusion.

### E11: Closest Config Wins, With Parent Directory-Pruning

Setup:

```text
$T/repo/pyproject.toml
$T/repo/src/pkg/pyproject.toml
$T/repo/src/pkg/a.py
```

Parent config:

```toml
[tool.ruff]
include = ["*.py"]
exclude = ["src/pkg/*.py"]
```

Child config:

```toml
[tool.ruff]
include = ["*.py"]
```

Command from `$T/repo` selected:

```text
$T/repo/src/pkg/a.py
```

The parent file exclude did not apply to a file governed by the closer child config.

Changing the child config to:

```toml
[tool.ruff]
include = ["*.py"]
exclude = ["a.py"]
```

selected no files.

Changing the parent config to `exclude = ["src/pkg"]` also selected no files, because the parent directory exclude pruned traversal before Ruff entered the child directory.

### E12: Gitignore Applies To Discovered Files

Setup:

```text
$T/repo/.git/
$T/repo/.gitignore
$T/repo/keep.py
$T/repo/ignored.py
```

`.gitignore`:

```text
ignored.py
```

With default `respect-gitignore = true`, selected:

```text
$T/repo/keep.py
```

With `--no-respect-gitignore`, selected:

```text
$T/repo/ignored.py
$T/repo/keep.py
```

This affected discovery only; it did not change any include or exclude pattern base.

### E13: Explicit Files, Include, Exclude, Gitignore, And `force-exclude`

Setup:

```text
$T/repo/.git/
$T/repo/.gitignore
$T/repo/skip.py
$T/repo/ignored.py
$T/repo/note.txt
$T/repo/pyproject.toml
```

Config:

```toml
[tool.ruff]
include = ["*.py"]
exclude = ["skip.py"]
```

`.gitignore`:

```text
ignored.py
```

Observed results:

| Command | Selected files |
| --- | --- |
| `uvx ruff check --show-files --no-cache skip.py` | `$T/repo/skip.py` |
| `uvx ruff check --show-files --no-cache --force-exclude skip.py` | no files |
| `uvx ruff check --show-files --no-cache ignored.py` | `$T/repo/ignored.py` |
| `uvx ruff check --show-files --no-cache --force-exclude ignored.py` | `$T/repo/ignored.py` |
| `uvx ruff check --show-files --no-cache --force-exclude --no-respect-gitignore ignored.py` | `$T/repo/ignored.py` |

With `include = ["*.py"]` and `force-exclude = true`, an explicit `note.txt` was still selected. With `select = ["F401"]`, Ruff reported `F401` in that explicit `note.txt`. Adding `exclude = ["*.txt"]` and keeping `force-exclude = true` selected no files for `note.txt`.

### E14: Per-File Ignores Use Config-Directory Relative Paths

Setup:

```text
$T/repo/pyproject.toml
$T/repo/src/pkg/a.py
```

`a.py` contained:

```python
import os
```

Config in `$T/repo/pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["F401"]

[tool.ruff.lint.per-file-ignores]
"src/pkg/*.py" = ["F401"]
```

Command from `$T/repo/src`:

```bash
uvx ruff check --no-cache .
```

Output:

```text
All checks passed!
```

Changing the ignore pattern to `"pkg/*.py" = ["F401"]` reported `F401` at `pkg/a.py`. Bare patterns `"*.py" = ["F401"]` and `"a.py" = ["F401"]` both ignored the nested file.

### E15: Per-File Ignores Also Ignore The Git Root As A Pattern Base

Setup:

```text
$T/repo/.git/HEAD
$T/repo/src/pyproject.toml
$T/repo/src/pkg/a.py
```

Config in `$T/repo/src/pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["F401"]

[tool.ruff.lint.per-file-ignores]
"pkg/*.py" = ["F401"]
```

Command from `$T/repo/src/pkg`:

```bash
uvx ruff check --no-cache ..
```

Output:

```text
All checks passed!
```

Changing the pattern to `"src/pkg/*.py" = ["F401"]` reported `F401`, even though `$T/repo` was the Git root.

### E16: Explicit `--config PATH` Also Makes Per-File Ignores Cwd Relative

Setup:

```text
$T/config/ruff.toml
$T/repo/src/pkg/a.py
```

Config in `$T/config/ruff.toml`:

```toml
[lint]
select = ["F401"]

[lint.per-file-ignores]
"src/pkg/*.py" = ["F401"]
```

Command from `$T/repo`:

```bash
uvx ruff check --no-cache --config "$T/config/ruff.toml" .
```

Output:

```text
All checks passed!
```

Command from `$T/repo/src` with the same explicit config file reported `F401` at `pkg/a.py`. Changing the explicit config pattern to `"pkg/*.py" = ["F401"]` and running from `$T/repo/src` passed.

### E17: CLI Per-File Ignores Are Cwd Relative

Setup:

```text
$T/repo/pyproject.toml
$T/repo/src/pkg/a.py
```

Config:

```toml
[tool.ruff.lint]
select = ["F401"]
```

Command from `$T/repo/src`:

```bash
uvx ruff check --no-cache --per-file-ignores 'pkg/*.py:F401' .
```

Output:

```text
All checks passed!
```

Command from the same cwd:

```bash
uvx ruff check --no-cache --per-file-ignores 'src/pkg/*.py:F401' .
```

reported `F401` at `pkg/a.py`.

### E18: Per-File Ignores Apply To Explicit Files Too

Setup:

```text
$T/repo/pyproject.toml
$T/repo/src/pkg/a.py
```

Config in `$T/repo/pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["F401"]

[tool.ruff.lint.per-file-ignores]
"src/pkg/*.py" = ["F401"]
```

Command from `$T/repo/src`:

```bash
uvx ruff check --no-cache pkg/a.py
```

Output:

```text
All checks passed!
```

## References

- Ruff configuration docs: https://docs.astral.sh/ruff/configuration/
- Ruff settings docs: https://docs.astral.sh/ruff/settings/
