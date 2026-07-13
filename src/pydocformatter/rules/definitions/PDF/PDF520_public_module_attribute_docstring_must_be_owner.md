# public-module-attribute-docstring-must-be-owner (PDF520)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF521`.

## What it does
Checks for attached docstrings on public module attributes when module attribute documentation must live in the module docstring.

PDF520 checks supported module-scope assignments, annotations, multi-target assignments, and tuple-unpacked assignment leaves. Attribute names that do not begin with `_` are public.

PDF520 is a location policy: it reports attached public module attribute docstrings because the module docstring is required. It does not check whether all public attributes are documented; use PDF510 for missing documentation, PDF511 for stale module docstring entries, and PDF513 for duplicates when both locations are allowed.

## Why is this useful?
Some projects centralize public module attribute documentation in module docstrings so generated API documentation keeps the exported attribute list in one place.

## Ruff compatibility
None.

## Examples
A public module attribute with an attached docstring is reported:

```pydocfmt-example
[input]
timeout: float
"""Request timeout in seconds."""

[output=unchanged]
[findings]
PDF520: Line 2: Public module attribute 'timeout' must use module docstring documentation, not attached docstring
```

Same-line docstrings, concatenated docstrings, and shared tuple-unpacked docstrings are checked by target name:

```pydocfmt-example
[input]
timeout = 30.0; """Request timeout."""
retries: int
"""Retry """ "count."
primary, (_fallback, *aliases) = endpoints
"""Endpoint values."""

[output=unchanged]
[findings]
PDF520: Line 1: Public module attribute 'timeout' must use module docstring documentation, not attached docstring
PDF520: Line 3: Public module attribute 'retries' must use module docstring documentation, not attached docstring
PDF520: Line 5: Public module attribute 'primary' must use module docstring documentation, not attached docstring
PDF520: Line 5: Public module attribute 'aliases' must use module docstring documentation, not attached docstring
```

Only the attribute name controls public/private classification. Public attributes are still checked in private module paths, while private attributes and unsupported targets are ignored by PDF520:

```pydocfmt-example
[input=package/_private.py]
timeout: float
"""Request timeout."""

_token: str
"""Internal token."""

items[0] = 1
"""Ignored subscript target."""

[output=unchanged]
[findings]
PDF520: Line 2: Public module attribute 'timeout' must use module docstring documentation, not attached docstring
```

## Options
None.
