# public-class-attribute-docstring-must-be-owner (PDF518)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF519`.

## What it does
Checks for attached docstrings on public class attributes when class attribute documentation must live in the class docstring.

PDF518 checks class-scope attributes and supported `self.*` instance attributes assigned in `__init__`. Attribute names that do not begin with `_` are public.

PDF518 is a location policy: it reports attached public class attribute docstrings because the class docstring is required. It does not check whether all public attributes are documented; use PDF508 for missing documentation, PDF509 for stale class docstring entries, and PDF512 for duplicates when both locations are allowed.

## Why is this useful?
Some projects centralize public class attribute documentation in class docstrings so generated API documentation keeps the public attribute list in one place.

## Ruff compatibility
None.

## Examples
A public class attribute with an attached docstring is reported:

```pydocfmt-example
[input]
class Client:
    timeout: float
    """Request timeout in seconds."""

[output=unchanged]
[findings]
PDF518: Line 3: Public class attribute 'timeout' must use class docstring documentation, not attached docstring
```

Same-line docstrings, concatenated docstrings, and shared tuple-unpacked docstrings are checked by target name:

```pydocfmt-example
[input]
class Client:
    timeout = 30.0; """Request timeout."""
    retries: int
    """Retry """ "count."
    primary, (_fallback, *aliases) = endpoints
    """Endpoint values."""

[output=unchanged]
[findings]
PDF518: Line 2: Public class attribute 'timeout' must use class docstring documentation, not attached docstring
PDF518: Line 4: Public class attribute 'retries' must use class docstring documentation, not attached docstring
PDF518: Line 6: Public class attribute 'primary' must use class docstring documentation, not attached docstring
PDF518: Line 6: Public class attribute 'aliases' must use class docstring documentation, not attached docstring
```

Only the attribute name controls public/private classification. Public attributes in private classes are still checked, while private attributes and unsupported targets are ignored by PDF518:

```pydocfmt-example
[input]
class _Client:
    timeout: float
    """Request timeout."""

    _token: str
    """Internal token."""

    items[0] = 1
    """Ignored subscript target."""

[output=unchanged]
[findings]
PDF518: Line 3: Public class attribute 'timeout' must use class docstring documentation, not attached docstring
```

## Options
- `require-explicit`: Keeps PDF518 out of broad rule selections by default. Exact rule-code selection enables it.
