# closing-quotes-whitespace (PDF006)

Fix is always available.

## What it does
Checks for spaces and tabs between content and same-line closing quotes on the final evaluated docstring line. The fix normally removes that whitespace while leaving the content, quote style, string prefix, remaining source spelling, and line endings otherwise unchanged.

If removing all quote-adjacent whitespace would collide with the closing delimiter, PDF006 first tries to escape delimiter quote characters while preserving the evaluated docstring value. If no value-preserving spelling is available while keeping the original prefix and delimiter, PDF006 keeps exactly one ASCII space before the closing quotes instead, such as for raw strings ending in an odd run of backslashes.

PDF006 only looks at the final evaluated docstring line, and only when the closing quotes are on that same evaluated line. It does not change spaces or tabs after opening quotes, and it does not change trailing whitespace on non-final evaluated lines.

PDF006 only handles quote-adjacent whitespace when the final evaluated line also contains non-empty content. Whitespace-only closing quote lines are PDF004 findings. Non-empty lines followed by an evaluated newline before the closing quotes are PDF003 findings.

PDF006 only rewrites safely mapped simple docstring literals. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escaped newline sequences or unsupported escape spellings.

## Why is this useful?
Removing accidental trailing whitespace gives docstrings a predictable shape and avoids trailing spaces in rendered docstring text.

## Ruff compatibility
This rule is intended to replace the closing-quotes part of Ruff's `D210` when pydocformatter is responsible for docstring whitespace.

## Example
The canonical PDF006 fix removes spaces immediately before same-line closing quotes:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.  """

[output]
def area(radius: float) -> float:
    """Return the area."""
```

Multiple spaces and tabs before same-line closing quotes are removed from one-line and multiline docstrings:

```pydocfmt-example
[input]
def one_line() -> str:
    """Return the value.	 """

def describe(value: int) -> str:
    """Return the description.
    Keep the detail.	"""

[output]
def one_line() -> str:
    """Return the value."""

def describe(value: int) -> str:
    """Return the description.
    Keep the detail."""
```

Only the closing side is changed by PDF006:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """  Return the area.  """

[output]
def area(radius: float) -> float:
    """  Return the area."""
```

If removing all whitespace would collide with the closing delimiter, PDF006 escapes delimiter quote characters when that preserves the evaluated value. Raw strings ending in an odd run of backslashes still keep one separator space:

```pydocfmt-example
[input]
def quote_one() -> str:
    """Return "  """

def quote_two() -> str:
    """Return ""  """

def path_hint() -> str:
    r"""Return C:\temp\  """

[output]
def quote_one() -> str:
    """Return \""""

def quote_two() -> str:
    """Return \"\""""

def path_hint() -> str:
    r"""Return C:\temp\ """
```

An existing single separator for a delimiter quote collision is also removed by escaping when possible, while the raw backslash fallback remains unchanged:

```pydocfmt-example
[input]
def quote_one() -> str:
    """Return " """

def quote_two() -> str:
    """Return "" """

def path_hint() -> str:
    r"""Return C:\temp\ """

[output]
def quote_one() -> str:
    """Return \""""

def quote_two() -> str:
    """Return \"\""""

def path_hint() -> str:
    r"""Return C:\temp\ """
```

Trailing whitespace before an evaluated newline is left for PDF003:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.  
    """

[output=unchanged]
```

Whitespace-only closing quote lines are left for PDF004:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.
      """

[output=unchanged]
```

Spaces and tabs are the only characters PDF006 removes. Other evaluated whitespace before the closing quotes is preserved as content:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.\u00a0	 """

[output]
def area(radius: float) -> float:
    """Return the area.\u00a0"""
```

Module, class, parenthesized, and simple-suite docstrings are all handled when they are simple safely mapped literals:

```pydocfmt-example
[input]
"""Module summary.  """

class Widget:
    ("""Class summary.  """)

def area(radius: float) -> float: """Return the area.  """; return 0.0

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
    r'''Return C:\temp.	 '''

[output]
def path_hint() -> str:
    r'''Return C:\temp.'''
```

Triple-single-quoted docstrings use the same escaping behavior when content ends in single delimiter quote characters:

```pydocfmt-example
[input]
def quote_one() -> str:
    '''Return '  '''

def quote_two() -> str:
    '''Return ''  '''

[output]
def quote_one() -> str:
    '''Return \''''

def quote_two() -> str:
    '''Return \'\''''
```

Concatenated docstrings and docstrings with escaped newlines are skipped because the exact source line ownership is ambiguous for this rule:

```pydocfmt-example
[input]
def concatenated() -> None:
    ("Summary.\n"
     "Body.  ")

def escaped_newline() -> None:
    """Summary.\nBody.  """

[output=unchanged]
```

Empty docstrings and non-docstring string expressions are also unchanged:

```pydocfmt-example
[input]
def empty() -> None:
    """"""

def not_docstring() -> None:
    value = 1
    """Summary.  """

[output=unchanged]
```

## Options
None.
