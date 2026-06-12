# too-many-blank-lines (PDF100)

Fix is always available.

## What it does
Checks for excess blank logical lines inside safely rewritable docstrings.

A blank logical line is an evaluated docstring line with no non-whitespace content after docstring indentation has been mapped by pydocformatter's parser. Lines that contain only spaces, tabs, or other Unicode whitespace are blank for PDF100. PDF004 is responsible for normalizing the exact whitespace spelling of a retained blank line.

PDF100 keeps at most one blank line between adjacent semantic chunks. It removes blank lines before the first chunk, removes blank lines after the last chunk, and collapses runs of multiple blank lines between chunks to one blank line. It only removes excess blank lines; it does not insert missing blank lines between chunks that are already adjacent.

A chunk is any non-blank semantic block recognized by the docstring parser, including summaries, paragraphs, sections, section entries, lists, headings, doctests, code fences, literal blocks, directives, tables, block quotes, Sphinx fields, and verbatim blocks. Blank lines inside opaque protected blocks are preserved, while blank-line runs around those protected blocks are still collapsed. Directive and literal-block bodies keep their internal blank lines, but trailing blank runs after their indented bodies are treated as exterior spacing between chunks.

With Google or NumPy conventions enabled, the same spacing policy is applied recursively inside recognized sections. This means extra blank lines between a section header and its first entry are collapsed to one blank line, and extra blank lines between entries and following section content are removed when the parser treats them as excess spacing inside the section.

When the closing quotes are already on their own canonical indentation line, PDF100 preserves that final quote-prefix line while removing extra blank lines before it. If the final whitespace-only line before the closing quotes is not at the canonical docstring margin, PDF100 treats it as excess blank content and removes it, which can move same-line closing quotes onto the preceding content line.

Docstrings with no chunks are collapsed to an empty docstring when they can be safely rewritten. This includes multi-line blank-only docstrings and one-line whitespace-only docstrings.

PDF100 only rewrites safely mapped simple docstring literals. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escaped newline sequences. `PDF000` can rewrite some of those skipped literals first, allowing PDF100 to run in a later rule pass when both rules are selected.

## Why is this useful?
Predictable blank-line spacing keeps summaries, descriptions, sections, and protected examples visually distinct without adding vertical noise.

## Ruff compatibility
This rule is intended to replace the fixable extra-blank-line cases covered by Ruff's `D205`; `PDF105` handles summaries that still span multiple lines.

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

PDF100 does not insert missing blank lines where none already exist:

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

With Google-style section parsing enabled, extra blank lines inside sections are collapsed recursively:

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

NumPy-style sections are handled the same way when NumPy convention parsing is enabled:

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

Generic structure settings control whether special-looking blocks are protected. With code fence parsing disabled, PDF100 can collapse blank lines inside fenced-looking text:

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

When `PDF000` is also selected outside this rule-specific example context, it can literalize escaped blank lines before PDF100 collapses them in a later rule pass.

## Options
- `docstring-convention`: Enables recursive spacing inside recognized Google or NumPy sections. `none` and `pep257` leave convention-specific section headers as ordinary generic chunks.
- `docstring-parse-list-items`: Controls whether list items are distinct chunks.
- `docstring-parse-headings`: Controls whether Markdown and reStructuredText headings are distinct chunks.
- `docstring-parse-doctests`: Controls whether doctest transcripts are protected chunks.
- `docstring-parse-code-fences`: Controls whether Markdown fenced code blocks are protected chunks.
- `docstring-parse-block-quotes`: Controls whether Markdown block quotes are distinct chunks.
- `docstring-parse-tables`: Controls whether Markdown and reStructuredText tables are protected chunks.
- `docstring-parse-directives`: Controls whether reStructuredText directives and their indented bodies are protected chunks.
- `docstring-parse-literal-blocks`: Controls whether reStructuredText literal blocks and their indented bodies are protected chunks.
- `docstring-parse-sphinx-fields`: Controls whether Sphinx fields are distinct chunks.
