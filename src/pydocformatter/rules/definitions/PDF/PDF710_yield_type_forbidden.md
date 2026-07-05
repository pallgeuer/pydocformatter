# yield-type-forbidden (PDF710)

Fix is not available.

Rule is ignored if `docstring-convention` is `none`, `pep257`, `google`, `numpy`, or `rest`.

Rule is incompatible with `PDF709`, `PDF711`.

## What it does
Checks that parsed yield entries in owning function docstrings do not include documented types.

Only functions that actually contain yield expressions are checked. The rule is exact opt-in and cannot be combined with the required-type or type-mismatch yield policies.

## Why is this useful?
Projects that rely on code annotations can prevent duplicated yield type documentation.

## Ruff compatibility
None.

## Examples
PDF710 reports yield entries that include docstring type text:

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
[findings]
PDF710: Line 5: Function yield 'yield' docstring entry should not include a type
```

Yield entries without types are accepted:

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
```

reST `:ytype:` fields are also forbidden because they provide docstring type text:

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
[findings]
PDF710: Line 5: Function yield 'yield' docstring entry should not include a type
```

## Options
- `docstring-convention`: The rule is exact opt-in; exact rule-code selection restores it for parsed conventions.
