# private-class-attribute-docstring-must-be-owner (PDF522)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF514` and `PDF523`.

## What it does
Checks for attached docstrings on private class attributes when private class attribute documentation must live in the class docstring.

PDF522 checks class-scope attributes and supported `self.*` instance attributes assigned in `__init__`. Attribute names beginning with `_` are private.

PDF522 is a location policy: it reports attached private class attribute docstrings because the class docstring is required. It conflicts with PDF514, which forbids private class owner-docstring entries entirely, and with PDF523, the opposite attached-docstring policy.

## Why is this useful?
Some projects choose to document private class state in owner docstrings for internal API reference builds while avoiding scattered attached docstrings.

## Ruff compatibility
None.

## Examples
A private class attribute with an attached docstring is reported:

```pydocfmt-example
[input]
class Client:
    _token: str
    """Internal token."""

[output=unchanged]
[findings]
PDF522: Line 3: Private class attribute '_token' must use class docstring documentation, not attached docstring
```

Same-line docstrings, shared tuple-unpacked docstrings, and supported `self.*` assignments from `__init__` are checked:

```pydocfmt-example
[input]
class Client:
    _token = ""; """Internal token."""
    _primary, fallback, *_aliases = endpoints
    """Endpoint internals."""

    def __init__(self):
        self._cache = {}
        """Internal cache."""

[output=unchanged]
[findings]
PDF522: Line 2: Private class attribute '_token' must use class docstring documentation, not attached docstring
PDF522: Line 4: Private class attribute '_primary' must use class docstring documentation, not attached docstring
PDF522: Line 4: Private class attribute '_aliases' must use class docstring documentation, not attached docstring
PDF522: Line 8: Private class attribute '_cache' must use class docstring documentation, not attached docstring
```

Public attributes, repeated targets in one assignment, and unsupported targets are handled by target name:

```pydocfmt-example
[input]
class Client:
    timeout: float
    """Public timeout."""

    _token, _token = values
    """Internal token."""

    items[0] = ""
    """Ignored subscript target."""

[output=unchanged]
[findings]
PDF522: Line 6: Private class attribute '_token' must use class docstring documentation, not attached docstring
```

## Options
- `require-explicit`: Keeps PDF522 out of broad rule selections by default. Exact rule-code selection enables it.
