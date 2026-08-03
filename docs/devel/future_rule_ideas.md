# Future rule ideas

The main remaining opportunities are:

- Inventory and ordering: attribute declaration order.
- Conservative autofixes: duplicate directive selectors.

There are currently 138 rules: 7 PCF and 131 PDF. Fix availability is 22 always, 21 usually, 13 sometimes, and 82 never.

## Current coverage audit

Fix abbreviations: A = always, U = usually, S = sometimes, N = never.

### Comments

| Rule   | Reports and automatic behavior                                                                                                                                          | Fix |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----:|
| PCF001 | Formats standalone comments, including whitespace-only empty-comment normalization; preserves recognized markup and hard breaks; reports ambiguity without unsafe fixes |   U |
| PCF002 | Trailing-comment delimiter spacing, ordinary marker spacing, and trailing whitespace; protected directive bodies remain intact                                          |   A |
| PCF003 | Safe spelling and spacing normalization for recognized type/tool directives and comma/bracket payloads                                                                  |   A |
| PCF004 | Overlong ordinary trailing comments that can safely move above code; atomically wraps recognized inline markup and rejects ambiguous extraction candidates              |   U |
| PCF005 | Literal non-ASCII source in any Python comment, including protected comments                                                                                            |   N |
| PCF006 | Invalid, unknown, or unused selected pydocfmt suppression selectors                                                                                                     |   N |
| PCF007 | Suspicious literal Unicode in comments; fixes nonbreaking indentation spaces and protects other hazards from comment rewrites                                           |   S |

The comment parser deliberately excludes empty/hash-only lines from ordinary runs after PCF001's narrow whitespace-only pre-pass and protects shebangs, encoding cookies, type comments, and known directives; see `PCF.md`.

### Literal and source formatting

| Rules      | Reports and automatic behavior                                                                                  | Fix |
|------------|-----------------------------------------------------------------------------------------------------------------|----:|
| PDF000     | Concatenated literals, no-op `u` prefixes, and safely literalizable whitespace escapes                          |   U |
| PDF001     | Anything other than triple double quotes, where value-preserving conversion may be possible                     |   U |
| PDF002     | Non-raw source containing reportable backslashes; adds `r` only when value-preserving                           |   S |
| PDF003     | Literal non-ASCII docstring source; escapes characters when value-preserving                                    |   U |
| PDF004     | Suspicious evaluated Unicode in simple and concatenated docstrings; fixes mapped nonbreaking indentation spaces |   S |
| PDF100     | Incorrect multiline indentation, including convention-specific entry indentation                                |   A |
| PDF101     | Reflows supported regions; preserves recognized markup and hard breaks; reports ambiguity without unsafe fixes  |   U |
| PDF102–105 | Whitespace normalization; PDF102 preserves recognized hard breaks                                               |   A |
| PDF106/107 | Multiline opening quotes/content on the same line versus separate lines                                         |   A |
| PDF108/109 | Multiline closing quotes/content on the same line versus separate lines                                         |   A |
| PDF110     | Summary-only multiline docstrings that fit as one physical line                                                 |   A |

### Blank lines and summaries

