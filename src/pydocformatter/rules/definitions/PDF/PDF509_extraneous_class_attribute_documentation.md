# extraneous-class-attribute-documentation (PDF509)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that class docstring attribute entries name attributes that are present on the class.

The rule compares names documented in the class docstring against supported class attribute inventory entries. Class-scope assignments, annotated assignments, multi-target assignments, tuple-unpacked assignment leaves, and supported `self.*` assignments from `__init__` count as present. Adjacent attribute docstrings are not checked by this rule because they are attached to an assignment that exists.

List destructuring targets, unsupported tuple leaves, subscript targets, `cls.*`, arbitrary object attributes, and attributes belonging to nested classes do not satisfy documentation on the containing class.

## Why is this useful?
Stale attribute entries can mislead readers about the documented class surface.

## Ruff compatibility
None.

## Examples
Stale class attribute entries are reported when the documented name is absent from the class inventory:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        timeout (float): Request timeout.
        stale (object): Removed attribute.
    """

    timeout: float

[output=unchanged]
[findings]
PDF509: Line 6: Class docstring documents attribute 'stale' that is not present
```

`self.*` assignments from `__init__` and private class attributes count as present when they are documented:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        timeout (float): Request timeout.
        _token (str): Internal token.
    """

    _token: str

    def __init__(self):
        self.timeout = 30.0

[output=unchanged]
```

Multi-target assignments and tuple-unpacked assignments make each supported target present:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        primary (str): Primary endpoint.
        fallback (str): Fallback endpoint.
        aliases (tuple[str, ...]): Endpoint aliases.
    """

    primary = fallback = "https://example.com"
    primary, (fallback, *aliases) = endpoints

[output=unchanged]
```

NumPy comma-separated entries are checked name by name, so a single entry line can contain both present and stale names:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """HTTP client.

    Attributes
    ----------
    primary, stale : str
        Request endpoints.
    """

    primary: str

[output=unchanged]
[findings]
PDF509: Line 6: Class docstring documents attribute 'stale' that is not present
```

Unsupported assignment targets do not make a documented attribute present:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        primary (str): Primary endpoint.
    """

    [primary, fallback] = endpoints

[output=unchanged]
[findings]
PDF509: Line 5: Class docstring documents attribute 'primary' that is not present
```

Attributes on nested classes do not satisfy documentation on the outer class:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Outer:
    """Outer client.

    Attributes:
        inner_timeout (float): Inner timeout.
    """

    class Inner:
        inner_timeout: float

[output=unchanged]
[findings]
PDF509: Line 5: Class docstring documents attribute 'inner_timeout' that is not present
```

## Options
- `docstring-convention`: Controls whether Google `Attributes` sections, NumPy `Attributes` sections, or reST attribute fields are parsed. Ignored by broad rule selections under `none` and `pep257`.
