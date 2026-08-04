# class-attribute-type-forbidden (PDF714)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF713` and `PDF715`.

## What it does
Checks that parsed class attribute entries in owning class docstrings do not include documented types.

Only entries that match inventoried class or instance attributes are checked, including proven literal slot members. The rule is convention opt-in and cannot be combined with the required-type or type-mismatch class attribute policies.

## Why is this useful?
Projects that rely on code annotations can prevent duplicated class attribute type documentation.

## Ruff compatibility
Ruff's `RUF023` and `PLE0237` inspect slot order and non-slot assignments. PDF714 instead applies docstring no-type policy to proven slot members.

## Examples
PDF714 reports class attribute entries that include docstring type text:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout (int): Timeout in seconds.
        retries: Retry count.
    """

    timeout: int = 1
    retries: int = 3

[output=unchanged]
[findings]
PDF714: Line 5: Class attribute 'timeout' docstring entry should not include a type
```

Class attribute entries without types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout: Timeout in seconds.
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
    fallback: str

[output=unchanged]
[findings]
PDF714: Line 6: Class attribute 'primary' docstring entry should not include a type
PDF714: Line 6: Class attribute 'fallback' docstring entry should not include a type
```

Literal slot members are inventoried even without real assignments, so their documented types are also forbidden:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Point:
    """Point.

    Attributes:
        x (float): Horizontal coordinate.
    """

    __slots__ = ("x",)

[output=unchanged]
[findings]
PDF714: Line 5: Class attribute 'x' docstring entry should not include a type
```

## Options
None.
