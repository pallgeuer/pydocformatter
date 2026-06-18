# extraneous-exception-documentation (PDF507)

Fix is not available.

Rule is ignored by broad selectors for all `docstring-convention` values. Select `PDF507` exactly to opt into this strict consistency check.

## What it does
Checks function and method docstrings for documented exception classes that are not directly raised by the function body.

The rule recognizes direct raises such as `raise ValueError`, `raise ValueError(...)`, `raise errors.ValueError`, and `raise errors.ValueError(...)`. Bare re-raises and dynamic raises such as `raise error` are ignored. Exception names are compared case-sensitively. Qualified names match exactly when both sides are qualified; otherwise the final class-name component is compared, so `errors.CustomError()` matches documented `CustomError` but not documented `other.CustomError`. Duplicate stale documented exception entries produce duplicate findings.

Exception documentation is read from recognized `Raises` sections and parsed rest exception fields. Prose-only `Raises` content and warning sections such as `Warns` and `Warnings` are not exception documentation for this rule. Functions without docstrings, abstract methods, and stub functions are ignored. Nested functions, classes, and lambdas are ignored by the enclosing function and checked independently when they have their own docstrings.

## Why is this useful?
Extraneous exception documentation can misstate the failure modes of an API.

## Ruff compatibility
This rule replaces Ruff's `DOC502`. It follows the same broad intent and keeps Ruff's known limitation that some projects intentionally document non-explicit exceptions. Because helper calls and delegated implementations can legitimately raise caller-visible exceptions, pydocformatter treats this as an opt-in rule instead of enabling it through broad selectors.

## Examples
This function documents an exception it does not directly raise:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError: If empty.
    """
    return value

[output=unchanged]
[findings]
PDF507: Line 5: Docstring documents exception 'ValueError' that is not explicitly raised
```

The rule reports only documented names that are absent from direct raises. Multiple names in one Google entry are checked independently:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError, TypeError: If parsing fails.
    """
    raise ValueError("empty")

[output=unchanged]
[findings]
PDF507: Line 5: Docstring documents exception 'TypeError' that is not explicitly raised
```

Unqualified documented exception names can match qualified raises. Qualified documented names, qualified raises, and exception causes can all match:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(kind, cause):
    """Parse a value.

    Raises:
        errors.ValueError: Empty value.
        LookupError: Missing value.
    """
    if kind == "lookup":
        raise errors.LookupError("missing") from cause
    raise ValueError("empty")

[output=unchanged]
```

Differently qualified names with the same final component do not match, and findings report the documented name as written:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        requests.Timeout: If parsing times out.
    """
    raise socket.Timeout("bad")

[output=unchanged]
[findings]
PDF507: Line 5: Docstring documents exception 'requests.Timeout' that is not explicitly raised
```

Duplicate stale exception entries produce duplicate findings because each docstring entry is stale:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError: Empty value.
        ValueError: Invalid value.
    """
    return value

[output=unchanged]
[findings]
PDF507: Line 5: Docstring documents exception 'ValueError' that is not explicitly raised
PDF507: Line 6: Docstring documents exception 'ValueError' that is not explicitly raised
```

Only direct raises are compared. Dynamic raises are ignored, so documentation for a dynamically raised exception is still stale for this rule:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(error):
    """Parse a value.

    Raises:
        ValueError: If parsing fails.
    """
    raise error

[output=unchanged]
[findings]
PDF507: Line 5: Docstring documents exception 'ValueError' that is not explicitly raised
```

Prose-only `Raises` content and warning sections are not exception documentation for this rule:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def prose():
    """Parse a value.

    Raises:
        If parsing fails.
    """


def warning_doc():
    """Parse a value.

    Warns:
        ValueError: Bad value.
    """

[output=unchanged]
```

Rest exception fields are checked only under the rest convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def parse(value):
    """Parse a value.

    :raises ValueError: If parsing fails.
    """
    return value

[output=unchanged]
[findings]
PDF507: Line 4: Docstring documents exception 'ValueError' that is not explicitly raised
```

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
def parse(value):
    """Parse a value.

    :raises ValueError: If parsing fails.
    """
    return value

[output=unchanged]
```

## Options
- `docstring-convention`: Controls whether Google `Raises` sections, NumPy `Raises` sections, or rest exception fields such as `:raises ValueError:` are recognized. Ignores PDF507 for broad rule selections under every convention.
