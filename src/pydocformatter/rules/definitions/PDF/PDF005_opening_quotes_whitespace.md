# opening-quotes-whitespace (PDF005)

Fix is always available.

## What it does
Checks for spaces and tabs between the opening quotes and content on the first evaluated docstring line. The fix removes that quote-adjacent whitespace while leaving the content, quote style, string prefix, remaining source spelling, and line endings otherwise unchanged.

The rule only looks at the first evaluated docstring line. It does not change indentation or whitespace on later lines, and it does not change spaces or tabs before closing quotes. Those cases are owned by other PDF rules.

PDF005 only handles quote-adjacent whitespace when the first evaluated line also contains non-empty content. A line containing only spaces and tabs after the opening quotes is a blank docstring line, so PDF004 owns that case.

PDF005 only rewrites safely mapped simple docstring literals. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escaped newline sequences.

## Why is this useful?
Removing accidental leading whitespace gives docstrings a predictable shape and avoids leading spaces in rendered docstring text.

## Ruff compatibility
This rule is intended to replace the opening-quotes part of Ruff's `D210` when pydocformatter is responsible for docstring whitespace.

## Example
The canonical PDF005 fix removes spaces immediately after the opening quotes:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """  Return the area."""

[output]
def area(radius: float) -> float:
    """Return the area."""
```

Multiple spaces and tabs after the opening quotes are removed from one-line and multiline docstrings:

```pydocfmt-example
[input]
def one_line() -> str:
    """	  Return the value."""

def describe(value: int) -> str:
    """   Return the description.
    Detail lines keep their own indentation.
    """

[output]
def one_line() -> str:
    """Return the value."""

def describe(value: int) -> str:
    """Return the description.
    Detail lines keep their own indentation.
    """
```

Only the opening side is changed by PDF005. Closing quote whitespace is left for PDF006:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """  Return the area.  """

[output]
def area(radius: float) -> float:
    """Return the area.  """
```

Whitespace-only opening quote lines are left for PDF004:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """   
    Return the area.
    """

[output=unchanged]
```

Spaces and tabs are the only characters PDF005 removes. Other evaluated whitespace next to the opening quotes is preserved as content:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """   \u00a0Return the area."""

[output]
def area(radius: float) -> float:
    """\u00a0Return the area."""
```

Module, class, parenthesized, and simple-suite docstrings are all handled when they are simple safely mapped literals:

```pydocfmt-example
[input]
"""  Module summary."""

class Widget:
    ("""  Class summary.""")

def area(radius: float) -> float: """  Return the area."""; return 0.0

[output]
"""Module summary."""

class Widget:
    ("""Class summary.""")

def area(radius: float) -> float: """Return the area."""; return 0.0
```

Quote delimiters, raw prefixes, and literal backslashes are preserved when the docstring can be safely mapped:

```pydocfmt-example
[input]
def path_hint() -> str:
    r'''  Return C:\temp.'''

[output]
def path_hint() -> str:
    r'''Return C:\temp.'''
```

PDF005 can remove whitespace before content that starts with delimiter quote characters, as long as the resulting source still represents the same simple string:

```pydocfmt-example
[input]
def double_quote() -> str:
    """  "quoted"."""

def single_quote() -> str:
    '''  'quoted'.'''

[output]
def double_quote() -> str:
    """"quoted"."""

def single_quote() -> str:
    ''''quoted'.'''
```

Concatenated docstrings and docstrings with escaped newlines are skipped because the exact source line ownership is ambiguous for this rule:

```pydocfmt-example
[input]
def concatenated() -> None:
    ("  Summary.\n"
     "Body.")

def escaped_newline() -> None:
    """  Summary.\nBody."""

[output=unchanged]
```

Empty docstrings and non-docstring string expressions are also unchanged:

```pydocfmt-example
[input]
def empty() -> None:
    """"""

def not_docstring() -> None:
    value = 1
    """  Summary."""

[output=unchanged]
```

## Options
None.
