# class-attribute-type-required (PDF713)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF714`.

## What it does
Checks that parsed class attribute entries in owning class docstrings include documented types. For classes that directly inherit from a configured enum-like base, the policy is inverted and present docstring types are reported.

Only entries that match inventoried class or instance attributes are checked. Attached attribute docstrings are intentionally not checked by PDF7xx rules. The rule is exact opt-in because many projects rely on class annotations instead of repeating attribute types in docstrings.

## Why is this useful?
Projects can require class attribute type documentation while avoiding redundant enum member type text.

## Ruff compatibility
None.

## Examples
PDF713 reports ordinary class attribute entries without docstring types:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout: Timeout in seconds.
        retries (int): Retry count.
    """

    timeout: int = 1
    retries: int = 3

[output=unchanged]
[findings]
PDF713: Line 5: Class attribute 'timeout' docstring entry is missing a type
```

Class attribute entries with types are accepted for ordinary classes:

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

For configured enum-like bases, PDF713 is inverted and reports entries that include redundant types:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
from enum import Enum


class Color(Enum):
    """Color.

    Attributes:
        RED (int): Red value.
        BLUE: Blue value.
    """

    RED = 1
    BLUE = 2

[output=unchanged]
[findings]
PDF713: Line 8: Class attribute 'RED' docstring entry should not include a type
```

Dotted configured enum-like base names match import aliases, while unqualified configured names are syntactic-only:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-class-attribute-no-type-base-classes = ["enum.Enum"]

[input]
import enum as e


class Color(e.Enum):
    """Color.

    Attributes:
        RED (int): Red value.
    """

    RED = 1

[output=unchanged]
[findings]
PDF713: Line 8: Class attribute 'RED' docstring entry should not include a type
```

## Options
- `docstring-class-attribute-no-type-base-classes`: Direct enum-like base names whose class attribute entries should not include types. Dotted names also match direct import aliases resolved statically by LibCST, and unqualified names are syntactic-only.
