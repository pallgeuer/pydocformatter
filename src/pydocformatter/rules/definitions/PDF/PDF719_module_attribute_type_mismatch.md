# module-attribute-type-mismatch (PDF719)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF718`.

## What it does
Checks that parsed module attribute docstring types conservatively match annotated module attributes.

The comparison uses a small, syntax-only type-expression subset. Unparseable or ambiguous expressions are skipped instead of guessed. Only entries that match inventoried module attributes are checked, and NumPy entries that document multiple names are checked once per matching attribute.

## Why is this useful?
Stale module attribute type text can mislead readers when annotations have changed.

## Ruff compatibility
None.

## Examples
PDF719 reports module attribute docstring types that do not match annotations:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    timeout (str): Timeout in seconds.
"""

timeout: int = 1

[output=unchanged]
[findings]
PDF719: Line 4: Module attribute 'timeout' docstring type does not match the annotation
```

Matching module attribute types are accepted:

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
fallback: int

[output=unchanged]
[findings]
PDF719: Line 5: Module attribute 'fallback' docstring type does not match the annotation
```

## Options
None.
