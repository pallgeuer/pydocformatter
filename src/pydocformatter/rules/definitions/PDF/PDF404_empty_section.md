# empty-section (PDF404)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF404 reports recognized Google and NumPy sections that contain no meaningful body content after the section header. Header-only sections and sections containing only blank lines are findings.

Any non-blank body content counts as content, including entries, prose, doctests, code fences, lists, block quotes, directives, literal blocks, tables, Sphinx fields, and verbatim blocks. The rule is diagnostic-only and leaves source unchanged.

## Why is this useful?
Empty sections imply documentation exists where readers will find none.

## Ruff compatibility
This rule is intended to replace Ruff's `D414`.

## Examples
PDF404 reports empty Google sections:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
    """

[output=unchanged]
[findings]
PDF404: Line 4: Docstring section 'Args' should not be empty
```

Adjacent header-only sections are separate findings:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
    Returns:
    """

[output=unchanged]
[findings]
PDF404: Line 4: Docstring section 'Args' should not be empty
PDF404: Line 5: Docstring section 'Returns' should not be empty
```

NumPy sections are checked after their underline:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters
    ----------
    """

[output=unchanged]
[findings]
PDF404: Line 4: Docstring section 'Parameters' should not be empty
```

Any non-blank section body counts as content, including protected or structured content:

````pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def example():
    """Show an example.

    Examples:
        ```python
        example()
        ```

    Args:
        :param value: Legacy field content also counts.
    """

[output=unchanged]
````

Section-like text is ignored when section parsing is disabled:

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
def value(arg):
    """Return the value.

    Args:
    """

[output=unchanged]
```

## Options
- `docstring-convention`: Enables Google and NumPy section recognition. `none` and `pep257` ignore this rule.
