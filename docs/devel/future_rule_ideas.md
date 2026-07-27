# Future rule ideas

The main remaining opportunities are:

- Entry substance: generic descriptions.
- Convention exactness: variadic markers, reST directive introducers, NumPy return-entry shape, and obvious type spelling defects.
- Inventory and ordering: attribute declaration order and literal `__slots__` members.
- Conservative autofixes: whitespace-only empty comments and duplicate directive selectors.
- Optional semantic coverage: treating `assert` as a possible documented `AssertionError`.

There are currently 133 rules: 7 PCF and 126 PDF. Fix availability is 22 always, 5 usually, 20 sometimes, and 86 never.

## Current coverage audit

Fix abbreviations: A = always, U = usually, S = sometimes, N = never.

### Comments

| Rule   | Reports and automatic behavior                                                                                                                             | Fix |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------|----:|
| PCF001 | Formats standalone comments; preserves recognized markup and hard breaks; reports ambiguity without unsafe fixes                                           |   U |
| PCF002 | Trailing-comment delimiter spacing, ordinary marker spacing, and trailing whitespace; protected directive bodies remain intact                             |   A |
| PCF003 | Safe spelling and spacing normalization for recognized type/tool directives and comma/bracket payloads                                                     |   A |
| PCF004 | Overlong ordinary trailing comments that can safely move above code; atomically wraps recognized inline markup and rejects ambiguous extraction candidates |   U |
| PCF005 | Literal non-ASCII source in any Python comment, including protected comments                                                                               |   N |
| PCF006 | Invalid, unknown, or unused selected pydocfmt suppression selectors                                                                                        |   N |
| PCF007 | Suspicious literal Unicode in comments; fixes nonbreaking indentation spaces and protects other hazards from comment rewrites                              |   S |

The comment parser deliberately excludes empty/hash-only lines and protects shebangs, encoding cookies, type comments, and known directives; see `PCF.md`.

### Literal and source formatting

| Rules      | Reports and automatic behavior                                                                                  | Fix |
|------------|-----------------------------------------------------------------------------------------------------------------|----:|
| PDF000     | Concatenated literals, no-op `u` prefixes, and safely literalizable whitespace escapes                          |   U |
| PDF001     | Anything other than triple double quotes, where value-preserving conversion may be possible                     |   S |
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

| Rules      | Reports and automatic behavior                                                                                                  | Fix |
|------------|---------------------------------------------------------------------------------------------------------------------------------|----:|
| PDF200     | Leading, trailing, repeated, section-internal, and inter-block excess blank lines                                               |   A |
| PDF201     | Safely provable missing separators around summaries, structures, and convention sections                                        |   A |
| PDF202     | Evaluated docstrings containing no non-whitespace text                                                                          |   N |
| PDF203     | Parsed top-level summaries that still occupy multiple logical lines                                                             |   N |
| PDF212     | Nonempty collected docstrings without a parsed top-level summary                                                                |   N |
| PDF213     | Complete evaluated docstrings matching configured placeholder markers                                                           |   N |
| PDF204/205 | Zero versus exactly one blank line before function/method docstrings                                                            |   A |
| PDF206/207 | Zero versus exactly one blank line after function/method docstrings                                                             |   A |
| PDF208/209 | Zero versus exactly one blank line before class docstrings                                                                      |   A |
| PDF210/211 | Zero versus exactly one blank line after class docstrings                                                                       |   A |
| PDF300/301 | Period-only versus general terminal punctuation for summaries; safely replaces semicolons and standalone commas                 |   S |
| PDF302     | Known non-imperative first words in function/method summaries                                                                   |   N |
| PDF303     | Function name immediately followed by `(` in a summary                                                                          |   N |
| PDF304     | Safely capitalizable lowercase ASCII summary first words                                                                        |   S |
| PDF305     | Summaries whose normalized first word is “this”                                                                                 |   N |
| PDF306/307 | Conservative generic parameter or attribute descriptions                                                                        |   N |
| PDF308/309 | Period-only versus general terminal punctuation for parsed entry descriptions; safely replaces semicolons and standalone commas |   S |
| PDF310     | Safely capitalizable entry-description first words                                                                              |   S |
| PDF311     | Property summaries beginning with a small action-verb list                                                                      |   N |

### Convention structure

