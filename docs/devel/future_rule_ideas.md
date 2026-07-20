# Future rule ideas

The main remaining opportunities are:

- Parser blind spots: malformed or mixed-convention documentation currently becomes ordinary prose.
- Ordering and ownership: parameter order, constructor/class documentation, method inventories, and `__all__`.
- Entry completeness: exceptions, warnings, methods, `See Also`, and attached attribute docstrings.
- Markup safety: inline roles, links, code spans, Markdown hard breaks, and malformed reST/fences.
- Conservative autofixes for several existing diagnostic-only rules.

There are currently 122 rules: 6 PCF and 116 PDF. Fix availability is 24 always, 3 usually, 18 sometimes, and 77 never.

## Current coverage audit

Fix abbreviations: A = always, U = usually, S = sometimes, N = never.

### Comments

| Rule   | Reports and automatic behavior                                                                                                                                | Fix |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|----:|
| PCF001 | Noncanonical standalone-comment hashes/spaces/trailing whitespace/wrapping; understands configured lists, tasks, quotes, preserved markup, and code detection |   A |
| PCF002 | Trailing-comment delimiter spacing, ordinary marker spacing, and trailing whitespace; protected directive bodies remain intact                                |   A |
| PCF003 | Safe spelling and spacing normalization for recognized type/tool directives and comma/bracket payloads                                                        |   A |
| PCF004 | Overlong ordinary trailing comments that can safely move above code; extracts and wraps them                                                                  |   A |
| PCF005 | Literal non-ASCII source in any Python comment, including protected comments                                                                                  |   N |
| PCF006 | Invalid, unknown, or unused selected pydocfmt suppression selectors                                                                                           |   N |

The comment parser deliberately excludes empty/hash-only lines and protects shebangs, encoding cookies, type comments, and known directives; see `PCF.md`.

### Literal and source formatting

| Rules      | Reports and automatic behavior                                                                      | Fix |
|------------|-----------------------------------------------------------------------------------------------------|----:|
| PDF000     | Concatenated literals, no-op `u` prefixes, and safely literalizable whitespace escapes              |   U |
| PDF001     | Anything other than triple double quotes, where value-preserving conversion may be possible         |   S |
| PDF002     | Non-raw source containing reportable backslashes; adds `r` only when value-preserving               |   S |
| PDF003     | Literal non-ASCII docstring source; escapes characters when value-preserving                        |   U |
| PDF100     | Incorrect multiline indentation, including convention-specific entry indentation                    |   A |
| PDF101     | Noncanonical wrapping of summaries, prose, entries, fields, lists, and block quotes                 |   U |
| PDF102–105 | Nonblank trailing whitespace, blank-line whitespace, and opening-/closing-quote-adjacent whitespace |   A |
| PDF106/107 | Multiline opening quotes/content on the same line versus separate lines                             |   A |
| PDF108/109 | Multiline closing quotes/content on the same line versus separate lines                             |   A |
| PDF110     | Summary-only multiline docstrings that fit as one physical line                                     |   A |

### Blank lines and summaries

| Rules      | Reports and automatic behavior                                                           | Fix |
|------------|------------------------------------------------------------------------------------------|----:|
| PDF200     | Leading, trailing, repeated, section-internal, and inter-block excess blank lines        |   A |
| PDF201     | Safely provable missing separators around summaries, structures, and convention sections |   A |
| PDF202     | Evaluated docstrings containing no non-whitespace text                                   |   N |
| PDF203     | Parsed top-level summaries that still occupy multiple logical lines                      |   N |
| PDF204/205 | Zero versus exactly one blank line before function/method docstrings                     |   A |
| PDF206/207 | Zero versus exactly one blank line after function/method docstrings                      |   A |
| PDF208/209 | Zero versus exactly one blank line before class docstrings                               |   A |
| PDF210/211 | Zero versus exactly one blank line after class docstrings                                |   A |
| PDF300/301 | Period-only versus general terminal punctuation for summaries                            |   S |
| PDF302     | Known non-imperative first words in function/method summaries                            |   N |
| PDF303     | Function name immediately followed by `(` in a summary                                   |   N |
| PDF304     | Safely capitalizable lowercase ASCII summary first words                                 |   S |
| PDF305     | Summaries whose normalized first word is “this”                                          |   N |
| PDF306/307 | Conservative generic parameter or attribute descriptions                                 |   N |
| PDF308/309 | Period-only versus general terminal punctuation for parsed entry descriptions            |   S |
| PDF310     | Safely capitalizable entry-description first words                                       |   S |
| PDF311     | Property summaries beginning with a small action-verb list                               |   N |

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

