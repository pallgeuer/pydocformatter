# Changelog

All notable changes to this project will be documented in this file.

The format is based on the ideas of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) (e.g. Added, Changed, Removed, Fixed headings), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

### Added

- **Docstring formatting:**
  - Added convention-aware semantic docstring preparation with explicit reflow regions and configurable recognition of lists, headings, doctests, code fences, block quotes, tables, directives, literal blocks, and Sphinx fields.
  - Added the `docstring-convention` setting with `none`, `google`, `numpy`, and `pep257` modes.
  - Added `PDF000` to rewrite implicitly concatenated docstrings as equivalent simple triple-double-quoted literals.
  - Added `PDF001` and `PDF002` to normalize simple docstring quote style and report non-raw docstrings with source backslashes, suppressing ASCII-only non-ASCII character escape spellings and using automatic fixes only when the rewrite preserves the evaluated docstring value.
  - Added `PDF101` to reflow safely mapped docstring summaries, paragraphs, section descriptions, Sphinx fields, list items, and block quotes.
  - Added `PDF100` to normalize safely mapped multi-line simple docstring indentation, including convention-aware Google and NumPy section indentation.
  - Added `PDF102` and `PDF103` to normalize safely mapped docstring trailing whitespace and blank-line whitespace.
  - Added `PDF104` and `PDF105` to normalize quote-adjacent whitespace around safely mapped simple docstring content.
  - Added `PDF200` to collapse excess blank lines around docstring chunks and collapse blank-only docstrings to empty docstrings.
  - Added `PDF201` to insert safe missing blank lines before recognized docstring structures and convention sections.
  - Added `PDF202`, `PDF300` through `PDF305`, `PDF400` through `PDF405`, and `PDF500` through `PDF507` as implementation-pending stubs for the remaining Ruff docstring style and validation rules.
  - Added `PDF106` through `PDF109` to normalize multi-line docstring opening and closing quote placement.
  - Added `PDF110` and `PDF203` to collapse safe summary-only docstrings that fit on one line and report summaries that remain multi-line.

- **CLI:**
  - Added Ruff-style subcommands with `pydocfmt check` for read-only checks and `pydocfmt check --fix` for formatting.
  - Added `pydocfmt help [command]`, `pydocfmt version`, `pydocfmt --version`, `pydocfmt check --show-settings`, and `pydocfmt check --show-rules`.
  - Added `--line-ending` to control line endings used when rewriting files.
  - Added `--output-format grouped` for rule findings.
  - Added `--legacy` / `--no-legacy` for opting into the legacy formatter path.
  - Added `--show-files` to report all considered files during discovery, including included files and ignored files with include/exclude reasons, without formatting files.
  - Added Ruff-style stdin support via `pydocfmt check -` and `--stdin-filename`.
  - Added Ruff-style `-o` / `--output-file` for redirecting diagnostics and show output.
  - Added Ruff-style `pydocfmt check --diff` for previewing fixes without writing files.
  - Added Ruff-style `-e` / `--exit-zero` and `--exit-non-zero-on-fix` status controls.
  - Added `--respect-gitignore` / `--no-respect-gitignore`, with enabled-by-default behavior and matching `pyproject.toml` configuration.
  - Added Ruff-style `--config` and `--isolated` global options for explicit config files, inline setting overrides, and config-free runs.
  - Added `pydocfmt config` to list and describe supported configuration options in text or JSON format.
  - Added active-rule listing output for `pydocfmt check --show-rules`, including effective fixability markers.
  - Added `pydocfmt rule` to explain individual rules or all rules in Ruff-style text or JSON output.
  - Added `pydocfmt linter` to list rule-prefix linters in Ruff-style text or JSON output.

