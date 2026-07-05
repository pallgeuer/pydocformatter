# class-attribute-type-mismatch (PDF715)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF714`.

## What it does
Checks that parsed class attribute docstring types conservatively match annotated class attributes.

The comparison uses a small, syntax-only type-expression subset. Unparseable or ambiguous expressions are skipped instead of guessed. Only entries that match inventoried class or instance attributes are checked, and NumPy entries that document multiple names are checked once per matching attribute.

## Why is this useful?
Stale class attribute type text can mislead readers when annotations have changed.

## Ruff compatibility
None.

## Examples
PDF715 reports class attribute docstring types that do not match annotations:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout (str): Timeout in seconds.
    """

    timeout: int = 1

[output=unchanged]
[findings]
PDF715: Line 5: Class attribute 'timeout' docstring type does not match the annotation
```

Matching class attribute types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout (int): Timeout in seconds.
    """

    timeout: int = 1

[output=unchanged]
```

NumPy entries that document multiple names are checked once per matching attribute:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """Client.

    Attributes
    ----------
    primary, fallback : str
        Request endpoints.
    """

    primary: str
    fallback: int

[output=unchanged]
[findings]
PDF715: Line 6: Class attribute 'fallback' docstring type does not match the annotation
```

## Options
- `docstring-convention`: Google, NumPy, and reST entries are checked.
