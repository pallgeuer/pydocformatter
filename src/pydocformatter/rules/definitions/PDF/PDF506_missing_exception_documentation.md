# missing-exception-documentation (PDF506)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks function and method docstrings for directly raised exception classes missing from the exception documentation.

The rule recognizes direct raises such as `raise ValueError`, `raise ValueError(...)`, `raise errors.ValueError`, and `raise errors.ValueError(...)`. Bare re-raises and dynamic raises such as `raise error` are ignored. Exception names are compared case-sensitively. Qualified names match exactly when both sides are qualified; otherwise the final class-name component is compared, so `errors.CustomError()` matches documented `CustomError` but not documented `other.CustomError`. Repeated raises of the same undocumented exception produce one finding at the first raise line.

Exception documentation is read from recognized `Raises` sections and parsed reST exception fields. Warning sections such as `Warns` and `Warnings` are not exception documentation for this rule. Functions without docstrings, abstract methods, and stub functions are ignored. Nested functions, classes, and lambdas are ignored by the enclosing function and checked independently when they have their own docstrings.

By default, this rule reports missing exception documentation only when the docstring already has recognized exception documentation, such as a `Raises` section. Broader shared missing-documentation modes can require exception documentation for public docstrings with body content, or for all public docstrings.

## Why is this useful?
Exception documentation helps callers understand failure modes without reading the implementation.

## Ruff compatibility
This rule replaces Ruff's `DOC501`. It follows the same broad intent, while using pydocformatter's configured docstring parser and without Ruff's pydoclint-specific one-line-docstring option.

## Examples
This function directly raises an undocumented exception:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def parse(value):
    """Parse a value."""
    if not value:
        raise ValueError("empty")
    return value

[output=unchanged]
[findings]
PDF506: Line 4: Raised exception 'ValueError' is missing docstring documentation
```

The rule reports each distinct directly raised exception once, at the first raise line for that exception:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def validate(flag):
    """Validate a flag."""
    if flag == "value":
        raise ValueError("bad")
    if flag == "again":
        raise ValueError("bad again")
    raise TypeError("bad")

[output=unchanged]
[findings]
PDF506: Line 4: Raised exception 'ValueError' is missing docstring documentation
PDF506: Line 7: Raised exception 'TypeError' is missing docstring documentation
```

Unqualified documented exception names can match qualified raises. Multiple names in one Google entry, qualified raises, and exception causes are supported:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def validate(flag, cause):
    """Validate a flag.

    Raises:
        ValueError, TypeError: Bad value.
        LookupError: Missing value.
    """
    if flag == "type":
        raise errors.TypeError("bad")
    if flag == "missing":
        raise LookupError("missing") from cause
    raise ValueError("bad")

[output=unchanged]
```

Differently qualified names with the same final component do not match:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def validate():
    """Validate a value.

    Raises:
        requests.Timeout: Bad value.
    """
    raise socket.Timeout("bad")

[output=unchanged]
[findings]
PDF506: Line 7: Raised exception 'socket.Timeout' is missing docstring documentation
```

Warning sections are not exception documentation for this rule, and dynamic raises are not comparable direct exception raises:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def warning_doc():
    """Validate a value.

    Warns:
        ValueError: Bad value.
    """
    raise ValueError("bad")


def dynamic(error):
    """Raise a provided exception."""
    raise error

[output=unchanged]
[findings]
PDF506: Line 7: Raised exception 'ValueError' is missing docstring documentation
```

reST exception fields satisfy the rule under the reST convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def validate():
    """Validate a value.

    :raises ValueError: Bad value.
    """
    raise ValueError("bad")

[output=unchanged]
```

```pydocfmt-example
[settings]
docstring-convention = "none"
docstring-missing-documentation = "all-docstrings"

[input]
def validate():
    """Validate a value.

    :raises ValueError: Bad value.
    """
    raise ValueError("bad")

[output=unchanged]
```

## Options
- `docstring-missing-documentation`: Controls whether missing exception documentation is reported only when exception documentation already exists, for non-summary docstrings, or for all eligible docstrings.
- `docstring-missing-documentation-public-only`: Limits broad missing-exception checks to public functions and methods when enabled.
