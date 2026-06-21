# docstring-reflow (PDF101)

Fix is usually available.

## What it does
Checks for docstring text regions whose normalized wrapping does not match the configured line length and indentation settings.

This rule rewrites safely mapped simple string docstrings by replacing the complete string literal with an equivalent literal that preserves the original string prefix, quote delimiter, and reusable source spellings for moved text. It can reflow summaries, paragraphs, convention section descriptions, reST field descriptions, list items, and block quotes.

PDF101 treats each reflowable semantic region independently. It joins consecutive physical lines in the same region before wrapping, so a finding can be emitted even when no individual input line is over the configured line length. Blank lines and protected structures remain region boundaries.

The rule intentionally skips docstrings whose evaluated value cannot be mapped back to source text safely. This includes concatenated string docstrings and docstrings whose logical lines come from escape sequences such as `\n`. If a docstring needs reflow but cannot be rendered back with the existing prefix and delimiter without changing its evaluated value, the finding is reported without an automatic fix.

PDF101 accounts for the docstring opening and closing delimiters when wrapping generated docstring lines. It does not account for unchanged Python source that follows the closing delimiter on the same physical line, such as `; return None` in a single-line suite.

When `url-aware-wrapping` is enabled, URL tokens remain unbroken but surrounding prose may use less greedy line breaks.

## Why is this useful?
Consistent wrapping keeps docstrings readable in editors, terminals, review diffs, and generated documentation. Reflowing semantic chunks instead of raw line ranges keeps summaries, paragraphs, parameter descriptions, fields, lists, and quoted text readable without disturbing protected examples or code-like content.

## Ruff compatibility
This rule complements Ruff's docstring lint rules. Ruff reports many docstring style issues, while pydocformatter rewrites docstring content that can be formatted mechanically.

PDF101 is closest in spirit to a formatter pass rather than a pure linter rule. It can change line breaks inside docstrings, but it does not add missing documentation, validate parameter coverage, or enforce a docstring convention.

## Examples
Canonical summary wrapping:

```pydocfmt-example
[settings]
line-length = 72

[input]
def area(radius: float) -> float:
    """Return the area for a circle with the supplied radius after validating that the radius is finite and non-negative."""

[output]
def area(radius: float) -> float:
    """Return the area for a circle with the supplied radius after
    validating that the radius is finite and non-negative."""
```

Short physical lines in the same summary are joined before wrapping, while paragraphs stay separated by blank lines:

```pydocfmt-example
[settings]
line-length = 72

[input]
def normalize(text):
    """Normalize whitespace
    in short lines.

    The long paragraph after the summary is wrapped independently from the summary and does not cross the blank line.
    """

[output]
def normalize(text):
    """Normalize whitespace in short lines.

    The long paragraph after the summary is wrapped independently from
    the summary and does not cross the blank line.
    """
```

Google-style entries use fixed continuation indentation. If a long name or type prefix leaves too little first-line room, the description moves to the following line:

```pydocfmt-example
[settings]
line-length = 78
docstring-convention = "google"

[input]
def fetch(path, payload, timeout):
    """Fetch data.

    Args:
        path (str): A filesystem path with a description that should wrap using fixed continuation indentation.
        payload (Mapping[str, Sequence[tuple[str, object, bytes, float]]]): Data to send with enough explanation to require another generated line.
        timeout (float): Number of seconds to wait before failing.

    """

[output]
def fetch(path, payload, timeout):
    """Fetch data.

    Args:
        path (str): A filesystem path with a description that should wrap
            using fixed continuation indentation.
        payload (Mapping[str, Sequence[tuple[str, object, bytes, float]]]):
            Data to send with enough explanation to require another generated
            line.
        timeout (float): Number of seconds to wait before failing.

    """
```

reST fields keep field-prefix hanging indentation under the reST convention:

```pydocfmt-example
[settings]
line-length = 78
docstring-convention = "rest"

[input]
def fetch(path):
    """Fetch data.

    :returns: The loaded bytes with enough explanation to require another generated line.
    """

[output]
def fetch(path):
    """Fetch data.

    :returns: The loaded bytes with enough explanation to require another
              generated line.
    """
```

NumPy section descriptions reflow under their existing indentation. List items and block quotes keep their semantic prefixes:

```pydocfmt-example
[settings]
line-length = 66
docstring-convention = "numpy"

[input]
def summarize(values):
    """Summarize values.

    Parameters
    ----------
    values : list[int]
        Values to summarize with a description that should wrap under the existing indentation.

    - A list item with enough words to wrap onto a continuation line using hanging indentation.
    > A block quote with enough words to wrap onto a continuation line while preserving the quote prefix.
    """

[output]
def summarize(values):
    """Summarize values.

    Parameters
    ----------
    values : list[int]
        Values to summarize with a description that should wrap
        under the existing indentation.

    - A list item with enough words to wrap onto a continuation
      line using hanging indentation.
    > A block quote with enough words to wrap onto a continuation
    > line while preserving the quote prefix.
    """
```

Protected structures, such as code fences, are left unchanged while adjacent prose still reflows:

````pydocfmt-example
[settings]
line-length = 66

[input]
def example():
    """Introductory prose that should wrap before the protected example.

    ```python
    result = call_with_a_very_long_argument_name_that_is_left_unchanged()
    ```

    Trailing prose that should wrap after the protected example as its own paragraph.
    """

[output]
def example():
    """Introductory prose that should wrap before the protected
    example.

    ```python
    result = call_with_a_very_long_argument_name_that_is_left_unchanged()
    ```

    Trailing prose that should wrap after the protected example as
    its own paragraph.
    """
````

Disabling structural parsing makes matching lines fall back to ordinary paragraph reflow instead of list-item or block-quote reflow:

```pydocfmt-example
[settings]
line-length = 54
docstring-parse-list-items = false
docstring-parse-block-quotes = false

[input]
def example():
    """- A list item with enough words to wrap using normal paragraph rules.

    > A block quote with enough words to wrap using normal paragraph rules.
    """

[output]
def example():
    """- A list item with enough words to wrap using
    normal paragraph rules.

    > A block quote with enough words to wrap using
    normal paragraph rules.
    """
```

## Options
- `line-length`: Maximum display width used when wrapping generated docstring lines.
- `url-aware-wrapping`: Enables URL-aware line balancing without splitting URL tokens.
- `line-ending`: Line ending used inside rewritten docstring literals. Untouched source outside the replacement is preserved.
- `indent-width`: Tab display width used for wrapping calculations and generated continuation indentation.
- `docstring-convention`: Enables convention-aware parsing for Google sections, NumPy sections, or reST fields.
- `docstring-parse-list-items`: Controls whether list items are reflowed with list hanging indentation.
- `docstring-parse-headings`: Controls whether Markdown and reStructuredText headings are protected.
- `docstring-parse-doctests`: Controls whether doctest transcripts are protected.
- `docstring-parse-code-fences`: Controls whether fenced code blocks are protected.
- `docstring-parse-block-quotes`: Controls whether block quotes are reflowed with quote prefixes.
- `docstring-parse-tables`: Controls whether Markdown and reStructuredText tables are protected.
- `docstring-parse-directives`: Controls whether reStructuredText directives and their bodies are protected.
- `docstring-parse-literal-blocks`: Controls whether literal blocks are protected.
