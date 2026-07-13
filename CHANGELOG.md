# Changelog

All notable changes to this project will be documented in this file.

The format is based on the ideas of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) (e.g. Added, Changed, Fixed, Removed), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Release diffs

- **Unreleased:** <https://github.com/pallgeuer/pydocformatter/compare/v1.0.0...HEAD>
- **v1.0.0:** <https://github.com/pallgeuer/pydocformatter/compare/v0.2.0...v1.0.0>
- **v0.2.0:** <https://github.com/pallgeuer/pydocformatter/releases/tag/v0.2.0>

---

## Unreleased

### Added

#### Docstring formatting

- Added convention-aware semantic docstring preparation with explicit reflow regions and configurable recognition of lists, headings, doctests, code fences, block quotes, tables, directives, literal blocks, and reST fields.
- Added the `docstring-convention` setting with `none`, `pep257`, `google`, `numpy`, and `rest` modes.
- Added `PDF000` to rewrite implicitly concatenated docstrings as equivalent simple triple-double-quoted literals.
- Added `PDF001` and `PDF002` to normalize simple docstring quote style and report non-raw docstrings with source backslashes, suppressing ASCII-only non-ASCII character escape spellings and using automatic fixes only when the rewrite preserves the evaluated docstring value.
- Added opt-in `PDF003` to report docstrings with literal non-ASCII source characters and escape them when doing so preserves the evaluated docstring value.
- Added `PDF101` to reflow safely mapped docstring summaries, paragraphs, section descriptions, reST fields, list items, and block quotes.
- Added `PDF100` to normalize safely mapped multi-line simple docstring indentation, including convention-aware Google and NumPy section indentation.
- Added `PDF102` and `PDF103` to normalize safely mapped docstring trailing whitespace and blank-line whitespace.
- Added `PDF104` and `PDF105` to normalize quote-adjacent whitespace around safely mapped simple docstring content.
- Added `PDF200` to collapse excess blank lines around docstring chunks and collapse blank-only docstrings to empty docstrings.
- Added `PDF201` to insert safe missing blank lines before recognized docstring structures and convention sections.
- Added `PDF204` through `PDF211` to normalize blank-line spacing immediately before and after function and class docstring statements.
- Added `PDF202`, `PDF300` through `PDF305`, `PDF400` through `PDF409`, and `PDF500` through `PDF507` as implementation-pending stubs for the remaining Ruff docstring style and validation rules.
- Added `PDF401` and `PDF402` to normalize Google/NumPy section-name pluralization, preferred equivalent Google/NumPy section-name terms, and reStructuredText field-name aliases.
- Added `PDF408` to report repeated recognized Google and NumPy docstring sections and reST fields, including known spelling variants for the same semantic item.
- Added `PDF409` to normalize spacing in parsed Google, NumPy, and reST convention entries and fields.
- Added `PDF410` to normalize parsed Google, NumPy, and reST exception and warning entry names to no backticks and comma-separated exception lists.
- Added `PDF411` to normalize internal spacing in parsed convention type-like tokens using conservative AST validation.
- Added `PDF412` to report repeated parsed Google, NumPy, and named reST docstring entries within one docstring.
- Added `PDF413` to remove superfluous trailing colons from recognized NumPy section names.
- Added parser support for standalone colon-ended docstring lines so docstring reflow does not merge them with adjacent prose.
- Added `PDF508` through `PDF511` to validate missing and extraneous class and module attribute documentation against an explicit attribute inventory.
- Added `PDF512` and `PDF513` to report attached class and module attribute docstrings that duplicate owner docstring attribute documentation.
- Added `PDF514` through `PDF517` to report private class and module attributes documented in owner docstrings or by attached attribute docstrings.
- Added opt-in `PDF518` through `PDF525` to enforce owner-docstring or attached-docstring placement policies for public and private class and module attribute documentation.
- Added `PDF600` through `PDF615` to report missing package, module, class, nested class, function, method, dunder method, and `__init__` docstrings across public and opt-in private variants.
- Added `PDF616` to report docstrings on functions decorated with configured no-docstring decorators, including standard overload decorators by default.
- Added `PDF700` through `PDF719` to check parsed owning-docstring entry descriptions, docstring type presence policies, and conservative annotation/type mismatches for parameters, returns, yields, class attributes, and module attributes.
- Added `PDF306` and `PDF307` to report parameter and attribute documentation that only restates the documented name with generic filler.
- Added `PDF308` through `PDF310` to normalize punctuation and safe first-word capitalization for parsed docstring entry descriptions.
- Added signature-backed `PDF306` detection for variadic parameter descriptions such as `*args: Positional arguments.` and `**kwargs: Keyword arguments.`.
- Added tuple-unpacked module, class, and `__init__` instance attribute inventory support for `PDF508` through `PDF511`.
- Added `PDF106` through `PDF109` to normalize multi-line docstring opening and closing quote placement.
- Added `PDF110` and `PDF203` to collapse safe summary-only docstrings that fit on one line and report summaries that remain multi-line.
- Added `PDF311` to report property-like function summaries whose first normalized word is a known function-style verb.
- Added PDF processing for module, class, and `__init__` instance attribute docstrings recognized by common documentation tools.

#### CLI

