# missing-public-class-documentation (PDF604)

Fix is not available.

## What it does
Checks for public top-level classes that are missing docstrings.

Nested classes are handled by the nested-class rules, and local classes inside functions are ignored. A top-level class is public when its own name and containing module path are public.

## Why is this useful?
Public classes should describe their purpose and behavior.

## Ruff compatibility
This rule replaces Ruff's `D101`.

## Examples
A public top-level class without a docstring is reported:

```pydocfmt-example
[input]
class Client:
    pass

[output=unchanged]
[findings]
PDF604: Line 1: Public class 'Client' is missing docstring
```

A documented public top-level class is accepted:

```pydocfmt-example
[input]
class Client:
    """Client API."""

[output=unchanged]
```

Nested classes are handled by PDF606 and PDF607 instead:

```pydocfmt-example
[input]
class Client:
    """Client API."""

    class Response:
        pass

[output=unchanged]
```

Private class names and private module paths are handled by PDF605 instead:

```pydocfmt-example
[input=client/_models.py]
class Client:
    pass

class _PrivateClient:
    pass

[output=unchanged]
```

## Options
None.
