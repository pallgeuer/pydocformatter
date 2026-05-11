# File Selection Compatibility Specification

This document specifies how `pydocfmt` selects files for processing.

The compatibility surface is intentionally limited to:

- `line-length`
- `line-ending`
- `indent-style`
- `indent-width`
- `include`
- `extend-include`
- `exclude`
- `extend-exclude`
- `respect-gitignore`
- `force-exclude`

Settings outside this list are not part of the Ruff compatibility contract.

## Compatibility Deltas

- **D1: pydocformatter include default.**
  pydocformatter defaults to `["*.py", "*.pyi", "*.pyw"]`, because these are the file types it can process. This intentionally differs from Ruff's broader default include set.
- **D2: gitignore scope.**
  pydocformatter applies gitignore-style filtering through the existing git-based implementation. It does not add a separate Ruff-style `.ignore` file parser.

## Defaults

- `line-length = 88`
- `line-ending = "auto"`
- `indent-style = "space"`
- `indent-width = 4`
- `include = ["*.py", "*.pyi", "*.pyw"]`
- `extend-include = []`
- `exclude = [".bzr", ".direnv", ".eggs", ".git", ".git-rewrite", ".hg", ".mypy_cache", ".nox", ".pants.d", ".pytype", ".ruff_cache", ".svn", ".tox", ".venv", "__pypackages__", "_build", "buck-out", "dist", "node_modules", "venv"]`
- `extend-exclude = []`
- `respect-gitignore = true`
- `force-exclude = false`

The `exclude` default is kept aligned with Ruff's current documented top-level default.

## Configuration Layout

Configuration is read from `[tool.pydocfmt]`.

Resolution order:

1. Start with hard-coded defaults.
2. Apply `[tool.pydocfmt]`.
3. Apply command-line options.

For every setting, including `extend-include` and `extend-exclude`, the highest-precedence specified value wins. Lists do not accumulate across configuration and command-line layers.

`line-ending` follows Ruff's formatter values: `"auto"`, `"lf"`, `"cr-lf"`, and `"native"`. `"auto"` uses the first line ending detected in the source file, defaulting to LF when the file has no line endings. The setting controls rewritten files; files that do not require formatting are not rewritten solely to normalize line endings.

## File Selection Algorithm

Given positional CLI paths, defaulting to `.` when no paths are specified:

1. Treat direct file arguments as explicit file inputs.
2. Recursively discover files under directory arguments.
3. Keep deterministic traversal order by sorting directory and file names.
4. Prune excluded directories during discovery and record ignored decisions for them.
5. For discovered files, require a match against `include` or `extend-include`.
6. Reject files matching `exclude` or `extend-exclude`.
7. If `respect-gitignore = true`, reject files matched by the gitignore filter.
8. Return accepted files and structured decisions for file-selection output.

Include and exclude patterns are glob patterns, not regexes. Matching uses normalized POSIX-style paths. Bare exclude patterns can match file basenames or parent directory segments. Slash-containing patterns are matched relative to the repository root when a git repository is found, otherwise relative to the current working directory.
Slash-containing exclude patterns that match a directory path also exclude descendant files.
Glob lists cannot contain empty strings. Include patterns must target files, so directory-only patterns such as `src/` are rejected for `include` and `extend-include`.

## Decision Table

`Filter result` means the combined include, exclude, and gitignore checks.

| Input kind      | `force-exclude` | Filter result             | Outcome   |
|-----------------|-----------------|---------------------------|-----------|
| Explicit file   | `false`         | Any result                | Accepted  |
| Explicit file   | `true`          | Included and not excluded | Accepted  |
| Explicit file   | `true`          | Not included              | Rejected  |
| Explicit file   | `true`          | Excluded by glob          | Rejected  |
| Explicit file   | `true`          | Excluded by gitignore     | Rejected  |
| Discovered file | `false`         | Included and not excluded | Accepted  |
| Discovered file | `false`         | Not included              | Rejected  |
| Discovered file | `false`         | Excluded by glob          | Rejected  |
| Discovered file | `false`         | Excluded by gitignore     | Rejected  |
| Discovered file | `true`          | Included and not excluded | Accepted  |
| Discovered file | `true`          | Not included              | Rejected  |
| Discovered file | `true`          | Excluded by glob          | Rejected  |
| Discovered file | `true`          | Excluded by gitignore     | Rejected  |

## CLI List Options

The CLI accepts multiple glob values per option occurrence:

```bash
pydocfmt src/ --include "*.py" "*.pyi" --exclude "generated" "skip.py"
```

When list options appear before positional paths, use `--` to end option parsing:

```bash
pydocfmt --include "*.py" "*.pyi" -- src/
```

## Validation Guidance

Tests should encode this contract directly and should not invoke Ruff as an oracle. Contract tests should be named or fixture-tagged with `ruff_spec`.
