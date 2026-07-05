# return-type-required (PDF705)

Fix is not available.

Rule is ignored if `docstring-convention` is `none`, `pep257`, `google`, `numpy`, or `rest`.

Rule is incompatible with `PDF706`.

## What it does
Checks that parsed return entries in owning function docstrings include a documented type.

Generator functions are skipped by return-entry rules because their value documentation belongs in yield entries. The rule is exact opt-in because many projects rely on function annotations instead of repeating return types in docstrings.

## Why is this useful?
Projects that keep return types in docstrings can enforce complete return type documentation.

## Ruff compatibility
None.

## Examples
PDF705 reports return entries without docstring types:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> int:
    """Return a value.

    :returns: Result value.
    """
    return 1

[output=unchanged]
[findings]
PDF705: Line 4: Function return 'return' docstring entry is missing a type
```

Return entries with types are accepted:

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

reST `:rtype:` fields provide the type for a paired `:returns:` field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> int:
    """Return a value.

    :returns: Result value.
    :rtype: int
    """
    return 1

[output=unchanged]
```

## Options
- `docstring-convention`: The rule is exact opt-in; exact rule-code selection restores it for parsed conventions.
