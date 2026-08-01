# section-name-term-normalization (PDF402)

Fix is usually available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
PDF402 reports recognized Google and NumPy section names whose spelling uses a non-preferred equivalent term for the active docstring convention. For Google docstrings, it normalizes `Arguments` to `Args`, `Keyword Arguments` to `Keyword Args`, and `Other Arguments` to `Other Args`. For NumPy docstrings, it normalizes `Other Params` to `Other Parameters`. For reStructuredText docstrings, it normalizes Sphinx-style field aliases with clear preferred spellings: `arg`, `argument`, `key`, `keyword`, `kwarg`, and `parameter` become `param`, while `except` and `exception` become `raises`.

The rule only targets structures parsed by the active convention. Google sections are ignored unless `docstring-convention = "google"`, NumPy sections are ignored unless `docstring-convention = "numpy"`, and reStructuredText fields are ignored unless `docstring-convention = "rest"`.

PDF402 does not normalize singular names to plural names; PDF401 handles that separately. It also does not normalize Google `Warns` to `Warning` or `Warnings`, or the reverse, because `Warns` documents emitted warnings while `Warning` and `Warnings` are admonition sections. The fix changes only the section or field name text. It preserves indentation, colons, line endings, field arguments, underlines, and content. If a NumPy section name changes length, the underline may no longer match the section-name length after running only PDF402; PDF405 handles NumPy underline normalization separately. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Consistent section-name terminology reduces equivalent spellings without changing the meaning of sections that only look similar.

## Ruff compatibility
None.

## Examples
PDF402 normalizes equivalent Google section terms:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Arguments:
        arg: The value.

    Keyword Arguments:
        option: The option.

    Other Arguments:
        other: Other value.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg: The value.

    Keyword Args:
        option: The option.

    Other Args:
        other: Other value.
    """
```

PDF402 normalizes equivalent NumPy section terms. The output shows only the PDF402 fix, so the NumPy underline is preserved even when the changed section name no longer matches it:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Other Params
    ------------
    arg : int
        The value.
    """

[output]
def value(arg):
    """Return the value.

    Other Parameters
    ------------
    arg : int
        The value.
    """
```

PDF402 normalizes equivalent reStructuredText field terms:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :parameter arg: The value.
    :arg other: Other value.
    :KEY option: Option value.
    :exception ValueError: Bad value.
    :except RuntimeError: Worse value.
    """

[output]
def value(arg):
    """Return the value.

    :param arg: The value.
    :param other: Other value.
    :param option: Option value.
    :raises ValueError: Bad value.
    :raises RuntimeError: Worse value.
    """
```

PDF402 does not pluralize singular section names. PDF401 handles singular-to-plural spellings:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Argument:
        arg: The value.

    Keyword Argument:
        option: The option.
    """

[output=unchanged]
```

PDF402 preserves distinct Google warning section meanings:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Warning:
        Be careful.

    Warns:
        RuntimeWarning: May warn.
    """

[output=unchanged]
```

PDF402 can normalize mixed-case equivalent reStructuredText field terms by itself, but plural field spellings such as `RETURNS` still belong to PDF400 and PDF401:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :PARAMETER arg: The value.
    :Exception ValueError: Bad value.
    """

[output]
def value(arg):
    """Return the value.

    :param arg: The value.
    :raises ValueError: Bad value.
    """
```

PDF402 reports unsafe source mappings without applying a fix:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Arguments:\n"
     "    arg: The value.")

[output=unchanged]
[findings]
PDF402: Lines 2-4: Docstring section name 'Arguments' should use equivalent term 'Args'
```

## Options
None.
