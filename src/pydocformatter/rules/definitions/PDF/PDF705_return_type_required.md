# return-type-required (PDF705)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF706`.

## What it does
Checks that parsed return entries in owning function docstrings include a documented type. It checks existing return entries rather than requiring a return section or field to be added.

The rule recognizes types in Google and NumPy return entries and in inline or paired reStructuredText fields. Generator functions are skipped because their produced values belong in yield entries.

When a single-line return annotation is available, PDF705 adds a paired canonical reStructuredText `:rtype:` field or fills an existing empty, single-line field. Google and NumPy entries, functions without usable return annotations, and source shapes that cannot be mapped safely remain diagnostic.

The rule is exact opt-in because many projects rely on function annotations instead of repeating return types in docstrings.

## Why is this useful?
Projects that keep return types in docstrings can enforce complete return type documentation.

## Ruff compatibility
None.

## Examples
PDF705 canonically copies a return annotation into a paired reStructuredText `:rtype:` field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> int:
    """Return a value.

    :returns: Result value.
    """
    return 1

[output]
def function() -> int:
    """Return a value.

    :returns: Result value.
    :rtype: int
    """
    return 1
```

Google return entries with types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function() -> int:
    """Return a value.

    Returns:
        int: Result value.
    """
    return 1

[output=unchanged]
```

Without a return annotation, PDF705 reports the missing docstring type but cannot infer a replacement:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function():
    """Return a value.

    :returns: Result value.
    """
    return 1

[output=unchanged]
[findings]
PDF705: Line 4: Function return 'return' docstring entry is missing a type
```

An existing empty reStructuredText type field is filled instead of adding a duplicate field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function() -> int:
    """Return a value.

    :returns: Result value.
    :rtype:
    """
    return 1

[output]
def function() -> int:
    """Return a value.

    :returns: Result value.
    :rtype: int
    """
    return 1
```

## Options
None.
