# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and pydocformatter follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Release diffs

- **Unreleased:** <https://github.com/pallgeuer/pydocformatter/compare/v1.0.0...HEAD>
- **v1.0.0:** <https://github.com/pallgeuer/pydocformatter/compare/v0.2.0...v1.0.0>
- **v0.2.0:** <https://github.com/pallgeuer/pydocformatter/releases/tag/v0.2.0>

---

## Unreleased

### Added

- **Rule selection:**
  - Added exact canonical rule-name selectors across selection, fixability, explicit-selection, per-file-ignore, CLI, inline-configuration, and settings-profile inputs, with catalog-wide name validation and deterministic lookup.
- **Suppression policies:**
  - Added PCF102 and PCF103 as explicitly selected, mutually incompatible policies for name-only or code-only bracketed pydocfmt and Ruff suppression comments, including safe local conversions and diagnostic-only Ruff findings.
- **Docstring diagnostics:**
  - Added effectively opt-in PDF528 to report module and class attribute documentation that does not follow the complete first-seen source inventory order.
  - Added PDF418 to report high-confidence malformed reStructuredText directive introducers while preserving their bodies as structured content for other docstring rules.
  - Added PDF417 to validate NumPy single-value and multiple-value `Returns` entry structure.
  - Added usually-fixable PDF527 to enforce signature variadic markers in Google and NumPy documentation and bare parameter names in reStructuredText value and type fields.
  - Added `docstring-include-assertion-errors` so PDF506 and PDF507 can optionally treat syntactic assertions as possible `AssertionError` occurrences.
  - Added PDF312 to report exact content-free return, yield, exception, warning, and method descriptions.
  - Added PDF416 to safely normalize trailing periods, redundant outer parentheses, and lowercase `none` in parsed docstring type slots.
  - Added PDF213 to report complete evaluated docstrings that match configurable placeholder markers.
  - Added PDF723 to report method entries without prose descriptions in class-owned Google and NumPy docstrings.
  - Added PDF212 to report nonempty primary and supported attached attribute docstrings without a parsed top-level summary.
  - Added PDF526 to report parsed parameter documentation that does not follow function signature order.
  - Added PDF414 and PDF415 to report high-confidence malformed Google, NumPy, and reStructuredText entry syntax and Google or NumPy entry indentation without unsafe fixes.
  - Added PDF720 and PDF721 to report named raised-exception and emitted-warning entries without prose descriptions.
  - Added PDF722 to report reStructuredText type fields without one-to-one corresponding value fields.
- **Unicode safety:**
  - Added PDF004 and PCF201 to report explicit suspicious bidi, invisible-format, control, and separator characters in evaluated docstrings and literal comments, with exact fixes for nonbreaking indentation spaces.
- **Persistent caching:**
  - Added strict persistent clean-proof caching for disk-backed checks and fixes, with complete source hashing, semantic analysis-setting and final-rule-code invalidation, shared invocation-local analysis fingerprints, engine/path invalidation, miss-only process execution, bounded parent-side probes, and source-free warm results.
  - Added `cache` and `cache-dir` settings, `--cache`/`--no-cache`, `--cache-dir`, opt-in `--cache-stats`, safe project cache self-pruning, and the ownership-checked `pydocfmt clean` command with its own `--cache-dir` override.
  - Added a dedicated public cache reference covering validation, population, mode reuse, storage, cleanup, failures, trust, statistics, and performance expectations.

### Changed

- **Compatibility:**
  - Documented support for Python 3.11 and newer on Ubuntu 20.04 and newer and macOS 14 and newer, best-effort support for other POSIX Linux systems, and no native Windows or WSL support.
  - Clarified that CPython is officially supported, PyPy and GraalPy compatibility is intended but unverified due to LibCST native-parser packaging, and Jython and IronPython are unsupported.
  - Added blocking glibc, musl, x64, ARM64, Intel macOS, and ARM64 macOS test coverage across Python 3.11 through 3.14.
- **Breaking PCF rule-code reassignment:**
  - Reorganized PCF codes into general comment formatting (`PCF0xx`), directives and suppressions (`PCF1xx`), and ASCII/Unicode character policies (`PCF2xx`). Canonical rule-name selectors remain unchanged, while old code selectors are not retained as aliases.

