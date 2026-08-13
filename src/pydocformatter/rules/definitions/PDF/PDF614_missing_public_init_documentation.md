# missing-public-init-documentation (PDF614)

Fix is not available.

Rule applies only when `source-context` is `module`.

## What it does
Checks for public `__init__` methods that are missing docstrings.

The rule is separate from dunder-method checks so projects can select constructor documentation independently. An `__init__` method is public when its containing class and containing module path are public.

## Why is this useful?
Constructors often define required initialization arguments and side effects.

## Ruff compatibility
This rule replaces Ruff's `D107`.

## Examples
A public `__init__` method without a docstring is reported:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __init__(self, timeout):
        self.timeout = timeout

[output=unchanged]
[findings]
PDF614: Line 4: Public __init__ method 'Client.__init__' is missing docstring
```

A documented public `__init__` method is accepted:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __init__(self, timeout):
        """Initialize the client."""
        self.timeout = timeout

[output=unchanged]
```

Other dunder methods are handled by PDF612 and PDF613 instead:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __str__(self):
        return "client"

[output=unchanged]
```

Private owner chains are handled by PDF615 instead:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def __init__(self, timeout):
        self.timeout = timeout

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Function decorator names that allow a public `__init__` method to omit a docstring.
- `docstring-forbidden-function-decorators`: Function decorator names that allow a public `__init__` method to omit a docstring because PDF616 reports docstrings on those definitions instead.
