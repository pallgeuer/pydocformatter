# missing-private-nested-class-documentation (PDF607)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

## What it does
Checks for private classes nested directly in classes that are missing docstrings.

A nested class is private when its own name, an ancestor class name, or the package/module path is private.

## Why is this useful?
Private nested classes can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
A private nested class without a docstring is reported:

```pydocfmt-example
[input]
class Client:
    """Client."""

    class _Response:
        pass

[output=unchanged]
[findings]
PDF607: Line 4: Private nested class 'Client._Response' is missing docstring
```

A public-looking nested class under a private top-level class is private:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    class Response:
        pass

[output=unchanged]
[findings]
PDF607: Line 4: Private nested class '_Client.Response' is missing docstring
```

A public-looking nested class in a private module path is also private:

```pydocfmt-example
[input=client/_models.py]
class Client:
    """Client."""

    class Response:
        pass

[output=unchanged]
[findings]
PDF607: Line 4: Private nested class 'Client.Response' is missing docstring
```

A documented private nested class is accepted:

```pydocfmt-example
[input]
class Client:
    """Client."""

    class _Response:
        """Internal response."""

[output=unchanged]
```

Public nested classes are handled by PDF606 instead:

```pydocfmt-example
[input]
class Client:
    """Client."""

    class Response:
        pass

[output=unchanged]
```

## Options
None.