| Rules  | Reports and automatic behavior                                        | Fix |
|--------|-----------------------------------------------------------------------|----:|
| PDF400 | Section/field-name capitalization                                     |   S |
| PDF401 | Preferred singular/plural section and reST field spellings            |   S |
| PDF402 | Preferred equivalent section/field terminology                        |   S |
| PDF403 | Google section content incorrectly sharing the header line            |   S |
| PDF404 | Missing Google section colon                                          |   S |
| PDF405 | Missing, misplaced, wrong-character, or wrong-length NumPy underlines |   S |
| PDF406 | Empty sections and reST fields                                        |   N |
| PDF407 | Convention-defined section/field order violations                     |   N |
| PDF408 | Repeated semantic sections/non-named fields                           |   N |
| PDF409 | Google, NumPy, and reST entry-prefix spacing                          |   S |
| PDF410 | Exception-list backticks, pipes, commas, and spacing                  |   S |
| PDF411 | AST-safe whitespace inside parsed type-like slots                     |   S |
| PDF412 | Repeated named entries across an entire docstring                     |   N |
| PDF413 | Superfluous NumPy section colon                                       |   S |
| PDF414 | High-confidence malformed convention entry syntax                     |   N |
| PDF415 | High-confidence Google and NumPy entry indentation                    |   N |

Recognized section names and ordering are explicit tables in `docstring_sections.py`. PDF414 and PDF415 intentionally diagnose only high-confidence malformed entry syntax and indentation so arbitrary prose remains untouched.

### Semantic consistency and ownership

All PDF5xx–7xx rules are diagnostic-only.

| Rules          | Current check                                                                           |
|----------------|-----------------------------------------------------------------------------------------|
| PDF500/501/526 | Missing or extraneous parameters and documentation order against the signature          |
| PDF502/503     | Missing or extraneous ordinary return documentation based on function-body returns      |
| PDF504/505     | Missing or extraneous yield documentation based on function-body yields                 |
| PDF506/507     | Missing or extraneous directly raised exceptions                                        |
| PDF508/509     | Missing public or extraneous class/instance attribute documentation                     |
| PDF510/511     | Missing public or extraneous module attribute documentation                             |
| PDF512/513     | Attribute documentation duplicated between owner and attached docstrings                |
| PDF514/515     | Private class/module attributes forbidden in owner docstrings                           |
| PDF516/517     | Private class/module attributes forbidden from attached docstrings                      |
| PDF518/519     | Public class attributes must use owner versus attached documentation                    |
| PDF520/521     | Public module attributes must use owner versus attached documentation                   |
| PDF522/523     | Private class attributes must use owner versus attached documentation                   |
| PDF524/525     | Private module attributes must use owner versus attached documentation                  |
| PDF600/601     | Missing public/private package docstrings                                               |
| PDF602/603     | Missing public/private module docstrings                                                |
| PDF604/605     | Missing public/private top-level class docstrings                                       |
| PDF606/607     | Missing public/private nested-class docstrings                                          |
| PDF608/609     | Missing public/private top-level function docstrings                                    |
| PDF610/611     | Missing public/private non-dunder method docstrings                                     |
| PDF612/613     | Missing public/private dunder-method docstrings                                         |
| PDF614/615     | Missing public/private `__init__` docstrings                                            |
| PDF616         | Docstrings forbidden by configured decorators, defaulting to overload decorators        |
| PDF700–703     | Parameter description presence, type required/forbidden, and annotation mismatch        |
| PDF704–707     | Return description presence, type required/forbidden, and annotation mismatch           |
| PDF708–711     | Yield description presence, type required/forbidden, and generator-annotation mismatch  |
| PDF712–715     | Class-attribute description presence, type required/forbidden, and annotation mismatch  |
| PDF716–719     | Module-attribute description presence, type required/forbidden, and annotation mismatch |
| PDF720/721     | Raised-exception and emitted-warning description presence                               |
| PDF722         | Orphan reStructuredText type fields without corresponding value fields                  |
| PDF723         | Method-entry description presence in class docstrings                                   |

The category’s exact inventory boundaries are documented in `PDF.md`.

## Proposed additions and extensions

Ideas #1–#3 were implemented and removed from this list; the remaining idea numbers are retained for stable cross-references.

4. **Require exact variadic markers when configured.** PDF500/501 intentionally equate `args` with `*args`; add an opt-in rule requiring `*args` and `**kwargs` to retain their stars. Google's guide explicitly recommends those spellings. [Google Python style guide](https://google.github.io/styleguide/pyguide.html)

5. **Canonicalize whitespace-only empty comments.** Normalize `#   ` to `#`. Do not alter deliberate hash separators such as `#####`.

6. **Validate NumPy return-entry shape.** Check that a single return entry starts with a type and that multiple returned values use valid multi-entry structure. This corresponds to a mature numpydoc rule without requiring runtime inference.

