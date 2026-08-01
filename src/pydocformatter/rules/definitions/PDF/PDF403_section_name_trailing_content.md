# section-name-trailing-content (PDF403)

Fix is usually available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, `numpy`, or `rest`.

## What it does
PDF403 reports recognized Google section names that have section content on the same logical line when that line is parsed as ordinary paragraph text. The target layout keeps the section name on its own line and moves the trailing content to the next line at the configured Google section body indentation.

The rule skips summary lines, protected structures such as code fences, and text inside already parsed convention sections. It also leaves lines containing non-default whitespace or suspicious controls unchanged so PDF004 and source-preserving rules remain authoritative. The fix is available for safely mapped simple docstrings. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Keeping section names on their own line makes section boundaries unambiguous for readers and convention-aware parsers.

## Ruff compatibility
This rule covers a Google-specific section-header cleanup. Ruff's current `D406` default is NumPy-only, but pydocformatter enables PDF403 by default under the Google convention because the rule only affects recognized Google section headers.

## Examples
PDF403 moves same-line Google section content below the section name:

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

PDF403 does not capitalize section names while moving content. That is handled by PDF400:

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

A recognized header in a concatenated docstring is reported without an unsafe rewrite:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def function(value):
    ("Summary.\n\n"
     "Args: value: Description.")

[output=unchanged]
[findings]
PDF403: Lines 2-3: Docstring section 'Args' should be followed by a line break
```

## Options
- `indent-style`: Indentation style used for content moved below the section name.
- `indent-width`: Indentation width used for content moved below the section name.
