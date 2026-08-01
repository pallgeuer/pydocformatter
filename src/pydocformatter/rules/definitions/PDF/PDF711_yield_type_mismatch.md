# yield-type-mismatch (PDF711)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF710`.

## What it does
Checks that parsed yield docstring types conservatively match the yielded type extracted from recognized generator or iterator return annotations. It checks existing yield entries only in functions that contain yield expressions.

The yielded type is the first type argument of `Generator`, `Iterator`, `Iterable`, `AsyncGenerator`, `AsyncIterator`, or `AsyncIterable` from `typing` or `collections.abc`. Direct qualified names, stringized annotations, and unshadowed import aliases are recognized; local or shadowed names are not assumed to be typing containers.

The comparison uses a syntax-only type-expression subset that covers common names, qualified names, subscriptions, tuples, and unions. Unparseable, unsupported, ambiguous, or unrecognized annotations are skipped instead of guessed. Google, NumPy, and inline or paired reStructuredText types are supported. Findings are diagnostic-only because choosing between conflicting documentation and code requires human judgment.

## Why is this useful?
Stale yield type text can mislead readers when generator annotations have changed.

## Ruff compatibility
None.

## Examples
PDF711 reports yield docstring types that do not match recognized generator annotations:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
from typing import Iterator


def function() -> Iterator[int]:
    """Yield values.

    Yields:
        str: Next value.
    """
    yield 1

[output=unchanged]
[findings]
PDF711: Line 8: Function yield 'yield' docstring type does not match the annotation
```

Matching yield types are accepted for supported generator and iterator annotations:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> typing.Generator[dict[str, int], None, None]:
    """Yield values.

    Yields:
        dict[str, int]: Next value.
    """
    yield {"value": 1}

[output=unchanged]
```

For paired reStructuredText fields, a mismatch is reported on the `:ytype:` field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> typing.Iterator[int]:
    """Yield values.

    :yields: Next value.
    :ytype: str
    """
    yield 1

[output=unchanged]
[findings]
PDF711: Line 5: Function yield 'yield' docstring type does not match the annotation
```

Unrecognized generator annotations are skipped by mismatch checks:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> CustomStream[int]:
    """Yield values.

    Yields:
        str: Next value.
    """
    yield 1

[output=unchanged]
```

## Options
None.