- Added Ruff-style subcommands with `pydocfmt check` for read-only checks and `pydocfmt check --fix` for formatting.
- Added `pydocfmt help [command]`, `pydocfmt version`, `pydocfmt --version`, `pydocfmt check --show-settings`, and `pydocfmt check --show-rules`.
- Added `--line-ending` to control line endings used when rewriting files.
- Added `--output-format grouped` for rule findings.
- Added `--show-files` to report all considered files during discovery, including included files and ignored files with include/exclude reasons, without formatting files.
- Added Ruff-style stdin support via `pydocfmt check -` and `--stdin-filename`.
- Added Ruff-style `-o` / `--output-file` for redirecting diagnostics and show output.
- Added Ruff-style `pydocfmt check --diff` for previewing fixes without writing files.
- Added Ruff-style `-e` / `--exit-zero` and `--exit-non-zero-on-fix` status controls.
- Added `--respect-gitignore` / `--no-respect-gitignore`, with enabled-by-default behavior and matching `pyproject.toml` configuration.
- Added Ruff-style `--config` and `--isolated` global options for explicit config files, inline setting overrides, and config-free runs.
- Added `pydocfmt config` to list and describe supported configuration options in text or JSON format.
- Added `parallelism` / `--parallelism` to control deterministic file-level parallelism for disk-backed checks.
- Added active-rule listing output for `pydocfmt check --show-rules`, including effective fixability markers.
- Added `pydocfmt rule` to explain individual rules or all rules in Ruff-style text or JSON output.
- Added `pydocfmt linter` to list rule-prefix linters in Ruff-style text or JSON output.
- Added public documentation URLs to `pydocfmt linter --output-format json` and `pydocfmt rule --output-format json`.

#### Packaging

- Added build artifact selection rules to keep rule documentation templates source-only while excluding CI and agent configuration from source distributions.

#### Configuration

- Added `rest` as the convention value for semantic reStructuredText/Sphinx field parsing.
- Added generic rule-selection effects driven by resolved setting values, with exact-selector restoration for ignored rules and unconditional removal for disabled rules.
- Added TOML-only `[tool.pydocfmt.docstring]` and `[tool.pydocfmt.comment]` tables as the preferred spelling for docstring and comment settings, with flat `docstring-*` and `comment-*` keys still supported as mutually exclusive compatibility forms.
- Added mutually validated rule incompatibility metadata and deterministic conflict resolution that keeps the first selected rule and reports later conflicts as operational errors.
- Added docstring-convention effects for `PDF106` through `PDF109` while keeping PCF rules convention-independent.
- Enabled comment list-item and block-quote formatting, structural preservation, and Python statement detection by default, while leaving heuristic disabled-code and expression detection disabled.
- Added `require-explicit` to keep configured opt-in rules selectable by exact rule code without enabling them through broad selectors like `ALL`, `PDF`, or `PCF`.
- Added `output-format` for formatter configuration, currently supporting only `"grouped"`.
- Added Ruff-style `line-ending` configuration with `"auto"`, `"lf"`, `"cr-lf"`, and `"native"` values.
- Added `indent-style` and `indent-width` for generated docstring section indentation, with Ruff-style defaults of `"space"` and `4`.
- Added `url-aware-wrapping`, enabled by default, for URL-aware comment and docstring line balancing without splitting URL tokens.
- Added `docstring-blank-line-style` with `"blank"` and `"aligned"` modes for PDF103 blank-line whitespace normalization.
- Added `docstring-class-attribute-no-type-base-classes` to invert PDF713 for direct enum-like class bases, with import-aware matching for dotted configured names.
- Added `docstring-blank-line-after-last-section` to control whether PDF200 and PDF201 keep one blank line after the final recognized Google or NumPy docstring section.
- Added `docstring-require-init-attribute-documentation` to control whether class missing-attribute documentation checks require supported `self.*` assignments from `__init__`.
- Added `docstring-forbidden-function-decorators` and `docstring-optional-function-decorators` to configure function decorators that forbid docstrings or make them optional, with import-aware matching for dotted configured names.
- Added `docstring-property-decorators` to configure function decorators that make property-specific summary rules treat functions as properties, with import-aware matching for dotted configured names.
- Added `comment-trailing-extraction-syntax-aware`, enabled by default, to keep overlong trailing comments inline in syntax-sensitive positions.
- Added `comment-trailing-extraction-content-aware`, enabled by default, to keep overlong trailing comments inline when enabled standalone comment structure/code detectors or the operator heuristic make extraction unsafe.
- Added `comment-task-marker-mode` with `none`, `no-wrap`, and `hanging` modes, defaulting to `no-wrap` for recognized task-marker comments such as `TODO:`, `FIXME:`, and `HACK:`.
- Added `comment-task-markers` to configure the exact uppercase labels recognized as comment task markers.
- Added TOML-only `per-file-settings` for file-pattern-specific formatter behavior overrides that do not affect file selection or rule selection.
- Added Ruff-style rule settings under `[tool.pydocfmt]`: `select`, `ignore`, `extend-select`, `per-file-ignores`, `extend-per-file-ignores`, `fixable`, `unfixable`, and `extend-fixable`.
- Added `respect-gitignore` for formatter configuration, defaulting to `true`.
- Added explicit config-file support for `--config PATH`, including pyproject-style `[tool.pydocfmt]` files and dedicated top-level pydocfmt TOML files.
- Added Ruff-style path-aware auto-discovery for the closest containing `[tool.pydocfmt]` `pyproject.toml`.
- Added independent comment-formatting settings for standalone paragraph joining, list items, headings, doctests, code fences, block quotes, tables, reStructuredText directives, and disabled-code detection.

#### Documentation

