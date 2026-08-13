# missing-private-method-documentation (PDF611)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule applies only when `source-context` is `module`.

## What it does
Checks for private non-dunder methods that are missing docstrings.

A method is private when its own name, containing class, or package/module path is private. Dunder methods and `__init__` are handled by separate rules. Methods decorated with configured optional-docstring decorators, such as standard override decorators by default, may omit docstrings because inherited method documentation is usually authoritative.

## Why is this useful?
Private methods can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
A private method without a docstring is reported:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def _connect(self):
        pass

[output=unchanged]
[findings]
PDF611: Line 4: Private method 'Client._connect' is missing docstring
```

A public-looking method under a private class is private:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def connect(self):
        pass

[output=unchanged]
[findings]
PDF611: Line 4: Private method '_Client.connect' is missing docstring
```

A public-looking method in a private module path is also private:

```pydocfmt-example
[input=client/_models.py]
class Client:
    """Client."""

    def connect(self):
        pass

[output=unchanged]
[findings]
PDF611: Line 4: Private method 'Client.connect' is missing docstring
```

Override methods and documented private methods are accepted:

```pydocfmt-example
[input]
class Client:
    """Client."""

    @typing.override
    def _connect(self):
        pass

    def _close(self):
        """Close internally."""

[output=unchanged]
```

Public non-dunder methods are handled by PDF610 instead:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def connect(self):
        pass

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Function decorator names that allow a private non-dunder method to omit a docstring.
- `docstring-forbidden-function-decorators`: Function decorator names that allow a private non-dunder method to omit a docstring because PDF616 reports docstrings on those definitions instead.
