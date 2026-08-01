# section-name-superfluous-colon (PDF413)

Fix is usually available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, `google`, or `rest`.

## What it does
PDF413 reports recognized NumPy section names that end with a superfluous trailing colon. The fix removes the colon and any spaces or tabs after it from the section-name line, while preserving the section-name spelling and indentation.

The rule handles both parsed NumPy sections with underlines and malformed section-name lines at clear section-boundary positions that look like recognized NumPy headings but cannot be parsed yet, such as `Returns:` after a blank line followed directly by body text. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

PDF413 only removes a colon immediately after the recognized section name. It does not remove spaced colons, double colons, same-line section content, pure trailing whitespace, unrecognized headings, or prose-adjacent labels inside section bodies.

## Why is this useful?
NumPy-style section headers are written without trailing colons. Removing the colon keeps the header spelling compatible with tools that expect NumPy docstring syntax.

## Ruff compatibility
This rule is intended to replace Ruff's `D406` colon-suffix checks. Accidental pure trailing-whitespace section-name findings from Ruff's `D406` are covered by PDF102; intentional two-or-more-space Markdown hard breaks are preserved.

## Examples
PDF413 removes a superfluous colon from a canonical NumPy section name:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters:
    ----------
    arg : int
        The value.
    """

[output]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg : int
        The value.
    """
```

Multiple section-name colons in one docstring are fixed together, and trailing spaces or tabs after each colon are removed:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters:	
    ----------
    arg : int
        The value.

    Returns:   
    -------
    int
        The value.
    """

[output]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg : int
        The value.

    Returns
    -------
    int
        The value.
    """
```

PDF413 also fixes recognized NumPy section names that are malformed enough not to parse as sections yet, including multi-word section names and section names before same-line closing quotes:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def related():
    """Return related references.

    See Also:
    Other reference.
    """

def value():
    """Return the value.

    Returns:"""

[output]
def related():
    """Return related references.

    See Also
    Other reference.
    """

def value():
    """Return the value.

    Returns"""
```

When PDF405 is selected together with PDF413, the formatter converges this kind of malformed section into a full NumPy section. PDF413 removes the colon first, which exposes the section name to a later fix pass; PDF405 then inserts the dashed underline:

```python
def related():
    """Return related references.

    See Also:
    Other reference.
    """
```

becomes:

```python
def related():
    """Return related references.

    See Also
    --------
    Other reference.
    """
```

PDF413 preserves the section-name spelling and only removes the colon suffix. Other section-name rules can normalize capitalization, pluralization, and underline length when they are selected:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value():
    """Return the value.

    return:
    ------
    int
        The value.
    """

[output]
def value():
    """Return the value.

    return
    ------
    int
        The value.
    """
```

PDF413 only removes a colon directly after a recognized NumPy section name. Spaced colons, double colons, same-line section content, pure trailing whitespace, and unrecognized headings are left unchanged:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters :
    ----------
    arg : int
        The value.

    Returns::
    -------
    int
        The value.

    Yields   
    ------
    int
        Another value.

    Unknown:
    -------
    Unknown value.
    """

[output=unchanged]
```

PDF413 and PDF102 together cover the mechanically safe Ruff `D406` surface: PDF413 removes section-name colons, while PDF102 removes accidental pure trailing whitespace from non-empty docstring lines without deleting intentional Markdown hard breaks.

Section-like text inside parsed entries, prose-adjacent section body lines, and protected structures is not treated as a section name:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def nested(arg):
    """Return the value.

    Parameters
    ----------
    arg : int
        Returns:
            Nested prose, not a section.
    """

def notes():
    """Return notes.

    Notes
    -----
    Some narrative prose.
    Returns:
    This is still prose, not a section.
    See Also:
    This is still prose, not a section.
    """

def literal():
    """Return an example.

    Example::

        Returns:
        -------
    """

def doctest():
    """Return an example.

    >>> Returns:
    >>> pass
    """

[output=unchanged]
```

Protected code fences are ignored by default, but disabling code-fence parsing can expose clear section-boundary lines to PDF413 like ordinary paragraph text:

````pydocfmt-example
[settings]
docstring-convention = "numpy"
docstring-parse-code-fences = false

[input]
def value():
    """Return the value.

    ```text

    Returns:
    -------
    ```
    """

[output]
def value():
    """Return the value.

    ```text

    Returns
    -------
    ```
    """
````

PDF413 only applies to NumPy sections. Google-style section names require a trailing colon:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg: The value.
    """

[output=unchanged]
```

Concatenated docstrings are reported when a colon-suffixed NumPy section can be parsed, but they are not safely rewritten:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Parameters:\n"
     "----------\n"
     "arg : int\n"
     "    The value.")

[output=unchanged]
[findings]
PDF413: Lines 2-6: Docstring section 'Parameters' should not end with a colon
```

## Options
None.
