# return-missing-description (PDF704)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed return entries in owning function docstrings include a prose description.

Generator functions are skipped by return-entry rules because their value documentation belongs in yield entries. Stub and abstract functions are also skipped.

An orphan reST `:rtype:` field has no return value entry whose description PDF704 could check, so PDF722 owns that structural problem.

## Why is this useful?
Return documentation should explain the meaning of the returned value.

## Ruff compatibility
None.

## Examples
PDF704 reports return entries without descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> int:
    """Return a value.

    Returns:
        int:
    """
    return 1

[output=unchanged]
[findings]
PDF704: Line 5: Function return 'return' docstring entry is missing a description
```

Return entries with descriptions are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> int:
    """Return a value.

    Returns:
        int: Result value.
    """
    return 1

[output=unchanged]
```

NumPy return entries are checked in the same way:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def function() -> int:
    """Return a value.

    Returns
    -------
    int
    """
    return 1

[output=unchanged]
[findings]
PDF704: Line 6: Function return 'return' docstring entry is missing a description
```

For reST, PDF704 reports an empty value field even when it has a paired type field. A surplus or standalone `:rtype:` field has no value description to check and is left to PDF722:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> int:
    """Return a value.

    :rtype: int
    :return:
    :rtype: str
    """
    return 1

[output=unchanged]
[findings]
PDF704: Line 5: Function return 'return' docstring entry is missing a description
```

Generator functions are not checked by return-entry rules:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def generate() -> Iterator[int]:
    """Yield values.

    Returns:
        int:
    """
    yield 1

[output=unchanged]
```

## Options
None.
