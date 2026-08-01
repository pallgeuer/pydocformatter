# numpy-return-entry-shape (PDF417)

Fix is not available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, `google`, or `rest`.

## What it does
Checks the structure of recognized NumPy `Returns` sections in primary function and method docstrings.

A section containing one parsed return entry must use the bare type form. A section containing multiple parsed entries may use bare types, named values, or a mixture of both, but every value must occupy a separate entry. A compact head containing multiple names is therefore invalid.

The rule checks each repeated `Returns` section independently. It does not infer runtime return arity, inspect `Yields`, validate general type syntax, or expand tuple and container types. Empty sections and malformed entries remain the responsibility of PDF406 and PDF414.

## Why is this useful?
Consistent return-entry shape follows numpydoc's RT02 convention and makes single-return and multiple-return documentation unambiguous without guessing about Python return values.

## Ruff compatibility
Ruff has no direct equivalent.

## Examples
A single return value uses a bare type:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def count():
    """Count records.

    Returns
    -------
    result : int
        Number of records.
    """

[output=unchanged]
[findings]
PDF417: Line 6: Single-value NumPy Returns entry should contain only the type
```

Multiple values use separate entries:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def bounds():
    """Return bounds.

    Returns
    -------
    minimum : int
        Minimum value.
    str
        Name of the maximum.
    """

[output=unchanged]
```

A compact multi-name head is reported:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def bounds():
    """Return bounds.

    Returns
    -------
    minimum, maximum : int
        Bounds.
    """

[output=unchanged]
[findings]
PDF417: Line 6: NumPy Returns entry should document each returned value in a separate entry
```

A tuple or container type remains one bare entry; the rule does not infer runtime return arity from type spelling:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def bounds():
    """Return both bounds.

    Returns
    -------
    tuple[int, int]
        Minimum and maximum.
    """

[output=unchanged]
```

Repeated return sections are evaluated independently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def convert():
    """Convert a value.

    Returns
    -------
    result : int
        Converted value.

    Returns
    -------
    str
        Display form.
    """

[output=unchanged]
[findings]
PDF417: Line 6: Single-value NumPy Returns entry should contain only the type
```

## Options
None.
