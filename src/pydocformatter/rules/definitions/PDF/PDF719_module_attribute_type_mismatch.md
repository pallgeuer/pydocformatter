# module-attribute-type-mismatch (PDF719)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF718`.

## What it does
Checks that parsed module attribute docstring types conservatively match annotated module attributes. It checks only entries in the module docstring that match inventoried attributes and have both a documented type and a usable annotation. Attached attribute docstrings are outside the scope of PDF7xx rules.

The comparison uses a syntax-only type-expression subset that covers common names, qualified names, subscriptions, tuples, unions, and stringized annotations. Unshadowed import aliases are normalized before comparison. Unparseable, unsupported, or ambiguous expressions are skipped instead of guessed.

Google, NumPy, and inline or paired reStructuredText types are supported. NumPy entries that document multiple names are checked once per matching attribute. Findings are diagnostic-only because choosing between conflicting documentation and code requires human judgment.

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

For paired reStructuredText fields, a mismatch is reported on the `:vartype:` field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module settings.

:var timeout: Timeout in seconds.
:vartype timeout: str
"""

timeout: int = 1

[output=unchanged]
[findings]
PDF719: Line 4: Module attribute 'timeout' docstring type does not match the annotation
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