| Previous code | New code | Rule name                            |
|---------------|----------|--------------------------------------|
| `PCF001`      | `PCF000` | `standalone-comment-formatting`      |
| `PCF002`      | `PCF001` | `trailing-comment-spacing`           |
| `PCF004`      | `PCF002` | `trailing-comment-extraction`        |
| `PCF003`      | `PCF100` | `comment-directive-normalization`    |
| `PCF006`      | `PCF101` | `unused-suppression`                 |
| `PCF008`      | `PCF102` | `rule-codes-in-suppression-comments` |
| `PCF009`      | `PCF103` | `rule-names-in-suppression-comments` |
| `PCF005`      | `PCF200` | `comment-ascii-only`                 |
| `PCF007`      | `PCF201` | `comment-suspicious-unicode`         |

- **Rule stability:**
  - Marked every current built-in rule as stable since 1.1.0 after auditing direct changes and observable shared execution, source-editing, selection, and suppression changes since v1.0.0.
- **Fix execution:**
  - Increased the maximum number of automatic fix iterations from 20 to 30.
  - Made canonical source-edit application return both the reparsed module and exact edited source, centralized direct-rule test contexts with production-equivalent position remapping and source bounds, and kept the final LibCST module internal to rule execution.
- **Documentation:**
  - Renamed the generated rule index label `Convention-explicit` to `Convention opt-in` and the public rule compatibility table column `Explicit` to `Require explicit`.
- **Developer documentation:**
  - Reran and refreshed the complete rule performance audit for all 141 tracked rules, including current inventory, measurements, source analysis, and the retained class attached-attribute and exception-inventory optimizations.
  - Corrected the rule settings audit to distinguish disabled rules from rules ignored only by broad selectors, with metadata-backed regression coverage.
  - Distinguished convention opt-in policies from `require-explicit`, with exhaustive conflict-free convention profiles and meaningful explicit-selection defaults enforced by regression tests.
- **Developer tooling:**
  - Expanded the repository's own pydocformatter policy with attribute declaration-order checks, constructor-assigned attribute coverage, joined comment reflow, hanging task-marker formatting, and consistent forced exclusions.
  - Updated the fixed documentation, test, and development dependency pins and migrated Ruff selectors and suppressions to the human-readable names supported by Ruff 0.16.
  - Replaced the repository-local Markdown table formatter, release checksum generator, and pytest working-directory isolation fixtures with the shared `la-dev-codex-plugins` implementations.
  - Strengthened semantic Markdown table tests with full-document parsing and normalized all generated documentation tables to the shared canonical style.
- **Internal cleanup:**
  - Centralized setting-effect resolution with disabled precedence across runtime rule selection, documentation generation, and metadata-backed tests.
  - Separated reusable docstring source editing, literal rendering, section spacing, and comment formatting from rule category preparation, and returned PDF312-specific phrase matching to its rule module.
- **Rule selection:**
  - Resolved exact code/name aliases to one concrete rule identity with full-code selection strength and shared cache identity, while distinguishing unknown canonical names from malformed selectors.
  - Made stronger selectors silently override incompatible weaker selections by source priority and specificity, while preserving deterministic collection-order errors that name only the equal-strength blockers.
  - Rejected code-shaped canonical rule names and catalogs where one full rule code would also broadly select another rule.
- **Rule suppressions:**
  - Accepted mixed-case canonical names in bracketed pydocfmt `ignore` and `file-ignore` comments, semantically deduplicated exact code/name aliases by first occurrence, and extended PCF100 and PCF101 to consume the shared directive model.
  - Collapsed repeated normalized pydocfmt selectors before suppression and PCF101 auditing so check-only and fixing runs preserve coverage without duplicate unused-selector findings.
  - Made inline suppressions after any component token of an implicitly concatenated docstring cover the complete expression for PDF findings while preserving line-local PCF coverage and existing local and standalone attachment boundaries.
  - Collected bracket directives and source suppressions in one source traversal per pass, made directive self-suppression an explicit rule-metadata capability for PCF102 and PCF103, and kept their policy fixes independent from PCF100's general deduplication.
