# File selection specification

This document specifies how `pydocfmt` selects files for processing.

## Defaults

- `include = ["*.py", "*.pyi", "*.pyw"]`
- `extend-include = []`
- `exclude = [".bzr", ".direnv", ".eggs", ".git", ".git-rewrite", ".hg", ".mypy_cache", ".nox", ".pants.d", ".pydocfmt_cache", ".pytype", ".ruff_cache", ".svn", ".tox", ".venv", "__pypackages__", "_build", "buck-out", "dist", "node_modules", "venv"]`
- `extend-exclude = []`
- `respect-gitignore = true`
- `force-exclude = false`

## Configuration layout

General configuration loading, source priority, and path-pattern bases are specified in [Settings specification](settings_spec.md). File selection consumes the resolved `include`, `extend-include`, `exclude`, `extend-exclude`, `respect-gitignore`, and `force-exclude` settings for each evaluated path.

Auto-discovered configuration is hierarchical: the single closest config file applies to the file or directory being evaluated, and parent config files are not merged into child config files. During traversal, a parent directory exclude can still prune a child directory before that child directory's config is entered.

`--show-settings` displays settings resolved for the current working directory. The `respect-gitignore`, `cache`, and `cache-dir` values used for run-level file-selection behavior are also resolved from the current working directory, not separately from each traversed path.

## File selection algorithm

Given positional CLI paths, defaulting to `.` when no paths are specified:

1. Treat non-directory path arguments as explicit file inputs, regardless of whether the file exists.
2. Treat directory arguments as traversal roots. A directory argument can itself be rejected by exclude rules before traversal starts; otherwise, recursively discover files under it.
3. Keep deterministic traversal order by sorting directory and file names.
4. Resolve settings for each traversed directory or file with closest-config semantics.
5. Prune the safe run-level internal cache directory before entering it and record the distinct `cache-directory` decision reason.
6. Prune excluded directories during discovery and record ignored decisions for them.
7. For discovered files, require a match against `include` or `extend-include`.
8. Reject files matching `exclude` or `extend-exclude`.
9. If `respect-gitignore = true` in the settings resolved for the current working directory, reject discovered files matched by the gitignore filter, or abort file selection if gitignore checks fail.
10. Deduplicate accepted paths that resolve to the same physical file, recording later aliases as ignored duplicate decisions.
11. Return accepted files and structured decisions for file-selection output.

Include and exclude patterns are glob patterns, not regexes. Matching uses normalized POSIX-style paths. Pattern bases follow the source of each setting:

- Defaults are current-working-directory relative.
- Auto-discovered config-file patterns are relative to the directory containing that config file.
- Explicit `--config PATH`, inline `--config`, and dedicated CLI option patterns are current-working-directory relative.

Bare include patterns such as `*.py` match basenames at any depth. Slash-containing include patterns are anchored to their setting base. Include patterns select files, not directory subtrees: `src` and `src/` do not include files below `src`, while `src/**` does.

Bare exclude patterns can match file basenames or parent directory segments. Slash-containing exclude patterns are anchored to their setting base. Slash-containing exclude patterns that match a directory path also exclude descendant files.

Explicit files bypass include matching and gitignore filtering. With `force-exclude = true`, explicit files are rejected only when the applicable exclude matcher matches them.

Directory arguments are not explicit files. A directory argument is skipped when the directory path matches the applicable source-base-aware exclude matcher. When `force-exclude = true`, a directory argument is also skipped when the final exclude pattern list matches the CLI path relative to the current working directory. If a directory argument is not skipped, files discovered below it are normal discovered files.

Only the cache root resolved from the current-working-directory profile can receive special internal-cache pruning. Cache roots configured only by profiles discovered below a traversal root do not select additional stores and receive normal include and exclude handling. The run root is pruned when it has the exact pydocfmt ownership tag, even when it is reached through a physical alias such as a symlinked parent and caching is disabled. While caching is enabled, an empty non-symlinked directory that the store can safely claim is also pruned. A non-empty unowned directory and a directory whose final component is a symlink are never specially pruned and instead receive normal include and exclude handling. The cache root does not suppress the traversal root itself if both paths are equal. `--show-files` reports `IGNORED: internal pydocfmt cache directory` for a pruned descendant. The default `.pydocfmt_cache` name remains in the default exclude list independently of this ownership-aware behavior. See [Persistent cache](cache_spec.md) for cache-directory ownership and lifecycle behavior.

