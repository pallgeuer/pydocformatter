# return-missing-description (PDF704)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed return entries in owning function docstrings include a prose description.

Generator functions are skipped by return-entry rules because their value documentation belongs in yield entries. Stub and abstract functions are also skipped.

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

reST `:rtype:` fields provide type text but not prose descriptions:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> int:
    """Return a value.

    :rtype: int
    """
    return 1

[output=unchanged]
[findings]
PDF704: Line 4: Function return 'return' docstring entry is missing a description
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