- **Docstring diagnostics:**
  - Made PDF206 require one blank line before a first nested function or class definition while retaining no blank line before ordinary function-body statements, matching Ruff formatter output while intentionally reporting the zero-blank nested-definition case accepted by D202.
  - Standardized rule metadata and instance messages, added concrete normalization rewrites, and made atomic grouped fixes fall back to rule metadata when they contain distinct diagnostics.
  - Made strict trailing-period rules PDF300 and PDF308 mutually exclusive with their terminal-punctuation alternatives PDF301 and PDF309, with broad convention profiles choosing one alternative consistently.
  - Made PDF409 solely responsible for parsed entry spacing while PDF410 now edits only parser-mapped semantic exception and warning name lists, so both independent fixes compose without overlapping replacements or rule-local syntax reparsing.
  - Made each private attribute documentation placement policy incompatible with every overlapping or opposing policy, and changed PDF523 and PDF525 to convention opt-in rules so broad profiles remain conflict-free.
  - Included proven members from final effective immutable literal `__slots__` declarations in class attribute documentation coverage, placement, description, and type checks while retaining later real assignments and annotations as documentation attachment and type sources.
  - Made PDF414 sometimes fixable for deterministic Google and NumPy separators and reStructuredText closing delimiters while leaving missing or unexpected field arguments diagnostic-only, and made PDF415 usually fixable for mapped convention indentation.
  - Made PDF701, PDF705, PDF709, PDF713, and PDF717 sometimes fixable from available code annotations, including canonical paired reStructuredText type fields.
  - Kept PDF713's enum-like no-type inversion for Google and reStructuredText entries while letting NumPy grammar take precedence for typed enum entries.
  - Extended PDF506 and PDF507 with one ordered exception-occurrence inventory that preserves direct-raise behavior while supporting optional assertion-derived `AssertionError`.
  - Made PDF300, PDF301, PDF308, and PDF309 safely replace terminal semicolons and standalone commas with periods when the source mapping is exact, while leaving commas before recognized structured content diagnostic-only.
  - Preserved commas before protected nested content owned by reStructuredText field entries, including lists, fences, doctests, directives, literal blocks, tables, headings, and block quotes.
  - Made PDF202 target the complete physical empty-docstring expression, including delimiter-only closing lines, consistently with other whole-docstring diagnostics.
  - Parse docstrings after collecting complete owner parameter, attribute, and method inventories, and keep invalid standard reStructuredText field arity structural but outside semantic entry collections.
  - Required reStructuredText value fields for parameter, return, yield, and attribute documentation coverage, while keeping orphan type fields available to type, duplicate, empty, extraneous, and PDF722 checks without indirect missing-description findings.
- **Command performance:**
  - Indexed attached attribute docstrings by owner for PDF516, PDF518, and PDF522, and adaptively indexed large PDF506 and PDF507 exception inventories while preserving source order and qualified-name matching semantics.
  - Centralized lazy entry-description target caches for PDF308, PDF309, and PDF310 so PDF308 and PDF309 share each parsed entry's following structural block and terminal target once per analyzed file, retaining a measured 31% improvement on a 10,000-entry punctuation benchmark without regressing smaller cases.
  - Normalized the configured PDF213 placeholder marker inventory once per analyzed file instead of once per docstring.
  - Reused successfully parsed configuration documents, closest-config discovery results, and resolved source profiles within each invocation.
  - Reduced directory-walk resolver calls and repeated cache-root, glob-segment, and literal-pattern preparation without changing file-selection semantics.
  - Preindexed direct class attributes and methods once for malformed-entry confidence and skipped those inventories for conventions that cannot use them.
  - Centralized semantic reStructuredText field-family metadata and paired all supported value/type families in one pass for orphan-field checks.
  - Removed redundant token validation from AST-backed type comparison while preserving conservative comment rejection, parser recursion handling, and iterative AST traversal.
- **Caching performance:**
  - Reused resolved package ancestry and canonical sibling path encodings within each invocation while preserving exact cache identities and rule-facing path semantics.
  - Batched complete-source proof validation with worker-proportional task submission and pending futures while preserving full-content hashing, ordered results, and the all-hit no-analysis-pool path.
  - Released raw input bytes before parsing and rule execution, and skipped metadata collection when clean source snapshots are not requested.
  - Derived normal-wheel implementation identities from complete trusted distribution-manifest metadata only when it identifies the imported package root, with complete source-tree hashing retained for editable installs, source runs, mismatched installations, and unusable manifests.
  - Reduced worker requests to immutable path-specific rule execution plans, returned frozen batch results, made probe and persistence outcomes explicit, aggregated cache statistics once per phase, and touched each engine retention row once with its maximum observed day.
  - Deferred engine, path-builder, and store construction until at least one selected file is cacheable, so disabled and wholly uncacheable runs avoid cache-only fingerprint work.
