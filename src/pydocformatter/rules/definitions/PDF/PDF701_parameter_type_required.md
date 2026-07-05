# parameter-type-required (PDF701)

Fix is not available.

Rule is ignored if `docstring-convention` is `none`, `pep257`, `google`, `numpy`, or `rest`.

Rule is incompatible with `PDF702`.

## What it does
Checks that parsed parameter entries in owning function docstrings include a documented type.

Only entries that match real signature parameters are checked. The rule is exact opt-in because many projects rely on code annotations instead of repeating parameter types in docstrings.

## Why is this useful?
Projects that keep types in docstrings can enforce complete parameter type documentation.

## Ruff compatibility
None.

## Examples
PDF701 reports matching parameter entries without docstring types:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: int, timeout: float):
    """Connect to the service.

    Args:
        value: Endpoint identifier.
        timeout (float): Timeout in seconds.
    """

[output=unchanged]
[findings]
PDF701: Line 5: Function parameter 'value' docstring entry is missing a type
```

Google and NumPy entries with types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def function(value: int, timeout: float):
    """Connect to the service.

    Parameters
    ----------
    value : int
        Endpoint identifier.
    timeout : float
        Timeout in seconds.
    """

[output=unchanged]
```

reST `:type:` fields provide the type even when the value field contains only prose:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function(value: int):
    """Connect to the service.

    :param value: Endpoint identifier.
    :type value: int
    """

[output=unchanged]
```

## Options
- `docstring-convention`: The rule is exact opt-in; exact rule-code selection restores it for parsed conventions.
