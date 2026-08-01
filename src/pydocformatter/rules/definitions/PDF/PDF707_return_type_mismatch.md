# return-type-mismatch (PDF707)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF706`.

## What it does
Checks that parsed return docstring types conservatively match function return annotations. It checks existing return entries only when both a documented type and a usable annotation are present.

The comparison uses a syntax-only type-expression subset that covers common names, qualified names, subscriptions, tuples, unions, and stringized annotations. Unshadowed import aliases are normalized before comparison. Unparseable, unsupported, or ambiguous expressions are skipped instead of guessed.

Google, NumPy, and inline or paired reStructuredText types are supported. Generator functions are skipped because their produced values are checked by PDF711, and stub or abstract functions are not treated as concrete return implementations. Findings are diagnostic-only because choosing between conflicting documentation and code requires human judgment.

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

For paired reStructuredText fields, a mismatch is reported on the `:rtype:` field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> str:
    """Return a value.

    :returns: Result value.
    :rtype: int
    """
    return "value"

[output=unchanged]
[findings]
PDF707: Line 5: Function return 'return' docstring type does not match the annotation
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
None.
