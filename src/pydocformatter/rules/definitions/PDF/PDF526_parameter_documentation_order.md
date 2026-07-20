# parameter-documentation-order (PDF526)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed parameter documentation follows the declaration order of the owning function signature. PDF526 checks the primary docstrings of synchronous and asynchronous functions, methods, and nested functions. It does not check module or class docstrings, attribute docstrings, additional string literals after a primary docstring, or functions without docstrings.

The rule compares the first parsed occurrence of each real signature parameter across the complete docstring. It reports every first occurrence preceded by a parameter that appears later in the signature. Each message names the highest-ranked signature parameter seen earlier in the docstring, so one reversed sequence can produce several findings. A reported occurrence does not reset that comparison point.

Missing parameters do not need to be filled in for the remaining documented parameters to be ordered. Extraneous names, wrong-case names, repeated later entries, and keys documented for an unpacked `TypedDict` do not establish or reset the order. Matching is case-sensitive. Leading stars are ignored when matching a docstring name to a signature parameter, but `*args` and `**kwargs` retain their stars in diagnostic messages.

Google and NumPy parameter-section aliases form one sequence across the complete docstring. A NumPy declaration containing multiple names preserves their written left-to-right order. For reStructuredText docstrings, the first parsed value or type field for a parameter establishes its position; subsequent fields for the same parameter are repetitions and do not affect the result.

Positional-only, positional-or-keyword, variadic positional, keyword-only, and variadic keyword parameters use their declaration order. Explicitly documented method receivers participate at their signature position, while omitted receivers have no effect. Every function is checked against its own signature, including a nested function inside another checked function.

Only entries recognized by the active `docstring-convention` participate. Parser-protected examples, literal blocks, code fences, directives, doctests, and similar structures do not look like parameter documentation merely because their text resembles an entry. The `none` and `pep257` conventions have no parsed parameter entries, so the rule is disabled under those conventions even when selected by its exact code.

Fixes are not offered because moving one parsed entry safely can require moving its multiline description, preserving comments and blank lines, and deciding whether entries should cross section boundaries.

## Why is this useful?
Keeping documentation aligned with a function signature makes parameters easier to scan, review, and compare with call sites. It also exposes stale documentation after a signature is reordered without requiring every parameter to be documented.

## Ruff compatibility
Ruff has no direct parameter-documentation-order rule. PDF526 complements Ruff's `D417` and `DOC102` checks by validating the relative order of documentation that already matches real signature parameters. It covers the same broad problem as numpydoc's `PR03` and pydoclint's `check-arg-order`, with pydocformatter-specific behavior for multiple sections, reStructuredText fields, repeated entries, receivers, and unpacked keyword documentation.

## Examples
A parameter appearing after a later signature parameter is reported on its docstring entry:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def combine(first, second, third):
    """Combine values.

    Args:
        second: Second value.
        first: First value.
        third: Third value.
    """

[output=unchanged]
[findings]
PDF526: Line 6: Docstring parameter 'first' should appear before 'second' to match the function signature
```

The sequence spans recognized parameter-section aliases:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def configure(first, *, mode, timeout):
    """Configure the client.

    Keyword Args:
        mode: Operating mode.
        timeout: Timeout in seconds.

    Other Arguments:
        first: First value.
    """

[output=unchanged]
[findings]
PDF526: Line 9: Docstring parameter 'first' should appear before 'timeout' to match the function signature
```

Each late name in a NumPy multi-name entry receives a precise finding, even when the findings share a line:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def combine(first, second, third):
    """Combine values.

    Parameters
    ----------
    third, first, second : int
        Values.
    """

[output=unchanged]
[findings]
PDF526: Line 6: Docstring parameter 'first' should appear before 'third' to match the function signature
PDF526: Line 6: Docstring parameter 'second' should appear before 'third' to match the function signature
```

The first reStructuredText value or type field for each name establishes its position:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def combine(first, second):
    """Combine values.

    :type second: int
    :param first: First value.
    :param second: Second value.
    :type first: int
    """

[output=unchanged]
[findings]
PDF526: Line 5: Docstring parameter 'first' should appear before 'second' to match the function signature
```

Missing, extraneous, repeated, and unpack-expanded names do not disturb the order of real first occurrences:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
from typing import TypedDict, Unpack


class Options(TypedDict):
    mode: str


def configure(first, second, **kwargs: Unpack[Options]):
    """Configure values.

    Args:
        first: First value.
        mode: Unpacked option.
        stale: Obsolete value.
        second: Second value.
        first: Repeated first value.
        kwargs: Complete options.
    """

[output=unchanged]
```

All signature parameter categories use one declaration order. Explicit stars are optional in the docstring for matching but are retained in messages, and an explicitly documented receiver occupies the first position:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Builder:
    def build(self, first, /, *items, mode, **options):
        """Build a value.

        Args:
            **options: Additional options.
            items: Input items.
            mode: Build mode.
            first: First value.
            self: Builder instance.
        """

[output=unchanged]
[findings]
PDF526: Line 7: Docstring parameter '*items' should appear before '**options' to match the function signature
PDF526: Line 8: Docstring parameter 'mode' should appear before '**options' to match the function signature
PDF526: Line 9: Docstring parameter 'first' should appear before '**options' to match the function signature
PDF526: Line 10: Docstring parameter 'self' should appear before '**options' to match the function signature
```

Entry-like text inside a protected literal block is example content, not parameter documentation. The real entries below it remain ordered:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def combine(first, second):
    """Combine values.

    Args:
        Example::

            second: This is example text, not documentation.

        first: First value.
        second: Second value.
    """

[output=unchanged]
```

## Options
None.
