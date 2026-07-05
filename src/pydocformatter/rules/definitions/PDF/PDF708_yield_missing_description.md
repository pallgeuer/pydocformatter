# yield-missing-description (PDF708)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed yield entries in owning function docstrings include a prose description.

Only functions that actually contain yield expressions are checked. Stub and abstract functions are skipped.

## Why is this useful?
Yield documentation should explain the meaning of generated values.

## Ruff compatibility
None.

## Examples
PDF708 reports yield entries without descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> Iterator[int]:
    """Yield values.

    Yields:
        int:
    """
    yield 1

[output=unchanged]
[findings]
PDF708: Line 5: Function yield 'yield' docstring entry is missing a description
```

Yield entries with descriptions are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> Iterator[int]:
    """Yield values.

    Yields:
        int: Next value.
    """
    yield 1

[output=unchanged]
```

Non-generator functions are not checked by yield-entry rules:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> int:
    """Return a value.

    Yields:
        int:
    """
    return 1

[output=unchanged]
```

## Options
- `docstring-convention`: Google, NumPy, and reST entries are checked.
