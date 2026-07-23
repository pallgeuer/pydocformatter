# docstring-reflow (PDF101)

Fix is usually available.

## What it does
Checks for docstring text regions whose normalized wrapping does not match the configured line length and indentation settings.

This rule rewrites safely mapped simple string docstrings by replacing the complete string literal with an equivalent literal that preserves the original string prefix, quote delimiter, and reusable source spellings for moved text. It can reflow summaries, paragraphs, convention section descriptions, reST field descriptions, list items, and block quotes.

PDF101 treats each reflowable semantic region independently. It joins consecutive physical lines in the same region before wrapping, so a finding can be emitted even when no individual input line is over the configured line length. Blank lines, standalone colon-ended lines, and protected structures remain region boundaries.

Within each logical line, PDF101 preserves a conservative set of recognized inline markup as indivisible source-aware tokens: non-empty same-line backtick spans whose opening and closing delimiter runs have equal length; inline and full or collapsed reference-style Markdown links and images; CommonMark-style URI and email autolinks; and boundary-valid reStructuredText interpreted text, prefix and suffix roles, phrase and anonymous references, embedded targets, inline literals, and substitution references. Escaped and nested Markdown labels, empty inline labels or destinations, link titles delimited by `"..."`, `'...'`, or `(...)`, and destination parentheses nested up to three levels are supported. reStructuredText role names use alphanumeric components separated by isolated `-`, `_`, `+`, `:`, or `.` characters. The complete whitespace-delimited punctuation envelope around a recognized construct stays together, and exact source spelling inside the token is retained.

Emphasis, raw HTML or XML, Markdown shortcut references and definitions, and multiline inline constructs are not parsed as safe inline constructs. Generic unmatched brackets, pipes, and angle brackets remain ordinary prose unless stronger syntax identifies an attempted supported construct. A line-leading run of at least three backticks or tildes is treated as ordinary fence-like text rather than ambiguous inline markup, including when an info string follows the opener; whether a complete fenced block is protected is controlled separately by docstring parsing. For a bare single-backtick dialect collision, an escaped inner backtick remains content when a later valid closer exists; otherwise, strong evidence such as a missing closer, incomplete recognized prefix, or excessive destination nesting makes the region ambiguous. PDF101 reports an ambiguous region only when its canonical layout would differ and does not attach an unsafe fix. Safe non-ambiguous regions in the same docstring can still be combined into a separate whole-literal fix.

An evaluated nonblank line ending in at least two ASCII spaces before an evaluated newline is a space hard break. An odd-length terminal evaluated backslash run is a backslash hard break; only its final unescaped backslash establishes the boundary, but the complete run is retained. PDF101 never joins across either boundary, reserves the exact source suffix width while wrapping, and reattaches its original source spelling, including three or more spaces and Python escape spellings such as `\x20\x20`. If tabs occur immediately before a space-break suffix, PDF101 removes only those tabs and preserves any spaces before them. Whitespace-only lines, final lines without an evaluated newline, and even backslash runs are not hard breaks.

PDF101 uses a lossless evaluated-value-to-source map for simple string docstrings. Source continuations outside a changed reflow region remain byte-for-byte unchanged; continuations inside a changed region are canonicalized with the rest of that region. Concatenated docstrings, unsupported escapes, and regions containing value-producing newline escapes such as `\n` cannot be rewritten safely. If any such region needs reflow, PDF101 emits one diagnostic-only finding covering the complete physical docstring while still allowing independent safe regions in the same docstring to be fixed.

PDF101 accounts for the docstring opening and closing delimiters when wrapping generated docstring lines. It does not account for unchanged Python source that follows the closing delimiter on the same physical line, such as `; return None` in a single-line suite.

Recognized markup is always indivisible. When `url-aware-wrapping` is enabled, destination-bearing tokens—bare URLs, autolinks, inline Markdown links or images, and reStructuredText embedded targets—activate balanced line selection around the token. Disabling the setting restores greedy line selection without allowing recognized markup to split.

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

Recognized same-line inline markup remains indivisible even when it is wider than the configured line length:

```pydocfmt-example
[settings]
line-length = 42
url-aware-wrapping = false

[input]
def reference():
    """Read [the complete reference label](https://example.com/target) before continuing with the remaining prose."""

[output]
def reference():
    """Read
    [the complete reference label](https://example.com/target)
    before continuing with the remaining
    prose."""
```

Enabling URL-aware wrapping changes only line selection around a destination-bearing construct; the complete Markdown link remains the same atomic token in either mode:

```pydocfmt-example
[settings]
line-length = 42
url-aware-wrapping = true

[input]
def reference():
    """alpha beta [label](https://example.com/path) alpha after"""

[output]
def reference():
    """alpha
    beta [label](https://example.com/path)
    alpha after"""
```

An escaped two-space hard break retains its exact Python source spelling and reserves room on the boundary line while preceding words reflow:

```pydocfmt-example
[settings]
line-length = 36

[input]
def space_break():
    """Alpha beta gamma delta epsilon\x20\x20
    zeta eta theta iota.
    """

[output]
def space_break():
    """Alpha beta gamma delta
    epsilon\x20\x20
    zeta eta theta iota.
    """
```

A backslash hard break remains a semantic boundary while the text on either side wraps independently:

```pydocfmt-example
[settings]
line-length = 38

[input]
def hard_break():
    r"""Alpha beta gamma delta epsilon\
    Zeta eta theta iota kappa."""

[output]
def hard_break():
    r"""Alpha beta gamma delta
    epsilon\
    Zeta eta theta iota kappa."""
```

Ambiguous markup is reported without an unsafe fix:

```pydocfmt-example
[settings]
line-length = 38

[input]
def ambiguous():
    """Read [the label](missing destination words that would otherwise wrap."""

[output=unchanged]

[findings]
PDF101: Line 2: Docstring chunk needs reflow
```

Standalone colon-ended lines also stop adjacent prose from being joined across the line:

```pydocfmt-example
[settings]
line-length = 64

[input]
def choices():
    """Introductory prose before the values list that is long enough to require wrapping.

    The accepted values are:
    pending, active, and disabled.

    Trailing prose after the values list that is long enough to require wrapping.
    """

[output]
def choices():
    """Introductory prose before the values list that is long
    enough to require wrapping.

    The accepted values are:
    pending, active, and disabled.

    Trailing prose after the values list that is long enough to
    require wrapping.
    """
```

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
- `url-aware-wrapping`: Uses balanced rather than greedy line selection around destination-bearing tokens; recognized markup remains indivisible either way.
- `indent-style`: Indentation style used for generated continuation indentation.
- `indent-width`: Tab display width used for wrapping calculations and generated indentation width.