- Added a Zensical-based documentation site pipeline with authored user guides, generated rule and settings references, copied public project/reference documents, strict local builds, and GitHub Pages workflow support.
- Added generated Previous rule and Next rule navigation links at the top of each rule detail page.
- Grouped the generated rules reference by rule category, with prefix-first category links, compact navigation labels, explanatory rule-table labels, category-page explanation links, and per-category all-rules tables.
- Refined the generated settings reference with clearer CLI and TOML guidance, compact summary tables, concise long-default prose, and related rules discovered from rule metadata and documented rule options.
- Added a test-performance audit plan for finding coverage-preserving speedups across the complete test set, fixtures, helpers, and testing approaches.
- Added a settings specification at `docs/public/settings_spec.md`, covering configuration loading, path-pattern bases, per-file settings, and setting behavior notes formerly duplicated in the README and narrower specs.
- Added a file-selection specification at `docs/public/file_selection_spec.md`, including exact defaults, precedence rules, force-exclude behavior, config-relative glob bases, and explicit pydocformatter deviations.
- Added a rule-selection specification at `docs/public/rule_selection_spec.md`, covering rule collection, selectors, fixability, and rule explanation output.
- Added adjacent Markdown documentation for all built-in pydocformatter rules, including Ruff compatibility notes where relevant.
- Clarified that PDF rules ignored under every docstring convention are effectively opt-in by exact rule-code selection, separately from `require-explicit` rules.
- Added a rule implementation specification documenting the implementation, documentation, testing, and release-note touch points for adding rules.
- Added stricter rule and category Markdown checks for canonical preambles, template placeholders, category Code ranges and Options tables, Ruff compatibility references, rule-code references, pipe tables, and rule Options bullets.
- Added source module, rule class, and public class attribute docstrings across the pydocformatter package surface, with code-informed attribute descriptions and guidance against low-information generated docstrings.
- Centralized module attribute documentation in owning module docstrings instead of standalone attribute docstrings.
- Removed helper module alias reexports of PDF definition types.
- Trimmed private implementation docstrings and private attribute entries from public `Attributes` sections.
- Expanded code-informed docstrings for internal rule helpers, docstring parser routines, descriptor methods, and section-normalization utilities.
- Changed non-fixable findings in rule examples to label singular and plural line references explicitly.
- Expanded the PDF101 documentation with explicit behavior notes, setting interactions, safety limits, and verified qualitative examples.
- Expanded the PDF104 and PDF105 documentation with explicit behavior boundaries, safety notes, and verified qualitative examples.
- Expanded the PDF110 and PDF203 documentation with explicit behavior boundaries, setting interactions, safety notes, and verified qualitative examples.
- Added a reusable rule documentation Markdown template at `src/pydocformatter/rules/templates/rule_template.md`.
- Added adjacent documentation for each rule category and a reusable rule category documentation template.
- Added a rule-suppression specification at `docs/public/rule_suppressions.md` with structured examples executed by pytest.
- Added docstrings for public glob matching methods, the dependency-pin check tool, and important configuration, CLI, and file-selection helpers.
- Completed Google-style docstrings for public source APIs and added concise docstrings for private helpers that previously lacked them.

#### Developer workflow

- Applied `docstring-missing-documentation = "has-section"` to `tests/**/test_*.py` in the project pydocformatter configuration instead of blanket-ignoring missing-documentation PDF5xx rules.
- Enabled comment disabled-code and expression detection in the project pydocformatter configuration.
- Added a pytest pre-commit hook that runs the test suite before commits.
- Added a guarded shared pytest working directory for tests that do not request filesystem isolation, with explicit `isolated_cwd` opt-in for tests that need a writable temporary CWD.
- Added pytest coverage that checks the pydocformatter rule tables in `docs/public/ruff_rule_links.md` against actual rule metadata.
- Added pytest coverage that checks Git-tracked Markdown pipe tables for padded cell widths and separator alignment.
- Changed Markdown pipe table checks to enforce PyCharm-style separator rows without outer padding.
- Added a `tools/fix_markdown_tables.py` helper for normalizing Markdown pipe table alignment, and mention it in the pytest failure message for table-style failures.
- Added pytest coverage that executes structured examples from built-in rule Markdown documentation.
- Added pytest coverage that check/fix findings for structured rule Markdown examples stay in correspondence.
- Added exact diagnostic message checks to structured rule Markdown examples.
- Added validation that structured rule Markdown examples use `[output=unchanged]` when the documented output is identical to the input.
- Added validation that built-in rule Markdown documentation includes every template section, including empty `Options` sections.
- Added regression coverage for Ruff-compatible file-selection and per-file-ignore pattern-base behavior.
- Vastly expanded PCF rule tests across comment classification, run boundaries, structure preservation, code detection, width handling, line endings, mixed formatting, syntax-position safety, convergence, idempotence, and rule independence.
- Added targeted PCF edge-case coverage for no-final-newline standalone wrapping, formatting after preserved standalone structures, and current standalone/trailing/directive rule-selection boundaries.
- Vastly expanded PDF category preparation tests across docstring collection, source metadata, semantic sections and entries, protected structures, reflow regions, malformed inputs, and mixed edge cases.
- Added PDF101 regression coverage for short-line joining, protected structures, disabled structure parsing, simple-suite docstrings, and line-ending settings.
- Added representative PDF rule regression coverage for formatting attached attribute docstrings across punctuation, summary-style, source-rewrite, structural, and parsed-entry rule families.
- Added PDF parser regression coverage for generic-looking return, yield, and exception type spellings across Google, NumPy, and reStructuredText/reST conventions.

#### Formatter engine

- Added the LibCST-based rule execution framework with ordered category preprocessing, repeated automatic-fix passes, final read-only checks, and non-convergence diagnostics.
- Added typed PCF comment and PDF docstring category data, together with a shared validated source-edit helper, as the foundation for individual rule implementations.
- Implemented PCF001 standalone-comment formatting, PCF002 trailing-comment spacing, and PCF004 trailing-comment extraction with independent fixes, protected directive handling, tab-expanded widths, stable impossible-width behavior, and exact EOF preservation.
- Added PCF003 comment-directive-normalization for safe marker spacing and syntax around known type and tool directives.
- Added pydocfmt suppression directives for rule findings, including `PCF006` unused-suppression reporting.
- Added suppression support for docstring-owned missing-documentation diagnostics that report on signature and body lines.
- Added opt-in diagnostic `PCF005` to report comments with literal non-ASCII source characters.
- Added PCF support for ty suppression directives by protecting and normalizing `ty: ignore[...]` comments and mixed `type: ignore[ty:...]` payloads.
- Added PCF support for Ruff suppression directives by normalizing `ruff: ignore[...]`, `ruff: disable[...]`, `ruff: enable[...]`, `ruff: file-ignore[...]`, and `ruff: isort: ...` comments.
- Added PCF support for single-line PyCharm directives by protecting and normalizing `noinspection`, `language=`, and `@formatter:on`/`@formatter:off` marker comments.
- Changed PCF004 to keep overlong trailing comments inline by default in decorators, compound statement headers, arguments, and parenthesized or continuation contexts.
- Added shared URL-aware wrapping helpers used by PCF001, PCF004, and PDF101 when `url-aware-wrapping` is enabled.

