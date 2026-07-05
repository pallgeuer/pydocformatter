# return-type-forbidden (PDF706)

Fix is not available.

Rule is ignored if `docstring-convention` is `none`, `pep257`, `google`, `numpy`, or `rest`.

Rule is incompatible with `PDF705`, `PDF707`.

## What it does
Checks that parsed return entries in owning function docstrings do not include documented types.

Generator functions are skipped by return-entry rules because their value documentation belongs in yield entries. The rule is exact opt-in and cannot be combined with the required-type or type-mismatch return policies.

## Why is this useful?
Projects that rely on code annotations can prevent duplicated return type documentation.

## Ruff compatibility
None.

## Examples
PDF706 reports return entries that include docstring type text:

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
[findings]
PDF706: Line 5: Function return 'return' docstring entry should not include a type
```

Return entries without types are accepted:

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
```

reST `:rtype:` fields are also forbidden because they provide docstring type text:

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
[findings]
PDF706: Line 5: Function return 'return' docstring entry should not include a type
```

## Options
- `docstring-convention`: The rule is exact opt-in; exact rule-code selection restores it for parsed conventions.
