# extraneous-module-attribute-documentation (PDF511)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that module docstring attribute entries name attributes that are present at module scope.

The rule compares names documented in the module docstring against supported module attribute inventory entries. Module-level assignments, annotated assignments, multi-target assignments, and tuple-unpacked assignment leaves count as present. Adjacent attribute docstrings are not checked by this rule because they are attached to an assignment that exists.

Class attributes, list destructuring targets, unsupported tuple leaves, subscript targets, and arbitrary object attributes do not satisfy module-level attribute documentation.

## Why is this useful?
Stale module attribute entries can mislead readers about available module state.

## Ruff compatibility
None.

## Examples
Stale module attribute entries are reported when the documented name is absent from the module inventory:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    timeout: Request timeout.
    stale: Removed attribute.
"""

timeout: float

[output=unchanged]
[findings]
PDF511: Line 5: Module docstring documents attribute 'stale' that is not present
```

Existing private module attributes may be voluntarily documented, and multi-target assignments and tuple-unpacked assignments make each supported target present:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    _timeout: Internal timeout.
    primary: Primary endpoint.
    fallback: Fallback endpoint.
    aliases: Endpoint aliases.
"""

_timeout: float
primary = fallback = "https://example.com"
primary, (fallback, *aliases) = endpoints

[output=unchanged]
```

Class attributes do not satisfy module attribute documentation:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    timeout: Request timeout.
"""

class Client:
    timeout: float

[output=unchanged]
[findings]
PDF511: Line 4: Module docstring documents attribute 'timeout' that is not present
```

NumPy comma-separated entries are checked name by name, so a single entry line can contain both present and stale names:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Client defaults.

Attributes
----------
primary, stale : str
    Request endpoints.
"""

primary: str

[output=unchanged]
[findings]
PDF511: Line 5: Module docstring documents attribute 'stale' that is not present
```

reStructuredText attribute fields are parsed under the `rest` convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Client defaults.

:ivar stale: Removed attribute.
:vartype other: str
"""

[output=unchanged]
[findings]
PDF511: Line 3: Module docstring documents attribute 'stale' that is not present
PDF511: Line 4: Module docstring documents attribute 'other' that is not present
```

Unsupported assignment targets do not make a documented attribute present:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    primary: Primary endpoint.
"""

[primary, fallback] = endpoints

[output=unchanged]
[findings]
PDF511: Line 4: Module docstring documents attribute 'primary' that is not present
```

## Options
- `docstring-convention`: Controls whether Google `Attributes` sections, NumPy `Attributes` sections, or reST attribute fields are parsed. Ignored by broad rule selections under `none` and `pep257`.
