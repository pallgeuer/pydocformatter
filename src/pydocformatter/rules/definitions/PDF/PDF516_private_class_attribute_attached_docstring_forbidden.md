# private-class-attribute-attached-docstring-forbidden (PDF516)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF523`.

## What it does
Checks for attached docstrings on private class attributes.

PDF516 checks attached docstrings for class-scope attributes and supported `self.*` instance attributes assigned in `__init__`. Class-scope assignments, annotated assignments, same-line docstrings, next-line docstrings, concatenated string docstrings, multi-target assignments, and tuple-unpacked assignment leaves are matched by target name. Attribute names beginning with `_` are private, including dunder-style names such as `__slots__`.

The rule reports on the attached docstring source lines. When one attached docstring belongs to multiple private targets, each private target is reported. When the same private target has multiple attached docstrings, each attached docstring is reported. The `docstring-require-init-attribute-documentation` setting does not affect PDF516; supported `self.*` docstrings in `__init__` are always checked when the rule is selected.

Assignments inside methods other than `__init__`, nested class attributes owned by another class, list destructuring targets, unsupported tuple leaves, subscript targets, `cls.*`, arbitrary object attributes, bytes literals, and f-strings are not class attribute docstrings for this rule.

PDF516 forbids attached docstrings on private class attributes. If the project instead wants private class attributes documented in class docstrings, use PDF522; if it wants private class attributes documented by attached docstrings, use PDF523 and do not enable PDF516.

## Why is this useful?
Private class and instance attributes are implementation details and should usually be documented with nearby comments or internal design documentation rather than API docstrings.

## Ruff compatibility
None.

## Examples
An attached docstring on a private class attribute is reported:

```pydocfmt-example
[input]
class Client:
    _token: str
    """Internal token."""

    timeout: float
    """Request timeout in seconds."""

[output=unchanged]
[findings]
PDF516: Line 3: Private class attribute '_token' should not have an attached docstring
```

Supported `self.*` assignments in `__init__` are checked:

```pydocfmt-example
[input]
class Client:
    def __init__(self):
        self._token = ""
        """Internal token."""

    def configure(self):
        self._cache = {}
        """Ignored non-init instance attribute docstring."""

[output=unchanged]
[findings]
PDF516: Line 4: Private class attribute '_token' should not have an attached docstring
```

Same-line and concatenated attached docstrings are also checked:

```pydocfmt-example
[input]
class Client:
    _token = ""; """Class token."""

    _cache: dict[str, object]
    """Internal """ "cache."

[output=unchanged]
[findings]
PDF516: Line 2: Private class attribute '_token' should not have an attached docstring
PDF516: Line 5: Private class attribute '_cache' should not have an attached docstring
```

Attached docstrings shared by multiple targets report each private target. Repeated private attributes with separate attached docstrings are reported separately:

```pydocfmt-example
[input]
class Client:
    _primary, (fallback, *_aliases) = endpoints
    """Endpoint internals."""

    _primary = fallback
    """Fallback endpoint."""

[output=unchanged]
[findings]
PDF516: Line 3: Private class attribute '_primary' should not have an attached docstring
PDF516: Line 3: Private class attribute '_aliases' should not have an attached docstring
PDF516: Line 6: Private class attribute '_primary' should not have an attached docstring
```

Dunder-style names are private because they begin with `_`:

```pydocfmt-example
[input]
class Client:
    __slots__ = ("_token",)
    """Slot names."""

[output=unchanged]
[findings]
PDF516: Line 3: Private class attribute '__slots__' should not have an attached docstring
```

Unsupported assignment targets, non-`__init__` instance assignments, bytes literals, and f-strings are ignored:

```pydocfmt-example
[input]
class Client:
    items[0] = ""
    """Subscript target."""

    [_name] = values
    """List destructuring target."""

    def configure(self):
        self._cache = {}
        """Ignored non-init instance attribute docstring."""

    _bytes = b""
    b"Bytes are not docstrings."

    _formatted = ""
    f"Formatted {value}"

[output=unchanged]
```

## Options
None.