| Rules          | Reports and automatic behavior                                                                                                  | Fix |
|----------------|---------------------------------------------------------------------------------------------------------------------------------|----:|
| PDF200         | Leading, trailing, repeated, section-internal, and inter-block excess blank lines                                               |   A |
| PDF201         | Safely provable missing separators around summaries, structures, and convention sections                                        |   A |
| PDF202         | Evaluated docstrings containing no non-whitespace text                                                                          |   N |
| PDF203         | Parsed top-level summaries that still occupy multiple logical lines                                                             |   N |
| PDF212         | Nonempty collected docstrings without a parsed top-level summary                                                                |   N |
| PDF213         | Complete evaluated docstrings matching configured placeholder markers                                                           |   N |
| PDF204/205     | Zero versus exactly one blank line before function/method docstrings                                                            |   A |
| PDF206/207     | Zero versus exactly one blank line after function/method docstrings                                                             |   A |
| PDF208/209     | Zero versus exactly one blank line before class docstrings                                                                      |   A |
| PDF210/211     | Zero versus exactly one blank line after class docstrings                                                                       |   A |
| PDF300/301     | Period-only versus general terminal punctuation for summaries; safely replaces semicolons and standalone commas                 |   S |
| PDF302         | Known non-imperative first words in function/method summaries                                                                   |   N |
| PDF303         | Function name immediately followed by `(` in a summary                                                                          |   N |
| PDF304         | Safely capitalizable lowercase ASCII summary first words                                                                        |   U |
| PDF305         | Summaries whose normalized first word is “this”                                                                                 |   N |
| PDF306/307/312 | Conservative generic parameter, attribute, return, yield, exception, warning, or method descriptions                            |   N |
| PDF308/309     | Period-only versus general terminal punctuation for parsed entry descriptions; safely replaces semicolons and standalone commas |   S |
| PDF310         | Safely capitalizable entry-description first words                                                                              |   U |
| PDF311         | Property summaries beginning with a small action-verb list                                                                      |   N |

### Convention structure

| Rules  | Reports and automatic behavior                                                                    | Fix |
|--------|---------------------------------------------------------------------------------------------------|----:|
| PDF400 | Section/field-name capitalization                                                                 |   U |
| PDF401 | Preferred singular/plural section and reST field spellings                                        |   U |
| PDF402 | Preferred equivalent section/field terminology                                                    |   U |
| PDF403 | Google section content incorrectly sharing the header line                                        |   U |
| PDF404 | Missing Google section colon                                                                      |   U |
| PDF405 | Missing, misplaced, wrong-character, or wrong-length NumPy underlines                             |   U |
| PDF406 | Empty sections and reST fields                                                                    |   N |
| PDF407 | Convention-defined section/field order violations                                                 |   N |
| PDF408 | Repeated semantic sections/non-named fields                                                       |   N |
| PDF409 | Google, NumPy, and reST entry-prefix spacing                                                      |   U |
| PDF410 | Exception-list backticks, pipes, commas, and spacing                                              |   U |
| PDF411 | AST-safe whitespace inside parsed type-like slots                                                 |   U |
| PDF412 | Repeated named entries across an entire docstring                                                 |   N |
| PDF413 | Superfluous NumPy section colon                                                                   |   U |
| PDF414 | High-confidence malformed convention entry syntax                                                 |   S |
| PDF415 | High-confidence Google and NumPy entry indentation                                                |   U |
| PDF416 | Conservative trailing-period, outer-parenthesis, and lowercase `none` type spelling normalization |   U |
| PDF417 | NumPy single-value versus multiple-value `Returns` entry shape                                    |   N |
| PDF418 | High-confidence reStructuredText directive introducers with one trailing colon                    |   N |

Recognized section names and ordering are explicit tables in `docstring_sections.py`. PDF414 and PDF415 intentionally diagnose only high-confidence malformed entry syntax and indentation so arbitrary prose remains untouched.

### Semantic consistency and ownership

Most PDF5xx–7xx rules are diagnostic-only. PDF527 is usually fixable, while PDF701, PDF705, PDF709, PDF713, and PDF717 are sometimes fixable from source annotations or convention-specific policy.

