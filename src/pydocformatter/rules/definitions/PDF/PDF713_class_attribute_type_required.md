# class-attribute-type-required (PDF713)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF714`.

## What it does
Checks that parsed class attribute entries in owning class docstrings include documented types. It checks only entries that match inventoried class or instance attributes; it does not require undocumented attributes to be added to the class docstring. Attached attribute docstrings are outside the scope of PDF7xx rules.

For classes that directly inherit from a configured enum-like base, the policy is inverted: present Google and reStructuredText types are reported as redundant. Dotted configured base names are resolved through unshadowed imports and aliases, while unqualified configured names match syntactically. NumPy grammar takes precedence and is not inverted.

For ordinary classes with available single-line annotations, PDF713 inserts a mapped Google type or adds a paired canonical reStructuredText `:vartype:` field, filling an existing empty, single-line field first. For configured enum-like classes, it removes mapped Google types and paired reStructuredText `:vartype:` fields. NumPy entries, missing annotations, and source shapes that cannot be mapped safely remain diagnostic.

The rule is exact opt-in because many projects rely on class annotations instead of repeating attribute types in docstrings.

## Why is this useful?
Projects can require class attribute type documentation while avoiding redundant enum member type text.

## Ruff compatibility
None.

## Examples
PDF713 canonically copies an ordinary class attribute annotation into a Google entry that has no type:

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

[output]
class Client:
    """Client.

    Attributes:
        timeout (int): Timeout in seconds.
        retries (int): Retry count.
    """

    timeout: int = 1
    retries: int = 3
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

Without an attribute annotation, PDF713 reports the missing docstring type but cannot infer a replacement:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout: Timeout in seconds.
    """

    timeout = 1

[output=unchanged]
[findings]
PDF713: Line 5: Class attribute 'timeout' docstring entry is missing a type
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

[output]
from enum import Enum


class Color(Enum):
    """Color.

    Attributes:
        RED: Red value.
        BLUE: Blue value.
    """

    RED = 1
    BLUE = 2
```

NumPy entries keep their required grammar in enum-like classes, so a documented type remains accepted:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
from enum import Enum


class Color(Enum):
    """Color.

    Attributes
    ----------
    RED : int
        Red value.
    """

    RED = 1

[output=unchanged]
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

[output]
import enum as e


class Color(e.Enum):
    """Color.

    Attributes:
        RED: Red value.
    """

    RED = 1
```

## Options
- `docstring-class-attribute-no-type-base-classes`: Direct enum-like base names whose class attribute entries should not include types. Dotted names also match direct import aliases resolved statically by LibCST, and unqualified names are syntactic-only.