- **Configuration:**
  - Added generic rule-selection effects driven by resolved setting values, with exact-selector restoration for ignored rules and unconditional removal for disabled rules.
  - Added TOML-only `[tool.pydocfmt.docstring]` and `[tool.pydocfmt.comment]` tables as the preferred spelling for docstring and comment settings, with flat `docstring-*` and `comment-*` keys still supported as mutually exclusive compatibility forms.
  - Added mutually validated rule incompatibility metadata and deterministic conflict resolution that keeps the first selected rule and reports later conflicts as operational errors.
  - Added docstring-convention effects for `PDF106` through `PDF109` while keeping PCF rules convention-independent.
  - Enabled comment list-item and block-quote formatting, structural preservation, and Python statement detection by default, while leaving heuristic disabled-code and expression detection disabled.
  - Added `output-format` for formatter configuration, currently supporting only `"grouped"`.
  - Added `legacy` for formatter configuration, defaulting to `false`.
  - Added Ruff-style `line-ending` configuration with `"auto"`, `"lf"`, `"cr-lf"`, and `"native"` values.
  - Added `indent-style` and `indent-width` for generated docstring section indentation, with Ruff-style defaults of `"space"` and `4`.
  - Added `docstring-blank-line-style` with `"blank"` and `"aligned"` modes for PDF103 blank-line whitespace normalization.
  - Added `docstring-blank-line-after-last-section` to control whether PDF200 and PDF201 keep one blank line after the final recognized Google or NumPy docstring section.
  - Added Ruff-style rule settings under `[tool.pydocfmt]`: `select`, `ignore`, `extend-select`, `per-file-ignores`, `extend-per-file-ignores`, `fixable`, `unfixable`, and `extend-fixable`.
  - Added `respect-gitignore` for formatter configuration, defaulting to `true`.
  - Added explicit config-file support for `--config PATH`, including pyproject-style `[tool.pydocfmt]` files and dedicated top-level pydocfmt TOML files.
  - Added Ruff-style path-aware auto-discovery for the closest containing `[tool.pydocfmt]` `pyproject.toml`.
  - Added independent comment-formatting settings for standalone paragraph joining, list items, headings, doctests, code fences, block quotes, tables, reStructuredText directives, and disabled-code detection.

- **Documentation:**
  - Added a Ruff file-selection compatibility specification at `docs/file_selection_spec.md`, including exact defaults, precedence rules, force-exclude behavior, config-relative glob bases, and explicit pydocformatter deviations.
  - Added a rule-selection specification at `docs/rule_selection_spec.md`, covering rule collection, selectors, fixability, and rule explanation output.
  - Added adjacent Markdown documentation for all built-in pydocformatter rules, including Ruff compatibility notes where relevant.
  - Changed non-fixable findings in rule examples to label singular and plural line references explicitly.
  - Expanded the PDF101 documentation with explicit behavior notes, setting interactions, safety limits, and verified qualitative examples.
  - Expanded the PDF104 and PDF105 documentation with explicit behavior boundaries, safety notes, and verified qualitative examples.
  - Expanded the PDF110 and PDF203 documentation with explicit behavior boundaries, setting interactions, safety notes, and verified qualitative examples.
  - Added a reusable rule documentation Markdown template at `src/pydocformatter/rules/templates/rule_template.md`.
  - Added adjacent documentation for each rule category and a reusable rule category documentation template.
  - Added docstrings for public glob matching methods, the dependency-pin check tool, and important configuration, CLI, and file-selection helpers.
  - Completed Google-style docstrings for public source APIs and added concise docstrings for private helpers that previously lacked them.

- **Developer workflow:**
  - Added a pytest pre-commit hook that runs the test suite before commits.
  - Added pytest coverage that checks the pydocformatter rule tables in `docs/formatting_rules.md` against actual rule metadata.
  - Added pytest coverage that executes structured examples from built-in rule Markdown documentation.
  - Added validation that structured rule Markdown examples use `[output=unchanged]` when the documented output is identical to the input.
  - Added regression coverage for Ruff-compatible file-selection and per-file-ignore pattern-base behavior.
  - Vastly expanded PCF rule tests across comment classification, run boundaries, structure preservation, code detection, width handling, line endings, mixed formatting, syntax-position safety, convergence, idempotence, and rule independence.
  - Vastly expanded PDF category preparation tests across docstring collection, source metadata, semantic sections and entries, protected structures, reflow regions, malformed inputs, and mixed edge cases.
  - Added PDF101 regression coverage for short-line joining, protected structures, disabled structure parsing, simple-suite docstrings, and line-ending settings.