- **Rule and path contracts:**
  - Added parser-owned Google type-edit bounds for typed documentation fixes and made enum-specific forbidden-type removal an explicit correction policy independent of descriptive fix metadata.
  - Defined `Usually` fix availability for rules whose every semantic violation kind has a correction but whose individual findings can fail conservative safety checks, and reserved `Sometimes` for rules with intentionally diagnostic-only violation kinds.
  - Validated terminal-punctuation policies at construction so contradictory classifications and unusable canonical endings fail immediately.
  - Centralized the shared trailing-period and terminal-punctuation policies and kept comma-introduced structure classification in the punctuation helper rather than the PDF parser core.
  - Centralized the deliberately closed ASCII space-and-tab policy used by layout and convention normalization without broadening Unicode whitespace ownership.
  - Unified parsed type semantics and optional source spans in one parser-owned value object, replaced rule-specific fragment safety state with complete evaluated-value offsets, and completed shared replacement accumulation across convention normalization rules.
  - Encapsulated accumulated replacement requests in one private record collection and made normalization safety checks short-circuit without allocating detailed Unicode occurrences.
  - Centralized package, module, symlink-target, and public/private path semantics in a precomputed rule context shared with cache invalidation.
  - Made rule cache dependencies explicit and fail closed, with every built-in rule audited as file-local and new external dependency kinds requiring canonical invalidation before cache use.
- **Configuration:**
  - Added `docstring-placeholder-markers` for configuring the exact marker inventory used by PDF213, including an empty-list opt-out that does not change rule selection.
  - Extended settings profiles with the auto-discovered project root so default cache locations are stable across nested paths and relocated workspaces.
- **Comment formatting:**
  - Made PCF100 stably remove repeated normalized items from validated set-like directive lists while preserving first occurrence, author order, namespaces, rationale tails, malformed payloads, and Ruff range-boundary multiplicity.
  - Recognized the complete Unicode-aware reStructuredText directive-name grammar, including namespaced directives and the optional space before `::`, when preserving directive blocks in standalone and extracted trailing comments.
  - Made PCF000 normalize regular standalone comments containing only ASCII space, tab, or form-feed payloads to bare `#` while preserving deliberate hash separators and source line endings.

### Fixed

- **Cross-platform behavior:**
  - Kept surrogate-path gitignore encoding coverage independent of host filesystem filename restrictions and ran Ubuntu 20.04 dependency synchronization and tests with one consistent unprivileged user environment.
  - Deduplicated case-insensitive, hard-link, and symlink path aliases by physical file identity while treating zero-valued inode information as unusable, and made a missing Git executable produce an actionable `--no-respect-gitignore` diagnostic.
  - Kept invalid-escape docstring and annotation analysis and deeply nested type-token validation stable on Python 3.12 through 3.14, including conservative lone-carriage-return handling, closed test-owned SQLite connections explicitly for consistent musl runs, and retained isolated pytest temporary boundaries through Python 3.14 multiprocessing shutdown.
  - Removed dependencies on private argparse interfaces while preserving CLI help output across direct, inherited, subparser, and mutually exclusive argument registration, and made deep type-token fallback independent of tokenizer diagnostic wording.
- **Configuration:**
  - Made ASCII case-insensitive duplicate `docstring-placeholder-markers` diagnostics deterministic when multiple configured spellings have the same normalized value.
  - Reported invalid `docstring-placeholder-markers` entries before checking ASCII case-insensitive duplicates, so Unicode case-folding collisions receive the relevant syntax error.
- **Developer tooling:**
  - Restored heading ownership checks for semantic documentation tables, kept Markdown pipe parsing aligned with GitHub Flavored Markdown, and retained a focused downstream release-checksum command contract test.
  - Limited documentation environments to the base shared tooling package while requesting its consumer-facing pytest integration only in test environments.
