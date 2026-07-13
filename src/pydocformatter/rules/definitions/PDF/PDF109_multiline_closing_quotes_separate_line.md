# multiline-closing-quotes-separate-line (PDF109)

Fix is always available.

Rule is incompatible with `PDF108`.

## What it does
Checks safely mapped simple multiline docstrings with content and moves same-line closing triple quotes onto their own line.

The generated closing-quote prefix line uses the docstring's canonical continuation margin. For ordinary indented suites this is the existing docstring margin. For simple suites, such as `def f(): """Summary."""; return None`, it is one configured indentation unit deeper than the containing line.

PDF109 moves the closing quotes without trimming spaces or tabs from the final content line. That whitespace belongs to whitespace-specific rules such as `PDF105`.

The rule changes docstrings that have at least one content line and span multiple evaluated lines. It does not rewrite blank-only docstrings, docstrings whose closing quotes are already on a separate line, or true one-line docstrings such as `"""Summary."""`.

PDF109 only rewrites safely mapped simple docstring literals. It preserves the original quote delimiter, string prefix, remaining source spelling, and line endings when a rewrite is safe. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escape sequences in a multiline non-raw literal.

## Why is this useful?
Projects that prefer expanded docstrings can keep the closing delimiter visually separate from the content.

## Ruff compatibility
This rule is intended to replace Ruff's `D209` when pydocformatter is responsible for closing-quote placement.

## Examples
The canonical PDF109 fix moves same-line closing quotes onto their own line:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative."""

[output]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """
```

PDF109 preserves final content trailing whitespace so whitespace-specific rules can handle it:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.  """

[output]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.  
    """
```

Single-content-line docstrings are included when the literal itself spans multiple lines:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """
    Return the area."""

[output]
def area(radius: float) -> float:
    """
    Return the area.
    """
```

Parenthesized docstrings keep their aligned margin, and simple-suite docstrings use the configured generated indentation unit:

```pydocfmt-example
[settings]
indent-width = 2

[input]
class Widget:
    (
        """Class summary.

        Class body."""
    )

def area(radius: float) -> float: """Return the area.
The radius must be non-negative."""; return 0.0

[output]
class Widget:
    (
        """Class summary.

        Class body.
        """
    )

def area(radius: float) -> float: """Return the area.
The radius must be non-negative.
  """; return 0.0
```

Tab indentation is used for generated simple-suite closing lines when configured:

```pydocfmt-example
[settings]
indent-style = "tab"

[input]
def area(radius: float) -> float: """Return the area.
The radius must be non-negative."""; return 0.0

[output]
def area(radius: float) -> float: """Return the area.
The radius must be non-negative.
	"""; return 0.0
```

Module, nested, decorated, async, and class docstrings each use the canonical margin for their own owner:

```pydocfmt-example
[input]
"""Module summary.

Module body."""

class Widget:
    @decorator
    async def render(self) -> None: """Method summary.
Method body."""; return None

    class Inner:
        """Class summary.

        Class body."""

[output]
"""Module summary.

Module body.
"""

class Widget:
    @decorator
    async def render(self) -> None: """Method summary.
Method body.
        """; return None

    class Inner:
        """Class summary.

        Class body.
        """
```

Quote delimiters, raw prefixes, and literal backslashes are preserved:

```pydocfmt-example
[input]
def path_hint() -> str:
    r'''Return C:\temp.
    Keep the path literal.'''

[output]
def path_hint() -> str:
    r'''Return C:\temp.
    Keep the path literal.
    '''
```

Already expanded docstrings, true one-line docstrings, blank-only docstrings, concatenated docstrings, multiline non-raw literals with escapes, and non-docstring strings are unchanged:

```pydocfmt-example
[input]
def already_expanded() -> None:
    """Summary.

    Body.
    """

def true_one_line() -> None:
    """Summary only."""

def blank_only() -> None:
    """  
    """

def concatenated() -> None:
    ("Summary.\n"
     "Body.")

def escaped_multiline() -> None:
    """Summary.\nBody."""

def not_docstring() -> None:
    value = 1
    """Summary.

    Body."""

[output=unchanged]
```

## Options
- `indent-style`: Indentation style used when generating the separate closing-quote line.
- `indent-width`: Indentation width used when generating the separate closing-quote line and measuring indentation.
