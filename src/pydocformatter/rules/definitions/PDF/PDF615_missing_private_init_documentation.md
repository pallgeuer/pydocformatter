# missing-private-init-documentation (PDF615)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule applies only when `source-context` is `module`.

## What it does
Checks for private `__init__` methods that are missing docstrings.

An `__init__` method is private when its containing class or package/module path is private.

## Why is this useful?
Private constructors can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
An `__init__` method on a private class is reported as private:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def __init__(self, timeout):
        self.timeout = timeout

[output=unchanged]
[findings]
PDF615: Line 4: Private __init__ method '_Client.__init__' is missing docstring
```

A public-looking `__init__` method in a private module path is also private:

```pydocfmt-example
[input=client/_models.py]
class Client:
    """Client."""

    def __init__(self, timeout):
        self.timeout = timeout

[output=unchanged]
[findings]
PDF615: Line 4: Private __init__ method 'Client.__init__' is missing docstring
```

A documented private `__init__` method is accepted:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def __init__(self, timeout):
        """Initialize the internal client."""
        self.timeout = timeout

[output=unchanged]
```

Public `__init__` methods are handled by PDF614 instead:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __init__(self, timeout):
        self.timeout = timeout

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Function decorator names that allow a private `__init__` method to omit a docstring.
- `docstring-forbidden-function-decorators`: Function decorator names that allow a private `__init__` method to omit a docstring because PDF616 reports docstrings on those definitions instead.