- **Formatting:**
  - Added the LibCST-based rule execution framework with ordered category preprocessing, repeated automatic-fix passes, final read-only checks, and non-convergence diagnostics.
  - Added typed PCF comment and PDF docstring category data, together with a shared validated source-edit helper, as the foundation for individual rule implementations.
  - Implemented PCF001 standalone-comment formatting and PCF002 trailing-comment formatting with independent fixes, protected directive handling, tab-expanded widths, stable impossible-width behavior, and exact EOF preservation.

### Changed

- **Docstring formatting:**
  - Implemented `PDF302` through `PDF305`, replacing their previous stub behavior with first-summary-line diagnostics, safe first-word capitalization fixes, and Ruff-style convention-selection effects.
  - Changed summary first-word normalization to preserve Unicode alphanumeric characters when removing punctuation, avoiding false positives such as `This\u00e9`.
  - Implemented `PDF202`, `PDF300`, and `PDF301`, replacing their previous stub behavior with empty-docstring diagnostics, safe summary-punctuation fixes, and parser-recognized section and Sphinx-field skips for the active settings.
  - Changed `PDF000` to normalize safe `\n` and `\t` whitespace escape spellings in docstrings, including non-concatenated docstrings, without changing evaluated docstring values.
  - Changed `PDF106` through `PDF109` to also normalize single-content-line docstrings when the docstring literal itself spans multiple lines.
  - Changed same-line quote placement for `PDF106` and `PDF108` to keep one separator space when needed for valid Python source.
  - Changed `PDF200` to remove blank lines after Google/NumPy section headers and between consecutive convention entries.
  - Changed `PDF100` to replace Ruff `D206` by expanding tabs in rewritten docstring indentation when `indent-style = "space"`.
  - Renumbered PDF rules into topic-based ranges, keeping literal normalization in `PDF0xx`, core source formatting in `PDF1xx`, blank-line checks in `PDF2xx`, first-line style in `PDF3xx`, section style in `PDF4xx`, and signature/docstring validation in `PDF5xx`.
  - Changed PDF101 Google-style entry wrapping to use fixed continuation indentation and to place descriptions on the following line when long entry prefixes leave too little room.
  - Changed directive and literal-block parsing so trailing blank lines are represented as ordinary docstring blank-line blocks instead of part of the protected body.
  - Centralized docstring string-literal rendering for `PDF000` and `PDF101`, preserving reusable escape spellings and literal non-ASCII characters while reporting unsafe rewrites as non-fixable findings.
  - Centralized quote-collision rendering for `PDF110` so one-line docstring collapse reuses the shared PDF escape and separator fallback behavior.

### Fixed

- **Docstring formatting:**
  - Fixed PDF302 to skip property getter, setter, and deleter accessor docstrings.
  - Fixed PDF302 third-person summary detection to avoid invalid generated forms such as `trys` and `processs`, and to recognize `has`.
  - Fixed PDF101 to account for opening and same-line closing docstring quote delimiters when wrapping generated docstring source lines.
  - Fixed PDF300 and PDF301 to let `docstring-parse-headings` consistently control underlined heading-style summaries.
  - Fixed PDF200, PDF201, PDF108, and PDF109 to preserve genuine leading spaces or tabs on first-line docstring content while rewriting surrounding docstring structure.
  - Fixed PDF108 to move bare closing quotes after single-content-line docstrings whose literal spans multiple physical lines.
  - Fixed PDF106 to keep a distinct, value-preserving source spelling when moving content that starts with the docstring delimiter quote character onto the opening quote line.
  - Fixed PDF105 and PDF108 to escape delimiter-quote collisions before falling back to a value-changing separator space.
  - Fixed PDF201 to avoid inserting a trailing blank line after a header-only final Google or NumPy section.
  - Fixed PDF100 to leave first-line Google and NumPy sections unchanged instead of partially reindenting their entries or adornments away from the section header.
  - Fixed PDF100 to preserve the canonical margin for under-indented same-line closing quotes.
  - Fixed PDF102 and PDF103 to treat only spaces and tabs as removable docstring line whitespace, preserving other evaluated whitespace characters.
  - Fixed PDF103 to leave empty docstrings unchanged instead of inserting indentation before the closing quotes.
  - Fixed PDF101 source mapping for reflow regions whose text also appears earlier on the same raw docstring line.
  - Removed dead string-literal escape handling and tightened edge-case wrapping for source-aware docstring text.