### Changed

#### Documentation and settings

- Replaced the experimental MkDocs/Material documentation toolchain with a MkDocs-free Zensical build pipeline.
- Standardized public and developer documentation site section headings to sentence case.
- Deferred generated Python API reference pages until Zensical provides native API-reference support that does not require MkDocs.
- Renamed the placeholder API reference page and navigation entry to `API reference`.
- Updated the Ruff compatibility table with current pydocformatter-relevant Ruff rules and bidirectional replacement guidance for comment and docstring rules.
- Expanded the Ruff rule links reference with paired Ruff/pydocformatter configuration guidance, generated-site table styling, rule-code links, and matching project Ruff ignores for pydocformatter-owned comment rules.
- Moved the Ruff rule links page from the Reference URL and navigation group to the end of the Rules group.
- Changed default-value documentation to avoid brittle repeated literals and added consistency checks for remaining generated or tabular default displays.
- Standardized rule `Options` documentation to list only settings that directly affect each rule's findings or fix output.
- Added a tracked rule settings audit and consistency checks so new rule implementations document direct and helper-driven settings usage.
- Changed generated rule site pages to default examples to the Before tab, collapse unchanged Before/After examples, link Options settings to the Settings page, and order footer tag chips by category, rule code, then rule name.
- Renamed the Ruff rule links, rule suppression, and rule implementation documents to `docs/public/ruff_rule_links.md`, `docs/public/rule_suppressions.md`, and `docs/devel/rule_implementation_spec.md`, and refocused the rule selection, file selection, and performance audit specs.
- Split repository documentation sources into public docs under `docs/public/` and private development docs under `docs/devel/`, keeping rule implementation guidance out of the generated public reference site.
- Renamed `PDF508` and `PDF510` user-facing rule names and diagnostics to refer to missing public class and module attribute documentation.
- Changed the default `docstring-convention` from `none` to `pep257`, keeping `none` as the stricter no-convention profile for generic rules that can act without Google, NumPy, or reST parsing.
- Changed convention-dependent rules that have no possible target under a convention to use disabled selection effects, so exact rule-code selection no longer restores rules under `none` or `pep257` when parsed convention entries are unavailable.
- Standardized docstring convention display order as None, PEP257, Google, NumPy, and reST, while keeping lowercase configuration values unchanged.

#### Comment formatting

- Renamed PCF003 from `directive-normalization` to `comment-directive-normalization`, keeping the `PCF003` rule code while clarifying that the rule owns recognized directive marker and payload normalization from `#` onward.

#### Developer workflow

- Renamed the published fixing pre-commit hook to `pydocfmt-fix`, retained `pydocfmt-check`, and documented examples for both published and local uv hook styles.
- Harmonized default tool discovery so Ruff, pydocfmt, and ty use project-root defaults with explicit gitignore-respecting configuration.
- Updated Ruff to 0.15.20 and adjusted check-command output error handling for the current preview lint rules.
- Replaced Black, isort, and mypy with Ruff and ty for project formatting, linting, import sorting, and type checking, while keeping pydocfmt responsible for comment and docstring formatting.
- Moved packaging from setuptools to hatchling, with the package version read from `src/pydocformatter/_version.py` and project license metadata updated to `GPL-3.0-or-later`.
- Changed the Loupe review skill to orchestrate parallel Claude Code and Codex CLI review passes with a timeout-bounded helper script and verified final review synthesis.
- Changed the Loupe reviewer runner to require explicit review scope text, report global and reviewer-specific elapsed times separately, and expose extensible reviewer definitions.
- Changed the Loupe review workflow to snapshot temporary diff and reviewer-output artifacts, use a 30000-token capture budget, and recover truncated reviewer output from the runner's `--output` artifact instead of rerunning reviewers.
- Changed the Loupe review workflow to require full small-diff artifact contents in chat instead of guessed preview ranges.
- Changed the Loupe review workflow to clean successful temporary artifact directories by deleting only known artifact files before removing the empty directory.
- Moved dependency-pin validation into pytest and removed the dedicated dependency-pin pre-commit hook.
- Updated pytest to 9.1.1.
- Updated ty to 0.0.57.
- Changed the Loupe final review format to keep one continuous finding number sequence across all reviewer sections.
- Changed Loupe reviewer definitions to declare optional required executables instead of deriving launch requirements from reviewer display names.
- Changed Loupe reviewer launch planning to attach helper dependency failures directly to planned reviewer runs in one cached availability pass.
- Changed pytest to treat warnings as errors by default.
- Changed pytest to use pytest-xdist multiprocessing by default for local, pre-commit, and CI test runs.
- Reduced brittle test snapshots of built-in rule inventories while preserving coverage of rule ordering, opt-in selection behavior, and broad-profile differences.
- Collected return, yield, and raise facts during PDF preparation so PDF50x value-documentation rules reuse the existing definition traversal instead of walking documented function bodies again.
- Shared setup and initial check work across structured rule Markdown example assertions to reduce pytest runtime.
- Cached rule-context source text and source lines per module state to reduce repeated LibCST source regeneration during checks.
- Reused cached source lines and line bounds for rule-based source edits to avoid repeated line splitting.
- Skipped fix-mode LibCST source comparison for same-module no-op fixes.
- Shared LibCST position metadata across selected rule categories for each module state.
- Deferred expensive decorator and enum-base metadata checks in selected PDF rules to reduce check runtime without changing diagnostics.
- Skipped LibCST qualified-name metadata resolution for configured decorator and enum-base names that cannot match syntactically or through a relevant import alias.
- Resolved configured decorator, enum-base, and yield-container names from cached top-level bindings before falling back to LibCST qualified-name metadata.
- Lazily cached PDF value-documentation facts to avoid repeated return, yield, and raise body walks across PDF502 through PDF507 without adding work for unrelated PDF rule selections.
- Resolved PCF parent metadata lazily so selections such as `PCF001` avoid syntax-parent work needed only by trailing-comment extraction.
- Skipped fix passes when an initial clean check proves there are no effectively fixable findings.
- Skipped PCF category CST traversal for source files that cannot contain Python comments because they have no `#` character.
- Seeded the initial rule context from already-read LibCST-aligned source text to avoid redundant LibCST source regeneration for unchanged modules.
- Changed internal rule execution to use canonical `RuleViolation` values from `violations()` hooks, with runner-owned suppression filtering, configured fixability, source-edit application, and consistency validation.
- Required explicit constructor values for important internal dataclass fields that previously supplied implicit defaults.
- Renamed selected built-in rule names, rule definition files, and rule classes for clearer public metadata while keeping rule codes and selection behavior unchanged.
- Reorganized rule helper modules so whole-rule logic lives in individual rule files while shared helper modules contain reusable source, layout, decorator, section-edit, and reStructuredText field primitives.
- Moved reusable docstring section and reStructuredText field metadata out of `PDF.py` into a focused helper module used by the parser, section rules, and documentation helpers.

