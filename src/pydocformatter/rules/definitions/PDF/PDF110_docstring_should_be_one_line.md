# docstring-should-be-one-line (PDF110)

Fix is always available.

## What it does
Checks safely mapped simple multiline docstrings whose complete non-blank content is exactly one parsed summary line. If the whole docstring literal can be rendered on one physical source line without exceeding `line-length`, PDF110 collapses the opening quotes, summary, and closing quotes onto that line.

The line-length check uses the complete resulting physical source line, including indentation, any source before the literal, the full rendered string literal, and any same-line source after the literal. Tabs are measured using `indent-width`.

PDF110 only rewrites summary-only docstrings. It does not collapse docstrings with a body, paragraph, section, recognized structure, blank-only content, or a summary that spans multiple logical lines. It also skips true one-line docstrings, concatenated docstrings, and simple literals whose evaluated lines cannot be mapped safely back to physical source lines.

When a summary starts or ends with the quote delimiter character, PDF110 keeps valid Python source by using a value-preserving escape where possible, or a minimal separator space when escaping is not possible. That separator fallback can add a leading or trailing space to the evaluated `__doc__` value.

Parsing settings affect what counts as a recognized structure. For example, a single list item, heading, doctest, directive, Sphinx field, or block quote is protected by default and is not treated as a plain summary. Disabling the matching `docstring-parse-*` setting can make that text eligible for collapse if it is then parsed as a single summary line.

## Why is this useful?
Single-line docstrings are easier to scan when their complete content fits comfortably on one source line.

## Ruff compatibility
This rule is intended to replace Ruff's `D200` while respecting the configured line length before collapsing a docstring. Ruff's `D200` fix is unsafe because it can create overlong source lines; PDF110 checks the final physical source line first.

## Example
The canonical PDF110 fix collapses a multiline docstring that contains only one summary line:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """
    Return the area.
    """

[output]
def area(radius: float) -> float:
    """Return the area."""
```

Module, class, function, and method docstrings are all considered. Same-line source after the closing quotes is preserved:

```pydocfmt-example
[input]
"""
Module summary.
"""

class Circle:
    """
    Circle model.
    """

    def area(self) -> float:
        """
        Return the area.
        """  # public API

[output]
"""Module summary."""

class Circle:
    """Circle model."""

    def area(self) -> float:
        """Return the area."""  # public API
```

Space/tab-only logical lines around the summary are removed as part of the collapse, but content whitespace on the summary line itself is preserved:

```pydocfmt-example
[input]
def stripped() -> None:
    """  
	
    Return the area.
      
    """

def leading_space() -> None:
    """  Summary with leading spaces.
    """

[output]
def stripped() -> None:
    """Return the area."""

def leading_space() -> None:
    """  Summary with leading spaces."""
```

PDF110 only collapses when the complete resulting source line fits within `line-length`:

```pydocfmt-example
[settings]
line-length = 19

[input]
def area(radius: float) -> float:
    """
    Return the area.
    """

[output=unchanged]
```

Same-line prefix and suffix source are included in the line-length check:

```pydocfmt-example
[settings]
line-length = 39

[input]
def area(radius: float) -> float: """
    Return the area.
    """; return 0.0

[output=unchanged]
```

Tabs are measured using the configured `indent-width`:

```pydocfmt-example
[settings]
line-length = 22
indent-width = 4

[input]
def area() -> float:
	"""
	Return area.
	"""

[output]
def area() -> float:
	"""Return area."""
```

Docstrings with a body, a paragraph, or a multi-line summary are unchanged:

```pydocfmt-example
[input]
def body() -> None:
    """Summary.

    Body.
    """

def wrapped() -> None:
    """Summary line
    continuation line.
    """

[output=unchanged]
```

Recognized structures are not treated as summary-only docstrings:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def section(value: int) -> None:
    """
    Args:
        value: Input value.
    """

def list_item() -> None:
    """
    - item
    """

[output=unchanged]
```

If the relevant structure parser is disabled, the same text can become a plain one-line summary and be collapsed:

```pydocfmt-example
[settings]
docstring-parse-list-items = false

[input]
def list_item() -> None:
    """
    - item
    """

[output]
def list_item() -> None:
    """- item"""
```

PDF110 preserves the original string prefix and quote delimiter when possible, and escapes quote collisions when needed:

```pydocfmt-example
[input]
def raw_path() -> None:
    r'''
    Path C:\\temp.
    '''

def quoted() -> None:
    """
    "quoted"
    """

[output]
def raw_path() -> None:
    r'''Path C:\\temp.'''

def quoted() -> None:
    """\"quoted\""""
```

Concatenated docstrings and ambiguous escaped multiline simple strings are skipped because their evaluated lines cannot be rewritten safely:

```pydocfmt-example
[input]
def concatenated() -> None:
    ("Summary "
     "text.")

def escaped() -> None:
    """
    Summary with tab\t escape.
    """

[output=unchanged]
```

## Options
- `line-length`: Maximum display width allowed for the complete collapsed source line.
- `indent-width`: Display width used when measuring tabs.
- `docstring-convention`: Controls whether Google and NumPy sections are recognized instead of treated as summary text.
- `docstring-parse-*`: Controls whether generic structures such as lists, headings, doctests, directives, Sphinx fields, and block quotes are protected from one-line summary collapse.