- **Rule documentation:**
  - Expanded the PCF001 and PCF002 rule examples to demonstrate common spacing, wrapping, structure, protection, boundary, and extraction behavior.
  - Documented that PDF110 separator fallback can add a leading or trailing space to the evaluated `__doc__` value when value-preserving escaping is impossible.
  - Documented that PDF101 delimiter-aware wrapping does not reserve width for unchanged source after a same-line closing docstring delimiter.
  - Rephrased rule example results to describe the effect of applying each rule.
  - Kept planned PDF rule examples in ordinary Python fences until their formatter behavior is implemented and can be tested as structured examples.

- **Developer workflow:**
  - Included top-level Markdown documentation files from `docs/` in source distributions.
  - Fixed rule Markdown example coverage so every built-in rule must provide at least one executed structured example.
  - Changed the mypy pre-commit hook to use the locked project environment through `uv run mypy`.
  - Split rule registration decorators from rule collection discovery so rule category modules can be imported directly without eager collection initialization.
  - Added an explicit test package boundary and moved reusable PCF test helpers out of `conftest.py`, allowing mypy to check multiple directory-scoped pytest configurations without exclusions.
  - Organized rule tests by category and rule code under `tests/rules/`.

- **Rule framework:**
  - Split rule models, authoring contracts, execution, and line-ending utilities into focused modules while keeping formatter file and source orchestration separate.
  - Moved shared modern-rule text wrapping and display-width helpers into a neutral rules helper module.
  - Moved rule codes and selectors into `pydocformatter.rules.codes` and added immutable, hashable setting-effect metadata to rule definitions.
  - Changed internal PDF and PCF classification types from string-compatible enums to ordinary enums.
  - Renamed PCF001 to `standalone-comment-formatting` and PCF002 to `trailing-comment-formatting` to reflect their spacing and wrapping behavior.
  - Required rule and category definitions to explicitly provide `setting_effects` and `url` metadata, including empty or absent values.

- **CLI:**
  - Made rule-based formatting the default and added `--legacy` for temporarily selecting the previous formatter implementation.
  - Reorganized `pydocfmt check --help` into Ruff-inspired argument groups for options, rule selection, and file selection.
  - Moved argparse helpers from `pydocformatter.cli.utils` to `pydocformatter.utils.argparser`.
  - Moved `--output-format` and `--legacy` to the Formatting help group, and moved `--output-file` to the end of the Options group.
  - Refactored parser setup to share global option definitions and isolate version/help subcommand construction.
  - Updated `pydocfmt check --help` argument ordering and metavars to keep help, settings output, and documentation consistent.
  - Rule and file-selection list options now use comma-separated CLI values, such as `--select PDF,PCF` and `--include "*.py,*.pyi"`.
  - `pydocfmt` now formats both docstrings and comments in one run.
  - `pydocfmt` now exposes command-line overrides for Ruff-style rule settings.
  - `pydocfmt` now defaults to formatting the current directory when no files or directories are specified.
  - `--include`, `--extend-include`, `--exclude`, and `--extend-exclude` now accept multiple glob values in one option usage (e.g. `--include *.py *.pyi`).
  - Check summaries now report fixed and remaining rule-check counts separately, including fixable remaining counts for diff output.

