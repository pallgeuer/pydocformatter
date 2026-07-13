# module-attribute-type-forbidden (PDF718)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF717` and `PDF719`.

## What it does
Checks that parsed module attribute entries in owning module docstrings do not include documented types.

Only entries that match inventoried module attributes are checked. The rule is exact opt-in and cannot be combined with the required-type or type-mismatch module attribute policies.

## Why is this useful?
Projects that rely on code annotations can prevent duplicated module attribute type documentation.

## Ruff compatibility
None.

## Examples
PDF718 reports module attribute entries that include docstring type text:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    timeout (int): Timeout in seconds.
    retries: Retry count.
"""

timeout: int = 1
retries: int = 3

[output=unchanged]
[findings]
PDF718: Line 4: Module attribute 'timeout' docstring entry should not include a type
```

Module attribute entries without types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    timeout: Timeout in seconds.
"""

timeout: int = 1

[output=unchanged]
```

NumPy entries that document multiple names are checked once per matching attribute:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Module.

Attributes
----------
primary, fallback : str
    Request endpoints.
"""

primary: str
fallback: str

[output=unchanged]
[findings]
PDF718: Line 5: Module attribute 'primary' docstring entry should not include a type
PDF718: Line 5: Module attribute 'fallback' docstring entry should not include a type
```

## Options
None.
