# Changelog

All notable changes to this project will be documented in this file.

The format is based on the ideas of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) (e.g. Added, Changed, Removed, Fixed headings), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

### Added

- **CLI:**
  - Added Ruff-style subcommands with `pydocfmt check` for read-only checks and `pydocfmt check --fix` for formatting.
  - Added `pydocfmt help [command]`, `pydocfmt version`, `pydocfmt --version`, and `pydocfmt check --show-settings`.
  - Added `--line-ending` to control line endings used when rewriting files.
  - Added `--output-format grouped` for rule findings.
  - Added `--experimental` / `--no-experimental` for opting into the experimental formatter path.
  - Added `--show-files` to report all considered files during discovery, including included files and ignored files with include/exclude reasons, without formatting files.
  - Added Ruff-style stdin support via `pydocfmt check -` and `--stdin-filename`.
  - Added Ruff-style `-o` / `--output-file` for redirecting diagnostics and show output.
  - Added Ruff-style `pydocfmt check --diff` for previewing fixes without writing files.
  - Added Ruff-style `-e` / `--exit-zero` and `--exit-non-zero-on-fix` status controls.
  - Added `--respect-gitignore` / `--no-respect-gitignore`, with enabled-by-default behavior and matching `pyproject.toml` configuration.
  - Added Ruff-style `--config` and `--isolated` global options for explicit config files, inline setting overrides, and config-free runs.
  - Added `pydocfmt config` to list and describe supported configuration options in text or JSON format.

- **Configuration:**
  - Added `output-format` for formatter configuration, currently supporting only `"grouped"`.
  - Added `experimental` for formatter configuration, defaulting to `false`.
  - Added Ruff-style `line-ending` configuration with `"auto"`, `"lf"`, `"cr-lf"`, and `"native"` values.
  - Added `indent-style` and `indent-width` for generated docstring section indentation, with Ruff-style defaults of `"space"` and `4`.
  - Added Ruff-style rule settings under `[tool.pydocfmt]`: `select`, `ignore`, `extend-select`, `per-file-ignores`, `extend-per-file-ignores`, `fixable`, `unfixable`, and `extend-fixable`.
  - Added `respect-gitignore` for formatter configuration, defaulting to `true`.
  - Added explicit config-file support for `--config PATH`, including pyproject-style `[tool.pydocfmt]` files and dedicated top-level pydocfmt TOML files.

- **Documentation:**
  - Added a Ruff file-selection compatibility specification at `docs/file_selection_spec.md`, including exact defaults, precedence rules, force-exclude behavior, and explicit pydocformatter deviations.
  - Added docstrings for public glob matching methods, the dependency-pin check tool, and important configuration, CLI, and file-selection helpers.

- **Developer workflow:**
  - Added a pytest pre-commit hook that runs the test suite before commits.

### Changed

- **CLI:**
  - Reorganized `pydocfmt check --help` into Ruff-inspired argument groups for options, rule selection, and file selection.
  - Moved argparse helpers from `pydocformatter.cli.utils` to `pydocformatter.utils.argparser`.
  - Moved `--output-format` and `--experimental` to the Formatting help group, and moved `--output-file` to the end of the Options group.
  - Refactored parser setup to share global option definitions and isolate version/help subcommand construction.
  - Updated `pydocfmt check --help` argument ordering and metavars to keep help, settings output, and documentation consistent.
  - Rule and file-selection list options now use comma-separated CLI values, such as `--select PDF,PCF` and `--include "*.py,*.pyi"`.
  - `pydocfmt` now formats both docstrings and comments in one run.
  - `pydocfmt` now exposes command-line overrides for Ruff-style rule settings.
  - `pydocfmt` now defaults to formatting the current directory when no files or directories are specified.
  - `--include`, `--extend-include`, `--exclude`, and `--extend-exclude` now accept multiple glob values in one option usage (e.g. `--include *.py *.pyi`).