#### Project identity

- Reset the planned next release to `1.0.0` and present pydocformatter as a new standalone Ruff-style formatter.

#### Docstring formatting

- Changed `PDF304` to check all parsed docstring summaries, including module, class, and attached attribute docstrings.
- Changed `PDF500` to be enabled by broad rule selections under the NumPy docstring convention.
- Changed automatic fixing to stop after 20 fix iterations.
- Added instance-specific diagnostic messages for parameter consistency, section-style, and selected summary-style rule findings where the offending parameter, section, function, word, or span length is useful context.
- Changed Sphinx-style field parsing to the explicit `docstring-convention = "rest"` mode. The removed `docstring_parse_sphinx_fields` setting now raises an unknown-setting error; set the reST convention to parse and protect `:param:`/`:rtype:` style fields.
- Changed broad convention-based rule defaults so `PDF500` follows Ruff's `D417` convention behavior while `PDF403` remains enabled by default under the Google convention.
- Changed `PDF507` to be ignored by broad rule selections under every docstring convention, making the direct-raise-only exception documentation check exact-selection opt-in.
- Changed missing-documentation configuration from PDF500-specific `docstring-missing-parameter-*` settings to shared `docstring-missing-documentation*` settings used by missing parameter, return, yield, and exception documentation rules.
- Renumbered section-style rules so `PDF401` and `PDF402` are section-name normalization rules, `PDF403` is section-name trailing-content, `PDF404` is section-name trailing-colon, `PDF405` is section underline-format, `PDF406` is empty-section, `PDF407` is section-order, `PDF408` is repeated-section, and `PDF409` is docstring-entry-spacing, and aligned built-in rule filenames and class names with rule metadata.
- Implemented `PDF502` through `PDF507`, replacing their previous stub behavior with return, yield, and exception documentation consistency diagnostics.
- Implemented `PDF500` and `PDF501`, replacing their previous stub behavior with parsed docstring/signature parameter consistency diagnostics and configurable PDF500 activation.
- Implemented `PDF400` through `PDF409`, replacing their previous stub behavior with convention-aware section-name normalization fixes, Google section trailing-content fixes, NumPy underline normalization, convention entry spacing fixes, and section content/order diagnostics.
- Changed Google `Warning` and `Warnings` section parsing to treat them as admonition-style fields, while Google `Warns` and NumPy `Warns`/`Warnings` remain warning-exception sections.
- Implemented `PDF302` through `PDF305`, replacing their previous stub behavior with first-summary-line diagnostics, safe first-word capitalization fixes, and Ruff-style convention-selection effects.
- Changed summary first-word normalization to preserve Unicode alphanumeric characters when removing punctuation, avoiding false positives such as `This\u00e9`.
- Implemented `PDF202`, `PDF300`, and `PDF301`, replacing their previous stub behavior with empty-docstring diagnostics, safe summary-punctuation fixes, and parser-recognized section and reST-field skips for the active convention.
- Changed `PDF000` to normalize safe `\n` and `\t` whitespace escape spellings in docstrings and remove plain no-op `u`/`U` docstring prefixes, including non-concatenated docstrings, without changing evaluated docstring values.
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

#### Repository checks

- Added missing docstring summaries and documentation sections so repository `pydocfmt check` passes.
- Added a rule documentation check that verifies docstring-convention ignored and disabled notices match rule metadata.
- Fixed nondeterministic pytest parametrization order that could make xdist workers report different collected tests.

#### Documentation

- Fixed generated documentation cross-links and project page headings that still used title case, and removed the manual table of contents from the public contributing guide.
- Fixed generated docs to convert structured `pydocfmt-example` blocks in every copied Markdown source, including public reference docs such as the rule suppressions guide.
- Fixed generated docs to keep adjacent structured examples in separate tab groups.
- Fixed generated project documentation to preserve label-prefixed Markdown lists as bullet lists in the final Zensical site.

#### Docstring formatting

- Fixed import-aware configured decorator, enum-base, and yield-container matching to use source-position-aware top-level bindings so later rebindings do not affect earlier uses and later imports override earlier local assignments.
- Fixed configured decorator, enum-base, and yield-container matching for guarded and function-local imports while avoiding false matches from local shadowing, mismatched canonical module aliases, and top-level `for`/`with`/`except` binders.
- Fixed configured decorator matching so dynamic call receivers such as `@typing().overload` are not treated as exact static decorator names.
- Fixed attached attribute docstring checks to avoid duplicate findings for repeated assignment target names and to report private attached attribute docstrings in source order.
- Fixed `PDF7xx` typed entry checks to evaluate every name in parsed NumPy multi-name parameter and attribute entries.
- Fixed import-aware decorator and typed-entry matching to avoid local-shadow false positives, pair reST variadic parameter value/type fields, and evaluate repeated reST typed entries in source order.
- Fixed `PDF7xx` typed reST checks to validate inline and paired type fields independently and report type-specific diagnostics on the field that supplies the type.
- Fixed `PDF7xx` typed mismatch checks to compare safe import aliases consistently, recognize quoted yield container aliases, and report type diagnostics in source order.

