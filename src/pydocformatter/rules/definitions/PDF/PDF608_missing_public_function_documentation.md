# missing-public-function-documentation (PDF608)

Fix is not available.

## What it does
Checks for public top-level functions that are missing docstrings.

Methods are handled by the method rules, and local functions inside functions are ignored. A top-level function is public when its own name and containing module path are public.

## Why is this useful?
Public functions should describe their behavior and API contract.

## Ruff compatibility
This rule replaces Ruff's `D103`.

## Examples
A public top-level function without a docstring is reported:

```pydocfmt-example
[input]
def connect():
    pass

[output=unchanged]
[findings]
PDF608: Line 1: Public function 'connect' is missing docstring
```

Async top-level functions are checked the same way:

```pydocfmt-example
[input]
async def connect():
    pass

[output=unchanged]
[findings]
PDF608: Line 1: Public function 'connect' is missing docstring
```

A documented public top-level function is accepted:

```pydocfmt-example
[input]
def connect():
    """Connect to the service."""

[output=unchanged]
```

Methods and local functions are not top-level function targets:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def connect(self):
        pass

def build():
    """Build a client."""

    def inner():
        pass

[output=unchanged]
```

Private function names and private module paths are handled by PDF609 instead:

```pydocfmt-example
[input=client/_helpers.py]
def connect():
    pass

def _connect():
    pass

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Function decorator names that allow a public top-level function to omit a docstring.
- `docstring-forbidden-function-decorators`: Function decorator names that allow a public top-level function to omit a docstring because PDF616 reports docstrings on those definitions instead.