- **Configuration:**
  - Simplified resolved CLI setting metadata so `SettingCLIDefinition` uses a generated dataclass initializer.
  - Split unresolved CLI setting metadata into `SettingCLIOptions` while keeping `SettingCLIDefinition` as the resolved argparse metadata shape.
  - Added explicit `available_in_cli` setting metadata and treat empty documentation as omitted documentation.
  - Renamed `SettingDefinition.type` to `value_type` to avoid ambiguity with argparse's `type` option.
  - Made `SettingDefinition` generic over its validated setting value and reordered its optional metadata fields.
  - Tightened `SettingsSchema.overrides_type` typing, reordered schema fields, and made `table_path` explicit.
  - Converted settings schema definition/key helpers to methods and added CLI-specific key/flag helpers.
  - Tightened `SettingCLIDefinition` type annotations to match the supported `argparse.add_argument` keyword shapes.
  - Limited automatic underscore-to-dash setting key derivation to the `SettingDefinition` default key construction path.
  - Renamed the configuration table from `[tool.pydocformatter]` to `[tool.pydocfmt]`.
  - Settings now resolve from one `[tool.pydocfmt]` table, followed by command-line overrides.
  - Resolved settings output is now formatted by the configuration layer.
  - Setting validation now uses shared generic validators for booleans, integers, string lists, and string enums.
  - Tightened `SettingDefinition.validator` typing after default validator resolution.
  - File-selection settings now use Ruff-style glob lists (`include`, `extend-include`, `exclude`, `extend-exclude`) and `force-exclude`.
  - For each setting key, the highest-priority value wins (`dedicated CLI option > inline --config > explicit --config file > auto-discovered config > defaults`), including `extend-include` and `extend-exclude`.
  - Simplified `--config` option loading by separating explicit config-file paths from inline TOML options directly.
  - Made settings loading accept keyword-only command-line overrides and nullable global arguments.

- **File discovery:**
  - `--show-files` now reports directories pruned by exclude patterns, such as `.venv`.
  - `pydocfmt` now applies gitignore-based filtering when `respect-gitignore` is enabled, and aborts file selection if gitignore checks cannot be executed.
  - `force-exclude` now consistently applies `.gitignore` filtering to explicitly passed file paths.
  - File selection now deduplicates paths that resolve to the same physical file and prefers relative display paths when possible.

- **Formatting:**
  - Added experimental `Rule`, `RuleFinding`, and `FormatterResult` data structures for reporting remaining rule issues after fixes.
  - Experimental formatter results now carry the formatted source alongside path, modification, finding, and error data.
  - `SourceFormatResult` now carries the original source alongside the possibly formatted source.
  - Formatter internals now require formatting controls such as line length, line endings, and indentation settings as explicit keyword-only arguments.
  - Formatter functions now receive resolved `CheckSettings` directly.
  - Generated Google-style docstring section indentation is now configurable while preserving the existing base docstring indentation.
  - Check-mode output now includes docstring and comment line locations, emitted once per subject per file with compressed consecutive ranges.

