# module-attribute-missing-description (PDF716)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed module attribute entries in owning module docstrings include a prose description.

Only entries that match inventoried module attributes are checked. Attached module attribute docstrings are intentionally not checked by PDF7xx rules.

An orphan reST `:vartype name:` field has no attribute value entry whose description PDF716 could check, so PDF722 owns that structural problem.

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

NumPy entries that document multiple attributes are checked once per matching module attribute, even though the findings share one entry line:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Module.

Attributes
----------
timeout, retries : int
"""

timeout: int = 1
retries: int = 3

[output=unchanged]
[findings]
PDF716: Line 5: Module attribute 'timeout' docstring entry is missing a description
PDF716: Line 5: Module attribute 'retries' docstring entry is missing a description
```

For reST, PDF716 checks attribute value fields rather than standalone type fields. A paired empty value field is reported, while a type-only entry for another real attribute is left to PDF722:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module.

:vartype timeout: int
:var timeout:
:vartype retries: int
"""

timeout: int = 1
retries: int = 3

[output=unchanged]
[findings]
PDF716: Line 4: Module attribute 'timeout' docstring entry is missing a description
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
None.
