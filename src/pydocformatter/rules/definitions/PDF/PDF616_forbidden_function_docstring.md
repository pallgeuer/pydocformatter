# forbidden-function-docstring (PDF616)

Fix is not available.

## What it does
Checks for function and method docstrings on definitions decorated with configured no-docstring decorators.

By default, the no-docstring decorators are the standard overload decorators `typing.overload` and `typing_extensions.overload`, including direct import aliases resolved statically by LibCST. Overload variants are type-checker signatures rather than the runtime implementation, so their docstrings are normally ignored by runtime documentation tools. Put user-facing documentation on the implementation function instead.

Decorator names are matched exactly after unwrapping calls. Dotted configured names also match import aliases, so `from typing import overload as ov; @ov` matches `typing.overload`. Unqualified configured names are syntactic-only, and pydocformatter does not execute imports or resolve dynamic decorator expressions.

PDF616 reports only existing function or method docstrings. A forbidden-decorator function without a docstring is allowed by this rule and by the PDF6xx missing-owner-docstring rules. Class decorators, dynamic decorators, and non-primary string literals are ignored.

## Why is this useful?
Keeping overload documentation on the concrete implementation avoids stale duplicate documentation and matches common docstring tooling behavior.

## Ruff compatibility
This rule replaces Ruff's `D418`.

## Examples
A canonical overload variant with a docstring is reported, while the implementation docstring is allowed:

```pydocfmt-example
[input]
@typing.overload
def parse(value: int) -> int:
    """Parse an integer."""
    pass

def parse(value):
    """Parse a value."""
    return value

[output=unchanged]
[findings]
PDF616: Line 3: Function decorated with '@typing.overload' should not have a docstring
```

The standard dotted overload decorators are also matched, and decorator calls are unwrapped:

```pydocfmt-example
[input]
@typing.overload()
def parse(value: int) -> int:
    """Parse an integer."""
    pass

@typing_extensions.overload
def parse(value: str) -> str:
    """Parse a string."""
    pass

def parse(value):
    """Parse a value."""
    return value

[output=unchanged]
[findings]
PDF616: Line 3: Function decorated with '@typing.overload' should not have a docstring
PDF616: Line 8: Function decorated with '@typing_extensions.overload' should not have a docstring
```

Forbidden decorators apply to methods, dunder methods, `__init__`, and local functions as well as top-level functions:

```pydocfmt-example
[input]
class Client:
    """Client."""

    @typing.overload
    def connect(self, value: int):
        """Connect an integer."""
        pass

    @typing.overload
    async def fetch(self, value: int):
        """Fetch an integer."""
        pass

    @typing.overload
    def __init__(self, value: int):
        """Initialize from an integer."""
        self.value = value

def outer():
    """Outer function."""

    @typing.overload
    def inner(value: int):
        """Handle an integer."""
        return value

[output=unchanged]
[findings]
PDF616: Line 6: Function decorated with '@typing.overload' should not have a docstring
PDF616: Line 11: Function decorated with '@typing.overload' should not have a docstring
PDF616: Line 16: Function decorated with '@typing.overload' should not have a docstring
PDF616: Line 24: Function decorated with '@typing.overload' should not have a docstring
```

Functions decorated with forbidden decorators may omit docstrings:

```pydocfmt-example
[input]
@typing.overload
def parse(value: int) -> int:
    pass

def parse(value):
    """Parse a value."""
    return value

[output=unchanged]
```

Unconfigured project-qualified and unresolved alias-like decorator names are not matched:

```pydocfmt-example
[input]
@project.overload
def parse(value: int):
    """Parse an integer."""
    pass

@t.overload
def build(value: int):
    """Build from an integer."""
    pass

[output=unchanged]
```

Custom no-docstring decorators can be configured:

```pydocfmt-example
[settings]
docstring-forbidden-function-decorators = ["project.overload", "t.overload"]

[input]
@project.overload
def parse(value: int):
    """Parse an integer."""
    pass

@t.overload()
def build(value: int):
    """Build from an integer."""
    pass

[output=unchanged]
[findings]
PDF616: Line 3: Function decorated with '@project.overload' should not have a docstring
PDF616: Line 8: Function decorated with '@t.overload' should not have a docstring
```

Dynamic decorators and non-exact dotted names are not matched:

```pydocfmt-example
[input]
class Client:
    """Client."""

    @decorator_factory(overload)
    def generated(self):
        """Generated method."""
        pass

    @(lambda method: method)
    def dynamic(self):
        """Dynamic method."""
        pass

    @typing.overload.extra
    def extended(self):
        """Extended method."""
        pass

[output=unchanged]
```

Class docstrings are not function docstrings, even when the class is decorated with a forbidden function decorator:

```pydocfmt-example
[input]
@overload
class Client:
    """Client."""

[output=unchanged]
```

If several forbidden decorators are present, the first matching decorator in source order is used in the diagnostic:

```pydocfmt-example
[input]
@typing.overload
@overload
def parse(value: int):
    """Parse an integer."""
    pass

[output=unchanged]
[findings]
PDF616: Line 4: Function decorated with '@typing.overload' should not have a docstring
```

Findings target the docstring's physical lines. This includes compact-suite docstrings, multiline docstrings, and implicitly concatenated docstrings:

```pydocfmt-example
[input]
@typing.overload
def compact(): """Compact."""

@typing.overload
def multiline():
    """Summary.

    Details.
    """
    pass

@typing.overload
def concatenated():
    (
        "Summary. "
        "Details."
    )
    pass

[output=unchanged]
[findings]
PDF616: Line 2: Function decorated with '@typing.overload' should not have a docstring
PDF616: Lines 6-9: Function decorated with '@typing.overload' should not have a docstring
PDF616: Lines 15-16: Function decorated with '@typing.overload' should not have a docstring
```

A suppression must target the docstring lines, not just the decorator or definition line:

```pydocfmt-example
[input]
@typing.overload  # pydocfmt: ignore[PDF616]
def decorator_suppressed(value: int):
    """Decorator directive does not suppress."""
    pass

@typing.overload
def definition_suppressed(value: int):  # pydocfmt: ignore[PDF616]
    """Definition directive does not suppress."""
    pass

@typing.overload
def docstring_suppressed(value: int):
    """Docstring directive suppresses."""  # pydocfmt: ignore[PDF616]
    pass

[output=unchanged]
[findings]
PDF616: Line 3: Function decorated with '@typing.overload' should not have a docstring
PDF616: Line 8: Function decorated with '@typing.overload' should not have a docstring
```

The optional-docstring setting does not make a decorator forbidden. It only affects missing-docstring rules:

```pydocfmt-example
[settings]
docstring-forbidden-function-decorators = []
docstring-optional-function-decorators = ["override"]

[input]
@override
def connect():
    """Connect."""
    pass

[output=unchanged]
```

## Options
- `docstring-forbidden-function-decorators`: Function decorator names that PDF616 reports when the decorated function has a docstring. Calls are unwrapped before matching, and dotted names also match import aliases resolved statically by LibCST.