- **Architecture:**
  - Renamed the generic settings module from `pydocformatter.config` to `pydocformatter.settings`, with `ConfigError` renamed to `SettingsError`.
  - Setting metadata now derives default TOML keys from field names and default CLI flags from setting keys, with `SettingCliDefinition` renamed to `SettingCLIDefinition`.
  - Utility helpers now live in explicit `pydocformatter.utils` submodules for diagnostics, glob matching, and line endings.
  - Consolidated diagnostics, line-ending, and automatic pluralization helpers in `pydocformatter.utils.misc`.
  - Experimental formatter interfaces now live in `pydocformatter.formatter`.
  - `pydocformatter.settings` now provides generic schema-driven settings machinery for config loading, validation, settings output, argparse setup, and CLI override extraction.
  - `pydocformatter.settings` now provides generic multi-string map typing and validation, and raw CLI setting definitions now show default values unless explicitly disabled.
  - Setting metadata now derives default validation, CLI behavior, and TOML rendering from each setting's declared type.
  - Centralized check setting metadata in `pydocformatter.cli.settings_check` so config keys, validation, settings output, dedicated CLI options, and CLI override extraction share one ordered source of truth.
  - Rule selector metadata is now inferred from setting group and CLI value shape instead of explicit setting definition tags.
  - Moved global `--config` and `--isolated` parsing into reusable `GlobalArgs` helpers, shared by the top-level and `check` parsers.
  - Renamed the CLI implementation module from `pydocformatter.cli.pydocfmt_main` to `pydocformatter.cli.main`.
  - Moved enabled-state help text formatting into the configuration layer.
  - Moved experimental file I/O diagnostics into the formatter layer.
  - Moved generic settings loading, formatting, argparse setup, and CLI override extraction onto `SettingsSchema`.
  - Made `SettingsSchema.load` accept parsed argparse namespaces directly for command-line setting overrides.
  - Simplified schema-driven settings argument extraction by removing unused destination-prefix plumbing and helper indirection.
  - Limited pyproject-style explicit config parsing to files named `pyproject.toml`.
  - Settings schema metadata now defaults omitted CLI definitions to standard CLI-backed settings and omitted documentation to the setting help text.
  - Settings schema metadata now supports config-example text for CLI introspection.
  - Settings schemas now record their override type and document the post-validation hook contract for implementers.

- **Developer dependencies:**
  - Updated mypy from 1.20.2 to 2.1.0.

### Fixed

- **Documentation:**
  - Updated README, contributing, release, pull request, and file-selection docs for the single-command workflow and latest file-selection behavior.

- **CLI:**
  - Legacy formatter findings now report the original changed source lines instead of a synthetic line number.
  - Formatter read, decode, and write errors now affect check exit status without being reported as rule findings.
  - `--force-exclude` now applies to virtual paths supplied through `--stdin-filename`.
  - `pydocfmt check` now prints `All checks passed!` to the configured output when no diagnostics are found.
  - `pydocfmt check --output-file` remains supported with the legacy formatter, while stdin input is limited to the experimental formatter path.
  - Operational errors no longer produce an `All checks passed!` success message.
  - Output-file setup errors are now reported without converting unrelated `OSError`s raised while producing diagnostics.
  - `pydocfmt` now skips files that fail UTF-8 decoding, emits an operational error in grouped output, and continues processing remaining files instead of crashing.
  - Invalid include glob patterns now report configuration or argument errors instead of crashing with a traceback.
  - `--help` now works even when the current `pyproject.toml` contains invalid pydocformatter configuration.
  - Missing or unreadable files now emit an operational error in grouped output and processing continues instead of crashing.
  - `--output-file` now creates only the direct parent directory instead of recursively creating nested output directories.

- **File discovery:**
  - Empty exclude glob patterns are now rejected as invalid configuration or arguments.
  - Slash-containing exclude patterns that name directories now exclude descendant files when the directory is passed directly or a child file is force-filtered.
  - Gitignore filtering now handles paths containing surrogate-escaped bytes.

- **Configuration:**
  - Malformed pydocformatter config tables are now consistently rejected, including falsy non-table values.

- **Formatting:**
  - Check mode now reports comment formatting diagnostics against original input line numbers.
  - Empty standalone comment separator lines are now preserved during comment formatting.
  - Preserved untouched line endings when formatting only selected docstring or comment spans.

### Removed

- **CLI:**
  - Removed legacy top-level formatting and check forms such as `pydocfmt` and `pydocfmt --check`; use `pydocfmt check --fix` or `pydocfmt check`.

- **Architecture:**
  - Removed the separate comment-formatting command and merged comment formatting into `pydocfmt`.
  - Removed tool-specific TOML configuration tables; nested formatter tables are now configuration errors.
  - Removed redundant shared CLI, formatter-type, and comment-command modules.

- **Developer dependencies:**
  - Removed the unused `build` and `twine` dev dependencies now that package build and publish workflows use uv directly.

