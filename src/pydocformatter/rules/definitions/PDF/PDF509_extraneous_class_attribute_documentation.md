# extraneous-class-attribute-documentation (PDF509)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that class docstring attribute entries name attributes that are present on the class.

The rule compares names documented in the class docstring against supported class attribute inventory entries. Class-scope assignments, annotated assignments, multi-target assignments, tuple-unpacked assignment leaves, supported `self.*` assignments from `__init__`, and proven members of the final effective literal `__slots__` declaration count as present. Literal slots always count for this extraneous check, independently of the setting that controls whether instance attributes are required by PDF508. Adjacent attribute docstrings are not checked by this rule because they are attached to an assignment that exists.

Only the final effective direct class-body `__slots__` binding contributes members. A dynamic, partially static, conditional, compound, deleted, or otherwise unsupported final binding contributes none; a later supported direct assignment recovers the static inventory, while an annotation-only declaration leaves the previous value effective. Evaluated identifier names retain literal order and exact decoded spelling without private-name mangling; duplicates, `__dict__`, `__weakref__`, and non-identifiers are ignored. Slots are not inherited by subclasses. List destructuring targets, unsupported tuple leaves, subscript targets, `cls.*`, arbitrary object attributes, and attributes belonging to nested classes do not satisfy documentation on the containing class.

PDF509 is an owner-docstring inventory check: it reports class docstring attribute entries for attributes that are not present. It does not report missing attributes, duplicate documentation, or a project's preferred documentation location; use PDF508, PDF512, or PDF518/PDF519 for those policies.

## Why is this useful?
Stale attribute entries can mislead readers about the documented class surface.

## Ruff compatibility
Ruff's `RUF023` sorts literal `__slots__` declarations, while `PLE0237` reports assignments to attributes absent from slots. PDF509 instead uses proven slot members to reject stale class documentation.

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

Literal slot names count only on the class that declares them and retain their exact spelling without private-name mangling. An inherited slot is therefore stale in the subclass inventory:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Base:
    __slots__ = ("x",)


class Derived(Base):
    """Derived point.

    Attributes:
        local (float): Local coordinate.
        __secret (str): Private value.
        x (float): Inherited coordinate.
    """

    __slots__ = ("local", "__secret")

[output=unchanged]
[findings]
PDF509: Line 11: Class docstring documents attribute 'x' that is not present
```

## Options
None.
