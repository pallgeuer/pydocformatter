# section-name-trailing-content (PDF401)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `none`, `numpy`, or `pep257`.

## What it does
PDF401 reports recognized Google section names that have section content on the same logical line when that line is parsed as ordinary paragraph text. The target layout keeps the section name on its own line and moves the trailing content to the next line at the configured Google section body indentation.

The rule skips summary lines, protected structures such as code fences, and text inside already parsed convention sections. The fix is available for safely mapped simple docstrings. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Keeping section names on their own line makes section boundaries unambiguous for readers and convention-aware parsers.

## Ruff compatibility
This rule is intended to replace the Google-style part of Ruff's `D406`.

## Examples
PDF401 moves same-line Google section content below the section name:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args: arg: The value.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg: The value.
    """
```

Multiple same-line section headers in one docstring are fixed together:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args: arg: The value.

    Returns: int: The value.

    Raises: ValueError: If the value is invalid.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg: The value.

    Returns:
        int: The value.

    Raises:
        ValueError: If the value is invalid.
    """
```

PDF401 does not capitalize section names while moving content. That is handled by PDF400:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    args: arg: The value.
    """

[output]
def value(arg):
    """Return the value.

    args:
        arg: The value.
    """
```

Summary lines that begin with a section-like prefix are not section headers:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def is_valid(arg):
    """Returns: True when the value is valid."""

[output=unchanged]
```

The rule also skips protected blocks such as code fences:

````pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def example():
    """Show command output.

    ```text
    Args: printed by the command.
    ```
    """

[output=unchanged]
````

## Options
- `docstring-convention`: Enables Google section recognition. `none`, `numpy`, and `pep257` ignore this rule.
- `indent-style` and `indent-width`: Control the generated indentation of content moved below the section name.
