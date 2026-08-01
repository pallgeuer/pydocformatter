# yield-type-required (PDF709)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF710`.

## What it does
Checks that parsed yield entries in owning function docstrings include a documented type. It checks existing yield entries rather than requiring a yield section or field to be added.

Only functions that actually contain yield expressions are checked. The yielded type is extracted from the first type argument of recognized `Generator`, `Iterator`, `Iterable`, `AsyncGenerator`, `AsyncIterator`, and `AsyncIterable` return annotations from `typing` or `collections.abc`, including unshadowed import aliases.

When a recognized single-line yield annotation is available, PDF709 adds a paired canonical reStructuredText `:ytype:` field or fills an existing empty, single-line field. Named reStructuredText yield fields retain their bare name. Google and NumPy entries, missing or unrecognized annotations, and source shapes that cannot be mapped safely remain diagnostic.

The rule is exact opt-in because many projects rely on generator annotations instead of repeating yield types in docstrings.

## Why is this useful?
Projects that keep yield types in docstrings can enforce complete yield type documentation.

## Ruff compatibility
None.

## Examples
PDF709 copies the yielded type from a recognized generator return annotation:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
from typing import Iterator


def function() -> Iterator[int]:
    """Yield values.

    :yields: Next value.
    """
    yield 1

[output]
from typing import Iterator


def function() -> Iterator[int]:
    """Yield values.

    :yields: Next value.
    :ytype: int
    """
    yield 1
```

Without a usable generator return annotation, the finding remains diagnostic:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function():
    """Yield values.

    :yields: Next value.
    """
    yield 1

[output=unchanged]
[findings]
PDF709: Line 4: Function yield 'yield' docstring entry is missing a type
```

Yield entries with types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> Iterator[int]:
    """Yield values.

    Yields:
        int: Next value.
    """
    yield 1

[output=unchanged]
```

Named reStructuredText yield fields retain their name when PDF709 inserts the paired type field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> typing.Iterator[int]:
    """Yield values.

    :yield item: Next value.
    """
    yield 1

[output]
def function() -> typing.Iterator[int]:
    """Yield values.

    :yield item: Next value.
    :ytype item: int
    """
    yield 1
```

## Options
None.
