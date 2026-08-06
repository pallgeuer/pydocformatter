# rule-names-in-suppression-comments (PCF009)

Fix is sometimes available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PCF008`.

## What it does

Checks bracketed pydocfmt and Ruff suppression comments for rule names when a project prefers rule codes. For pydocfmt, the rule checks `ignore[...]` and `file-ignore[...]`; for Ruff, it checks `ignore[...]`, `file-ignore[...]`, `disable[...]`, and `enable[...]`. Each affected directive produces one finding, even when it contains several names.

Known exact pydocfmt names can be replaced automatically while preserving the surrounding directive syntax and unrelated selectors. Code and name aliases for a converted local rule are deduplicated by their shared identity, while unrelated duplicates remain unchanged; PCF003 owns general list deduplication when selected. Broad pydocfmt selectors are already code selectors and remain permitted; unknown and invalid pydocfmt selectors are left to PCF006. Comments with unrecognized pydocfmt actions are ignored.

Ruff name-shaped selectors are diagnosed without a fix because pydocformatter does not own Ruff's rule catalog. This distinction between fixable local findings and diagnostic-only Ruff findings is why fixes are only sometimes available.

## Why is this useful?

Rule codes provide a compact, consistent suppression representation for projects whose tooling and review conventions are code-oriented.

## Ruff compatibility

This rule is the inverse local policy to PCF008. Ruff does not provide an equivalent rule that requires names to be converted to codes in suppression comments.

## Examples

In the canonical case, an exact pydocfmt rule name is replaced with its canonical code:

```pydocfmt-example
[input]
# pydocfmt: ignore[docstring-reflow]
value = 1

[output]
# pydocfmt: ignore[PDF101]
value = 1
```

Multiple exact names in one directive are fixed together. Broad, unknown, and invalid selectors remain unchanged, and trailing rationale text is preserved:

```pydocfmt-example
[input]
# pydocfmt: file-ignore[PDF, docstring-reflow, standalone-comment-formatting, future-rule, bad!]  # generated
value = 1

[output]
# pydocfmt: file-ignore[PDF, PDF101, PCF001, future-rule, bad!]  # generated
value = 1
```

Name and code aliases denote one local rule. The first occurrence determines the retained position, and the result uses the required code representation:

```pydocfmt-example
[input]
# pydocfmt: ignore[docstring-reflow, PDF101, standalone-comment-formatting]
value = 1

[output]
# pydocfmt: ignore[PDF101, PCF001]
value = 1
```

Ruff names are reported without changing the comment. Code-shaped Ruff selectors in the same directive are permitted:

```pydocfmt-example
[input]
# ruff: ignore[unused-import, F401]
value = 1
# ruff: disable[too-many-arguments]
call()
# ruff: enable[too-many-arguments]

[output=unchanged]
[findings]
PCF009: Line 1: Suppression comment should use rule codes instead of names
PCF009: Line 3: Suppression comment should use rule codes instead of names
PCF009: Line 5: Suppression comment should use rule codes instead of names
```

Broad pydocfmt selectors and comments with unrecognized pydocfmt actions do not trigger the rule:

```pydocfmt-example
[input]
# pydocfmt: ignore[ALL, PDF, PDF6, future-rule, bad!]
# pydocfmt: disable[docstring-reflow]  # Unsupported by pydocfmt.
value = 1
# pydocfmt: enable[docstring-reflow]  # Unsupported by pydocfmt.

[output=unchanged]
```

## Options

None.
