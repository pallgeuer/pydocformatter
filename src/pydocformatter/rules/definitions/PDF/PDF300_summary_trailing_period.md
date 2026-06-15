# summary-trailing-period (PDF300)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `google`.

## What it does
Checks that the docstring summary punctuation target ends with a period.

The target is the final non-empty line of the first logical summary paragraph. Empty docstrings, underlined title-style summaries, parser-recognized section-only docstrings, Sphinx field-only docstrings, and targets ending with a backslash are skipped. The automatic fix only inserts a period at the end of the trimmed target line; summaries ending with `,`, `?`, `!`, `:`, `;`, or `\u2026` are reported but not changed.

## Why is this useful?
Some projects prefer a strict PEP 257 summary sentence style where summaries consistently end in periods.

## Ruff compatibility
This rule replaces Ruff's `D400`. Use `PDF301` for the broader terminal-punctuation form. Unlike Ruff's unsafe fix, this rule does not report or fix underlined title-style summaries.

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

Summaries ending with non-period punctuation are reported but not changed because adding a period would produce questionable punctuation:

```pydocfmt-example
[input]
def comma():
    """Return the value,"""


def question():
    """Return the value?"""


def colon():
    """Return the value:"""

[output=unchanged]
[findings]
PDF300: Line 2
PDF300: Line 6
PDF300: Line 10
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
