# Configuration

pydocformatter reads `[tool.pydocfmt]` from the closest containing `pyproject.toml` for each checked path, with a format something like:

```toml
[tool.pydocfmt]
line-length = 100
respect-gitignore = true
extend-select = ["PDF701"]
ignore = ["PDF300"]

[tool.pydocfmt.docstring]
convention = "google"

[tool.pydocfmt.comment]
preserve-tables = false
```

It is recommended to use `[tool.pydocfmt.docstring]` and `[tool.pydocfmt.comment]` TOML sub-tables for setting docstring (`docstring-*`) and comment (`comment-*`) settings. The equivalent flat hyphenated keys such as `docstring-convention = "google"` and `comment-preserve-tables = false` are also accepted, but take care not to configure the same setting both ways within a single file.

## Discovery

Configuration is path-aware. When formatting files from different subtrees, pydocformatter resolves each path against the closest applicable configuration file.

Use `--isolated` to ignore discovered configuration:

```bash
pydocfmt check --isolated
```

Use `--config PATH` for an explicit configuration file, or `--config KEY=VALUE` for inline overrides:

```bash
pydocfmt check --config pyproject.toml
pydocfmt check --config 'line-length = 100'
```

## Per-file behavior

`per-file-ignores` adjusts rule selection for matching paths. `per-file-settings` adjusts formatting behavior for matching paths after global rule selection:

```toml
[tool.pydocfmt.per-file-ignores]
"tests/**/test_*.py" = ["PDF6"]

[tool.pydocfmt.per-file-settings]
"tests/**/test_*.py" = { docstring-missing-documentation = "has-section" }
```

Run-level cache settings cannot be overridden per file. The default cache location is relative to the auto-discovered project configuration root; explicitly configured relative locations follow their normal configuration source base. pydocformatter may create the cache directory, but its immediate parent must already exist as a directory. `pydocfmt clean` uses the same configuration discovery and global `--config`/`--isolated` arguments, and accepts `--cache-dir PATH` as a direct override.

## Reference

- [Settings](settings.md) lists every setting.
- [Persistent cache](reference/cache.md) documents cache validation, population, lifecycle, failures, and trust.
- [Settings specification](reference/settings-spec.md) documents loading and precedence.
- [File selection](reference/file-selection.md) documents include, exclude, gitignore, and explicit-path behavior.
- [Rule selection](reference/rule-selection.md) documents selectors, fixability, and per-file ignores.