- **Fix execution:**
  - Remapped LibCST positions onto exact source with structurally verified, parser-consistent right-biased, linear-time sparse alignment, preserving adjacent form feeds and omitted comment or blank lines, rejecting semantic mismatches, and retaining accumulated diagnostics when an unprovable post-fix alignment rolls back all partial fixes.
  - Kept checks and fixes active for valid sources with repeated omitted trivia, avoided redundant structural reparsing of internally produced edited source, and reported only automatic fixes that survive a repeated-source cycle.
- **Comment formatting:**
  - Derived PCF comment ranges from exact-source-remapped LibCST positions, preserving exact edited source across reparsing and recognizing multiline f-string comments consistently on Python 3.11.
  - Preserved invalid pydocfmt selector spelling, normalized whitespace-only selector lists, removed terminal whitespace from recognized bracket directives, and permitted broad Ruff selectors under both representation policies while retaining exact-code diagnostics.
- **Docstring diagnostics:**
  - Excluded indentation form feeds from canonical docstring margins so generated continuation, blank, and delimiter lines cannot copy tokenizer trivia into evaluated docstring values.
  - Eliminated fix cycles between PDF107 and PDF200, PDF108 and PDF201, PDF100 and PDF103, PDF100 and PDF101, PDF101 and PDF409, and PDF101 and PDF415 by assigning all whitespace-only lines to PDF103, sharing canonical attached-docstring margins, preserving relative Google and NumPy entry indentation and entry separators, retaining first-line structural and tab-based hanging indentation, making PDF200 delimiter-placement neutral, and preserving configured final-section spacing ahead of PDF108's compact closing style. Retained whitespace ownership inside first-line convention sections, rejected empty generic Google return and yield entry heads, made nested terminal-section spacing reach a fixed point, and corrected PDF405's tabbed section-underline source mapping.
  - Stopped automatic fixing as soon as an exact source state repeats, reported the cycle length and likely rules and lines, and retained the existing iteration limit for non-repeating changes.
  - Preserved internal punctuation in PDF311 source-word diagnostics, made its display helper robust to punctuation-only tokens, and made PDF312 name only distinct entries implicated by generic-description matches.
  - Made literal `__slots__` inventory conservative for mutable list values and skipped expensive slot metadata analysis in files without an exact `__slots__` name token.
  - Recognized current Sphinx version-directive names and the optional delimiter space in PDF418 malformed directive diagnostics.
  - Fixed PDF414 reStructuredText closing-colon repairs to use bounded syntactic heads instead of description prose, preserve inline parameter types and spaced exception lists, and leave ambiguous or unsupported heads diagnostic-only; made PDF527 recognize narrowly escaped reStructuredText variadic markers; fixed PDF414, PDF415, and PDF527 exact edits on escaped logical lines without physical line mappings.
  - Made PDF409 leave empty Google type slots unchanged and PDF414 report the malformed syntax instead of canonicalizing empty parentheses.
  - Made PDF312 recognize exact generic descriptions that preserve leading or trailing underscores in documented names.
  - Prevented PDF312 from matching descriptions whose original parsed fragments contain non-ASCII boundary characters, non-space/tab whitespace, or suspicious controls.
  - Prevented PDF416 trailing-period and redundant-parenthesis fixes from leaving newly exposed ASCII whitespace, sourced type-slot spans directly from convention parsing, restored fallback Google method type slots, cached repeated spellings, and left non-default whitespace and suspicious controls to PDF004.
  - Limited PDF403, PDF404, PDF409, PDF410, PDF411, and PDF416 convention normalization to ASCII spaces and tabs while preserving or deferring other whitespace and controls.
  - Made accumulated section replacements order-independent and prevented stale offsets or overlapping requests from corrupting same-line whole-docstring fallback fixes.
  - Consolidated PDF312 owner, pattern, and message behavior into one immutable policy per entry kind.
  - Preserved exact string-prefix spelling when PDF300 and PDF301 insert or replace summary punctuation.
  - Reported PDF410 warning normalization findings as warning entries while retaining exception-specific messages for raised exceptions.
