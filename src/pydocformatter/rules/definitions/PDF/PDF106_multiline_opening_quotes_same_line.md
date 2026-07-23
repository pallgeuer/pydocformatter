# multiline-opening-quotes-same-line (PDF106)

Fix is always available.

Rule is ignored if `docstring-convention` is `pep257` or `numpy`.

Rule is incompatible with `PDF107`.

## What it does
Checks safely mapped simple multiline docstrings with content and moves the first content line onto the opening triple-quote line.

PDF106 treats spaces and tabs as removable blank-line whitespace while looking for the first content line. If the opening quotes are followed by one or more logical lines containing only spaces and tabs, those logical lines are removed and the first real content line is rendered immediately after the opening quotes.

If moving the first content line directly after the opening quotes would produce invalid Python, PDF106 keeps one ASCII space after the opening quotes instead.

The rule changes docstrings that have at least one content line and span multiple evaluated lines. A true one-line docstring such as `"""Summary."""` is unchanged because the opening quotes, content, and closing quotes are already on one physical line.

PDF106 only rewrites safely mapped simple docstring literals. It preserves the original quote delimiter, string prefix, remaining source spelling, and line endings when a rewrite is safe. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escape sequences in a multiline non-raw literal.

## Why is this useful?
Projects that prefer compact docstrings can keep the opening delimiter and summary together while still allowing multi-line bodies.

## Ruff compatibility
This rule is intended to replace Ruff's `D212` or `D213` when the configured pydocformatter style keeps opening quotes on the summary line.

## Examples
The canonical PDF106 fix moves the first content line onto the opening quote line:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """
    Return the area.

    The radius must be non-negative.
    """

[output]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """
```

Space/tab-only logical lines before the first content line are removed as part of the same move:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """  
	
    Return the area.

    The radius must be non-negative.
    """

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
    Return the area.
    """

[output]
def area(radius: float) -> float:
    """Return the area.
    """
```

Module, class, parenthesized, nested, decorated, async, and simple-suite docstrings are handled when they are simple safely mapped literals:

```pydocfmt-example
[input]
"""
Module summary.

Module body.
"""

class Widget:
    ("""
    Class summary.

    Class body.
    """)

    @decorator
    async def render(self) -> None:
        """
        Method summary.

        Method body.
        """

def area(radius: float) -> float: """
    Return the area.

    The radius must be non-negative.
    """; return 0.0

[output]
"""Module summary.

Module body.
"""

class Widget:
    ("""Class summary.

    Class body.
    """)

    @decorator
    async def render(self) -> None:
        """Method summary.

        Method body.
        """

def area(radius: float) -> float: """Return the area.

    The radius must be non-negative.
    """; return 0.0
```

Quote delimiters, raw prefixes, and literal backslashes are preserved:

```pydocfmt-example
[input]
def path_hint() -> str:
    r'''
    Return C:\temp.

    Keep the path literal.
    '''

[output]
def path_hint() -> str:
    r'''Return C:\temp.

    Keep the path literal.
    '''
```

Already compact docstrings, true one-line docstrings, concatenated docstrings, and non-docstring strings are unchanged. Safely mapped escapes do not prevent moving the opening quotes:

```pydocfmt-example
[input]
def already_compact() -> None:
    """Summary.

    Body.
    """

def true_one_line() -> None:
    """Summary only."""

def concatenated() -> None:
    ("\n"
     "Summary.\n"
     "Body.")

def escaped_multiline() -> None:
    """
    Summary\t.

    Body.
    """

def not_docstring() -> None:
    value = 1
    """
    Summary.

    Body.
    """

[output]
def already_compact() -> None:
    """Summary.

    Body.
    """

def true_one_line() -> None:
    """Summary only."""

def concatenated() -> None:
    ("\n"
     "Summary.\n"
     "Body.")

def escaped_multiline() -> None:
    """Summary\t.

    Body.
    """

def not_docstring() -> None:
    value = 1
    """
    Summary.

    Body.
    """
```

## Options
None.
