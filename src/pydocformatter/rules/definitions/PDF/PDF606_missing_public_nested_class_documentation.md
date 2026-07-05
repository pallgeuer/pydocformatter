# missing-public-nested-class-documentation (PDF606)

Fix is not available.

## What it does
Checks for public classes nested directly in public classes that are missing docstrings.

Top-level classes are handled by the class rules, and local classes inside functions are ignored. A nested class is public when its own name, all ancestor class names, and the containing module path are public.

## Why is this useful?
Nested classes do not inherit the docstring of their containing class.

## Ruff compatibility
This rule replaces Ruff's `D106`.

## Examples
A public nested class without a docstring is reported:

```pydocfmt-example
[input]
class Client:
    """Client."""

    class Response:
        pass

[output=unchanged]
[findings]
PDF606: Line 4: Public nested class 'Client.Response' is missing docstring
```

Multiple public nested classes are reported independently:

```pydocfmt-example
[input]
class Client:
    """Client."""

    class Response:
        class Payload:
            pass

[output=unchanged]
[findings]
PDF606: Line 4: Public nested class 'Client.Response' is missing docstring
PDF606: Line 5: Public nested class 'Client.Response.Payload' is missing docstring
```

Top-level classes and local classes are not nested-class targets:

```pydocfmt-example
[input]
class Client:
    pass

def build():
    class Local:
        pass

[output=unchanged]
```

Nested classes under a private owner are handled by PDF607 instead:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    class Response:
        pass

[output=unchanged]
```

## Options
None.
