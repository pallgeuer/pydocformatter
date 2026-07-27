# yield-missing-description (PDF708)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed yield entries in owning function docstrings include a prose description.

Only functions that actually contain yield expressions are checked. Stub and abstract functions are skipped.

An orphan reST `:ytype:` field has no yield value entry whose description PDF708 could check, so PDF722 owns that structural problem.

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

NumPy yield entries are checked in the same way:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def function() -> Iterator[int]:
    """Yield values.

    Yields
    ------
    int
    """
    yield 1

[output=unchanged]
[findings]
PDF708: Line 6: Function yield 'yield' docstring entry is missing a description
```

For reST, PDF708 reports an empty value field even when it has a paired type field. A surplus or standalone `:ytype:` field has no value description to check and is left to PDF722:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> Iterator[int]:
    """Yield values.

    :ytype: int
    :yield:
    :ytype: str
    """
    yield 1

[output=unchanged]
[findings]
PDF708: Line 5: Function yield 'yield' docstring entry is missing a description
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
None.
