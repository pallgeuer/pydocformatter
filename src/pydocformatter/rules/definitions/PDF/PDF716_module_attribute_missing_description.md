# module-attribute-missing-description (PDF716)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed module attribute entries in owning module docstrings include a prose description.

Only entries that match inventoried module attributes are checked. Attached module attribute docstrings are intentionally not checked by PDF7xx rules.

## Why is this useful?
Module attribute entries should explain exported state or constants.

## Ruff compatibility
None.

## Examples
PDF716 reports module attribute entries without descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    timeout (int):
    retries:
"""

timeout: int = 1
retries: int = 3

[output=unchanged]
[findings]
PDF716: Line 4: Module attribute 'timeout' docstring entry is missing a description
PDF716: Line 5: Module attribute 'retries' docstring entry is missing a description
```

Module attribute entries with descriptions are accepted:

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

Attached module attribute docstrings are ignored by PDF7xx owning-docstring rules:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
timeout: int = 1
"""Timeout.

Attributes:
    timeout (str):
"""

[output=unchanged]
```

## Options
- `docstring-convention`: Google, NumPy, and reST entries are checked.
