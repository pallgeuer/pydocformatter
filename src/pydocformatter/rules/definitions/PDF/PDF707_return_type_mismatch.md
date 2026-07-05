# return-type-mismatch (PDF707)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF706`.

## What it does
Checks that parsed return docstring types conservatively match function return annotations.

The comparison uses a small, syntax-only type-expression subset. Unparseable or ambiguous expressions are skipped instead of guessed. Generator functions are skipped by return-entry rules because their yielded values are checked by PDF711.

## Why is this useful?
Stale return type text can mislead readers when annotations have changed.

## Ruff compatibility
None.

## Examples
PDF707 reports return docstring types that do not match annotations:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> int:
    """Return a value.

    Returns:
        str: Result value.
    """
    return 1

[output=unchanged]
[findings]
PDF707: Line 5: Function return 'return' docstring type does not match the annotation
```

Matching return types are accepted, including stringized annotations and union expressions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> "tuple[str | None, ...]":
    """Return values.

    Returns:
        tuple[str | None, ...]: Result values.
    """
    return ("value",)

[output=unchanged]
```

Generator return annotations are ignored by PDF707 and checked as yield types by PDF711:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def generate() -> Iterator[str]:
    """Yield values.

    Returns:
        int: Ignored by this rule for generators.

    Yields:
        str: Next value.
    """
    yield "value"

[output=unchanged]
```

## Options
- `docstring-convention`: Google, NumPy, and reST entries are checked.
