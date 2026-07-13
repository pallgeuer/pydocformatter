# module-attribute-type-required (PDF717)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF718`.

## What it does
Checks that parsed module attribute entries in owning module docstrings include documented types.

Only entries that match inventoried module attributes are checked. The rule is exact opt-in because many projects rely on module annotations instead of repeating attribute types in docstrings.

## Why is this useful?
Projects that keep types in docstrings can enforce complete module attribute type documentation.

## Ruff compatibility
None.

## Examples
PDF717 reports module attribute entries without docstring types:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    timeout: Timeout in seconds.
    retries (int): Retry count.
"""

timeout: int = 1
retries: int = 3

[output=unchanged]
[findings]
PDF717: Line 4: Module attribute 'timeout' docstring entry is missing a type
```

Module attribute entries with types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    timeout (int): Timeout in seconds.
"""

timeout: int = 1

[output=unchanged]
```

reST `:vartype:` fields provide the type for paired module attribute documentation:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module.

:var timeout: Timeout in seconds.
:vartype timeout: int
"""

timeout: int = 1

[output=unchanged]
```

## Options
None.
