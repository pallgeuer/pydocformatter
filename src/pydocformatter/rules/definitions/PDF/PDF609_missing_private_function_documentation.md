# missing-private-function-documentation (PDF609)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

## What it does
Checks for private top-level functions that are missing docstrings.

A top-level function is private when its own name or containing module path is private.

## Why is this useful?
Private functions can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
A private top-level function without a docstring is reported:

```pydocfmt-example
[input]
def _connect():
    pass

[output=unchanged]
[findings]
PDF609: Line 1: Private function '_connect' is missing docstring
```

A public-looking function in a private module path is private:

```pydocfmt-example
[input=client/_helpers.py]
def connect():
    pass

[output=unchanged]
[findings]
PDF609: Line 1: Private function 'connect' is missing docstring
```

Async private top-level functions are checked the same way:

```pydocfmt-example
[input]
async def _connect():
    pass

[output=unchanged]
[findings]
PDF609: Line 1: Private function '_connect' is missing docstring
```

A documented private top-level function is accepted:

```pydocfmt-example
[input]
def _connect():
    """Connect internally."""

[output=unchanged]
```

Public top-level functions are handled by PDF608 instead:

```pydocfmt-example
[input]
def connect():
    pass

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Function decorator names that allow a private top-level function to omit a docstring.
- `docstring-forbidden-function-decorators`: Function decorator names that allow a private top-level function to omit a docstring because PDF616 reports docstrings on those definitions instead.
