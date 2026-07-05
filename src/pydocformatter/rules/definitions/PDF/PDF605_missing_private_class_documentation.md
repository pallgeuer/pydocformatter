# missing-private-class-documentation (PDF605)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

## What it does
Checks for private top-level classes that are missing docstrings.

A top-level class is private when its own name or containing module path is private.

## Why is this useful?
Private classes can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
A private top-level class without a docstring is reported:

```pydocfmt-example
[input]
class _Client:
    pass

[output=unchanged]
[findings]
PDF605: Line 1: Private class '_Client' is missing docstring
```

A public-looking class in a private module path is private:

```pydocfmt-example
[input=client/_models.py]
class Client:
    pass

[output=unchanged]
[findings]
PDF605: Line 1: Private class 'Client' is missing docstring
```

A documented private top-level class is accepted:

```pydocfmt-example
[input]
class _Client:
    """Internal client."""

[output=unchanged]
```

Public top-level classes are handled by PDF604 instead:

```pydocfmt-example
[input]
class Client:
    pass

[output=unchanged]
```

## Options
None.
