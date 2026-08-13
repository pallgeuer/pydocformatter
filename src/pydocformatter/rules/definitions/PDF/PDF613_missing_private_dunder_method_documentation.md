# missing-private-dunder-method-documentation (PDF613)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule applies only when `source-context` is `module`.

## What it does
Checks for private dunder methods that are missing docstrings.

A dunder method is private when its containing class or package/module path is private. The rule excludes `__init__`, which is handled by PDF614 and PDF615.

## Why is this useful?
Private dunder methods can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
A dunder method on a private class is reported as private:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def __str__(self):
        return "client"

[output=unchanged]
[findings]
PDF613: Line 4: Private dunder method '_Client.__str__' is missing docstring
```

A dunder method in a private module path is also private:

```pydocfmt-example
[input=client/_models.py]
class Client:
    """Client."""

    def __str__(self):
        return "client"

[output=unchanged]
[findings]
PDF613: Line 4: Private dunder method 'Client.__str__' is missing docstring
```

`__init__` is intentionally excluded:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def __init__(self):
        pass

[output=unchanged]
```

A documented private dunder method is accepted:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def __str__(self):
        """Return the display name."""
        return "client"

[output=unchanged]
```

Public dunder methods are handled by PDF612 instead:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __str__(self):
        return "client"

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Function decorator names that allow a private dunder method to omit a docstring.
- `docstring-forbidden-function-decorators`: Function decorator names that allow a private dunder method to omit a docstring because PDF616 reports docstrings on those definitions instead.
