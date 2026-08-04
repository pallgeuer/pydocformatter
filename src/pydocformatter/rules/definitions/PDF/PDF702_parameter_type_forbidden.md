# parameter-type-forbidden (PDF702)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF701` and `PDF703`.

## What it does
Checks that parsed parameter entries in owning function docstrings do not include documented types.

Only entries that match real signature parameters are checked. The rule is convention opt-in and cannot be combined with the required-type or type-mismatch parameter policies.

## Why is this useful?
Projects that rely on code annotations can prevent duplicated parameter type documentation.

## Ruff compatibility
None.

## Examples
PDF702 reports parameter entries that include docstring type text:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: int, timeout: float):
    """Connect to the service.

    Args:
        value (int): Endpoint identifier.
        timeout: Timeout in seconds.
    """

[output=unchanged]
[findings]
PDF702: Line 5: Function parameter 'value' docstring entry should not include a type
```

Parameter entries without types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: int):
    """Connect to the service.

    Args:
        value: Input value.
    """

[output=unchanged]
```

reST `:type:` fields are also forbidden because they provide docstring type text:

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
[findings]
PDF702: Line 5: Function parameter 'value' docstring entry should not include a type
```

## Options
None.
