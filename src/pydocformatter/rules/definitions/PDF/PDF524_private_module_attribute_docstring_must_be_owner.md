# private-module-attribute-docstring-must-be-owner (PDF524)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF515` and `PDF525`.

## What it does
Checks for attached docstrings on private module attributes when private module attribute documentation must live in the module docstring.

PDF524 checks supported module-scope assignments, annotations, multi-target assignments, and tuple-unpacked assignment leaves. Attribute names beginning with `_` are private.

PDF524 is a location policy: it reports attached private module attribute docstrings because the module docstring is required. It conflicts with PDF515, which forbids private module owner-docstring entries entirely, and with PDF525, the opposite attached-docstring policy.

## Why is this useful?
Some projects choose to document private module state in module docstrings for internal API reference builds while avoiding scattered attached docstrings.

## Ruff compatibility
None.

## Examples
A private module attribute with an attached docstring is reported:

```pydocfmt-example
[input]
_token: str
"""Internal token."""

[output=unchanged]
[findings]
PDF524: Line 2: Private module attribute '_token' must use module docstring documentation, not attached docstring
```

Same-line docstrings, concatenated docstrings, and shared tuple-unpacked docstrings are checked by target name:

```pydocfmt-example
[input]
_token = ""; """Internal token."""
_cache: dict[str, object]
"""Internal """ "cache."
_primary, fallback, *_aliases = endpoints
"""Endpoint internals."""

[output=unchanged]
[findings]
PDF524: Line 1: Private module attribute '_token' must use module docstring documentation, not attached docstring
PDF524: Line 3: Private module attribute '_cache' must use module docstring documentation, not attached docstring
PDF524: Line 5: Private module attribute '_primary' must use module docstring documentation, not attached docstring
PDF524: Line 5: Private module attribute '_aliases' must use module docstring documentation, not attached docstring
```

Public attributes, repeated targets in one assignment, and unsupported targets are handled by target name:

```pydocfmt-example
[input]
timeout: float
"""Public timeout."""

_token, _token = values
"""Internal token."""

items[0] = ""
"""Ignored subscript target."""

[output=unchanged]
[findings]
PDF524: Line 5: Private module attribute '_token' must use module docstring documentation, not attached docstring
```

## Options
- `require-explicit`: Keeps PDF524 out of broad rule selections by default. Exact rule-code selection enables it.
