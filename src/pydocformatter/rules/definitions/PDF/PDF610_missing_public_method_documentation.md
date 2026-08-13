# missing-public-method-documentation (PDF610)

Fix is not available.

Rule applies only when `source-context` is `module`.

## What it does
Checks for public non-dunder methods that are missing docstrings.

Dunder methods and `__init__` are handled by separate rules. Methods decorated with configured optional-docstring decorators, such as standard override decorators by default, may omit docstrings because inherited method documentation is usually authoritative. A method is public when its own name, containing class, and containing module path are public.

## Why is this useful?
Public methods should describe their behavior and API contract.

## Ruff compatibility
This rule replaces Ruff's `D102`.

## Examples
A public method without a docstring is reported:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def connect(self):
        pass

[output=unchanged]
[findings]
PDF610: Line 4: Public method 'Client.connect' is missing docstring
```

Common method decorators do not remove the need for a docstring:

```pydocfmt-example
[input]
class Client:
    """Client."""

    @property
    def url(self):
        return "https://example.com"

    @classmethod
    def from_config(cls):
        return cls()

    @staticmethod
    def parse(value):
        return value

[output=unchanged]
[findings]
PDF610: Line 5: Public method 'Client.url' is missing docstring
PDF610: Line 9: Public method 'Client.from_config' is missing docstring
PDF610: Line 13: Public method 'Client.parse' is missing docstring
```

Methods decorated with configured optional-docstring decorators do not have to repeat inherited documentation:

```pydocfmt-example
[input]
class Client:
    """Client."""

    @typing.override
    def connect(self):
        pass

[output=unchanged]
```

Dunder methods and `__init__` are handled by separate rules:

```pydocfmt-example
[input]
class Client:
    """Client."""

    def __str__(self):
        return "client"

    def __init__(self):
        pass

[output=unchanged]
```

Private method names and private owners are handled by PDF611 instead:

```pydocfmt-example
[input]
class _Client:
    """Client."""

    def connect(self):
        pass

class PublicClient:
    """Client."""

    def _connect(self):
        pass

[output=unchanged]
```

## Options
- `docstring-optional-function-decorators`: Function decorator names that allow a public non-dunder method to omit a docstring.
- `docstring-forbidden-function-decorators`: Function decorator names that allow a public non-dunder method to omit a docstring because PDF616 reports docstrings on those definitions instead.
