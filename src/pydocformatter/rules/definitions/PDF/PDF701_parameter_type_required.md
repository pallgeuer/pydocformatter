# parameter-type-required (PDF701)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF702`.

## What it does
Checks that parsed parameter entries in owning function docstrings include a documented type. It checks only entries that match real signature parameters; it does not require undocumented parameters to be added to the docstring.

The rule recognizes types in Google and NumPy parameter entries and in inline or paired reStructuredText fields. Variadic markers are ignored when matching a reStructuredText `:param:` field to its corresponding `:type:` field.

When a single-line parameter annotation is available, PDF701 inserts its annotation text into a mapped Google entry or adds a paired canonical reStructuredText `:type:` field with the parameter's bare name. An existing empty, single-line reStructuredText type field is filled first. NumPy entries, parameters without usable annotations, and source shapes that cannot be mapped safely remain diagnostic.

The rule is convention opt-in because many projects rely on code annotations instead of repeating parameter types in docstrings.

## Why is this useful?
Projects that keep types in docstrings can enforce complete parameter type documentation.

## Ruff compatibility
None.

## Examples
PDF701 canonically copies a parameter annotation into a Google entry that has no type:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value: int, timeout: float):
    """Connect to the service.

    Args:
        value: Endpoint identifier.
        timeout (float): Timeout in seconds.
    """

[output]
def function(value: int, timeout: float):
    """Connect to the service.

    Args:
        value (int): Endpoint identifier.
        timeout (float): Timeout in seconds.
    """
```

An empty reStructuredText type field is filled instead of adding a duplicate field, and the variadic marker is omitted from the `:type:` field name:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def collect(*items: str):
    """Collect items.

    :param *items: Items to collect.
    :type items:
    """

[output]
def collect(*items: str):
    """Collect items.

    :param *items: Items to collect.
    :type items: str
    """
```

NumPy entries with documented types are accepted, including an entry shared by multiple signature parameters:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def function(value: int, timeout: int):
    """Connect to the service.

    Parameters
    ----------
    value, timeout : int
        Connection settings.
    """

[output=unchanged]
```

Without a parameter annotation, PDF701 reports the missing docstring type but cannot infer a replacement:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value):
    """Process a value.

    Args:
        value: Value to process.
    """

[output=unchanged]
[findings]
PDF701: Line 5: Function parameter 'value' docstring entry is missing a type
```

reST `:type:` fields provide the type even when the value field contains only prose:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def function(value: int):
    """Connect to the service.

    :param value: Endpoint identifier.
    :type value: int
    """

[output=unchanged]
```

## Options
None.
