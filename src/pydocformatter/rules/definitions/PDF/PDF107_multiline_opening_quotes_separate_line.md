# multiline-opening-quotes-separate-line (PDF107)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values.

Rule is incompatible with `PDF106`.

## What it does
Checks safely mapped simple multiline docstrings with content and moves first-line content below the opening triple quotes.

The generated content line uses the docstring's canonical continuation margin. For ordinary indented suites this is the existing docstring margin. For simple suites, such as `def f(): """Summary."""; return None`, it is one configured indentation unit deeper than the containing line.

PDF107 removes spaces and tabs immediately after the opening quotes before moving the first content line. Other evaluated whitespace characters are preserved as content.

The rule changes docstrings that have at least one content line and span multiple evaluated lines. It does not rewrite blank-only docstrings, docstrings whose opening quotes are already on a separate line, or true one-line docstrings such as `"""Summary."""`.

PDF107 only rewrites safely mapped simple docstring literals. It preserves the original quote delimiter, string prefix, remaining source spelling, and line endings when a rewrite is safe. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escape sequences in a multiline non-raw literal.

## Why is this useful?
Projects that prefer expanded docstrings can keep delimiters visually separate from the content.

## Ruff compatibility
This rule is intended to replace Ruff's `D212` or `D213` when the configured pydocformatter style puts opening quotes on a separate line.

## Examples
The canonical PDF107 fix moves first-line content below the opening quotes:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """

[output]
def area(radius: float) -> float:
    """
    Return the area.

    The radius must be non-negative.
    """
```

Spaces and tabs immediately after the opening quotes are stripped from the moved content line:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """ 	 Return the area.

    The radius must be non-negative.
    """

[output]
def area(radius: float) -> float:
    """
    Return the area.

    The radius must be non-negative.
    """
```

Single-content-line docstrings are included when the literal itself spans multiple lines:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.
    """

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

        Class body.
        """
    )

def area(radius: float) -> float: """Return the area.
The radius must be non-negative.
"""; return 0.0

[output]
class Widget:
    (
        """
        Class summary.

        Class body.
        """
    )

def area(radius: float) -> float: """
  Return the area.
The radius must be non-negative.
"""; return 0.0
```

Tab indentation is used for generated simple-suite content lines when configured:

```pydocfmt-example
[settings]
indent-style = "tab"

[input]
def area(radius: float) -> float: """Return the area.
The radius must be non-negative.
"""; return 0.0

[output]
def area(radius: float) -> float: """
	Return the area.
The radius must be non-negative.
"""; return 0.0
```

Quote delimiters, raw prefixes, and literal backslashes are preserved:

```pydocfmt-example
[input]
def path_hint() -> str:
    r'''Return C:\temp.
    Keep the path literal.'''

[output]
def path_hint() -> str:
    r'''
    Return C:\temp.
    Keep the path literal.'''
```

Already expanded docstrings, true one-line docstrings, concatenated docstrings, and non-docstring strings are unchanged. Safely mapped escapes do not prevent moving the opening quotes:

```pydocfmt-example
[input]
def already_expanded() -> None:
    """
    Summary.

    Body.
    """

def true_one_line() -> None:
    """Summary only."""

def concatenated() -> None:
    ("Summary.\n"
     "Body.")

def escaped_multiline() -> None:
    """Summary\t.

    Body.
    """

def not_docstring() -> None:
    value = 1
    """Summary.

    Body.
    """

[output]
def already_expanded() -> None:
    """
    Summary.

    Body.
    """

def true_one_line() -> None:
    """Summary only."""

def concatenated() -> None:
    ("Summary.\n"
     "Body.")

def escaped_multiline() -> None:
    """
    Summary\t.

    Body.
    """

def not_docstring() -> None:
    value = 1
    """Summary.

    Body.
    """
```

## Options
- `indent-style`: Indentation style used when generating the moved first content line.
- `indent-width`: Indentation width used when generating the moved first content line and measuring indentation.
