# parameter-type-mismatch (PDF703)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF702`.

## What it does
Checks that parsed parameter docstring types conservatively match parameter annotations. It checks only entries that match real signature parameters and have both a documented type and a usable annotation.

The comparison uses a syntax-only type-expression subset that covers common names, qualified names, subscriptions, tuples, unions, and stringized annotations. Unshadowed import aliases are normalized before comparison. Unparseable, unsupported, or ambiguous expressions are skipped instead of guessed.

Google, NumPy, and inline or paired reStructuredText types are supported. NumPy entries that document multiple names are checked once per matching parameter, so one shared type can produce a finding for only the names whose annotations differ. Findings are diagnostic-only because choosing between conflicting documentation and code requires human judgment.

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

For paired reStructuredText fields, a mismatch is reported on the type field rather than the value field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function(value: int):
    """Handle a value.

    :param value: Value to handle.
    :type value: str
    """

[output=unchanged]
[findings]
PDF703: Line 5: Function parameter 'value' docstring type does not match the annotation
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

Unparseable type expressions are ignored rather than compared speculatively:

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
