# multiline-closing-quotes-same-line (PDF108)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values.

Rule is incompatible with `PDF109`.

## What it does
Checks safely mapped simple multiline docstrings with content and moves the closing triple quotes onto the final content line.

PDF108 treats spaces and tabs as removable blank-line whitespace while looking for the final content line. If the final content line is followed by one or more logical lines containing only spaces and tabs, those logical lines are removed and the closing quotes are rendered immediately after the final content.

When `docstring-blank-line-after-last-section` is enabled, a semantic trailing blank after the final recognized Google or NumPy section takes precedence over compact closing quotes. PDF108 leaves the closing delimiter separate when that required blank is present. If the blank is missing, PDF201 can insert it and PDF108 then preserves it on later formatting passes.

If moving the closing quotes directly after final content would collide with the closing delimiter, PDF108 first tries to escape delimiter quote characters while preserving the evaluated docstring value. If no value-preserving spelling is available while keeping the original prefix and delimiter, PDF108 keeps one ASCII space before the closing quotes instead, such as for raw strings ending in an odd run of backslashes.

The rule can also remove a trailing evaluated newline before the closing delimiter, as long as the docstring has content.

PDF108 only changes docstrings that have at least one content line after ignoring space/tab-only lines and span multiple evaluated lines. It does not rewrite blank-only docstrings, docstrings whose closing quotes already share the final content line, or true one-line docstrings such as `"""Summary."""`.

PDF108 only rewrites safely mapped simple docstring literals. It preserves the original quote delimiter, string prefix, remaining source spelling, and line endings when a rewrite is safe. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escape sequences in a multiline non-raw literal.

## Why is this useful?
Projects that prefer compact docstrings can avoid a delimiter-only closing line when the configured style allows it.

## Ruff compatibility
This rule is intended to provide the compact closing-quotes style not available from Ruff's `D209`.

## Examples
The canonical PDF108 fix moves the closing quotes onto the final content line:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """

[output]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative."""
```

The configured trailing blank after a final Google or NumPy section keeps the closing quotes separate:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-blank-line-after-last-section = true

[input]
def area(radius: float) -> float:
    """Args:
        radius: Circle radius.

    """

[output=unchanged]
```

Space/tab-only logical lines before the closing quotes are removed as part of the same move:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
      
	
    """

[output]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative."""
```

Single-content-line docstrings are included when the literal itself spans multiple lines:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.
    """

[output]
def area(radius: float) -> float:
    """Return the area."""
```

A trailing evaluated newline before the closing delimiter is removed when the docstring has content:

```pydocfmt-example
[input]
"""Module summary.
Module body.
"""

[output]
"""Module summary.
Module body."""
```

Simple-suite docstrings are rewritten without moving following statements:

```pydocfmt-example
[input]
def area(radius: float) -> float: """Return the area.
The radius must be non-negative.
"""; return 0.0

[output]
def area(radius: float) -> float: """Return the area.
The radius must be non-negative."""; return 0.0
```

Quote delimiters, raw prefixes, literal backslashes, internal blank lines, and configured line endings are preserved:

```pydocfmt-example
[input]
def path_hint() -> str:
    r'''Return C:\temp.

    Keep the path literal.
    '''

[output]
def path_hint() -> str:
    r'''Return C:\temp.

    Keep the path literal.'''
```

PDF108 escapes delimiter quote characters when same-line closing quotes would otherwise collide with content. Raw strings ending in an odd run of backslashes still keep one separator space:

```pydocfmt-example
[input]
def quote_one() -> None:
    """Summary.

    Body "
    """

def quote_two() -> None:
    """Summary.

    Body ""
    """

def raw_backslash() -> None:
    r"""Summary.

    Path \
    """

[output]
def quote_one() -> None:
    """Summary.

    Body \""""

def quote_two() -> None:
    """Summary.

    Body \"\""""

def raw_backslash() -> None:
    r"""Summary.

    Path \ """
```

Already compact docstrings, true one-line docstrings, concatenated docstrings, and non-docstring strings are unchanged. Safely mapped escapes do not prevent moving the closing quotes:

```pydocfmt-example
[input]
def already_compact() -> None:
    """Summary.

    Body."""

def true_one_line() -> None:
    """Summary only."""

def concatenated() -> None:
    ("Summary.\n"
     "Body.\n")

def escaped_multiline() -> None:
    """Summary.

    Body\t.
    """

def not_docstring() -> None:
    value = 1
    """Summary.

    Body.
    """

[output]
def already_compact() -> None:
    """Summary.

    Body."""

def true_one_line() -> None:
    """Summary only."""

def concatenated() -> None:
    ("Summary.\n"
     "Body.\n")

def escaped_multiline() -> None:
    """Summary.

    Body\t."""

def not_docstring() -> None:
    value = 1
    """Summary.

    Body.
    """
```

## Options
- `docstring-blank-line-after-last-section`: Preserves separate closing quotes when the final recognized Google or NumPy section already has its required trailing blank.
