# yield-type-mismatch (PDF711)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF710`.

## What it does
Checks that parsed yield docstring types conservatively match recognized generator or iterator return annotations.

The comparison uses a small, syntax-only type-expression subset and extracts the first type argument from recognized generator and iterator return annotations resolved from `typing`, `collections.abc`, or direct qualified names such as `typing.Iterator`. Unparseable, ambiguous, or unrecognized annotations are skipped instead of guessed.

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
