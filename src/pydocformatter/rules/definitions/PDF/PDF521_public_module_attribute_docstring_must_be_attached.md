# public-module-attribute-docstring-must-be-attached (PDF521)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF520`.

## What it does
Checks for public module attributes documented in module docstring attribute entries when public module attribute documentation must use attached docstrings.

PDF521 checks parsed Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText attribute fields when the matching convention is active. The documented name must also match a supported module attribute inventory entry.

PDF521 is a location policy: it reports inventory-backed public module attributes documented in the module docstring because attached docstrings are required. It does not report stale module docstring entries; use PDF511 for those, PDF510 for missing documentation, and PDF513 for duplicates when both locations are allowed.

## Why is this useful?
Attached docstrings keep module attribute documentation next to the assignment, which can be clearer for projects with many constants or aliases.

## Ruff compatibility
None.

## Examples
A public module attribute documented in the module docstring is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module constants.

Attributes:
    timeout: Request timeout.
"""

timeout: float

[output=unchanged]
[findings]
PDF521: Line 4: Public module attribute 'timeout' must use attached docstring, not module docstring documentation
```

Stale documented names are left to PDF511, while repeated owner entries are reported independently:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module constants.

Attributes:
    timeout: Request timeout.
    missing: Stale docs.
    timeout: Repeated timeout docs.
"""

timeout: float

[output=unchanged]
[findings]
PDF521: Line 4: Public module attribute 'timeout' must use attached docstring, not module docstring documentation
PDF521: Line 6: Public module attribute 'timeout' must use attached docstring, not module docstring documentation
```

reStructuredText value and type fields are also checked:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module constants.

:var timeout: Request timeout.
:vartype retries: int
"""

timeout: float
retries: int

[output=unchanged]
[findings]
PDF521: Line 3: Public module attribute 'timeout' must use attached docstring, not module docstring documentation
PDF521: Line 4: Public module attribute 'retries' must use attached docstring, not module docstring documentation
```

When the active convention does not parse attribute entries, module docstring attribute-looking text is ignored:

```pydocfmt-example
[settings]
docstring-convention = "pep257"

[input]
"""Module constants.

Attributes:
    timeout: Request timeout.
"""

timeout: float

[output=unchanged]
```

## Options
None.
