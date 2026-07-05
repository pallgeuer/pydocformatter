# yield-type-required (PDF709)

Fix is not available.

Rule is ignored if `docstring-convention` is `none`, `pep257`, `google`, `numpy`, or `rest`.

Rule is incompatible with `PDF710`.

## What it does
Checks that parsed yield entries in owning function docstrings include a documented type.

Only functions that actually contain yield expressions are checked. The rule is exact opt-in because many projects rely on generator annotations instead of repeating yield types in docstrings.

## Why is this useful?
Projects that keep yield types in docstrings can enforce complete yield type documentation.

## Ruff compatibility
None.

## Examples
PDF709 reports yield entries without docstring types:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> Iterator[int]:
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

reST `:ytype:` fields provide the type for paired yield documentation:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> Iterator[int]:
    """Yield values.

    :yields: Next value.
    :ytype: int
    """
    yield 1

[output=unchanged]
```

## Options
- `docstring-convention`: The rule is exact opt-in; exact rule-code selection restores it for parsed conventions.