- **Convention parsing:**
  - Preserved complete multiline reStructuredText type-field semantics while exposing editable source slots only for line-local types.
  - Parsed balanced Google and NumPy method signatures as opaque method entry heads for PDF723 and related structural rules while preserving legacy Google colon-only and NumPy type-bearing entries.
  - Reported direct-method unbalanced Google and NumPy signatures with method-specific PDF414 diagnostics instead of treating signature contents as docstring type syntax, while leaving unknown prose-like candidates alone.
  - Kept NumPy `Warning` and `Warnings` caution sections as narrative content instead of treating their text as emitted-warning entries.
  - Kept raised exceptions and emitted warnings as separate semantic entry families, preventing PDF412 from conflating the same name across `Raises` and `Warns` sections.
  - Made PDF414 and PDF415 require owner-inventory evidence for ambiguous bare Google and empty-type NumPy candidates, use field arity to limit reStructuredText missing-delimiter findings, and distinguish valid NumPy return, yield, and exception peers from malformed continuations.
  - Required balanced nested delimiters and quotes for every parenthesized Google type, and validated PDF414 NumPy type candidates with a newline-aware iterative token grammar so deeply nested input does not enter Python's recursive expression parser.
  - Preserved sequence-shaped type state through grouping parentheses, preventing invalid NumPy type candidates from triggering missing-separator diagnostics.
  - Kept every PDF414 and PDF415 issue line as a distinct non-reflowable structural boundary so PDF101 cannot merge malformed entries or erase their diagnostics.
  - Compared convention indentation using raw evaluated whitespace, replaced regex-compatible entry matching with explicit match data, and centralized exhaustive issue precedence and message ownership without changing diagnostic identities.
- **Markup-aware reflow:**
  - Preserved recognized inline Markdown and reStructuredText constructs as indivisible source-aware tokens in PDF101, PCF000, and PCF002, while reporting ambiguous constructs without unsafe reflow or extraction fixes.
  - Recognized angle-bracket Markdown destinations and escaped parentheses in destinations without splitting valid links or images.
  - Retained space- and backslash-based Markdown hard breaks during PDF101, PDF102, and PCF000 formatting, including exact docstring source spellings.
  - Preserved zero-value source continuations and original line endings through simple-string fixes, canonicalizing continuations only inside PDF101 regions that are actually reflowed.
  - Made PDF101 report one whole-docstring diagnostic when required reflow cannot be source-mapped safely, and made PDF102 preserve source continuations inside every exact whitespace deletion.
  - Capitalized only the first evaluated character for PDF310 fixes so later escapes and source continuations remain unchanged.
  - Treated line-leading backtick and tilde fence openers with optional info strings consistently across docstring and comment parsing.
  - Shared semantic-line segmentation and inline scans across PDF101, PCF000, and PCF002 instead of rescanning the same text during wrapping.
  - Avoided markup-parser work for delimiter-free source-identical and source-aware prose, indexed escape and physical-line lookups, lazily materialized heavyweight string source maps, and removed repeated immutable envelope growth for long markup-heavy text.
  - Kept ambiguity evidence from identical malformed inline constructs distinct across joined logical lines.
  - Classified PCF000 and PCF002 as usually fixable because conservative ambiguity findings may intentionally omit fixes.
- **Unicode safety:**
  - Preserved diagnostic Unicode hazards through docstring and comment formatting, including protected comment structures and diagnostic whitespace at docstring boundaries; deferred unsafe payload reconstruction, kept accepted interior nonbreaking spaces indivisible during wrapping, and stabilized partial-mapping diagnostic order.
  - Reused prepared comment classifications and binary-searched source-position mapping while retaining canonical PCF002 width and syntax eligibility.
  - Cached docstring Unicode classifications and shared simple-string mappings, separated mapping capability from canonical rewrite policy, derived reportable membership from exhaustive diagnostic labels, and made inline rewrite barriers typed.
- **Rule suppressions:**
  - Kept PCF coverage line-local when an inline directive follows the final token of a concatenated string expression.
  - Limited complete-expression PDF coverage to recognized primary and supported attached docstrings, preventing directives on ordinary strings from suppressing unrelated findings while reducing string-topology storage to linear size.
  - Made complete-expression candidates category-neutral and indexed string topology by attachment line, avoiding repeated whole-source scans and retaining only complete expression ranges.
