# private-module-attribute-owner-documentation (PDF515)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks for private attributes documented in module docstring attribute documentation.

PDF515 checks Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields when the matching convention is active. Attribute names beginning with `_` are private, including dunder-style names such as `__all__`.

The rule checks parsed primary module docstrings only. It does not require the private attribute to exist in the module inventory, and it reports repeated private entries independently. Class docstrings, function docstrings, and additional string literals after the primary module docstring are not module owner docstrings for this rule.

## Why is this useful?
Private module attributes are implementation details and should usually stay out of module docstrings that describe the public module API.

## Ruff compatibility
None.

## Examples
A private module attribute documented in the module docstring is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    _token (str): Internal token.
    timeout (float): Request timeout.
"""

_token: str
timeout: float

[output=unchanged]
[findings]
PDF515: Line 4: Module docstring documents private attribute '_token'
```

NumPy and reStructuredText attribute entries are checked under their active conventions:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Client defaults.

Attributes
----------
_token, timeout, __all__ : object
    Module state.
_token : str
    Repeated internal token.
"""

[output=unchanged]
[findings]
PDF515: Line 5: Module docstring documents private attribute '_token'
PDF515: Line 5: Module docstring documents private attribute '__all__'
PDF515: Line 7: Module docstring documents private attribute '_token'
```

reStructuredText attribute value and type fields are checked under the `rest` convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Client defaults.

:ivar _token: Internal token.
:vartype _cache: dict[str, object]
:ivar timeout: Request timeout.
"""

[output=unchanged]
[findings]
PDF515: Line 3: Module docstring documents private attribute '_token'
PDF515: Line 4: Module docstring documents private attribute '_cache'
```

Only the primary module docstring is checked. Class docstrings and later string literals are ignored by PDF515:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults."""

"""Attributes:
_module_token: Internal token.
"""

class Client:
    """HTTP client.

    Attributes:
        _token: Internal token.
    """

[output=unchanged]
```

## Options
- `docstring-convention`: Controls whether Google `Attributes` sections, NumPy `Attributes` sections, or reST attribute fields are parsed. Ignored by broad rule selections under `none` and `pep257`.