- **Breaking configuration migration:**
  - Removed the old `[tool.pydocformatter]` config table from settings resolution.
  - Removed underscore aliases for settings such as `line_length`; only hyphenated keys are valid.
  - Removed regex include/exclude semantics in favor of glob-list file selection.
  - Removed legacy utility file-selection wrappers from `pydocformatter.utils`; use `pydocformatter.file_selection.select_files` directly.

## v0.2.0 (2026-05-01)

### Changed

- **Fork:**
  - Moved from `pyformatter` and `python-doc-formatter` to `pydocformatter` in both cases
  - Many files and directories were renamed and subject to find-replace
  - Updated project architecture and bug fixes

## v0.1.1 (2025-07-31)

### Fixed

- **Formatting:**
  - Multi-line summaries are now properly treated as a single summary block instead of splitting into summary + description
  - Proper blank line spacing between summary and sections when no description is present
  - Improved formatting consistency for various docstring structures
  - Enhanced multi-line summary support in Google-style docstring formatting

## v0.1.0 (2025-07-31)

### Added

- **pydocfmt:** Command-line tool for formatting Python docstrings
  - Google-style docstring formatting support
  - Intelligent line wrapping for docstring sections (Args, Returns, Raises, Examples, etc.)
  - Preservation of code blocks in Examples sections with automatic fencing
  - Support for parameter descriptions with type annotations
  - Proper handling of multi-paragraph descriptions and lists
  - Configuration via `pyproject.toml` and command-line arguments

- **pycommentfmt:** Command-line tool for formatting Python comments
  - Automatic comment line wrapping based on configurable line length
  - Intelligent handling of inline comments vs. block comments
  - Preservation of special comments (noqa, type: ignore, pylint directives, etc.)
  - Smart spacing correction for inline comments
  - Preservation of code-style comment blocks
  - Long inline comment extraction to separate comment blocks

- **Core Infrastructure:**
  - Configurable line length (default: 88 characters)
  - Include/exclude file patterns with regex support
  - Check mode for CI/CD integration (non-destructive validation)
  - Recursive directory processing
  - TOML configuration support via `pyproject.tool.<formatter>`

- **CLI Features:**
  - `--check` flag for validation without modification
  - `--line-length` for custom line length configuration
  - `--include` and `--exclude` for file filtering
  - Exit code 1 when formatting issues are detected in check mode

- **Google-style Docstring Support:**
  - Args/Arguments section formatting with type annotations
  - Returns/Return section formatting
  - Raises/Raise section formatting with exception backticks
  - Yields/Yield section formatting
  - Examples section with automatic code block fencing
  - Attributes section formatting
  - Intelligent paragraph and list handling in descriptions

- **Comment Formatting Features:**
  - Block comment rewrapping with proper indentation preservation
  - Inline comment spacing standardization
  - Long inline comment extraction and placement above code
  - Special comment preservation (tool directives, pragmas, etc.)
  - Code comment block detection and preservation

- **Testing & Quality Assurance:**
  - Comprehensive test suite with 100% coverage for core functionality
  - Unit tests for both docstring and comment formatting
  - Edge case handling for malformed docstrings and comments
  - Test coverage for check mode and file modification detection

- **Developer Experience:**
  - Pre-commit hook configuration
  - Pre-commit hooks for external repositories (`.pre-commit-hooks.yaml`)
  - GitHub Actions CI/CD workflows
  - Black and isort integration
  - Development environment configuration

- **Documentation:**
  - Comprehensive README with usage examples
  - Configuration documentation
  - Before/after formatting examples
  - Integration guides for popular tools

---

- **Unreleased:** https://github.com/pallgeuer/pydocformatter/compare/v0.2.0...HEAD
- **v0.2.0:** Not directly comparable to v0.1.1 as forked to a new GitHub repository
- **v0.1.1:** https://github.com/RikGhosh487/pyformatter/compare/v0.1.0...v0.1.1
- **v0.1.0:** https://github.com/RikGhosh487/pyformatter/releases/tag/v0.1.0