- Fixed `PDF101` docstring reflow to avoid merging lowercase and numeric colon-ended label lines with preceding prose.
- Fixed `PDF413` to apply mixed parsed and unparsed section-name colon fixes in source order and to avoid removing colons from prose-adjacent lowercase continuation lines or capitalized labels inside NumPy section prose.
- Fixed `PDF304` and `PDF310` to skip mixed-case first words such as `iOS` and `eBay` instead of over-capitalizing them.
- Fixed `PDF308` through `PDF310` source edits when the configured output line ending differs from the current file line endings.
- Fixed `PDF308` through `PDF310` to report non-fixable findings instead of corrupting source for docstrings with mixed physical line endings.

- Ignored PDF500 through PDF506 under the `none` and `pep257` docstring conventions for broad selections, while keeping exact-selected PDF500, PDF502, PDF504, and PDF506 inert so missing-documentation modes do not report convention-targeted findings without active convention parsing.
- Fixed `PDF306` and `PDF307` to skip reStructuredText type-only parameter and attribute fields instead of treating type names as generic prose descriptions.
- Fixed same-line docstring reflow to keep wrapped summaries as one summary instead of letting later blank-line and punctuation fixes split and punctuate the sentence mid-summary.
- Fixed `PDF200` to preserve one blank line between adjacent Google and NumPy sections after collapsing excess blank lines, matching `PDF201` missing-section-separator insertion.
- Fixed `PDF409` and `PDF410` to preserve Google exception-entry parentheticals, and fixed Google and NumPy parsing to keep malformed exception-like prose continuations from being normalized as separate entries.
- Fixed Google return and yield section parsing to treat bare `None` and `None.` entries as `None:` entries.
- Fixed `PDF501` to allow documented keys from same-module class-based `TypedDict` definitions used in `**kwargs: Unpack[...]` parameters, keep conservative suppression for unresolved unpack targets, and continue reporting unrelated documented names when the local keys are known.
- Fixed PDF502 and PDF503 to treat bare `yield` and `yield None` as generator behavior when classifying generator stop values, and fixed PDF506/PDF507 qualified exception diagnostics and matching.
- Fixed PDF500 and PDF501 to recognize typed reST parameter fields such as `:param int value:` and `:type value:` as documentation for the final parameter name.
- Fixed PDF411 to normalize type-like spacing in reST `:vartype name:` attribute type fields.
- Fixed reST fields with protected continuation bodies, such as indented lists, to count as non-empty field content without reflowing the protected body.
- Fixed `PDF101` reST field reflow to preserve protected continuation bodies after inline field descriptions and reflow later prose in the same reST field.
- Fixed `PDF408` to allow Google `Warning`/`Warnings` admonition sections alongside the distinct `Warns` warning-documentation section.
- Fixed `PDF408` to allow NumPy `Warning`/`Warnings` admonition sections alongside the distinct `Warn`/`Warns` warning-documentation section.
- Fixed `PDF403` to split Google section trailing content when whitespace appears before the section-name colon.
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

#### CLI

- Fixed `parallelism` worker resolution to cap Windows process pools at the platform-supported maximum.

- Reorganized `pydocfmt check --help` into Ruff-inspired argument groups for options, rule selection, and file selection.
- Moved argparse helpers from `pydocformatter.cli.utils` to `pydocformatter.utils.argparser`.
- Refactored parser setup to share global option definitions and isolate version/help subcommand construction.
- Updated `pydocfmt check --help` argument ordering and metavars to keep help, settings output, and documentation consistent.
- Rule and file-selection list options now use comma-separated CLI values, such as `--select PDF,PCF` and `--include "*.py,*.pyi"`.
- `pydocfmt` now formats both docstrings and comments in one run.
- `pydocfmt` now exposes command-line overrides for Ruff-style rule settings.
- `pydocfmt` now defaults to formatting the current directory when no files or directories are specified.
- `--include`, `--extend-include`, `--exclude`, and `--extend-exclude` now accept multiple glob values in one option usage (e.g. `--include *.py *.pyi`).
- Check summaries now report fixed and remaining rule-check counts separately, including fixable remaining counts for diff output.

- Formatter read, decode, and write errors now affect check exit status without being reported as rule findings.
- `pydocfmt check` now reports invalid nested path-specific configuration without producing a traceback.
- `--force-exclude` now applies to virtual paths supplied through `--stdin-filename`.
- `pydocfmt check` now prints `All checks passed!` to the configured output when no diagnostics are found.
- Operational errors no longer produce an `All checks passed!` success message.
- Output-file setup errors are now reported without converting unrelated `OSError`s raised while producing diagnostics.
- `pydocfmt` now skips files that fail UTF-8 decoding, emits an operational error in grouped output, and continues processing remaining files instead of crashing.
- Empty include glob patterns now report configuration or argument errors instead of crashing with a traceback.
- `--help` now works even when the current `pyproject.toml` contains invalid pydocformatter configuration.
- Missing or unreadable files now emit an operational error in grouped output and processing continues instead of crashing.
- `--output-file` now creates only the direct parent directory instead of recursively creating nested output directories.
- Path-aware rule-selection operational errors are now reported once for equivalent resolved profiles instead of once per selected directory.

#### Comment formatting

- Fixed `PCF001` standalone-line joining to avoid merging colon-ended label comments, including lowercase and numeric labels, with adjacent prose, while still allowing lowercase multi-word colon continuations to complete unfinished preceding prose.
- Fixed task-marker comment matching to reuse compiled marker patterns and share no-wrap normalization between default task-marker handling and code-like hanging task-marker payloads.

