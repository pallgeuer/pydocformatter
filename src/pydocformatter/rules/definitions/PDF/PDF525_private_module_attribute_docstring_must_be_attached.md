# private-module-attribute-docstring-must-be-attached (PDF525)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF517` and `PDF524`.

## What it does
Checks for private module attributes documented in module docstring attribute entries when private module attribute documentation must use attached docstrings.

PDF525 checks parsed Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText attribute fields when the matching convention is active. The documented name must also match a supported module attribute inventory entry.

PDF525 is a location policy: it reports inventory-backed private module attributes documented in the module docstring because attached docstrings are required. It differs from PDF515, which forbids private module owner-docstring entries even when the attribute is stale or otherwise not in inventory, and it conflicts with PDF517, which forbids attached private module docstrings.

## Why is this useful?
Attached docstrings let private module attributes be documented near their assignment without adding private details to the owner docstring's public attribute list.

## Ruff compatibility
None.

## Examples
A private module attribute documented in the module docstring is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module constants.

Attributes:
    _token: Internal token.
"""

_token: str

[output=unchanged]
[findings]
PDF525: Line 4: Private module attribute '_token' must use attached docstring, not module docstring documentation
```

NumPy entries are checked name by name. Stale documented names are left to PDF511 or PDF515, while repeated owner entries are reported independently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Module constants.

Attributes
----------
_token, timeout, _cache, _missing : object
    Module state.
_token : str
    Repeated internal token.
"""

_token: str
timeout: float
_cache: dict[str, object]

[output=unchanged]
[findings]
PDF525: Line 5: Private module attribute '_token' must use attached docstring, not module docstring documentation
PDF525: Line 5: Private module attribute '_cache' must use attached docstring, not module docstring documentation
PDF525: Line 7: Private module attribute '_token' must use attached docstring, not module docstring documentation
```

reStructuredText value and type fields are also checked:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module constants.

:var _token: Internal token.
:vartype _cache: dict[str, object]
"""

_token: str
_cache: dict[str, object]

[output=unchanged]
[findings]
PDF525: Line 3: Private module attribute '_token' must use attached docstring, not module docstring documentation
PDF525: Line 4: Private module attribute '_cache' must use attached docstring, not module docstring documentation
```

When the active convention does not parse attribute entries, module docstring attribute-looking text is ignored:

```pydocfmt-example
[settings]
docstring-convention = "pep257"

[input]
"""Module constants.

Attributes:
    _token: Internal token.
"""

_token: str

[output=unchanged]
```

## Options
None.
