# parameter-type-mismatch (PDF703)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF702`.

## What it does
Checks that parsed parameter docstring types conservatively match parameter annotations.

The comparison uses a small, syntax-only type-expression subset. Unparseable or ambiguous expressions are skipped instead of guessed. Only entries that match real signature parameters are checked, and NumPy entries that document multiple names are checked once per name.

## Why is this useful?
Stale parameter type text can mislead readers when annotations have changed.

## Ruff compatibility
None.

## Examples
PDF703 reports docstring parameter types that do not match annotations:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: int, timeout: float):
    """Connect to the service.

    Args:
        value (str): Endpoint identifier.
        timeout (float): Timeout in seconds.
    """

[output=unchanged]
[findings]
PDF703: Line 5: Function parameter 'value' docstring type does not match the annotation
```

Matching parameter types are accepted, including stringized annotations and union expressions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: "list[str | None]"):
    """Handle values.

    Args:
        value (list[str | None]): Values to handle.
    """

[output=unchanged]
```

NumPy entries that document multiple names are checked for each matching signature parameter:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def function(x: int, y: str):
    """Handle coordinates.

    Parameters
    ----------
    x, y : int
        Coordinate values.
    """

[output=unchanged]
[findings]
PDF703: Line 6: Function parameter 'y' docstring type does not match the annotation
```

Unparseable type expressions are ignored by mismatch checks:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: "list["):
    """Handle values.

    Args:
        value (Factory[int]()): Values to handle.
    """

[output=unchanged]
```

## Options
None.
