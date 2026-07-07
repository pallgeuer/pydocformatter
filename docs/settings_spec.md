# Settings Specification

This document specifies how `pydocfmt` loads, validates, resolves, displays, and applies configuration settings.

## Configuration Sources

For each path being checked, settings are resolved from these sources:

1. Hard-coded defaults.
2. An explicit `--config PATH` file, when supplied.
3. Otherwise, the single closest containing `pyproject.toml` with `[tool.pydocfmt]`, unless `--isolated` is set.
4. Inline `--config "<KEY> = <VALUE>"` setting overrides.
5. Dedicated command-line options.
6. In-process field overrides used by tests and callers.

Explicit `--config PATH` files and auto-discovered `pyproject.toml` files share config-file priority; an explicit config path disables auto-discovery for that settings resolution. Inline `--config` overrides still layer over explicit or auto-discovered config files. `--isolated` disables auto-discovered configuration files and can be combined with inline `--config` overrides, but not with `--config PATH`.

Auto-discovered configuration is hierarchical: the single closest config file applies to the path being evaluated, and parent config files are not merged into child config files. During directory traversal, a parent directory exclude can still prune a child directory before that child directory's config is entered.

## Source Priority

Settings use these source priorities:

- Defaults have priority `0`.
- Auto-discovered or explicit config-file settings have priority `1`.
- Inline `--config "<KEY> = <VALUE>"` settings have priority `2`.
- Dedicated command-line options have priority `3`.
- In-process field overrides used by tests and callers have priority `4`.

For every ordinary setting, the highest-priority specified value wins. The same list setting does not accumulate across configuration and command-line layers. Domain-specific settings can later interpret resolved base and extension fields together; for example, file selection appends resolved `extend-include` to resolved `include`, while rule selection applies its own selector precedence after the fields are resolved.

## Configuration Layout

Auto-discovered configuration is read from `[tool.pydocfmt]` in `pyproject.toml`.

Explicit `--config PATH` can load either:

- A pyproject-style file named `pyproject.toml` containing `[tool.pydocfmt]`.
- A dedicated pydocfmt TOML file with settings at the top level.

For TOML configuration, `[tool.pydocfmt.docstring]` and `[tool.pydocfmt.comment]` are the intended way to specify docstring and comment settings:

```toml
[tool.pydocfmt]
line-length = 100

[tool.pydocfmt.docstring]
convention = "google"

[tool.pydocfmt.comment]
preserve-tables = false
```

Flat hyphenated forms such as `docstring-convention = "google"` and `comment-preserve-tables = false` also work for compatibility. Do not specify both the flat form and the nested-table form for the same setting in one configuration. CLI flags, `pydocfmt config`, `--show-settings`, and inline `--config` overrides use flat hyphenated names.

## Path Pattern Bases

Path-pattern settings are matched against normalized POSIX-style paths relative to the setting source base.

Pattern bases:

- Defaults are current-working-directory relative.
- Auto-discovered config-file patterns are relative to the directory containing that config file.
- Explicit `--config PATH`, inline `--config`, and dedicated CLI option patterns are current-working-directory relative.

This base model is shared by file-selection patterns, per-file ignores, and per-file settings. Each domain still owns its own matching semantics and effect.

## Per-File Settings

`[tool.pydocfmt.per-file-settings]` maps file patterns to formatter setting override tables:

```toml
[tool.pydocfmt.per-file-settings]
"tests/**/*.py" = { docstring-missing-documentation = "has-section" }
"docs/**/*.py" = { line-length = 100 }
```

Per-file settings are TOML-only and have no dedicated CLI option. Each value must be a non-empty table of public setting keys. Nested `docstring` and `comment` tables are accepted inside an override table and are flattened the same way as top-level configuration; specifying the same setting twice in one override table is rejected.

Patterns use the same source-base behavior as other path-pattern settings. Matching uses `GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False)`, and a leading `!` negates the pattern so the entry applies to files that do not match the remaining pattern.

