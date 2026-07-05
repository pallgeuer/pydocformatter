# private-module-attribute-docstring (PDF517)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

## What it does
Checks for attached docstrings on private module attributes.

PDF517 checks attached docstrings for supported module-scope attributes. Module assignments, annotated assignments, same-line docstrings, next-line docstrings, concatenated string docstrings, multi-target assignments, and tuple-unpacked assignment leaves are matched by target name. Attribute names beginning with `_` are private, including dunder-style names such as `__all__`.

The rule reports on the attached docstring source lines. When one attached docstring belongs to multiple private targets, each private target is reported. When the same private target has multiple attached docstrings, each attached docstring is reported.

Class attributes, function-local assignments, list destructuring targets, unsupported tuple leaves, subscript targets, arbitrary object attributes, bytes literals, and f-strings are not module attribute docstrings for this rule.

## Why is this useful?
Private module attributes are implementation details and should usually be documented with nearby comments or internal design documentation rather than API docstrings.

## Ruff compatibility
None.

## Examples
An attached docstring on a private module attribute is reported:

```pydocfmt-example
[input]
_token: str
"""Internal token."""

timeout: float
"""Request timeout in seconds."""

[output=unchanged]
[findings]
PDF517: Line 2: Private module attribute '_token' should not have an attached docstring
```

Same-line and concatenated attached docstrings are also checked:

```pydocfmt-example
[input]
_token = ""; """Internal token."""

_cache: dict[str, object]
"""Internal """ "cache."

[output=unchanged]
[findings]
PDF517: Line 1: Private module attribute '_token' should not have an attached docstring
PDF517: Line 4: Private module attribute '_cache' should not have an attached docstring
```

Attached docstrings shared by multiple targets report each private target. Repeated private attributes with separate attached docstrings are reported separately:

```pydocfmt-example
[input]
_primary, (fallback, *_aliases) = endpoints
"""Endpoint internals."""

_primary = fallback
"""Fallback endpoint."""

[output=unchanged]
[findings]
PDF517: Line 2: Private module attribute '_primary' should not have an attached docstring
PDF517: Line 2: Private module attribute '_aliases' should not have an attached docstring
PDF517: Line 5: Private module attribute '_primary' should not have an attached docstring
```

Dunder-style names are private because they begin with `_`:

```pydocfmt-example
[input]
__all__ = ("Client",)
"""Export names."""

[output=unchanged]
[findings]
PDF517: Line 2: Private module attribute '__all__' should not have an attached docstring
```

Class attributes, function-local assignments, unsupported targets, bytes literals, and f-strings are ignored by PDF517:

```pydocfmt-example
[input]
class Client:
    _token: str
    """Class private attribute."""

def configure():
    _token = ""
    """Local string."""

items[0] = ""
"""Subscript target."""

[_name] = values
"""List destructuring target."""

_bytes = b""
b"Bytes are not docstrings."

_formatted = ""
f"Formatted {value}"

[output=unchanged]
```

## Options
- `require-explicit`: Keeps PDF517 out of broad rule selections by default. Exact rule-code selection enables it.
