# too-many-blank-lines (PDF200)

Fix is always available.

## What it does
Checks for excess blank logical lines inside safely rewritable docstrings.

A blank logical line is an evaluated docstring line with no non-whitespace content after docstring indentation has been mapped by pydocformatter's parser. Lines that contain only spaces, tabs, or other Unicode whitespace are blank for PDF200. PDF103 is responsible for normalizing the exact whitespace spelling of a retained blank line.

PDF200 keeps at most one blank line between adjacent semantic chunks. It removes blank lines before the first chunk, removes blank lines after the last chunk, and collapses runs of multiple blank lines between chunks to one blank line. It only removes excess blank lines; it does not insert missing blank lines between chunks that are already adjacent.

A chunk is any non-blank semantic block recognized by the docstring parser, including summaries, paragraphs, sections, section entries, reST fields under the reST convention, lists, headings, doctests, code fences, literal blocks, directives, tables, block quotes, and verbatim blocks. Blank lines inside opaque protected blocks are preserved, while blank-line runs around those protected blocks are still collapsed. Directive and literal-block bodies keep their internal blank lines, but trailing blank runs after their indented bodies are treated as exterior spacing between chunks.

With Google or NumPy conventions enabled, spacing is applied recursively inside recognized sections. Extra blank lines between a section header and its first body item are removed entirely, and extra blank lines between consecutive convention entries are removed entirely. Extra blank lines between adjacent whole sections collapse to one retained blank line. Other blank-line runs inside sections are still collapsed to one retained blank line unless they are inside opaque protected content.

The `docstring-blank-line-after-last-section` setting changes the trailing spacing rule for the final recognized Google or NumPy section. When enabled, PDF200 collapses trailing blank-line runs after the final recognized section to exactly one blank line. Otherwise, PDF200 removes blank lines after the final section. The setting has no effect unless the active `docstring-convention` parses the final block as a Google or NumPy section.

When the closing quotes are already on their own canonical indentation line, PDF200 preserves that final quote-prefix line while removing extra blank lines before it. If the final whitespace-only line before the closing quotes is not at the canonical docstring margin, PDF200 treats it as excess blank content and removes it, which can move same-line closing quotes onto the preceding content line.

Docstrings with no chunks are collapsed to an empty docstring when they can be safely rewritten. This includes multi-line blank-only docstrings and one-line whitespace-only docstrings.

PDF200 only rewrites safely mapped simple docstring literals. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escaped newline sequences. `PDF000` can rewrite some of those skipped literals first, allowing PDF200 to run in a later rule pass when both rules are selected.

## Why is this useful?
Predictable blank-line spacing keeps summaries, descriptions, sections, and protected examples visually distinct without adding vertical noise.

## Ruff compatibility
This rule is intended to replace the fixable extra-blank-line cases covered by Ruff's `D205`; `PDF203` handles summaries that still span multiple lines.

## Examples
Extra blank lines before the first chunk, between chunks, and after the last chunk are removed:

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

PDF200 does not insert missing blank lines where none already exist:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.
    The radius must be non-negative.
    """

[output=unchanged]
```

Closing quote prefix lines are preserved only when they are already at the canonical docstring margin:

```pydocfmt-example
[input]
def function():
    """Summary.


    """

def odd_prefix():
    """Summary.
      """

[output]
def function():
    """Summary.
    """

def odd_prefix():
    """Summary."""
```

Blank-only docstrings collapse to empty docstrings:

```pydocfmt-example
[input]
def placeholder() -> None:
    """

    """

def inline(): """   """

[output]
def placeholder() -> None:
    """"""

def inline(): """"""
```

Blank lines inside protected blocks are preserved, while extra blank lines around protected blocks are collapsed:

````pydocfmt-example
[input]
def example() -> None:
    """Run the example.


    ```text
    first

    second
    ```


    .. note:: Title

        directive first


        directive second


    Example::

        literal first


        literal second


    Done.
    """

[output]
def example() -> None:
    """Run the example.

    ```text
    first

    second
    ```

    .. note:: Title

        directive first


        directive second

    Example::

        literal first


        literal second

    Done.
    """
````

With Google-style section parsing enabled, section headers and consecutive convention entries use compact spacing, while adjacent whole sections keep one blank line between them:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def area(radius: float) -> float:
    """Return the area.

    Args:


        radius: Circle radius.


    Returns:
        float: Area.
    """

[output]
def area(radius: float) -> float:
    """Return the area.

    Args:
        radius: Circle radius.

    Returns:
        float: Area.
    """
```

The final-section setting controls whether one trailing blank after the last recognized section is retained:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-blank-line-after-last-section = true

[input]
def area(radius: float) -> float:
    """Return the area.

    Args:
        radius: Circle radius.


    """

[output]
def area(radius: float) -> float:
    """Return the area.

    Args:
        radius: Circle radius.

    """
```

NumPy-style section parsing applies the same compact spacing after section underlines and keeps one blank line between adjacent whole sections:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def area(radius: float) -> float:
    """Return the area.

    Parameters
    ----------


    radius : float
        Circle radius.


    Returns
    -------
    float
        Area.
    """

[output]
def area(radius: float) -> float:
    """Return the area.

    Parameters
    ----------
    radius : float
        Circle radius.

    Returns
    -------
    float
        Area.
    """
```

reST fields under the reST convention use compact spacing between adjacent fields:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(first: int, second: int) -> int:
    """Return a value.

    :param first: First value.


    :param second: Second value.
    """

[output]
def value(first: int, second: int) -> int:
    """Return a value.

    :param first: First value.
    :param second: Second value.
    """
```

Generic structure settings control whether special-looking blocks are protected. With code fence parsing disabled, PDF200 can collapse blank lines inside fenced-looking text:

````pydocfmt-example
[settings]
docstring-parse-code-fences = false

[input]
def example() -> None:
    """Summary.

    ```text
    first


    second
    ```
    """

[output]
def example() -> None:
    """Summary.

    ```text
    first

    second
    ```
    """
````

Concatenated docstrings and docstrings with escaped newlines are skipped because the exact source line ownership is ambiguous for this rule:

```pydocfmt-example
[input]
def escaped() -> None:
    """Summary.\n\n\nBody."""

def concatenated() -> None:
    ("Summary.\n\n\n"
     "Body.")

[output=unchanged]
```

When `PDF000` is also selected outside this rule-specific example context, it can literalize escaped blank lines before PDF200 collapses them in a later rule pass.

## Options
- `docstring-convention`: Enables recursive compact spacing inside recognized Google or NumPy sections, one retained blank line between adjacent Google or NumPy sections, and compact spacing between adjacent reST fields. `none` and `pep257` leave convention-specific syntax as ordinary generic chunks.
- `docstring-blank-line-after-last-section`: Keeps exactly one trailing blank line after the final recognized Google or NumPy section when enabled; removes final-section trailing blanks when disabled.
- `docstring-parse-*`: Controls whether generic structures such as lists, headings, doctests, code fences, block quotes, tables, directives, and literal blocks are distinct or protected chunks for blank-line collapsing.