Matching entries are evaluated in configuration order. If more than one matching entry updates the same setting, the later matching entry wins within the per-file-settings table.

Per-file settings apply after file selection and after global rule selection. They affect the `CheckSettings` passed to formatting and rule execution for that file only. Rule selection is not re-run from the per-file effective settings.

Per-file settings intentionally cannot change which files are selected or which rules are active. The validator rejects:

- Rule-selection settings, including `select`, `ignore`, `extend-select`, `require-explicit`, per-file ignores, fixability settings, and related selector settings.
- File-selection settings, including `include`, `extend-include`, `exclude`, `extend-exclude`, `respect-gitignore`, and `force-exclude`.
- Run-level settings, including `output-format` and `parallelism`.
- Nested `per-file-settings`.
- Any setting referenced by rule metadata `setting_effects`, such as `docstring-convention`.

Only formatting, docstring-formatting, and comment-formatting settings that do not affect rule selection are eligible for per-file overrides.

Per-file settings carry the source priority of the `per-file-settings` field itself. A matching per-file override applies to a setting only when the `per-file-settings` source priority is greater than or equal to that setting's current source priority. For example, a command-line `--line-length` value overrides a config-file per-file `line-length` value for every file.

`pydocfmt check --show-settings` remains current-working-directory oriented and does not apply path-specific per-file setting overrides.

## Setting Notes

`line-ending = "auto"` uses the first line ending detected in the source file, defaulting to LF when the file has no line endings. The setting controls rewritten files; files that do not require formatting are not rewritten solely to normalize line endings.

When `respect-gitignore` is enabled, pydocfmt aborts if gitignore filtering cannot be checked, because continuing without that filter could format files that should stay ignored.

When `url-aware-wrapping` is enabled, pydocfmt may choose less greedy line breaks around URL tokens in comment and docstring prose, but URLs and other long words are still not split.

The `comment-*` settings affect the rule-based formatter. PCF001 defaults to formatting each standalone physical line independently; joining and structured-markup interpretation are opt-in. PCF004 keeps syntax-sensitive and unsafe-content overlong trailing comments inline by default. See `pydocfmt rule PCF001`, `pydocfmt rule PCF002`, `pydocfmt rule PCF003`, and `pydocfmt rule PCF004` for exact detector precedence, spacing, extraction, and protected-comment behavior.

`comment-task-marker-mode` controls whether configured task-marker labels receive no special handling, are normalized without wrapping, or are reflowed with hanging indentation. `comment-task-markers` values match exactly and case-sensitively before a colon; an empty list disables task-marker recognition even when the mode is not `none`.

The `docstring-convention` setting never auto-detects a convention. Google sections, NumPy sections, and reST fields are only parsed when their matching convention is selected; `none` and `pep257` leave those convention syntaxes as ordinary content. The default `pep257` convention applies PEP 257/pydocstyle-compatible broad-rule carve-outs, while `none` is the stricter no-convention profile for generic rules that can act without convention parsing. Compared with `pep257`, `none` broadly enables PDF106, PDF301, and PDF305. The resolved convention can also ignore incompatible PDF rules selected through broad selectors; selecting an exact rule code restores an ignored rule, but disabled rules stay off even when selected exactly. The `docstring-parse-*` settings control generic semantic structures independently, `docstring-property-decorators` controls decorator names treated as property-like by property-specific summary rules, `docstring-class-attribute-no-type-base-classes` controls direct class bases whose class attribute entries should not include types for PDF713, and PCF rules are not affected by docstring conventions. For those name-matching settings and the function-decorator settings, dotted configured names also match import aliases resolved statically by LibCST; unqualified names are syntactic-only.

## Related Specifications

- [File Selection Specification](file_selection_spec.md) specifies how resolved file-selection settings choose files.
- [Rule Selection Specification](rule_selection_spec.md) specifies how resolved rule-selection settings choose active rules, per-file ignores, and fixability.
