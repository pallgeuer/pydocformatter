# missing-blank-line (PDF101)

Fix is always available.

## What it does
Checks for safely provable missing blank logical lines inside docstrings.

PDF101 inserts exactly one blank line when a blank separator is required and the surrounding structure is unambiguous. It inserts a separator between a one-line summary and a following recognized structure, including convention sections, headings, lists, doctests, code fences, block quotes, tables, directives, literal blocks, Sphinx fields, and verbatim blocks.

With `docstring-convention = "google"` or `docstring-convention = "numpy"`, PDF101 also inserts missing blank lines before recognized top-level sections. This covers a section that follows a paragraph and adjacent recognized sections. It does not insert blank lines between a section header and its content, and it does not insert blank lines between consecutive convention entries inside a section.

The `docstring-blank-line-after-last-section` setting controls whether a blank line is required after the final recognized Google or NumPy section. It defaults to `false`. When enabled, PDF101 inserts one trailing blank after the final recognized section when that section has body content, and uses a canonical closing-quote prefix line when the closing quotes were originally on the same line as section content. The setting has no effect when the active convention does not parse the final block as a Google or NumPy section.

Generated blank-line text follows `docstring-blank-line-style`: `blank` inserts an empty line, while `aligned` inserts the canonical docstring margin. Generated line endings follow the resolved file line ending.

PDF101 deliberately avoids guesses. It does not split ambiguous prose, does not split a multi-line summary, does not insert separators before unrecognized text, and does not rewrite concatenated docstrings or simple literals whose evaluated lines cannot be safely mapped back to source lines.

## Why is this useful?
Blank lines make boundaries between summaries, descriptions, structures, and sections explicit. This rule covers the cases where the parser has already identified the boundary, while leaving ambiguous prose for a human or a warning rule such as PDF107.

## Ruff compatibility
This rule covers fixable missing-blank-line cases from Ruff's `D205`, `D410`, `D411`, and optionally `D413` when pydocformatter can prove that a blank line is required. `D413`-style final-section spacing is controlled by `docstring-blank-line-after-last-section`.

## Examples
Missing blank line between a one-line summary and a Google section:

```pydocfmt-example
[settings]
docstring-convention = "google"

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

Missing blank lines before a section after a paragraph and before an adjacent section are inserted in one pass:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert(value: int) -> str:
    """Convert a value.

    More details about conversion.
    Args:
        value: Value to convert.
    Returns:
        str: Converted value.
    """

[output]
def convert(value: int) -> str:
    """Convert a value.

    More details about conversion.

    Args:
        value: Value to convert.

    Returns:
        str: Converted value.
    """
```

NumPy sections are recognized only when the NumPy convention is active:

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

Generic recognized structures after a summary are also separated:

````pydocfmt-example
[input]
def example() -> None:
    """Run the example.
    ```text
    first
    second
    ```
    """

def choices() -> None:
    """Choose a value.
    - alpha
      first choice
    """

[output]
def example() -> None:
    """Run the example.

    ```text
    first
    second
    ```
    """

def choices() -> None:
    """Choose a value.

    - alpha
      first choice
    """
````

The final-section setting optionally requires one blank line after the last recognized section:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-blank-line-after-last-section = true

[input]
def parse(value: str) -> int:
    """Parse a value.

    Args:
        value: Value to parse."""

[output]
def parse(value: str) -> int:
    """Parse a value.

    Args:
        value: Value to parse.

    """
```

Aligned blank-line style inserts the canonical docstring margin on generated blank lines:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-blank-line-style = "aligned"

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

Existing whitespace-only separators are not duplicated; PDF004 can normalize their exact whitespace spelling separately:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def area(radius: float) -> float:
    """Return the area.
      
    Args:
        radius: Circle radius.
    """

[output=unchanged]
```

Ambiguous prose and multi-line summaries are unchanged:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area
    after validating the radius.
    """

def other() -> None:
    """Summary.
    Body text that could be prose.
    """

[output=unchanged]
```

Unsafe source mappings are skipped:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def escaped() -> None:
    """Summary.\nArgs:\n    value: Description."""

def concatenated() -> None:
    ("Summary.\n"
     "Args:\n"
     "    value: Description.")

[output=unchanged]
```

## Options
- `docstring-convention`: Enables Google and NumPy section recognition. `none` and `pep257` leave convention section syntax as generic docstring content, though other enabled generic structure parsers can still recognize headings, lists, and other structures.
- `docstring-blank-line-style`: Controls the source whitespace used on inserted blank lines.
- `docstring-blank-line-after-last-section`: Requires one trailing blank line after the final recognized Google or NumPy section when enabled.
- `docstring-parse-list-items`: Controls whether list items are recognized as structures after a summary.
- `docstring-parse-headings`: Controls whether Markdown and reStructuredText headings are recognized as structures after a summary.
- `docstring-parse-doctests`: Controls whether doctest transcripts are recognized as structures after a summary.
- `docstring-parse-code-fences`: Controls whether Markdown fenced code blocks are recognized as structures after a summary.
- `docstring-parse-block-quotes`: Controls whether Markdown block quotes are recognized as structures after a summary.
- `docstring-parse-tables`: Controls whether Markdown and reStructuredText tables are recognized as structures after a summary.
- `docstring-parse-directives`: Controls whether reStructuredText directives are recognized as structures after a summary.
- `docstring-parse-literal-blocks`: Controls whether reStructuredText literal blocks are recognized as structures after a summary.
- `docstring-parse-sphinx-fields`: Controls whether Sphinx fields are recognized as structures after a summary.
