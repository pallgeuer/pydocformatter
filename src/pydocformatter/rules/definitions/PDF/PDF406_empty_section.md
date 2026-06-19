# empty-section (PDF406)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF406 reports recognized Google and NumPy sections, plus rest fields under the rest convention, that contain no meaningful body content after their header or field marker. Header-only sections, sections containing only blank lines, and empty rest fields are findings.

Any non-blank section body content counts as content, including entries, prose, doctests, code fences, lists, block quotes, directives, literal blocks, tables, rest-looking text, and verbatim blocks. The rule is diagnostic-only and leaves source unchanged.

## Why is this useful?
Empty sections imply documentation exists where readers will find none.

## Ruff compatibility
This rule is intended to replace Ruff's `D414`.

## Examples
PDF406 reports empty Google sections:

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
PDF406: Line 4: Docstring section 'Args' should not be empty
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
PDF406: Line 4: Docstring section 'Args' should not be empty
PDF406: Line 5: Docstring section 'Returns' should not be empty
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
PDF406: Line 4: Docstring section 'Parameters' should not be empty
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
        :param value: Ordinary section body content also counts.
    """

[output=unchanged]
````

Empty rest fields are checked under the rest convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :param arg:
    :returns: The value.
    """

[output=unchanged]
[findings]
PDF406: Line 4: Docstring field ':param arg:' should not be empty
```

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
- `docstring-convention`: Enables Google and NumPy section recognition and rest field recognition. `none` and `pep257` ignore this rule.