- **Configuration:**
  - Changed rule metadata fixability from a boolean to `FixAvailability` with `Always`, `Usually`, `Sometimes`, and `Never` values while keeping individual rule findings boolean-fixable.
  - Simplified resolved CLI setting metadata so `SettingCLIDefinition` uses a generated dataclass initializer.
  - Split unresolved CLI setting metadata into `SettingCLIOptions` while keeping `SettingCLIDefinition` as the resolved argparse metadata shape.
  - Added explicit `available_in_cli` setting metadata and treat empty documentation as omitted documentation.
  - Renamed `SettingDefinition.type` to `value_type` to avoid ambiguity with argparse's `type` option.
  - Made `SettingDefinition` generic over its validated setting value and reordered its optional metadata fields.
  - Tightened `SettingsSchema.overrides_type` typing, reordered schema fields, and made `table_path` explicit.
  - Kept settings schema metadata lookups on the definitions tuple instead of separate convenience helpers.
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
  - Consolidated settings file, TOML section, and raw field-value application around the profile-aware configuration path.

- **File discovery:**
  - `--show-files` now reports directories pruned by exclude patterns, such as `.venv`.
  - File-selection helpers now require a path-aware settings resolver instead of accepting raw `CheckSettings`.
  - `pydocfmt` now applies gitignore-based filtering when `respect-gitignore` is enabled, and aborts file selection if gitignore checks cannot be executed.
  - `force-exclude` now follows Ruff-style explicit-file behavior by applying exclude patterns while still bypassing include and gitignore filtering.
  - File selection now resolves include, exclude, and per-file-ignore patterns relative to their setting source, including closest auto config directories and cwd-relative CLI overrides.
  - Explicit `--config PATH` files now disable auto-discovered configuration and only one explicit config file is accepted, while inline `--config` overrides still layer over auto-discovered configuration.
  - Gitignore filtering now follows the `respect-gitignore` setting resolved for the current working directory.
  - Gitignore filtering now handles symlinked directory traversal by querying git with real paths while preserving symlinked display paths.
  - File selection now deduplicates paths that resolve to the same physical file and displays real filesystem paths as absolute normalized paths.

- **Formatting:**
  - Moved the previous formatter implementation into `pydocformatter.legacy` and gave the rule-based formatter APIs their permanent unsuffixed names.
  - Added `Rule`, `RuleFinding`, and `FormatterResult` data structures for reporting remaining rule issues after fixes.
  - Changed rule fixes to preserve untouched mixed line endings instead of normalizing the complete file after any source change.
  - Formatter results now carry the formatted source alongside path, modification, finding, and error data.
  - `SourceFormatResult` now carries the original source alongside the possibly formatted source.
  - Formatter internals now require formatting controls such as line length, line endings, and indentation settings as explicit keyword-only arguments.
  - Formatter functions now receive resolved `CheckSettings` directly.
  - Generated Google-style docstring section indentation is now configurable while preserving the existing base docstring indentation.
  - Check-mode output now includes docstring and comment line locations, emitted once per subject per file with compressed consecutive ranges.