- Fixed source suppression handling for PCF findings, PCF006 self-suppression, disabled-rule selectors, and pydocfmt directives with trailing reasons.
- Fixed PCF002 to normalize the code-to-`#` delimiter for trailing type comments and tool directives while preserving directive text from `#` onward.
- Fixed PCF002 to strip terminal whitespace from trailing type comments and tool directives when directive normalization is not selected.
- Fixed PCF003 to normalize standalone recognized directives and safe directive payload syntax, including directive-head casing, colon spacing, and machine-readable comma lists.
- Fixed PCF003 to preserve trailing code-to-`#` delimiter spacing so PCF002 and PCF003 no longer double-report a directive whose only defect is the code-to-`#` gap.
- Fixed PCF004 to treat leading `and`, `or`, and `not` as ordinary prose instead of always suppressing trailing-comment extraction.
- Fixed PCF004 content-aware extraction to honor the disabled-code indentation heuristic for trailing comments.
- Fixed syntax-aware trailing-comment extraction to keep comments inline on `except*` headers and one-line compound suites.
- Fixed PCF003 directive normalization to remove trailing directive whitespace.
- Fixed PCF003 directive normalization to avoid adding trailing whitespace for empty colon payloads.

#### Rule performance

- Shared top-level binding collection between configured-name matching and type-expression alias normalization, and shared simple-docstring source maps across direct docstring text-edit planners.
- Moved configured-name binding caching onto prepared PDF rule data instead of process-global state, and reused the shared simple-docstring source map for section direct edits.
- Fixed configured-name binding caching to avoid retaining LibCST metadata wrappers, removed duplicate PDF411 direct-edit planning, and removed the obsolete value-documentation body-walk fallback.
- Fixed PDF000, PDF100, and PDF107 to avoid unnecessary simple-string fragment reconstruction for already-normal literals, repeated indentation rewrites, and source-safe opening-quote moves.
- Fixed PCF004 previous-comment boundary checks, PDF411 repeated type-like normalization, and PDF501 TypedDict key lookup to avoid repeated or unnecessary rule-local work.
- Fixed PDF308, PDF309, and PDF310 entry-description checks to avoid repeated whole-docstring fix validation for source-safe punctuation and capitalization edits.
- Fixed PDF101 and PDF411 to avoid repeated source-fragment reconstruction for common source-safe docstring edits.
- Fixed PDF401 and PDF409 to use direct source edits for safely mapped section and entry replacements, and fixed PCF004 to classify syntax-sensitive trailing comments during comment collection instead of resolving parent metadata during the rule check.

#### Developer workflow

- Fixed the Markdown table normalizer to report non-fixable validation failures, normalize to header-row indentation while preserving existing line endings, handle escaped pipes, preserve indented code blocks, and follow stricter fenced-code parsing.

- Included top-level Markdown documentation files from `docs/` in source distributions.
- Fixed rule Markdown example coverage so every built-in rule must provide at least one executed structured example.
- Changed the mypy pre-commit hook to use the locked project environment through `uv run mypy`.
- Split rule registration decorators from rule collection discovery so rule category modules can be imported directly without eager collection initialization.
- Added an explicit test package boundary and moved reusable PCF test helpers out of `conftest.py`, allowing mypy to check multiple directory-scoped pytest configurations without exclusions.
- Organized rule tests by category and rule code under `tests/rules/`.

#### Rule internals

- Consolidated raised-exception name parsing used by PDF preparation and value-documentation stub detection into one helper.
- Fixed Loupe reviewer elapsed-time accounting to start individual reviewer timers at process launch.
- Fixed Loupe reviewer timeout cleanup to let collector threads own subprocess completion while the main thread only signals timed-out process groups.
- Fixed Loupe reviewer timeout handling to avoid blocking on detached child processes that inherit reviewer output handles.
- Fixed Loupe reviewer availability checks to match the shell environment used for reviewer launch.
- Fixed Loupe reviewer dependency checks to skip missing Codex reviewers and fail launchable reviewers clearly when helper executables such as `jq` are missing.
- Fixed Loupe reviewer runs to fail clearly instead of reporting success when no reviewers are launchable.

#### Formatter engine

- Fixed rule-runner line-target matching to normalize duplicate finding and planned-change targets consistently and keep suppression filtering owned by the suppression index.
- Fixed rule line-target validation to reject boolean values instead of accepting `True` as line `1`.
- Fixed `PDF101` variable-width source wrapping to use equivalent greedy wrapping and avoid quadratic runtime on long non-URL docstring paragraphs.
- Fixed repeated PDF docstring owner lookups to use cached identity-based lookup instead of rescanning prepared docstrings.
- Fixed `PDF508` and `PDF510` missing-attribute documentation checks to respect inert docstring conventions, private package paths, and per-target tuple-unpacking lines.
- Fixed `PDF510` module privacy checks to ignore underscore-prefixed filesystem ancestors that are not part of the importable package path.
- Fixed `PDF508` and `PDF510` attached attribute docstring suppressions so an ignore on one documented attribute does not hide missing documentation for unrelated attributes.
- Fixed PDF attribute documentation helper caches to expose read-only prepared data and avoid repeated owner attribute scans.
- Fixed URL-aware wrapping to avoid recursive crashes on long URL-containing paragraphs and to fall back to greedy wrapping when balanced wrapping exceeds its search budget.

- Added `Rule`, `RuleFinding`, and `FormatterResult` data structures for reporting remaining rule issues after fixes.
- Changed rule fixes to preserve untouched mixed line endings instead of normalizing the complete file after any source change.
- Formatter results now carry the formatted source alongside path, modification, finding, and error data.
- `SourceFormatResult` now carries the original source alongside the possibly formatted source.
- Formatter internals now require formatting controls such as line length, line endings, and indentation settings as explicit keyword-only arguments.
- Formatter functions now receive resolved `CheckSettings` directly.
- Generated Google-style docstring section indentation is now configurable while preserving the existing base docstring indentation.
- Check-mode output now includes docstring and comment line locations, emitted once per subject per file with compressed consecutive ranges.

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

- Check mode now reports comment formatting diagnostics against original input line numbers.
- Empty standalone comment separator lines are now preserved during comment formatting.
- Preserved untouched line endings when formatting only selected docstring or comment spans.

#### Rule documentation