Recognized section names and ordering are explicit tables in `docstring_sections.py`. Anything outside them can silently fall back to prose.

### Semantic consistency and ownership

All PDF5xx–7xx rules are diagnostic-only.

| Rules      | Current check                                                                           |
|------------|-----------------------------------------------------------------------------------------|
| PDF500/501 | Missing signature parameters and documented names absent from the signature             |
| PDF502/503 | Missing or extraneous ordinary return documentation based on function-body returns      |
| PDF504/505 | Missing or extraneous yield documentation based on function-body yields                 |
| PDF506/507 | Missing or extraneous directly raised exceptions                                        |
| PDF508/509 | Missing public or extraneous class/instance attribute documentation                     |
| PDF510/511 | Missing public or extraneous module attribute documentation                             |
| PDF512/513 | Attribute documentation duplicated between owner and attached docstrings                |
| PDF514/515 | Private class/module attributes forbidden in owner docstrings                           |
| PDF516/517 | Private class/module attributes forbidden from attached docstrings                      |
| PDF518/519 | Public class attributes must use owner versus attached documentation                    |
| PDF520/521 | Public module attributes must use owner versus attached documentation                   |
| PDF522/523 | Private class attributes must use owner versus attached documentation                   |
| PDF524/525 | Private module attributes must use owner versus attached documentation                  |
| PDF600/601 | Missing public/private package docstrings                                               |
| PDF602/603 | Missing public/private module docstrings                                                |
| PDF604/605 | Missing public/private top-level class docstrings                                       |
| PDF606/607 | Missing public/private nested-class docstrings                                          |
| PDF608/609 | Missing public/private top-level function docstrings                                    |
| PDF610/611 | Missing public/private non-dunder method docstrings                                     |
| PDF612/613 | Missing public/private dunder-method docstrings                                         |
| PDF614/615 | Missing public/private `__init__` docstrings                                            |
| PDF616     | Docstrings forbidden by configured decorators, defaulting to overload decorators        |
| PDF700–703 | Parameter description presence, type required/forbidden, and annotation mismatch        |
| PDF704–707 | Return description presence, type required/forbidden, and annotation mismatch           |
| PDF708–711 | Yield description presence, type required/forbidden, and generator-annotation mismatch  |
| PDF712–715 | Class-attribute description presence, type required/forbidden, and annotation mismatch  |
| PDF716–719 | Module-attribute description presence, type required/forbidden, and annotation mismatch |

The category’s exact inventory boundaries—including ignored additional docstrings and unsupported assignment targets—are documented in `PDF.md`.

## Recommended rule additions and extensions

1. **Report docstring-convention mismatch or mixing.** Detect strong Google, NumPy, or reST markers that conflict with the configured convention. This prevents all downstream rules silently treating real documentation as prose. Keep it diagnostic-only and require multiple unambiguous signals.

