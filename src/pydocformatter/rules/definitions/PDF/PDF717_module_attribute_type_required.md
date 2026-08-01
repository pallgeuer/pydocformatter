# module-attribute-type-required (PDF717)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF718`.

## What it does
Checks that parsed module attribute entries in the module docstring include documented types. It checks only entries that match inventoried module attributes; it does not require undocumented attributes to be added. Attached attribute docstrings are outside the scope of PDF7xx rules.

The rule recognizes types in Google and NumPy attribute entries and in inline or paired reStructuredText fields.

When a single-line module attribute annotation is available, PDF717 inserts its annotation text into a mapped Google entry or adds a paired canonical reStructuredText `:vartype:` field, filling an existing empty, single-line field first. NumPy entries, attributes without usable annotations, and source shapes that cannot be mapped safely remain diagnostic.

The rule is exact opt-in because many projects rely on module annotations instead of repeating attribute types in docstrings.

## Why is this useful?
Projects that keep types in docstrings can enforce complete module attribute type documentation.

## Ruff compatibility
None.

## Examples
PDF717 canonically copies a module attribute annotation into a Google entry that has no type:

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

[output]
"""Module.

Attributes:
    timeout (int): Timeout in seconds.
    retries (int): Retry count.
"""

timeout: int = 1
retries: int = 3
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

Without an attribute annotation, PDF717 reports the missing docstring type but cannot infer a replacement:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    timeout: Timeout in seconds.
"""

timeout = 1

[output=unchanged]
[findings]
PDF717: Line 4: Module attribute 'timeout' docstring entry is missing a type
```

PDF717 adds a canonical paired reStructuredText `:vartype:` field after a documented module attribute:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module.

:var timeout: Timeout in seconds.
"""

timeout: int = 1

[output]
"""Module.

:var timeout: Timeout in seconds.
:vartype timeout: int
"""

timeout: int = 1
```

## Options
None.
