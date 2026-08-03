# class-attribute-missing-description (PDF712)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed class attribute entries in owning class docstrings include a prose description.

Only entries that match inventoried class or instance attributes are checked. Proven literal slot members are instance attributes for this comparison. Attached attribute docstrings are intentionally not checked by PDF7xx rules.

An orphan reST `:vartype name:` field has no attribute value entry whose description PDF712 could check, so PDF722 owns that structural problem.

## Why is this useful?
Attribute entries without descriptions do not explain class state or constants.

## Ruff compatibility
Ruff's `RUF023` and `PLE0237` inspect slot order and non-slot assignments. PDF712 instead checks descriptions for documented attributes, including proven slot members.

## Examples
PDF712 reports class attribute entries without descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout (int):
        retries:
    """

    timeout: int = 1
    retries: int = 3

[output=unchanged]
[findings]
PDF712: Line 5: Class attribute 'timeout' docstring entry is missing a description
PDF712: Line 6: Class attribute 'retries' docstring entry is missing a description
```

Class attribute entries with descriptions are accepted:

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

NumPy entries that document multiple attributes are checked once per matching class attribute, even though the findings share one entry line:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """Client.

    Attributes
    ----------
    timeout, retries : int
    """

    timeout: int = 1
    retries: int = 3

[output=unchanged]
[findings]
PDF712: Line 6: Class attribute 'timeout' docstring entry is missing a description
PDF712: Line 6: Class attribute 'retries' docstring entry is missing a description
```

For reST, PDF712 checks attribute value fields rather than standalone type fields. A paired empty value field is reported, while a type-only entry for another real attribute is left to PDF722:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """Client.

    :vartype timeout: int
    :var timeout:
    :vartype retries: int
    """

    timeout: int = 1
    retries: int = 3

[output=unchanged]
[findings]
PDF712: Line 5: Class attribute 'timeout' docstring entry is missing a description
```

Attached attribute docstrings are ignored by PDF7xx owning-docstring rules:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    timeout: int = 1
    """Timeout.

    Attributes:
        timeout (str):
    """

[output=unchanged]
```

Proven literal slot members participate even without separate assignments, so an empty slot entry is checked like any other inventoried class attribute:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Point:
    """Point.

    Attributes:
        x (float):
        y (float): Vertical coordinate.
    """

    __slots__ = ("x", "y")

[output=unchanged]
[findings]
PDF712: Line 5: Class attribute 'x' docstring entry is missing a description
```

## Options
None.
