# parameter-missing-description (PDF700)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed parameter entries in owning function docstrings include a prose description.

Only entries that match real signature parameters are checked. Implicit `self` and `cls` receivers are ignored, while variadic names such as `*items` and `**options` match their signature parameters with or without the leading stars.

## Why is this useful?
Parameter entries without descriptions add structure without explaining caller-facing semantics.

## Ruff compatibility
None.

## Examples
PDF700 reports parameter entries that have a name and optional type but no description:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: int, *, timeout: float):
    """Connect to the service.

    Args:
        value (int):
        timeout:
    """

[output=unchanged]
[findings]
PDF700: Line 5: Function parameter 'value' docstring entry is missing a description
PDF700: Line 6: Function parameter 'timeout' docstring entry is missing a description
```

Entries with descriptions are accepted, and implicit receivers are ignored:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client."""

    def connect(self, value: int):
        """Connect to the service.

        Args:
            value (int): Endpoint identifier.
        """

[output=unchanged]
```

Variadic parameter entries match the corresponding signature parameters:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def configure(*items: int, **options: str):
    """Configure values.

    Args:
        *items (int):
        **options (str): Option values.
    """

[output=unchanged]
[findings]
PDF700: Line 5: Function parameter '*items' docstring entry is missing a description
```

## Options
None.
