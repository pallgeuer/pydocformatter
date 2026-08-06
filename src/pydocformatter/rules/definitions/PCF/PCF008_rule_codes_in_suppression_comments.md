# rule-codes-in-suppression-comments (PCF008)

Fix is sometimes available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PCF009`.

## What it does

Checks bracketed pydocfmt and Ruff suppression comments for rule codes when a project prefers rule names. For pydocfmt, the rule checks `ignore[...]` and `file-ignore[...]`; for Ruff, it checks `ignore[...]`, `file-ignore[...]`, `disable[...]`, and `enable[...]`. Each affected directive produces one finding, even when it contains several codes.

Known exact pydocfmt codes can be replaced automatically while preserving the surrounding directive syntax and unrelated selectors. Code and name aliases for a converted local rule are deduplicated by their shared identity, while unrelated duplicates remain unchanged; PCF003 owns general list deduplication when selected. Broad pydocfmt selectors such as `ALL`, `PDF`, and `PDF6` remain permitted because no single rule name has equivalent semantics; unknown and invalid pydocfmt selectors are left to PCF006. Comments with unrecognized pydocfmt actions are ignored.

Exact Ruff code-shaped selectors such as `F401` and `PLR0913` are diagnosed without a fix because pydocformatter does not own Ruff's rule catalog. Broad Ruff selectors such as `F`, `PLR`, and `ALL` remain permitted because no single rule name has equivalent semantics. This distinction between fixable local findings and diagnostic-only Ruff findings is why fixes are only sometimes available.

## Why is this useful?

Canonical rule names make suppression intent readable without consulting a code index and establish a consistent project-wide suppression style.

## Ruff compatibility

This rule complements Ruff's [RUF106](https://docs.astral.sh/ruff/rules/rule-codes-in-suppression-comments/). Ruff can convert its own exact codes because it owns the relevant catalog; pydocformatter intentionally reports exact Ruff codes without fixing them and permits broad Ruff selectors consistently with RUF106.

## Examples

In the canonical case, an exact pydocfmt code is replaced with its canonical rule name:

```pydocfmt-example
[input]
# pydocfmt: ignore[PDF101]
value = 1

[output]
# pydocfmt: ignore[docstring-reflow]
value = 1
```

Multiple exact codes in one directive are fixed together. Broad, unknown, and invalid selectors remain unchanged, and trailing rationale text is preserved:

```pydocfmt-example
[input]
# pydocfmt: file-ignore[PDF, PDF101, PCF001, future-rule, bad!]  # generated
value = 1

[output]
# pydocfmt: file-ignore[PDF, docstring-reflow, standalone-comment-formatting, future-rule, bad!]  # generated
value = 1
```

Code and name aliases denote one local rule. The first occurrence determines the retained position, and the result uses the required name representation:

```pydocfmt-example
[input]
# pydocfmt: ignore[PDF101, docstring-reflow, PCF001]
value = 1

[output]
# pydocfmt: ignore[docstring-reflow, standalone-comment-formatting]
value = 1
```

Ruff codes are reported without changing the comment. Name-shaped Ruff selectors in the same directive are permitted:

```pydocfmt-example
[input]
# ruff: ignore[F401, unused-import]
value = 1
# ruff: disable[PLR0913]
call()
# ruff: enable[PLR0913]

[output=unchanged]
[findings]
PCF008: Line 1: Suppression comment should use rule names instead of codes
PCF008: Line 3: Suppression comment should use rule names instead of codes
PCF008: Line 5: Suppression comment should use rule names instead of codes
```

Broad pydocfmt and Ruff selectors and comments with unrecognized pydocfmt actions do not trigger the rule:

```pydocfmt-example
[input]
# pydocfmt: ignore[ALL, PDF, PDF6, future-rule, bad!]
# pydocfmt: disable[PDF101]  # Unsupported by pydocfmt.
value = 1
# pydocfmt: enable[PDF101]  # Unsupported by pydocfmt.
# ruff: ignore[F, PLR, ALL]

[output=unchanged]
```

## Options

None.
