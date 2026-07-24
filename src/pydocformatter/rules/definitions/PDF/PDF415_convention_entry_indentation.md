# convention-entry-indentation (PDF415)

Fix is not available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, or `rest`.

## What it does
PDF415 reports high-confidence indentation defects in Google and NumPy convention entries:

- A high-confidence complete Google parameter, attribute, method, or exception entry head must be indented beyond its section header. Bare parameter, attribute, and method entries require an owner-inventory name match; a balanced parenthesized type supplies independent evidence, while exception entries require conventional exception-like names.
- When a parsed Google or NumPy entry has no inline description, an immediate description line must be indented beyond the entry head. This includes named parameter and exception entries and unnamed return or yield entries.

The continuation check is deliberately local. It does not cross a blank line, treat a valid next entry as a description, or report a new section, an adornment, or parser-recognized protected content such as a directive or code fence. Valid peers include bare NumPy return and yield types and both bare and colon-form NumPy exception entries. Correctly nested descriptions and inline Google descriptions are accepted.

PDF100 and PDF415 divide indentation responsibility by intent:

- PDF100 normalizes the absolute physical indentation of safely rewritable docstring lines against the docstring's canonical margin. For parsed Google and NumPy structures, it generates indentation from `indent-style` and `indent-width` and can shift an otherwise correctly nested section as a unit.
- PDF415 validates relative convention relationships using raw evaluated indentation, independently of the canonical margin, virtual margin stripping, or configured indentation width. It asks whether a Google entry is deeper than its section header and whether an immediate Google or NumPy description is deeper than its entry.

A convention section can therefore need only PDF100 when all of its elements are correctly nested but collectively displaced. Conversely, a section can need only PDF415 when its absolute margins are normal but malformed indentation prevented an intended description from being parsed as an entry continuation. Both rules can report independent facts when a structure is collectively displaced and also internally misnested. PDF100 is always fixable when it reports a safely normalizable source change; PDF415 remains diagnostic-only because recognizing a likely relationship does not make the intended replacement indentation certain. PDF415 can also diagnose concatenated or otherwise non-rewritable docstrings that PDF100 deliberately skips.

PDF415 handles indentation of otherwise parseable entries. Malformed delimiters, missing types, and unbalanced Google types belong to PDF414; when one line could resemble both a malformed next entry and an under-indented continuation, the syntax diagnosis takes precedence.

The rule reports the malformed entry or continuation line and does not infer replacement indentation. The correct nesting level depends on the surrounding style and indentation settings, so no fix is applied. Diagnosed lines are excluded from PDF101 prose reflow so another formatting rule cannot silently rewrite the uncertain relationship.

## Why is this useful?
Incorrect entry indentation can move intended documentation outside its section or make a description look like a new top-level block. Documentation tools and semantic checks may then miss parameters, return values, yields, or exceptions even though the text appears visually nearby.

## Ruff compatibility
None.

## Examples
PDF415 reports a Google entry that is not nested under its section:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert(value):
    """Convert a value.

    Args:
    value: The value.
    """

[output=unchanged]
[findings]
PDF415: Line 5: Google docstring entry 'value' should be indented beyond its section header
```

PDF415 reports immediate Google descriptions aligned with their entry heads. Return and yield entries have no semantic name, so their messages describe the entry without an empty name:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert(value):
    """Convert a value.

    Args:
        value:
        Value to convert.

    Returns:
        int:
        Converted value.
    """

[output=unchanged]
[findings]
PDF415: Line 6: Google docstring entry 'value' description should be indented beyond the entry
PDF415: Line 10: Google docstring entry description should be indented beyond the entry
```

This correctly nested Google section is collectively displaced. PDF415 accepts its internal relationships and leaves it unchanged, while PDF100 would move the header to the canonical margin and the entry one configured indent unit below it:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert(value):
    """Convert a value.

      Args:
          value: Value to convert.
    """

[output=unchanged]
```

PDF415 applies the same continuation rule to named and unnamed NumPy entries:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def convert(value):
    """Convert a value.

    Parameters
    ----------
    value : int
    Value to convert.

    Returns
    -------
    int
    Converted value.
    """

[output=unchanged]
[findings]
PDF415: Line 7: NumPy docstring entry 'value' description should be indented beyond the entry
PDF415: Line 12: NumPy docstring entry description should be indented beyond the entry
```

Complete Google exception lists provide enough evidence to diagnose an entry head aligned with its section:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert():
    """Convert a value.

    Raises:
    `ValueError` | pkg.CustomError: Conversion failed.
    """

[output=unchanged]
[findings]
PDF415: Line 5: Google docstring entry 'ValueError', 'pkg.CustomError' should be indented beyond its section header
```

Inline descriptions, nested continuation descriptions, and a valid next entry are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def combine(first, second):
    """Combine values.

    Args:
        first: First value.
        second:
            Second value.

    Returns:
        int:
            Combined value.
    """

[output=unchanged]
```

## Options
None.
