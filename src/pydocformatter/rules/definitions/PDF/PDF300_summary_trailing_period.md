# summary-trailing-period (PDF300)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `google`.

## What it does
Checks that the docstring summary punctuation target ends with a period.

The target is the final non-adornment line of the first logical summary paragraph. Empty docstrings, parser-recognized section-only docstrings, reST field-only docstrings under the reST convention, and targets ending with a backslash are skipped. Underlined title-style summaries are skipped when `docstring-parse-headings` is enabled. The automatic fix inserts a period when punctuation is absent, replaces a safely mapped final semicolon, and replaces a safely mapped final comma when the next nonblank block is not recognized structured content. Question marks, exclamation points, colons, Unicode ellipses (`\u2026`), and commas that may introduce structured content are reported but not changed.

Replacement requires the final evaluated punctuation character to correspond exactly to the same source character. A comma or semicolon produced by an escape sequence is reported but not changed. Automatic fixes edit only the mapped punctuation source slice and preserve all other literal spelling, including prefix case.

## Why is this useful?
Some projects prefer a strict PEP 257 summary sentence style where summaries consistently end in periods.

## Ruff compatibility
This rule replaces Ruff's `D400`. Use `PDF301` for the broader terminal-punctuation form. Unlike Ruff's unsafe fix, this rule does not report or fix underlined title-style summaries when heading parsing is enabled.

## Examples
Missing periods are inserted at the end of the summary target:

```pydocfmt-example
[input]
def value():
    """Return the value"""

[output]
def value():
    """Return the value."""
```

For multi-line summaries, the target is the final non-adornment line of the first summary paragraph:

```pydocfmt-example
[input]
def multiline():
    """Return the value
    after processing
    """

[output]
def multiline():
    """Return the value
    after processing.
    """
```

Standalone safely mapped commas and semicolons are replaced with periods, while expressive or structural punctuation is reported but not changed:

```pydocfmt-example
[input]
def comma():
    """Return the value,"""


def semicolon():
    """Return the cached value;"""


def question():
    """Return the value?"""


def colon():
    """Return the value:"""

[output]
def comma():
    """Return the value."""


def semicolon():
    """Return the cached value."""


def question():
    """Return the value?"""


def colon():
    """Return the value:"""

[findings]
PDF300: Line 10: Docstring summary should end with a period
PDF300: Line 14: Docstring summary should end with a period
```

A comma before recognized structured content is reported but not changed because it may introduce that content:

```pydocfmt-example
[input]
def choose():
    """Choose one,

    - first
    - second
    """

[output=unchanged]
[findings]
PDF300: Line 2: Docstring summary should end with a period
```

An escaped terminal comma has no exact one-character source mapping, so the finding remains non-fixable:

```pydocfmt-example
[input]
def value():
    """Return the value\x2c"""

[output=unchanged]
[findings]
PDF300: Line 2: Docstring summary should end with a period
```

Empty docstrings, parser-recognized section-only docstrings, and summaries ending with a backslash are skipped. With heading parsing enabled, underlined title-style summaries are also skipped. Recognized NumPy section headings such as `Parameters` followed by an underline are section headers, not summaries:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def empty():
    """"""


def title():
    """Result summary
    ==============
    """


def numpy_section_only(value):
    """Parameters
    ----------
    value : int
    """


def backslash():
    """Path C:\\"""

[output=unchanged]
```

reST field-only docstrings are skipped under the reST convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def rest_field(value):
    """:param value: Description"""

[output=unchanged]
```

When heading parsing is disabled, an underlined title-style summary is treated as summary text, and the underline adornment is not the punctuation target:

```pydocfmt-example
[settings]
docstring-parse-headings = false

[input]
def title():
    """Result summary
    ==============
    """

[output]
def title():
    """Result summary.
    ==============
    """
```

## Options
None.