| Rules          | Current check                                                                                           | Fix |
|----------------|---------------------------------------------------------------------------------------------------------|----:|
| PDF500/501/526 | Missing or extraneous parameters and documentation order against the signature                          |   N |
| PDF527         | Exact parameter variadic spelling against the signature                                                 |   U |
| PDF502/503     | Missing or extraneous ordinary return documentation based on function-body returns                      |   N |
| PDF504/505     | Missing or extraneous yield documentation based on function-body yields                                 |   N |
| PDF506/507     | Missing or extraneous directly raised exceptions, with optional assertion-derived `AssertionError`      |   N |
| PDF508/509     | Missing public or extraneous class/instance attribute documentation, including proven literal slots     |   N |
| PDF510/511     | Missing public or extraneous module attribute documentation                                             |   N |
| PDF512/513     | Attribute documentation duplicated between owner and attached docstrings                                |   N |
| PDF514/515     | Private class/module attributes forbidden in owner docstrings                                           |   N |
| PDF516/517     | Private class/module attributes forbidden from attached docstrings                                      |   N |
| PDF518/519     | Public class attributes must use owner versus attached documentation; slot-only names cannot attach     |   N |
| PDF520/521     | Public module attributes must use owner versus attached documentation                                   |   N |
| PDF522/523     | Private class attributes must use owner versus attached documentation; slot-only names cannot attach    |   N |
| PDF524/525     | Private module attributes must use owner versus attached documentation                                  |   N |
| PDF600/601     | Missing public/private package docstrings                                                               |   N |
| PDF602/603     | Missing public/private module docstrings                                                                |   N |
| PDF604/605     | Missing public/private top-level class docstrings                                                       |   N |
| PDF606/607     | Missing public/private nested-class docstrings                                                          |   N |
| PDF608/609     | Missing public/private top-level function docstrings                                                    |   N |
| PDF610/611     | Missing public/private non-dunder method docstrings                                                     |   N |
| PDF612/613     | Missing public/private dunder-method docstrings                                                         |   N |
| PDF614/615     | Missing public/private `__init__` docstrings                                                            |   N |
| PDF616         | Docstrings forbidden by configured decorators, defaulting to overload decorators                        |   N |
| PDF700/702/703 | Parameter description presence, forbidden types, and annotation mismatch                                |   N |
| PDF701         | Required parameter types                                                                                |   S |
| PDF704/706/707 | Return description presence, forbidden types, and annotation mismatch                                   |   N |
| PDF705         | Required return types                                                                                   |   S |
| PDF708/710/711 | Yield description presence, forbidden types, and generator-annotation mismatch                          |   N |
| PDF709         | Required yield types                                                                                    |   S |
| PDF712/714/715 | Class-attribute description presence, forbidden types, and annotation mismatch, including literal slots |   N |
| PDF713         | Required class-attribute types and enum-like no-type inversion; later real slot annotations can fix     |   S |
| PDF716/718/719 | Module-attribute description presence, forbidden types, and annotation mismatch                         |   N |
| PDF717         | Required module-attribute types                                                                         |   S |
| PDF720/721     | Raised-exception and emitted-warning description presence                                               |   N |
| PDF722         | Orphan reStructuredText type fields without corresponding value fields                                  |   N |
| PDF723         | Method-entry description presence in class docstrings                                                   |   N |

The category’s exact inventory boundaries, including final effective literal `__slots__` declarations, are documented in `PDF.md`.

## Proposed additions and extensions

Ideas #1–#11 were implemented and removed from this list; the remaining idea numbers are retained for stable cross-references.

12. **Deduplicate directive selectors and codes.** PCF003 can safely remove exact duplicate entries from `noqa`, `pydocfmt`, `ruff`, `pylint`, `type: ignore`, and similar comma or bracket lists. Sorting should be optional; deduplication is semantics-preserving.

13. **Check attribute entry order against declaration order.** This complements PDF508–513. It should be opt-in because conceptual ordering is sometimes intentional.

## Recommended implementation sequence

- **Highest priority:** #12 directive deduplication is a small, conservative extension of existing normalization.
- **Focused refinement:** #13 attribute ordering has narrower reach and preference-sensitive policy but remains worthwhile as an opt-in rule.

## Scored assessment

Every individual score uses a benefit-oriented scale where 1 is worst and 5 is best:

- **Implementation locality:** 1 means cross-cutting parser, model, settings, runner, or rule-family changes; 5 means a highly isolated rule or helper change.
- **Robustness:** 1 means difficult to make reliably false-positive-free; 5 means a bullet-proof implementation is readily achievable.
- **Broad agreement:** 1 means strongly preference-dependent; 5 means broad agreement is likely.
- **Scope clarity:** 1 means the boundary is inherently fuzzy; 5 means the target is crisp and easily bounded.
- **Check-time efficiency:** 1 means substantial additional uncached runtime work; 5 means negligible additional uncached runtime work.
- **Reach:** 1 means few users or projects benefit; 5 means broadly useful.
- **Implementation straightforwardness:** 1 means many non-obvious design decisions; 5 means the implementation path is direct.
- **Added value beyond Ruff:** 1 means Ruff already covers the same behavior well; 5 means the proposal is materially distinct, more exact, or better integrated with pydocfmt.
- **Overall recommendation:** 1 means reject or indefinitely defer; 5 means prioritize.

The **weighted average** is the arithmetic mean of the eight individual dimension scores after applying these weights: robustness 20%; scope clarity, reach, and added value beyond Ruff 15% each; implementation locality, check-time efficiency, and implementation straightforwardness 10% each; and broad agreement 5%. This prioritizes reliable behavior and clear user value while giving less weight to consensus because an opt-in rule can still be worthwhile when preferences differ. The overall recommendation is an independent synthesis and is not included in the weighted average. Rows are sorted by descending weighted average, then by descending overall recommendation and ascending idea number to break ties.

The Ruff comparison was checked against the official [rule catalog](https://docs.astral.sh/ruff/rules/), [pydoclint rules](https://docs.astral.sh/ruff/rules/#pydoclint-doc), [pydocstyle rules](https://docs.astral.sh/ruff/rules/#pydocstyle-d), [task-comment rules](https://docs.astral.sh/ruff/rules/invalid-todo-capitalization/), [suppression rules](https://docs.astral.sh/ruff/rules/unused-noqa/), [slot ordering](https://docs.astral.sh/ruff/rules/unsorted-dunder-slots/), [non-slot assignment](https://docs.astral.sh/ruff/rules/non-slot-assignment/), and [docstring code formatting](https://docs.astral.sh/ruff/formatter/#docstring-formatting) on 2026-08-01.

| Idea | Proposed change                                       | Implementation locality | Robustness | Broad agreement | Scope clarity | Check-time efficiency | Reach | Implementation straightforwardness | Added value beyond Ruff | Weighted average | Overall recommendation | Existing-code and design assessment                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|------|-------------------------------------------------------|------------------------:|-----------:|----------------:|--------------:|----------------------:|------:|-----------------------------------:|------------------------:|-----------------:|-----------------------:|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| #12  | Deduplicate directive selectors and codes             |                       4 |          4 |               5 |             4 |                     5 |     3 |                                  4 |                       3 |             3.85 |                      4 | PCF003 already parses and canonicalizes the relevant comma and bracket list families through `_normalized_comma_list()`, preserving rationale tails and rejecting unsafe token shapes. Stable first-occurrence deduplication is a small extension, but semantics should be audited separately for action pairs, `type: ignore` namespaces, case normalization, empty selectors, and tools where repeated tokens might carry unusual meaning. Ruff has strong suppression validation for its own directives, while pydocfmt's multi-tool directive coverage remains broader.    |
| #13  | Check attribute entry order against declaration order |                       4 |          4 |               2 |             4 |                     5 |     2 |                                  4 |                       5 |             3.85 |                      3 | `PDFCategoryData.attributes_for()` preserves collected assignment order, and parsed attribute entries preserve docstring order, so first-occurrence rank comparison can closely follow `parameter_order_issues()`. Multiple-target assignments, repeated declarations, instance attributes discovered through branches, and attached-versus-owner documentation need deterministic collapsing, but the technical boundary is manageable. Conceptual grouping is often intentional, making this appropriately opt-in and less broadly recommendable despite no Ruff equivalent. |