2. **Report unknown or likely misspelled section names.** At clear section boundaries, flag near-matches such as `Paramters` or convention-inappropriate aliases. A unique case-insensitive/edit-distance match could be safely auto-fixed. Numpydoc has an established “unknown section” check, supporting its broad usefulness. [Numpydoc validation](https://numpydoc.readthedocs.io/en/stable/validation.html)

3. **Report malformed convention entry syntax.** Detect entry-looking lines inside recognized sections that failed parsing, such as NumPy `value: int`, missing Google entry colons, malformed reST field delimiters, or incorrectly indented entry continuations. This should explain the actual syntax problem instead of causing only a later “missing parameter” finding.

4. **Report missing summaries.** Distinguish a nonempty docstring containing only sections, fields, examples, directives, or other structures from PDF202’s empty docstring. This is the largest basic PEP 257/numpydoc structural gap.

5. **Report placeholder docstrings.** Conservatively recognize exact placeholders such as `TODO`, `TBD`, `...`, `FIXME`, or `pass`, after punctuation normalization. Do not attempt an autofix.

6. **Add generic owner-documentation detection.** Extend PDF306/307’s conservative philosophy to summaries like `Foo class`, `The foo function`, `Foo method`, or a summary that only repeats the qualified name. Make convention-specific patterns opt-in.

7. **Report sections inappropriate for the owner.** Examples include `Returns`/`Yields` on class or module docstrings, `Parameters` on modules, `Attributes` on ordinary function docstrings, or constructor-only sections at the wrong ownership location.

8. **Check parameter entry order against the signature.** This is deterministic, widely implemented by numpydoc and pydoclint, and catches documentation drift that missing/extraneous checks cannot. It should understand positional-only, keyword-only, and variadic parameters. [Pydoclint configuration](https://jsh9.github.io/pydoclint/config_options.html)

9. **Require exact variadic markers when configured.** PDF500/501 intentionally equate `args` with `*args`; add an opt-in rule requiring `*args` and `**kwargs` to retain their stars. Google’s guide explicitly recommends those spellings. [Google Python style guide](https://google.github.io/styleguide/pyguide.html)

10. **Support constructor documentation ownership.** Add mutually exclusive policies for documenting constructor parameters/raises in the class docstring versus `__init__`, and make PDF500–507 compare the chosen docstring with `__init__`. This is especially important for NumPy style.

11. **Check exception and warning entries for missing descriptions.** PDF308–310 style existing descriptions, but PDF7xx has no analogue to PDF700/704/708 for `Raises` or `Warns`.

12. **Check method entries for missing descriptions.** `Methods` entries are parsed and styled, but there is no completeness rule for their prose.

13. **Fully parse `See Also` entries.** Add missing-description, capitalization, punctuation, duplicate-reference, and entry-spacing checks. Numpydoc already treats these as common validation targets.

14. **Check documented method inventory.** When a class has a `Methods` section, compare it with actual public methods: missing, extraneous, duplicated, and optionally wrong order. Use the same “has-section” activation policy as PDF500 to avoid requiring such sections universally.

15. **Check attribute entry order against declaration order.** This complements PDF508–513. It should be opt-in because conceptual ordering is sometimes intentional.

16. **Respect statically known `__all__` when deciding public API.** Use simple literal `__all__` assignments to refine PDF5xx/PDF6xx public/private classification. Fall back to underscore naming when `__all__` is dynamic.

17. **Add `warnings.warn` documentation consistency.** Match statically resolvable warning categories against `Warns` entries, analogous to PDF506/507. Treat extraneous-warning checking as opt-in for the same reason PDF507 is opt-in.

18. **Treat `assert` as a possible documented `AssertionError`.** This could extend PDF506 behind a setting; pydoclint exposes a corresponding check. Avoid enabling it broadly because assertions are often internal invariants.

19. **Resolve imported exception aliases.** Normalize `raise BadInput` imported from another module against qualified documentation when the binding is statically unambiguous.

20. **Make reflow aware of inline markup.** PDF101 and PCF001 should treat Markdown links, autolinks, code spans, reST roles, interpreted-text spans, substitutions, and explicit references as atomic wrapping tokens. Current URL awareness is narrower.

21. **Preserve or canonicalize Markdown hard line breaks.** Unconditional trailing-whitespace cleanup can erase the semantic meaning of two trailing spaces. Under Markdown-aware parsing, either preserve them or replace them with an explicit safe line-break spelling.

22. **Report suspicious invisible Unicode separately from ASCII-only policy.** Catch zero-width characters, bidi controls, nonbreaking spaces in indentation, and unexpected control characters while still allowing ordinary non-ASCII prose. Safe whitespace replacements could be fixed.

23. **Validate reST directive introducers.** Report directive-looking lines using one colon instead of `.. name::`, corresponding to numpydoc’s broadly useful GL10 check.

24. **Report unbalanced fenced/inline markup.** Cover unclosed code fences, unmatched inline-code delimiters, malformed reST roles, and dangling Markdown links when recognition is unambiguous.

25. **Validate protected Python examples syntactically.** Parse doctest inputs and explicitly Python-tagged fenced blocks without executing them. Report invalid Python or malformed doctest prompts; leave actual formatting to Ruff or another formatter.

26. **Report orphan reST type fields explicitly.** Diagnose `:type name:` without `:param name:`, `:rtype:` without a return field, `:ytype:` without a yield field, and `:vartype:` without attribute documentation. Current missing-description rules catch some cases indirectly but give a less precise diagnosis.

27. **Extend typed-entry rules to attached attribute docstrings.** Parse common `Type: description` attached-docstring forms and offer description presence, type policy, and annotation mismatch checks. PDF712–719 currently cover only owner-docstring entries.

28. **Extend annotation-based checks to stubs and abstract methods.** When there is no executable body, a non-`None` return annotation or recognized generator annotation can still support missing/type-mismatch validation. Keep body-dependent exception checks disabled.

29. **Broaden conservative type equivalence.** Support quoted forward references, `Optional[T]` versus `T | None`, `Union`, `Annotated`, `Literal` values, `Required`/`NotRequired`, and other common typing wrappers. The current accepted AST subset is intentionally small; see [type_expressions.py](/home/allgeuer/Code/PythonTools/pydocformatter/src/pydocformatter/rules/definition_helpers/type_expressions.py:38).

30. **Canonicalize obvious docstring type spelling defects.** Examples: a trailing period in a type slot, lowercase `none`, or redundant outer whitespace/parentheses when normalization is AST-proven. Avoid broader `List` versus `list` policy because target-version preferences differ.

31. **Validate NumPy return-entry shape.** Check that a single return entry starts with a type and that multiple returned values use valid multi-entry structure. This corresponds to a mature numpydoc rule without requiring runtime inference.

32. **Extend generic-description checks.** Conservatively flag `The return value`, `The yielded value`, `The exception`, `The method`, and similarly content-free warning descriptions.

33. **Normalize task-marker spelling.** Recognize configured markers case-insensitively and fix `todo`, `TODO `, or `TODO -` to a configured canonical `TODO:` form while excluding prose uses of the word. Keep issue-link requirements out of the base rule.

34. **Canonicalize whitespace-only empty comments.** Normalize `#   ` to `#`. Do not alter deliberate hash separators such as `#####`.

35. **Deduplicate directive selectors and codes.** PCF003 can safely remove exact duplicate entries from `noqa`, `pydocfmt`, `ruff`, `pylint`, `type: ignore`, and similar comma/bracket lists. Sorting should be optional; deduplication is semantics-preserving.

36. **Make PCF006 usually auto-fixable.** Remove an individual unused selector while preserving used selectors and rationale text; remove the whole directive only when nothing meaningful remains and placement is unambiguous.

37. **Make forbidden-type rules sometimes fixable.** PDF702/706/710/714/718 can remove a redundant type from Google or reST syntax when a valid description-bearing entry remains. NumPy cases may remain diagnostic-only because its entry grammar expects a type slot.

38. **Add conservative fixes to PDF407.** Reorder complete, independently parsed section/field blocks while preserving their content. Do not fix when unordered narrative material creates ambiguity.

39. **Add conservative fixes to PDF406/408/412.** Remove a wholly empty section and remove later byte-equivalent duplicate sections or entries. Semantically different duplicates should remain diagnostic-only.

40. **Strengthen punctuation fixes.** PDF300/301/308/309 could optionally replace a final comma or semicolon with the configured terminal punctuation. A final colon should remain non-fixable because it may introduce content.

41. **Capitalize through simple inline markup.** Extend PDF304/PDF310 to safely capitalize inside one unambiguous leading code/emphasis/reference wrapper while preserving delimiters.

42. **Support PEP 257 additional docstrings.** Apply mechanical formatting to string literals immediately following a primary docstring. The project explicitly excludes these now, although PEP 257 recognizes them as documentation. [PEP 257](https://peps.python.org/pep-0257/)

43. **Add property-versus-Attributes documentation policies.** Optionally treat properties as class attributes and detect missing, duplicate, or wrong-location property documentation. This should be separate from ordinary stored attributes because major conventions differ.

44. **Inventory literal `__slots__` members.** When `__slots__` is a statically known string/tuple/list, include those instance attributes in class documentation checks.

45. **Add opt-in capitalization/punctuation checks for standalone prose comments.** Apply only to clearly sentence-like standalone paragraphs, excluding trailing comments, task markers, labels, directives, headings, code, and fragments. Google’s guide recommends narrative capitalization and punctuation, but this should remain optional because comment fragments are common. [Google Python style guide](https://google.github.io/styleguide/pyguide.html)

## Highest priority

- **#4 — Report missing summaries**

   Probably the best first addition. It is broadly applicable, easy to explain, diagnostic-only, and should be robust because the parser already distinguishes summaries from sections and protected structures. It fills the obvious gap between “empty docstring” and “nonempty but structurally incomplete docstring.”

- **#8 — Check parameter order against the signature**

   High value for almost every project using structured parameter documentation. The expected order is objective, the necessary signature and entry models already exist, and a diagnostic-only implementation should be straightforward. It catches documentation drift that PDF500/501 cannot.

- **#20 and #21 — Make reflow markup-safe and preserve hard breaks**

   These are the most important safety fixes. A formatter should not split inline code, roles, links, or remove intentional Markdown hard breaks. They are more complex than #4 or #8, but preventing semantic damage should take priority over adding stylistic checks.

   I would initially:

   - Protect recognized inline constructs as atomic tokens.
   - Exempt intentional two-space Markdown breaks from whitespace cleanup.
   - Add extensive value-preservation and idempotence tests before considering broader markup normalization.

- **#3 — Report malformed convention entries**

   Very useful because malformed entries currently fall out of the semantic parser and can produce misleading secondary findings—or no finding at all. Start with highly certain patterns inside already recognized sections, such as a NumPy entry missing the required space before `:`. Avoid trying to diagnose arbitrary prose.

- **#11 — Require descriptions for exceptions and warnings**

   A natural and clearly scoped completion of PDF700/704/708. The entries are already parsed, so this should mostly reuse existing missing-description infrastructure. It prevents nearly content-free documentation such as `ValueError:`.

- **#22 — Report suspicious invisible Unicode**

   Broad, safe, and complementary to the much stricter ASCII-only rules. Limit it to an explicit, carefully justified set: bidi controls, zero-width characters, nonbreaking indentation whitespace, and disallowed control characters. Many projects want Unicode prose but still want these accidental or hazardous characters detected.

- **#26 — Report orphan reST type fields explicitly**

   Narrower reach, but exceptionally clear and robust. The parser already pairs value and type fields. A precise “`:type x:` has no corresponding `:param x:`” diagnostic is far better than indirectly reporting a missing description.

## Strong second wave

- **#2 — Unknown or misspelled sections**

   Valuable, especially because an unknown heading becomes prose, but implement conservatively. Only report at unambiguous section boundaries and auto-fix only a unique, very close match. Custom headings must remain valid.

- **#16 — Respect static `__all__`**

   Important for semantic correctness of all public-documentation rules. Restrict support initially to simple literal assignments and perhaps simple `+=` extensions. Dynamic forms should fall back to current underscore-based behavior.

- **#10 — Constructor documentation ownership**

   A major correctness improvement for NumPy-style projects, where constructor parameters are often documented on the class. It is more architectural than a simple rule because PDF500–507 need a configurable effective owner, but it closes a real convention-level gap.

- **#13/#14 — `See Also` and method inventory checks**

   Good follow-ons once malformed-entry handling is established. `See Also` description validation is mature and objective; method inventory checks should activate only when a `Methods` section already exists.

- **#27 — Typed checks for attached attribute docstrings**

   Important because attached docstrings are first-class documentation elsewhere in the tool but excluded from PDF712–719. Start with description presence; type extraction and mismatch checks can follow.

## Good low-cost refinements

These are worthwhile as a small cleanup batch, though none individually has the reach of the items above:

- **#30:** Reject or normalize an obvious trailing period in a type slot.
- **#34:** Normalize whitespace-only empty comments.
- **#35:** Deduplicate directive selectors without sorting them.
- **#36:** Auto-fix unused suppression selectors while preserving rationale text.
- **#39:** Remove empty sections and byte-equivalent duplicate entries in narrowly proven cases.

Of these, **#36** offers the best user experience improvement, while **#34** is likely the simplest implementation.

## Useful, but defer

I would defer these until the earlier parser and safety work is complete:

- **#1 convention mismatch:** valuable, but heuristic and prone to cascading false positives.
- **#17 warning-call consistency:** requires reliable import/call/category resolution.
- **#25 Python example validation:** useful, but overlaps Ruff and raises questions about supported doctest syntax.
- **#29 broader type equivalence:** valuable but can grow into a substantial type-normalization subsystem.
- **#38 section-order autofix:** moving large semantic blocks deserves more caution than merely diagnosing their order.
- **#40/#41 punctuation and capitalization extensions:** comparatively stylistic.
- **#42 additional docstrings, #43 properties, #44 `__slots__`:** legitimate coverage, but lower reach.