7. **Treat `assert` as a possible documented `AssertionError`.** This could extend PDF506 behind a setting; pydoclint exposes a corresponding check. Avoid enabling it broadly because assertions are often internal invariants.

8. **Canonicalize obvious docstring type spelling defects.** Examples include a trailing period in a type slot, lowercase `none`, or redundant outer whitespace or parentheses when normalization is AST-proven. Avoid broader `List` versus `list` policy because target-version preferences differ.

9. **Extend generic-description checks.** Conservatively flag `The return value`, `The yielded value`, `The exception`, `The method`, and similarly content-free warning descriptions.

10. **Validate reST directive introducers.** Report directive-looking lines using one colon instead of `.. name::`, corresponding to numpydoc's broadly useful GL10 check.

11. **Inventory literal `__slots__` members.** When `__slots__` is a statically known string, tuple, or list, include those instance attributes in class documentation checks.

12. **Deduplicate directive selectors and codes.** PCF003 can safely remove exact duplicate entries from `noqa`, `pydocfmt`, `ruff`, `pylint`, `type: ignore`, and similar comma or bracket lists. Sorting should be optional; deduplication is semantics-preserving.

13. **Check attribute entry order against declaration order.** This complements PDF508–513. It should be opt-in because conceptual ordering is sometimes intentional.

## Recommended implementation sequence

- **Highest priority:** #4 exact variadic markers and #5 empty-comment normalization combine robust detection or fixes with highly localized implementation work.
- **Strong follow-up:** #6 NumPy return-entry shape, #7 optional `AssertionError` documentation, #8 obvious type spelling, #9 generic descriptions, and #10 reST directive introducers remain well-bounded and materially extend current coverage.
- **Focused refinements:** #11 literal `__slots__` inventory, #12 directive deduplication, and #13 attribute ordering have narrower reach or more preference-sensitive policy but remain worthwhile.

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