- Aligned category documentation checks with the updated rule category template section order, including the new `Options` section.
- Fixed the PDF category options table to use the repository's minimal PyCharm-style Markdown table alignment.
- Expanded the PCF001, PCF002, and PCF004 rule examples to demonstrate common spacing, wrapping, structure, protection, boundary, and extraction behavior.
- Documented that PDF110 separator fallback can add a leading or trailing space to the evaluated `__doc__` value when value-preserving escaping is impossible.
- Documented that PDF101 delimiter-aware wrapping does not reserve width for unchanged source after a same-line closing docstring delimiter.
- Rephrased rule example results to describe the effect of applying each rule.
- Kept planned PDF rule examples in ordinary Python fences until their formatter behavior is implemented and can be tested as structured examples.

#### Rule framework

- Split rule models, authoring contracts, execution, and line-ending utilities into focused modules while keeping formatter file and source orchestration separate.
- Hardened built-in rule authoring around helper-based `RuleViolation` construction, import-time `violations()` signature validation, direct rule-test validation, and static tests that reject direct finding/fix construction in built-in rule modules.
- Moved shared modern-rule text wrapping and display-width helpers into a neutral rules helper module.
- Moved rule codes and selectors into `pydocformatter.rules.codes` and added immutable, hashable setting-effect metadata to rule definitions.
- Changed internal PDF and PCF classification types from string-compatible enums to ordinary enums.
- Renamed PCF001 to `standalone-comment-formatting` and PCF002 to `trailing-comment-spacing` to reflect their independent comment actions.
- Required rule and category definitions to explicitly provide `setting_effects` and `url` metadata, including empty or absent values.

- Category preprocessing data is now refreshed after an earlier rule changes the module while remaining shared by later rules processing the same module version.
- UTF-8 byte order marks are now preserved when automatic fixes rewrite source, and fixes that converge on the final permitted iteration no longer report a non-convergence error.
- Preserved exact rule-code overrides for setting-ignored rules when a higher-priority broad `extend-select` also selects the rule.

#### Configuration

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

- Malformed pydocformatter config tables are now consistently rejected, including falsy non-table values.

#### File discovery

- `--show-files` now reports directories pruned by exclude patterns, such as `.venv`.
- File-selection helpers now require a path-aware settings resolver instead of accepting raw `CheckSettings`.
- `pydocfmt` now applies gitignore-based filtering when `respect-gitignore` is enabled, and aborts file selection if gitignore checks cannot be executed.
- `force-exclude` now follows Ruff-style explicit-file behavior by applying exclude patterns while still bypassing include and gitignore filtering.
- File selection now resolves include, exclude, and per-file-ignore patterns relative to their setting source, including closest auto config directories and cwd-relative CLI overrides.
- Explicit `--config PATH` files now disable auto-discovered configuration and only one explicit config file is accepted, while inline `--config` overrides still layer over auto-discovered configuration.
- Gitignore filtering now follows the `respect-gitignore` setting resolved for the current working directory.
- Gitignore filtering now handles symlinked directory traversal by querying git with real paths while preserving symlinked display paths.
- File selection now deduplicates paths that resolve to the same physical file and displays real filesystem paths as absolute normalized paths.

- Empty exclude glob patterns are now rejected as invalid configuration or arguments.
- Slash-containing exclude patterns that name directories now exclude descendant files when the directory is passed directly or a child file is force-filtered.
- Gitignore filtering now handles paths containing surrogate-escaped bytes.

#### Architecture

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

#### Developer dependencies

- Updated mypy from 1.20.2 to 2.1.0.

#### Tests

- Added a session-wide temporary configuration boundary and per-test working directories so tests no longer inherit ancestor `[tool.pydocfmt]` configuration, removing latent coupling for CLI and file-selection tests.
- Made the README settings-documentation test locate `README.md` relative to the test file instead of the current working directory.

#### Documentation

- Updated README, contributing, release, pull request, and file-selection docs for the single-command workflow and latest file-selection behavior.

#### Rule selection

- Rule and fixability selectors now resolve conflicts by Ruff-style source priority before selector specificity, with disabling selectors winning equal-priority and equal-specificity ties.
- Per-file ignores now suppress every selected matching rule for matching files, without comparing the ignore selector specificity against the selector that enabled the rule.
- Per-file ignore patterns now support Ruff-style leading `!` negation.
- Repeated `--per-file-ignores` and `--extend-per-file-ignores` entries for the same pattern now append selector lists within the command-line layer.

### Removed

#### Configuration

- Removed `docstring-parse-sphinx-fields`; use `docstring-convention = "rest"` to parse reStructuredText/Sphinx fields semantically.

#### Documentation

- Removed the internal empirical Ruff file-selection design notes at `docs/ruff_file_selection_spec.md`.

#### CLI

- Removed top-level formatting and check forms such as `pydocfmt` and `pydocfmt --check`; use `pydocfmt check --fix` or `pydocfmt check`.

#### Architecture

- Removed the separate comment-formatting command and merged comment formatting into `pydocfmt`.
- Removed tool-specific TOML configuration tables; nested formatter tables are now configuration errors.
- Removed redundant shared CLI, formatter-type, and comment-command modules.
- Removed trivial `SettingsSchema` convenience helpers for field/key definition maps and CLI flag flattening.
- Removed unused rule-selector definition exports from check settings metadata.

#### Developer dependencies

- Removed the unused `build` and `twine` dev dependencies now that package build and publish workflows use uv directly.

#### Developer workflow

- Removed the Loupe Codex skill from this repository after moving it to the standalone `pallgeuer/la-dev-codex-plugins` marketplace repository.
- Removed timing-sensitive Loupe reviewer subprocess tests from the fast pytest suite.

#### Breaking configuration migration

- Removed the old `[tool.pydocformatter]` config table from settings resolution.
- Removed underscore aliases for settings such as `line_length`; only hyphenated keys are valid.
- Removed regex include/exclude semantics in favor of glob-list file selection.
- Removed utility file-selection wrappers from `pydocformatter.utils`; use `pydocformatter.file_selection.select_files` directly.

---

## v1.0.0

[//]: # (TODO: Use this section when the current unreleased changelog becomes the v1.0.0 release, which hasn't been released yet)

### Added

### Changed

### Fixed

### Removed
