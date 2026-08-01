# parameter-variadic-marker-style (PDF527)

Fix is usually available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that documented parameters use the convention-specific canonical variadic marker spelling.

Google and NumPy entries must match the owning function signature, including `*args` and `**kwargs`. reStructuredText parameter value and type fields must use bare names such as `args` and `kwargs`. A single reStructuredText backslash escaping one or two leading stars is recognized as the corresponding variadic marker, so `\*args` and `\**kwargs` can be matched and normalized without broadly unescaping field arguments. Bare reStructuredText names avoid interpreting unescaped stars as inline markup and keep paired value and type fields aligned.

The rule matches names using the same star-stripped, case-sensitive comparison as PDF500, PDF501, and PDF526, then compares the documented spelling with the convention's canonical style. It reports missing, excess, and wrong-count stars only for names that match real parameters. Unknown names remain exclusively the responsibility of PDF501.

Every mismatched occurrence is reported independently, including duplicates, individual names in NumPy multi-name entries, and reStructuredText type fields without a paired value field. For `**kwargs: Unpack[Options]`, individual `TypedDict` keys remain independent expanded documentation, while an explicitly documented `kwargs` container uses the normal convention-specific spelling.

The automatic fix replaces each parser-owned, safely mapped name span without changing surrounding entry syntax, inline types, descriptions, or spacing. Exact logical lines represented by escapes in a simple string can be fixed even when they do not have their own physical source line. Concatenated docstrings and other source mappings that cannot be rewritten safely are reported without a fix.

## Why is this useful?
Consistent marker spelling prevents accidental one-star and two-star confusion. Signature spelling keeps Google and NumPy entries aligned with the public function signature, while bare reStructuredText names avoid markup warnings and allow value and type fields to use one exact key.

## Ruff compatibility
PDF527 is related to Ruff's `D417`, while PDF500 remains the replacement for D417's missing-parameter behavior.

## Examples
Missing and incorrect Google variadic markers are fixed to match the function signature:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def collect(value, *args, **kwargs):
    """Collect values.

    Args:
        *value: Ordinary value.
        args: Positional values.
        *kwargs: Keyword values.
    """

[output]
def collect(value, *args, **kwargs):
    """Collect values.

    Args:
        value: Ordinary value.
        *args: Positional values.
        **kwargs: Keyword values.
    """
```

Every mismatched name in a NumPy multi-name entry is fixed independently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def collect(value, *args, **kwargs):
    """Collect values.

    Parameters
    ----------
    *value, args, *kwargs : object
        Values to collect.
    """

[output]
def collect(value, *args, **kwargs):
    """Collect values.

    Parameters
    ----------
    value, *args, **kwargs : object
        Values to collect.
    """
```

reStructuredText value and type fields are both normalized to bare names, including inline typed value fields:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def collect(*args, **kwargs):
    r"""Collect values.

    :param tuple[object, ...] \*args: Positional values.
    :type \*args: tuple[object, ...]
    :param **kwargs: Keyword values.
    :type **kwargs: dict[str, object]
    """

[output]
def collect(*args, **kwargs):
    r"""Collect values.

    :param tuple[object, ...] args: Positional values.
    :type args: tuple[object, ...]
    :param kwargs: Keyword values.
    :type kwargs: dict[str, object]
    """
```

Expanded `TypedDict` keys are ignored, but an explicitly documented unpacking container is fixed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
from typing import TypedDict, Unpack


class Options(TypedDict):
    mode: str


def configure(**kwargs: Unpack[Options]):
    """Configure values.

    Args:
        mode: Expanded option.
        kwargs: Complete option mapping.
    """

[output]
from typing import TypedDict, Unpack


class Options(TypedDict):
    mode: str


def configure(**kwargs: Unpack[Options]):
    """Configure values.

    Args:
        mode: Expanded option.
        **kwargs: Complete option mapping.
    """
```

Variadic names that already match the function signature are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def collect(*args, **kwargs):
    """Collect values.

    Args:
        *args: Positional values.
        **kwargs: Keyword values.
    """

[output=unchanged]
```

Source mappings that cannot be rewritten safely still produce a non-fixable finding:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def collect(*args):
    ("Collect values.\n\n"
     "Args:\n"
     "    args: Positional values.")

[output=unchanged]
[findings]
PDF527: Lines 2-4: Docstring parameter 'args' should be written as '*args' to match the function signature
```

## Options
None.
