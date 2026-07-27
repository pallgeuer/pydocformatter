# missing-public-module-attribute-documentation (PDF510)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

## What it does
Checks that public module attributes are documented either in the module docstring attribute documentation or by an adjacent attribute docstring.

The rule compares supported module-level assignments against names documented in Google `Attributes` sections, NumPy `Attributes` sections, reStructuredText `:ivar:`, `:cvar:`, and `:var:` value fields, and adjacent attribute docstrings. A type-only `:vartype:` field activates the consistency check but does not document the attribute value. Module assignments, annotated assignments, multi-target assignments, and tuple-unpacked assignment leaves are inventoried. Private module attributes are never required.

PDF510 checks whether public module attributes have any recognized documentation. It does not care whether that documentation is in the module docstring or attached to the assignment; use PDF520 or PDF521 for a location policy, PDF511 for stale module docstring entries, and PDF513 for duplicated module attribute documentation.

PDF510 is ignored by broad selectors under parsed docstring conventions, so select `PDF510` exactly under `google`, `numpy`, or `rest` to opt into this module-level check. With the default public-only setting, files named like private modules or private packages are skipped.

## Why is this useful?
Module attribute documentation can otherwise drift from exported module state.

## Ruff compatibility
None.

## Examples
Missing public module attribute documentation is reported when a module has attribute documentation but omits a public module attribute:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    timeout (float): Request timeout.
"""

timeout: float
retries: int

[output=unchanged]
[findings]
PDF510: Line 8: Public module attribute 'retries' is missing docstring documentation
```

An empty recognized `Attributes` section still opts the module into missing attribute checks:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
"""

timeout: float

[output=unchanged]
[findings]
PDF510: Line 6: Public module attribute 'timeout' is missing docstring documentation
```

Adjacent module attribute docstrings document their assignments, including every simple target in a multi-target assignment and supported tuple-unpacked assignment. Private module attributes are not required:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
timeout: float
"""Request timeout."""

retries: int

[output=unchanged]
[findings]
PDF510: Line 4: Public module attribute 'retries' is missing docstring documentation
```

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
timeout: float
"""Request timeout."""

primary = fallback = "https://example.com"
"""Request endpoints."""

host, (port, *aliases) = endpoint_parts
"""Unpacked endpoint parts."""

_token: str

[output=unchanged]
```

NumPy comma-separated attribute entries document each listed name independently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Client defaults.

Attributes
----------
primary, fallback : str
    Request endpoints.
"""

primary = fallback = "https://example.com"
retries: int

[output=unchanged]
[findings]
PDF510: Line 10: Public module attribute 'retries' is missing docstring documentation
```

Under the reST convention, a type-only field activates the consistency check but does not document any inventory attribute. An empty value field does document its named attribute for PDF510; description quality is handled by PDF716:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Client defaults.

:vartype removed: int
:var retries:
"""

timeout: float
retries: int

[output=unchanged]
[findings]
PDF510: Line 7: Public module attribute 'timeout' is missing docstring documentation
```

The `non-summary-docstrings` policy reports missing attributes for public modules whose docstring has more than a summary, even without an attribute section:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "non-summary-docstrings"

[input]
"""Client defaults.

Used by the transport layer.
"""

timeout: float

[output=unchanged]
[findings]
PDF510: Line 6: Public module attribute 'timeout' is missing docstring documentation
```

Private module paths are skipped by broad checks while `docstring-missing-documentation-public-only` is enabled:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"
docstring-missing-documentation-public-only = true

[input=_internal.py]
"""Client defaults."""

timeout: float

[output=unchanged]
```

Disabling the public-only setting applies the same broad policy to private module paths:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"
docstring-missing-documentation-public-only = false

[input=_internal.py]
"""Client defaults."""

timeout: float

[output=unchanged]
[findings]
PDF510: Line 3: Public module attribute 'timeout' is missing docstring documentation
```

## Options
- `docstring-missing-documentation`: Controls whether missing module attribute documentation is reported only when attribute documentation already exists, for non-summary module docstrings, or for all eligible module docstrings.
- `docstring-missing-documentation-public-only`: Skips private module paths for broad missing-module-attribute checks when enabled.