The Ruff comparison was checked against the official [rule catalog](https://docs.astral.sh/ruff/rules/), [pydoclint rules](https://docs.astral.sh/ruff/rules/#pydoclint-doc), [pydocstyle rules](https://docs.astral.sh/ruff/rules/#pydocstyle-d), [task-comment rules](https://docs.astral.sh/ruff/rules/invalid-todo-capitalization/), [suppression rules](https://docs.astral.sh/ruff/rules/unused-noqa/), and [docstring code formatting](https://docs.astral.sh/ruff/formatter/#docstring-formatting) on 2026-07-27.

| Idea | Proposed change                                          | Implementation locality | Robustness | Broad agreement | Scope clarity | Check-time efficiency | Reach | Implementation straightforwardness | Added value beyond Ruff | Weighted average | Overall recommendation | Existing-code and design assessment                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|------|----------------------------------------------------------|------------------------:|-----------:|----------------:|--------------:|----------------------:|------:|-----------------------------------:|------------------------:|-----------------:|-----------------------:|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| #4   | Require exact variadic markers when configured           |                       4 |          5 |               3 |             5 |                     5 |     3 |                                  5 |                       4 |             4.35 |                      4 | `SignatureParameter.display_name` already preserves `*` and `**`, parsed Google and NumPy entry names accept those prefixes, and only `parameter_comparison_name()` deliberately strips them for PDF500, PDF501, and PDF526 matching. An opt-in diagnostic can compare the raw documented spelling with the matched signature parameter without changing existing equivalence semantics. The rule is technically crisp and cheap, though some established documentation styles omit stars; Ruff D417 can ignore variadics but does not enforce their exact spelling.                                           |
| #5   | Canonicalize whitespace-only empty comments              |                       5 |          5 |               4 |             5 |                     5 |     3 |                                  5 |                       3 |             4.35 |                      4 | `CommentInfo.is_empty` and `is_hash_only` already classify the target, but `_standalone_runs()` deliberately excludes it, while PCF002 only canonicalizes empty trailing comments. A standalone-only change from `#   ` to `#` can be implemented as an isolated exact token replacement and must leave multi-hash separators unchanged. The result is nearly risk-free and cheap; Ruff may normalize some comment whitespace through formatting, but pydocfmt would make the policy independently selectable and complete across placements.                                                                  |
| #6   | Validate NumPy return-entry shape                        |                       4 |          4 |               5 |             4 |                     5 |     3 |                                  4 |                       5 |             4.15 |                      4 | `_numpy_entries()` currently accepts both bare return-type lines and any `name: type` entries, records their source order, and does not validate whether one versus multiple returned values uses the convention's expected shape. A NumPy-only rule can reason over the existing section and entry tuples without runtime inference, but must define named tuple-like returns, comma-separated types, `None`, generator sections, and malformed peers already handled by PDF414. The rule is mature in numpydoc and has no Ruff counterpart.                                                                  |
| #7   | Treat `assert` as a possible documented `AssertionError` |                       4 |          5 |               2 |             5 |                     5 |     2 |                                  5 |                       4 |             4.15 |                      3 | `_DefinitionCollector` can record `cst.Assert` beside `visit_Raise()` with the same nested-function and lambda exclusions, and PDF506 can include a synthetic `AssertionError` behind a setting. The static fact is unambiguous, although optimized Python can remove assertions and many projects regard them as internal invariants rather than public exceptions. Ruff can flag assert usage through S101, but its DOC501 rule documents explicitly raised exceptions and does not turn assertions into documentation obligations.                                                                          |
| #8   | Canonicalize obvious docstring type spelling defects     |                       4 |          4 |               4 |             4 |                     5 |     3 |                                  4 |                       5 |             4.10 |                      4 | PDF411 and `normalized_type_like_text()` already prove AST-preserving internal whitespace normalization, but `DocstringEntry` does not retain source offsets for the complete type slot and punctuation such as a trailing period prevents type parsing. A narrow pre-parse cleanup or stored type-span model can handle a final period, lowercase `none`, and provably redundant outer grouping without adopting version-sensitive `List` versus `list` policy. The cases are bounded and absent from Ruff's docstring rules, though fixes must retain the project's exact source-mapping guarantees.         |
| #9   | Extend generic-description checks                        |                       4 |          4 |               3 |             4 |                     5 |     3 |                                  4 |                       5 |             4.05 |                      4 | `documentation_style.DocumentedValueStylePolicy` already token-normalizes descriptions and detects content-free parameter and attribute phrases, and the parser exposes return, yield, exception, warning, and method entry descriptions. New subject-specific noun sets and target collectors can reuse that machinery with little cost. The main risk is overreaching on short but meaningful phrases such as “The result” in a tightly scoped API, so patterns should remain exact and conservative. Ruff has no semantic generic-description family.                                                       |
| #10  | Validate reST directive introducers                      |                       4 |          4 |               5 |             4 |                     5 |     2 |                                  4 |                       5 |             4.00 |                      4 | `_DIRECTIVE_RE` recognizes only valid `.. name::` openers, and invalid directive-looking lines otherwise become prose or colon headers. A focused diagnostic can inspect clear line boundaries for one-colon or missing-dot variants while excluding field lists, literal blocks, ellipses, examples, and ordinary prose; no semantic body rewrite is required. The syntax is standardized and numpydoc's GL10 demonstrates usefulness, though reach is mostly reST and NumPy documentation. Ruff has no corresponding directive-introducer rule.                                                              |
| #11  | Inventory literal `__slots__` members                    |                       3 |          4 |               4 |             5 |                     5 |     2 |                                  3 |                       5 |             3.90 |                      4 | `_AttributeDocstringCollector` inventories ordinary class assignments and `self.name` writes in `__init__`, but a literal `__slots__` assignment is currently just the attribute named `__slots__`. A bounded evaluator for a string, tuple, or list can add member names to the owning class inventory with declaration order, while rejecting dynamic expressions; name mangling, invalid slot values, duplicates, `__dict__`, `__weakref__`, and overlap with actual assignments need explicit handling. Ruff can sort `__slots__` through RUF023 but does not connect slots to documentation completeness. |
| #12  | Deduplicate directive selectors and codes                |                       4 |          4 |               5 |             4 |                     5 |     3 |                                  4 |                       3 |             3.85 |                      4 | PCF003 already parses and canonicalizes the relevant comma and bracket list families through `_normalized_comma_list()`, preserving rationale tails and rejecting unsafe token shapes. Stable first-occurrence deduplication is a small extension, but semantics should be audited separately for action pairs, `type: ignore` namespaces, case normalization, empty selectors, and tools where repeated tokens might carry unusual meaning. Ruff has strong suppression validation for its own directives, while pydocfmt's multi-tool directive coverage remains broader.                                    |
| #13  | Check attribute entry order against declaration order    |                       4 |          4 |               2 |             4 |                     5 |     2 |                                  4 |                       5 |             3.85 |                      3 | `PDFCategoryData.attributes_for()` preserves collected assignment order, and parsed attribute entries preserve docstring order, so first-occurrence rank comparison can closely follow `parameter_order_issues()`. Multiple-target assignments, repeated declarations, instance attributes discovered through branches, and attached-versus-owner documentation need deterministic collapsing, but the technical boundary is manageable. Conceptual grouping is often intentional, making this appropriately opt-in and less broadly recommendable despite no Ruff equivalent.                                 |
