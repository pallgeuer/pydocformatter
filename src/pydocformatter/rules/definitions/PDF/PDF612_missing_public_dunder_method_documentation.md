# missing-public-dunder-method-documentation (PDF612)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

## What it does
Checks for public dunder methods that are missing docstrings.

The rule checks methods whose names start and end with double underscores. It excludes `__init__`, which is handled by PDF614 and PDF615. A dunder method is public when its containing class and containing module path are public.

## Why is this useful?
Dunder methods define protocol behavior and often need documentation when a project opts into that policy.

## Ruff compatibility
This rule replaces Ruff's `D105`, but uses “dunder” terminology and excludes `__init__`.

## Examples
A public dunder method without a docstring is reported:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __str__(self):
        return "client"

[output=unchanged]
[findings]
PDF612: Line 4: Public dunder method 'Client.__str__' is missing docstring
```

Async dunder methods are checked the same way:

```pydocfmt-example
[input]
class Client:
    """Client."""

    async def __aenter__(self):
        return self

[output=unchanged]
[findings]
PDF612: Line 4: Public dunder method 'Client.__aenter__' is missing docstring
```

`__init__` is intentionally excluded:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __init__(self):
        pass

[output=unchanged]
```

Names must have both leading and trailing double underscores:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __helper(self):
        pass

    def helper__(self):
        pass

[output=unchanged]
```

Private owner chains are handled by PDF613 instead:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def __str__(self):
        return "client"

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Exact function decorator names that make PDF612 allow a public dunder method to omit a docstring.
- `docstring-forbidden-function-decorators`: Exact function decorator names that make PDF612 allow a public dunder method to omit a docstring because PDF616 reports docstrings on those definitions instead.