- **Architecture:**
  - Added hashable `SettingsProfile.Key` identities and moved rule templates and line-ending helpers under the rules package.
  - Added modular no-op rule check/fix hooks and category preprocessing contexts so rule implementations can share per-pass analysis without coupling rules to each other.
  - Replaced inferred rule-prefix linter metadata with first-class `RuleCategoryBase` classes that own rule registration, validation, ordering, and metadata.
  - Changed rule registries and collections to accept categories only, while exposing deterministic category and flattened rule iteration.
  - Updated rule definition loading to import explicit prefix-named category modules before rule modules without relying on package `__init__.py` exports.
  - Made rule definition loading reject inconsistent category layouts, registrations, module names, rule codes, and adjacent documentation.
  - Added `RuleCollectionError` for rule category registration, collection, and definition import failures.
  - Moved rule-to-category registration from `RuleCategoryBase` to the collection-level `register_rule_to(category)` decorator.
  - Added `RuleCode` and `RuleSelector` parsed value objects for rule metadata and selector handling.
  - Simplified rule metadata parsing so split helpers return `(None, None)` for invalid codes/selectors, `ALL` is handled as a reserved selector in the base rule API, and collection relies on `RuleMetadata` post-init validation.
  - Exposed rule metadata shortcuts such as `code`, `prefix`, and `fixable` as class-level properties on `RuleBase` subclasses.
  - Changed rule metadata to expose ordered `code`, `name`, `message`, and `fixable` fields, with parsed code parts available on `RuleCode`.
  - Centralized rule code and selector parsing in `pydocformatter.rules.base`, with selector matching handled by `RuleSelector.selects_code`.
  - Replaced the flat rule selector module with a modular `pydocformatter.rules` package, including `RuleBase`, `RuleMetadata`, decorator-based registration, and automatic collection from `rules/definitions/**`.
  - Added `pydocformatter.rules_selection` to resolve rule selection and effective fixability after settings load, reporting selector issues as operational errors.
  - Renamed the generic settings module from `pydocformatter.config` to `pydocformatter.settings`, with `ConfigError` renamed to `SettingsError`.
  - Setting metadata now derives default TOML keys from field names and default CLI flags from setting keys, with `SettingCliDefinition` renamed to `SettingCLIDefinition`.
  - Utility helpers now live in explicit `pydocformatter.utils` submodules for diagnostics, glob matching, and line endings.
  - Consolidated diagnostics, line-ending, and automatic pluralization helpers in `pydocformatter.utils.misc`.
  - Rule-based formatter interfaces now live in `pydocformatter.formatter`.
  - `pydocformatter.settings` now provides generic schema-driven settings machinery for config loading, validation, settings output, argparse setup, and CLI override extraction.
  - `pydocformatter.settings` now provides generic multi-string map typing and validation, and raw CLI setting definitions now show default values unless explicitly disabled.
  - Setting metadata now derives default validation, CLI behavior, and TOML rendering from each setting's declared type.
  - Centralized check setting metadata in `pydocformatter.cli.settings_check` so config keys, validation, settings output, dedicated CLI options, and CLI override extraction share one ordered source of truth.
  - Rule selector metadata is now inferred from setting group and CLI value shape instead of explicit setting definition tags.
  - Moved global `--config` and `--isolated` parsing into reusable `GlobalArgs` helpers, shared by the top-level and `check` parsers.
  - Renamed the CLI implementation module from `pydocformatter.cli.pydocfmt_main` to `pydocformatter.cli.main`.
  - Moved enabled-state help text formatting into the configuration layer.
  - Moved rule-based file I/O diagnostics into the formatter layer.
  - Simplified `RuleCollection` by storing rule classes directly, exposing a rule-code-to-class index, and replacing string-based selector existence checks with `matching_rules_exist`.
  - Rule registration now uses an explicit frozen `RuleRegistry`, allowing tests and custom collection paths to avoid stale global rule state.
  - Rule collection now happens when `pydocformatter.rules.collection` is imported and is exposed as `RULE_COLLECTION`.
  - Explicit rule package loading is now exposed as `import_package_rules`, with collections retrieved from the relevant `RuleRegistry`.
  - `RuleBase` subclasses now fail at class definition time unless they define `meta` as a `RuleMetadata` instance.
  - Registered the built-in PDF and PCF rule metadata modules so rule selection, active-rule listing, and rule explanation output share one catalog.
  - Rule collections now expose pre-collected rule-prefix linter metadata.
  - Rule metadata now requires an explicit stable version for every rule.
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

- **Tests:**
  - Added a session-wide temporary configuration boundary and per-test working directories so tests no longer inherit ancestor `[tool.pydocfmt]` configuration, fixing stdin checks that failed under the repository's `legacy = true` self-configuration and removing latent coupling for CLI and file-selection tests.
  - Made the README settings-documentation test locate `README.md` relative to the test file instead of the current working directory.