- **Persistent caching:**
  - Prevented a configured cache directory equal to the traversal root from suppressing all input files; an unusable shared or project-root cache now degrades without changing file selection.
  - Fingerprinted symlinked implementation sources and targets without disabling caching for valid symlinked package trees, while rejecting incomplete or cyclic identities.
  - Reused the frozen source-path context during rule execution so concurrent package-marker changes cannot misalign analysis and proof identities.
  - Limited internal-cache pruning to the safe current-working-directory run root so nested or non-empty unowned cache settings cannot hide source files.
  - Reported cache cleanup filesystem failures as contextual status-2 errors without leaking tracebacks, including safe retry guidance after partial cleanup.
  - Required exact ownership before corrupt or incompatible databases can be quarantined or replaced, preserved unowned databases and sidecars, and limited cleanup to numeric version directories and their quarantine files.
  - Required the ownership tag to be a non-symlinked regular file for lookup and every mutation, while retaining the intentional ability to claim an empty untagged directory only during cache creation.
  - Serialized cache writes, recovery, quarantine, pruning, and cleanup with a retained native file lock; writers now revalidate the current database after locking so stale lookup state cannot replace newer proofs.
  - Kept transaction rollback and connection closure inside the mutation-lock lifetime, and sampled each quarantine candidate through one non-following metadata read before retention decisions.
  - Preserved committed WAL data by checkpointing readable incompatible databases and quarantining main, WAL, and shared-memory files as recoverable groups with group-aware retention and partial-move rollback.
  - Counted engine-identity, shared-analysis, path-fingerprint, malformed-row, lookup, lock, recovery, and commit failures through explicit typed outcomes while keeping valid path-context mismatches as ordinary misses.
  - Prevented filesystem roots from contributing an empty package component to rule and cache path semantics.
  - Separated list identities from tuples and other canonical values, rejected non-finite floats, and made normal-wheel manifest identities complete and unambiguous.
  - Reported a missing or non-directory immediate cache parent exactly once while preserving uncached findings, fixes, and status.
  - Pruned the configured owned cache directory when traversal reaches it through a physical parent alias, while continuing to reject a symlinked final cache component.
  - Made retention days follow backward wall-clock changes so disposable cache entries are reanalyzed earlier instead of being pinned by future timestamps.
- **Configuration:**
  - Rejected NUL characters in `cache-dir` values from programmatic, inline, TOML, and command-line settings with contextual status-2 errors.
- **Documentation:**
  - Changed the README links for Contributing, Changelog, and License to absolute documentation-site targets so they resolve correctly in package descriptions rendered by PyPI.

### Removed

- **Developer documentation:**
  - Removed the exhausted future-rule ideas and coverage audit together with its audit-only consistency tests after implementing the remaining proposals.
- **Internal cleanup:**
  - Removed the full selector and per-file matcher payload from workers, duplicate path-fingerprint helper APIs, contradictory optional cache-evidence states, the parallel cache-role map, duplicate store-side clean-proof validators, the unused source-context display field, the test-only settings-discovery wrapper, cached glob-pattern tuples, optional rule-context path fallbacks, duplicate formatter and rule-runner compatibility entry points, pass-through CLI worker wrappers, dead or misleading string-source helper APIs, an unused inline-token source renderer, and a thin URL-classification facade.

---

## v1.0.0

Released 2026-07-16

### Added

#### Rule-based formatting

- Rebuilt pydocformatter as a rule-based linter and formatter with 122 stable, independently selectable rules: `PCF001` through `PCF006` for comments and 116 `PDF` rules for docstrings.
- Added conservative automatic fixes with repeated passes, convergence checks, source suppressions, per-finding fixability, exact source locations, and read-only diagnostics when a safe change cannot be inferred.
- Added convention-aware docstring parsing for PEP 257, Google, NumPy, and reStructuredText, including semantic sections and entries plus protected lists, headings, doctests, code fences, block quotes, tables, directives, literal blocks, and reST fields.
- Added docstring rules for literal and quote normalization, indentation, reflow, whitespace, blank lines, summary style, section structure, entry formatting, signature and documented-value consistency, attribute documentation placement, missing documentation, description quality, and conservative annotation/type agreement.
- Added comment rules for standalone prose reflow, trailing-comment spacing and extraction, recognized tool-directive normalization, non-ASCII reporting, and unused pydocfmt suppression reporting. Formatting preserves supported type-checker, linter, formatter, security, IDE, doctest, code, table, directive, and task-marker structures.

#### CLI and configuration

