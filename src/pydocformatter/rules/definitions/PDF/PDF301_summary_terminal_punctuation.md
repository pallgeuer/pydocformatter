# summary-terminal-punctuation (PDF301)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `numpy` or `pep257`.

## What it does
Checks that the docstring summary punctuation target ends with terminal punctuation: a period, question mark, exclamation point, or Unicode ellipsis (`\u2026`).

The target is the final non-empty line of the first logical summary paragraph. Empty docstrings, underlined title-style summaries, parser-recognized section-only docstrings, Sphinx field-only docstrings, and targets ending with a backslash are skipped. The automatic fix only inserts a period at the end of the trimmed target line; summaries ending with `,`, `:`, or `;` are reported but not changed.

## Why is this useful?
Terminal punctuation keeps summary lines sentence-like without forcing every valid question or exclamation into a period.

## Ruff compatibility
This rule replaces Ruff's `D415`. Use `PDF300` for the stricter period-only form. Unlike Ruff's unsafe fix, this rule does not report or fix underlined title-style summaries.

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

For multi-line summaries, the target is the final non-empty line of the first summary paragraph:

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

Commas, colons, and semicolons are reported but not changed because adding a period would produce questionable punctuation:

```pydocfmt-example
[input]
def comma():
    """Return the value,"""


def colon():
    """Return the value:"""


def semicolon():
    """Return the value;"""

[output=unchanged]
[findings]
PDF301: Line 2
PDF301: Line 6
PDF301: Line 10
```

Empty docstrings, underlined title-style summaries, parser-recognized section-only docstrings, Sphinx field-only docstrings, and summaries ending with a backslash are skipped. Recognized NumPy section headings such as `Parameters` followed by an underline are section headers, not summaries:

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


def sphinx_field(value):
    """:param value: Description"""


def backslash():
    """Path C:\\"""

[output=unchanged]
```

## Options
None.
