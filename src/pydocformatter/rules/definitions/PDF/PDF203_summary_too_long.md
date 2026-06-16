# summary-too-long (PDF203)

Fix is not available.

## What it does
Checks docstrings whose parsed top-level summary still spans multiple logical lines after selected automatic fixes have run.

PDF203 reports only summary blocks. It does not report one-line summaries, paragraphs after a blank line, convention sections, recognized structures, blank-only docstrings, or docstrings without a parsed summary. Because the rule is diagnostic-only, it leaves source unchanged and reports a non-fixable finding.

When selected together with `PDF101`, short wrapped summaries can be reflowed before PDF203 checks the final source. When selected together with `PDF201`, recognized structures can be separated from a one-line summary before PDF203 checks. Summaries that remain multi-line after selected fixes are reported for human rewriting or for a human decision about whether a blank line is missing between the summary and description.

Parsing settings affect what counts as a summary. Recognized structures such as list items, headings, doctests, directives, Sphinx fields, block quotes, code fences, and tables are protected by default. Disabling the matching `docstring-parse-*` setting can make those lines become part of the parsed summary and therefore reportable.

## Why is this useful?
A multi-line summary can be ambiguous: it may be a long summary that needs rewriting by a human, or a missing blank line between the summary and description.

## Ruff compatibility
This rule is intended to cover the non-fixable part of Ruff's `D205` behavior after pydocformatter has normalized fixable blank-line spacing. Ruff's `D205` cannot safely decide whether adjacent prose is a wrapped summary or a missing blank line; PDF203 reports that ambiguity without changing source.

## Example
PDF203 reports an ambiguous multi-line summary and does not change the source:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area for a circle
    after validating the radius.
    """

[output=unchanged]
[findings]
PDF203: Lines 2-3
```

When PDF203 is selected by itself, `line-length` does not make it reflow or suppress a multi-line summary:

```pydocfmt-example
[settings]
line-length = 88

[input]
def area(radius: float) -> float:
    """Return the area
    for a circle.
    """

[output=unchanged]
[findings]
PDF203: Lines 2-3
```

Multiple docstring shapes can be reported in one file. Line numbers point to the mapped summary source lines, falling back to the physical docstring line for escaped newline summaries:

```pydocfmt-example
[input]
"""Module summary line
continued here."""

def concatenated() -> None:
    ("Summary line\n"
     "continuation line.")

def escaped() -> None:
    """Summary line\ncontinuation line."""

[output=unchanged]
[findings]
PDF203: Lines 1-2
PDF203: Lines 5-6
PDF203: Line 9
```

One-line summaries followed by a blank-line-separated body, paragraph, or recognized section are not reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def body(radius: float) -> float:
    """Return the area.

    The radius is validated before the area is computed.
    """

def section(radius: float) -> float:
    """Return the area.

    Args:
        radius: Circle radius.
    """

[output=unchanged]
```

Only the top-level summary block is diagnostic. Later multi-line paragraphs and section entries are not reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def paragraph() -> None:
    """Summary.

    Body line one
    body line two.
    """

def section(value: int) -> None:
    """Summary.

    Args:
        value: Description line one
            continuation line.
    """

[output=unchanged]
```

Recognized structures are protected by default, even if they appear at the start of a docstring:

````pydocfmt-example
[input]
def list_item() -> None:
    """- item
    continuation
    """

def fenced() -> None:
    """```python
    print(value)
    ```
    """

[output=unchanged]
````

If the relevant structure parser is disabled, the same text can become a reportable multi-line summary:

```pydocfmt-example
[settings]
docstring-parse-list-items = false

[input]
def list_item() -> None:
    """- item
    continuation
    """

[output=unchanged]
[findings]
PDF203: Lines 2-3
```

Ambiguous prose without a blank line after a one-line opening sentence is reported because it may be either a wrapped summary or a missing summary/body separator:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.
    Validate the radius before computing it.
    """

[output=unchanged]
[findings]
PDF203: Lines 2-3
```

## Options
- `docstring-convention`: Controls whether Google and NumPy sections are recognized instead of treated as summary text.
- `docstring-parse-*`: Controls whether generic structures such as lists, headings, doctests, directives, Sphinx fields, block quotes, code fences, and tables are protected from summary-length checks.