- Added the Ruff-style `pydocfmt check` workflow, with `--fix`, `--diff`, stdin, output redirection, exit-status controls, explicit and inline configuration, isolated mode, deterministic file-level parallelism, line-ending control, and grouped diagnostics.
- Added `pydocfmt config`, `pydocfmt rule`, `pydocfmt linter`, `pydocfmt help`, `pydocfmt version`, and inspection output for settings, rules, and discovered files.
- Added Ruff-style rule selection and fixability controls, per-file ignores and settings, path-aware configuration discovery, glob-based file selection, gitignore support, explicit-file force exclusion, URL-aware wrapping, and detailed docstring and comment behavior settings.
- Added published `pydocfmt-check` and `pydocfmt-fix` pre-commit hooks.

#### Documentation and packaging

- Added a documentation site with tutorials, workflows, settings and rule references, Ruff compatibility guidance, executable examples, public behavior specifications, and adjacent documentation for every built-in rule.
- Added reproducible Hatchling builds, tested wheel and source-distribution contents, and portable release checksum generation.

### Changed

#### Breaking migration from v0.2.0

- Replaced the old top-level `pydocfmt` and `pydocfmt --check` forms with `pydocfmt check --fix` and `pydocfmt check`, respectively.
- Merged comment formatting into `pydocfmt` and removed the separate comment-formatting command.
- Renamed the configuration table from `[tool.pydocformatter]` to `[tool.pydocfmt]`. Only hyphenated setting keys are accepted, and nested `[tool.pydocfmt.docstring]` and `[tool.pydocfmt.comment]` tables are the preferred forms for formatter-specific settings.
- Replaced regex include and exclude settings with Ruff-style glob lists. Configuration now follows explicit source precedence, closest-file discovery, config-relative pattern bases, per-file overrides, and gitignore-aware file selection.
- Replaced `docstring-parse-sphinx-fields` with `docstring-convention = "rest"` for semantic reStructuredText and Sphinx field parsing.
- Changed the default docstring convention to `pep257`; convention-dependent rules are enabled, ignored, or disabled according to whether the selected convention supplies their semantic targets.

#### Project and behavior

- Established pydocformatter as a standalone Ruff-style formatter, with the package version sourced from `src/pydocformatter/_version.py` and the project licensed under `GPL-3.0-or-later`.
- Moved builds from setuptools to Hatchling, added Python 3.14 support metadata, and replaced Black, isort, and mypy with Ruff and ty in the development workflow.
- Made automatic edits preserve untouched mixed line endings, UTF-8 byte order marks, final-newline state, source encodings, escaped non-ASCII spellings, and evaluated docstring values whenever a rule promises semantic equivalence.
- Changed rule and fixability selector resolution to Ruff-style source priority and specificity, with deterministic conflict handling and exact-rule restoration where supported.

### Fixed

- Corrected docstring parsing, source mapping, indentation, wrapping, delimiter placement, line-ending handling, and protected-structure behavior across tab-indented, simple-suite, escaped, concatenated, mixed-ending, and convention-specific docstrings.
- Corrected comment locations, empty separators, directive handling, syntax-sensitive trailing comments, line endings, and interactions between extracted trailing comments and surrounding standalone prose.
- Corrected parameter, return, yield, exception, class-attribute, and module-attribute documentation checks for aliases, shadowing, rebindings, variadic parameters, tuple unpacking, private packages, repeated entries, and suppressions.
- Corrected configuration validation, rule-selection precedence, per-file ignores, explicit configuration, glob bases, gitignore filtering, symlink traversal, duplicate physical files, and surrogate-escaped paths.
- Prevented quadratic or recursive wrapping behavior for long paragraphs and URLs, reduced repeated syntax and metadata work, and fixed final-iteration convergence handling.

### Removed

- Removed the v0.2.0 direct-formatter configuration and command surfaces superseded by the rule-based CLI and settings model.
- Removed the old `[tool.pydocformatter]` table, underscore setting aliases, regex file-selection semantics, and `docstring-parse-sphinx-fields` setting.
- Removed source-only internal compatibility wrappers and obsolete formatter, command, selector, and configuration helpers that were not part of the new stable interface.

---

## v0.2.0

Released 2026-05-01

### Added

- Initial preliminary release of `pydocformatter` as a simple direct formatter of comments and docstrings (no linting, no concept of rules, no complete CLI interface, and no complete/correct coverage of formatting fixes yet).
