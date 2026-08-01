# missing-exception-documentation (PDF506)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks function and method docstrings for directly raised exception classes missing from the exception documentation. When `docstring-include-assertion-errors` is enabled, every syntactic `assert` also contributes a possible `AssertionError`.

The rule recognizes direct raises such as `raise ValueError`, `raise ValueError(...)`, `raise errors.ValueError`, and `raise errors.ValueError(...)`. Bare re-raises and dynamic raises such as `raise error` are ignored. Exception names are compared case-sensitively. Qualified names match exactly when both sides are qualified; otherwise the final class-name component is compared, so `errors.CustomError()` matches documented `CustomError` but not documented `other.CustomError`. Repeated occurrences of the same undocumented exception produce one finding at the first enabled occurrence.

Assertion collection is syntactic and does not attempt reachability analysis. Constant-true assertions and assertions inside branches, loops, and exception handlers all count when the option is enabled. Direct raises and assertions share source order and name deduplication. If an assertion owns the first missing `AssertionError` occurrence, the message is `AssertionError from assert statement is missing docstring documentation`; an earlier direct `raise AssertionError` retains the ordinary direct-raise message. Assertions inside nested functions, nested classes, and lambdas do not belong to the enclosing function.

The `docstring-include-assertion-errors` option is disabled by default because optimized Python execution can remove assertions and because assertions often express internal invariants rather than public API contracts.

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

Assertions contribute `AssertionError` only when explicitly enabled:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"
docstring-include-assertion-errors = true

[input]
def validate(value):
    """Validate a value."""
    assert value

[output=unchanged]
[findings]
PDF506: Line 3: AssertionError from assert statement is missing docstring documentation
```

Direct raises and assertions share source order when deduplicating `AssertionError`:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"
docstring-include-assertion-errors = true

[input]
def assertion_first(value):
    """Validate a value."""
    assert value
    raise AssertionError("bad")


def raise_first(value):
    """Validate another value."""
    raise AssertionError("bad")
    assert value

[output=unchanged]
[findings]
PDF506: Line 3: AssertionError from assert statement is missing docstring documentation
PDF506: Line 9: Raised exception 'AssertionError' is missing docstring documentation
```

A documented assertion-derived exception is consistent when the option is enabled:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-include-assertion-errors = true

[input]
def validate(value):
    """Validate a value.

    Raises:
        AssertionError: The value is false.
    """
    assert value

[output=unchanged]
```

Disabled conventions leave the rule inactive:

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
- `docstring-include-assertion-errors`: Treats every syntactic `assert` as a possible `AssertionError` when enabled.