`respect-gitignore` is evaluated once from the settings resolved for the current working directory. A closer child config can change include, exclude, and per-file-ignore behavior for files below it, but it does not enable or disable gitignore filtering for that run.

When gitignore filtering is enabled, only accepted discovered files are queried. Explicit files bypass gitignore filtering, including when `force-exclude = true`. Paths are grouped by the nearest detected Git root of their real filesystem path; symlinked traversal paths keep their symlinked display path, but gitignore matching is queried against the real path. Files outside a Git root are not gitignore-filtered. If `git check-ignore` exits with a status other than `0` or `1`, file selection aborts.

Glob lists cannot contain empty strings. Include patterns allow patterns such as `src/`, `src/**`, and `**`.

Existing filesystem paths are displayed as absolute normalized paths. Non-existing explicit paths are displayed as normalized lexical paths, and stdin uses `-`.

Accepted existing paths are deduplicated by normalized real path after gitignore filtering. The retained spelling is chosen by a stable display-path score; duplicate aliases are recorded as ignored duplicate decisions. Non-existing explicit paths are not deduplicated.

## Decision table

`Filter result` means the combined include, exclude, and gitignore checks for files.

| Input kind      | `force-exclude` | Filter result             | Outcome  |
|-----------------|-----------------|---------------------------|----------|
| Explicit file   | `false`         | Any result                | Accepted |
| Explicit file   | `true`          | Not excluded by glob      | Accepted |
| Explicit file   | `true`          | Not included              | Accepted |
| Explicit file   | `true`          | Excluded by glob          | Rejected |
| Explicit file   | `true`          | Excluded by gitignore     | Accepted |
| Discovered file | `false`         | Included and not excluded | Accepted |
| Discovered file | `false`         | Not included              | Rejected |
| Discovered file | `false`         | Excluded by glob          | Rejected |
| Discovered file | `false`         | Excluded by gitignore     | Rejected |
| Discovered file | `true`          | Included and not excluded | Accepted |
| Discovered file | `true`          | Not included              | Rejected |
| Discovered file | `true`          | Excluded by glob          | Rejected |
| Discovered file | `true`          | Excluded by gitignore     | Rejected |

Directory arguments are evaluated before this table applies to files below them. A directory argument that is excluded is rejected as an ignored directory decision. A directory argument that is not excluded is walked, and files found below it are evaluated as discovered files.

## CLI list options

The CLI accepts comma-separated glob values per option occurrence:

```bash
pydocfmt check --fix src/ --include "*.py,*.pyi" --exclude "generated,skip.py"
```

Repeated option occurrences append values within the command-line layer:

```bash
pydocfmt check --fix --include "*.py" --include "*.pyi" src/
```

The resulting command-line list still replaces lower-precedence values for the same setting. For example, `--extend-exclude cli.py` replaces a configured `extend-exclude = ["config.py"]`, although the resolved final exclude list is still `exclude + extend-exclude`.

## Ruff compatibility notes

pydocfmt intentionally uses Ruff-style file-selection settings where they map to pydocfmt behavior. The related settings are:

- `include`
- `extend-include`
- `exclude`
- `extend-exclude`
- `respect-gitignore`
- `force-exclude`

Settings outside this list are not part of the Ruff compatibility surface. Per-file-ignore pattern bases follow the same source-base rules as file-selection patterns, but per-file ignores are specified in the [Rule selection specification](rule_selection_spec.md) because they affect rule selection after a file has already been selected.

- **D1: pydocformatter include default.**
  pydocformatter defaults to the runtime `DEFAULT_INCLUDE` patterns, because these are the file types it can process. This intentionally differs from Ruff's broader default include set.
- **D2: gitignore scope.**
  pydocformatter applies gitignore-style filtering through a git-based implementation. It does not add a separate Ruff-style `.ignore` file parser, only filters files below detected Git roots, and aborts file selection if gitignore checks fail.
- **D3: show-files detail.**
  `pydocfmt check --show-files` keeps pydocformatter's richer decision output: included files, ignored files, pruned directories, and reasons. Ruff's `--show-files` only prints selected files.
- **D4: command-line `extend-include`.**
  pydocformatter exposes `--extend-include` as a dedicated CLI option. Ruff supports `extend-include` in configuration but does not expose a `ruff check --extend-include` option.
- **D5: list layering.**
  pydocformatter uses the same highest-precedence-wins rule for all list settings. In particular, CLI `--extend-exclude` replaces configured `extend-exclude` instead of accumulating with it. This intentionally differs from Ruff's CLI `--extend-exclude` behavior.