- **Formatting:**
  - Kept extracted trailing comments separate from preceding standalone comments, required fenced-region closers to contain no trailing text, and normalized tab-equivalent block-quote prefixes in one formatting pass.
  - Preserved CRLF line endings when `PDF000` rewrites concatenated docstrings whose evaluated values contain newlines.
  - Kept protected docstring structures opaque to convention section and entry parsing, preserved semantic entries and reflow regions in source order, used visual indentation for literal blocks, and avoided ambiguous evaluated-to-source line mappings.
  - Fixed semantic parsing of docstrings nested under multiple levels of tab indentation.
  - Preserved residual visual indentation when a leading tab crosses the docstring dedent margin.
  - Derived multiline simple-suite docstring margins from suite indentation instead of the literal's source column.
  - Kept non-ASCII code points escaped when normalizing concatenated docstrings so ASCII-compatible source encodings remain valid.
  - Kept non-ASCII code points escaped when reflowing docstrings that were originally ASCII-compatible.
  - Reflowed module docstrings whose evaluated value ends with a newline and whose closing delimiter is on a separate source line.
  - Preserved tab-indented PDF101 continuation lines when form feeds precede a docstring or a leading tab crosses the docstring dedent margin.
  - Required whitespace after `>>>` when recognizing protected doctest prompts.

- **Rule framework:**
  - Category preprocessing data is now refreshed after an earlier rule changes the module while remaining shared by later rules processing the same module version.
  - UTF-8 byte order marks are now preserved when automatic fixes rewrite source, and fixes that converge on the final permitted iteration no longer report a non-convergence error.
  - Preserved exact rule-code overrides for setting-ignored rules when a higher-priority broad `extend-select` also selects the rule.

- **Documentation:**
  - Updated README, contributing, release, pull request, and file-selection docs for the single-command workflow and latest file-selection behavior.

- **Rule selection:**
  - Rule and fixability selectors now resolve conflicts by Ruff-style source priority before selector specificity, with disabling selectors winning equal-priority and equal-specificity ties.
  - Per-file ignores now suppress every selected matching rule for matching files, without comparing the ignore selector specificity against the selector that enabled the rule.
  - Per-file ignore patterns now support Ruff-style leading `!` negation.
  - Repeated `--per-file-ignores` and `--extend-per-file-ignores` entries for the same pattern now append selector lists within the command-line layer.

- **CLI:**
  - Legacy formatter findings now report the original changed source lines instead of a synthetic line number.
  - Formatter read, decode, and write errors now affect check exit status without being reported as rule findings.
  - `pydocfmt check` now reports invalid nested path-specific configuration without producing a traceback.
  - `--force-exclude` now applies to virtual paths supplied through `--stdin-filename`.
  - `pydocfmt check` now prints `All checks passed!` to the configured output when no diagnostics are found.
  - `pydocfmt check --output-file` remains supported with the legacy formatter, while stdin input is limited to the rule-based formatter path.
  - Operational errors no longer produce an `All checks passed!` success message.
  - Output-file setup errors are now reported without converting unrelated `OSError`s raised while producing diagnostics.
  - `pydocfmt` now skips files that fail UTF-8 decoding, emits an operational error in grouped output, and continues processing remaining files instead of crashing.
  - Empty include glob patterns now report configuration or argument errors instead of crashing with a traceback.
  - `--help` now works even when the current `pyproject.toml` contains invalid pydocformatter configuration.
  - Missing or unreadable files now emit an operational error in grouped output and processing continues instead of crashing.
  - `--output-file` now creates only the direct parent directory instead of recursively creating nested output directories.
  - Path-aware rule-selection operational errors are now reported once for equivalent resolved profiles instead of once per selected directory.

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

- **Documentation:**
  - Removed the internal empirical Ruff file-selection design notes at `docs/ruff_file_selection_spec.md`.

- **CLI:**
  - Removed legacy top-level formatting and check forms such as `pydocfmt` and `pydocfmt --check`; use `pydocfmt check --fix` or `pydocfmt check`.

- **Architecture:**
  - Removed the separate comment-formatting command and merged comment formatting into `pydocfmt`.
  - Removed tool-specific TOML configuration tables; nested formatter tables are now configuration errors.
  - Removed redundant shared CLI, formatter-type, and comment-command modules.
  - Removed trivial `SettingsSchema` convenience helpers for field/key definition maps and CLI flag flattening.
  - Removed unused rule-selector definition exports from check settings metadata.

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
