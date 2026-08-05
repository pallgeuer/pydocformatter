# summary-terminal-punctuation (PDF301)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `none`, `pep257`, `numpy`, or `rest`.

Rule is incompatible with `PDF300`.

## What it does
Checks that the docstring summary punctuation target ends with terminal punctuation: a period, question mark, exclamation point, or Unicode ellipsis (`\u2026`).

The target is the final non-adornment line of the first logical summary paragraph. Empty docstrings, parser-recognized section-only docstrings, reST field-only docstrings under the reST convention, and targets ending with a backslash are skipped. Underlined title-style summaries are skipped when `docstring-parse-headings` is enabled. The automatic fix inserts a period when punctuation is absent, replaces a safely mapped final semicolon, and replaces a safely mapped final comma when the next nonblank block is not recognized structured content. A final colon or a comma that may introduce structured content is reported but not changed.

Replacement requires the final evaluated punctuation character to correspond exactly to the same source character. A comma or semicolon produced by an escape sequence is reported but not changed. Automatic fixes edit only the mapped punctuation source slice and preserve all other literal spelling, including prefix case.

## Why is this useful?
Terminal punctuation keeps summary lines sentence-like without forcing every valid question or exclamation into a period.

## Ruff compatibility
This rule replaces Ruff's `D415`. Use `PDF300` for the stricter period-only form. Unlike Ruff's unsafe fix, this rule does not report or fix underlined title-style summaries when heading parsing is enabled.

## Examples
Missing terminal punctuation is fixed by inserting a period:

```pydocfmt-example
[input]
def value():
    """Return the value"""

[output]
def value():
    """Return the value."""
```

Periods, question marks, exclamation points, and Unicode ellipses are all valid terminal punctuation:

```pydocfmt-example
[input]
def statement():
    """Return the value."""


def question():
    """Return the value?"""


def exclamation():
    """Return the value!"""


def ellipsis():
    """Return the value\u2026"""

[output=unchanged]
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

Standalone safely mapped commas and semicolons are replaced with periods, while a final colon is reported but not changed:

```pydocfmt-example
[input]
def comma():
    """Return the value,"""


def colon():
    """Return the value:"""


def semicolon():
    """Return the value;"""

[output]
def comma():
    """Return the value."""


def colon():
    """Return the value:"""


def semicolon():
    """Return the value."""

[findings]
PDF301: Line 6: Docstring summary should end with terminal punctuation
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
PDF301: Line 2: Docstring summary should end with terminal punctuation
```

An escaped terminal semicolon has no exact one-character source mapping, so the finding remains non-fixable:

```pydocfmt-example
[input]
def value():
    """Return the value\x3b"""

[output=unchanged]
[findings]
PDF301: Line 2: Docstring summary should end with terminal punctuation
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
