# empty-docstring (PDF202)

Fix is not available.

## What it does
Checks docstrings whose evaluated Python string value contains no non-whitespace content. It emits one finding for each affected docstring and does not modify the source.

The rule covers every primary docstring collected for a module, class, function, or method. It also covers supported PEP 258-style attribute docstrings attached to module variables, class variables, and instance attributes assigned in `__init__`. It does not report absent docstrings, additional string expressions, byte strings, f-strings, or strings in unsupported attachment positions.

Emptiness is determined after escape processing and implicit string concatenation. Python whitespace removed by `str.strip()`, including Unicode whitespace such as a non-breaking space, is empty. A character that `str.strip()` preserves, such as a zero-width space, makes the docstring nonempty even if it is visually unobtrusive.

The diagnostic covers all physical source lines occupied by the docstring's string tokens and interstitial lines, including delimiter-only closing lines and comments inside a concatenated string expression. Delimiter-only parenthesis lines are not included. This whole-expression target reflects that emptiness is a property of the complete docstring rather than of one particular content line.

## Why is this useful?
An empty docstring looks documented to tooling while conveying no useful information to readers.

## Ruff compatibility
This rule replaces Ruff's `D419`.

## Examples
Empty and whitespace-only docstrings are reported but not changed:

```pydocfmt-example
[input]
def value():
    """   """

[output=unchanged]
[findings]
PDF202: Line 2: Docstring is empty
```

The rule checks the evaluated docstring value, so escaped whitespace and concatenated whitespace-only docstrings are also empty:

```pydocfmt-example
[input]
def escaped():
    """\t\n"""


def concatenated():
    (" "
     "\t")

[output=unchanged]
[findings]
PDF202: Line 2: Docstring is empty
PDF202: Lines 6-7: Docstring is empty
```

Empty docstrings are reported wherever Python recognizes a real module, class, or function docstring:

```pydocfmt-example
[input]
""""""


class Example:
    """
    
    """

[output=unchanged]
[findings]
PDF202: Line 1: Docstring is empty
PDF202: Lines 5-7: Docstring is empty
```

Supported attached attribute docstrings are checked at module, class, and `__init__` instance scope:

```pydocfmt-example
[input]
module_timeout = 30
""""""


class Client:
    retries = 2
    """   """

    def __init__(self):
        self.endpoint = "https://example.invalid"
        (""
         "")

[output=unchanged]
[findings]
PDF202: Line 2: Docstring is empty
PDF202: Line 7: Docstring is empty
PDF202: Lines 11-12: Docstring is empty
```

Escape processing follows Python's whitespace semantics. A non-breaking space is empty, while a zero-width space is content:

```pydocfmt-example
[input]
def non_breaking_space():
    """\u00a0"""


def zero_width_space():
    """\u200b"""

[output=unchanged]
[findings]
PDF202: Line 2: Docstring is empty
```

Delimiter-only closing lines remain part of the empty docstring expression and are included in its finding:

```pydocfmt-example
[input]
"""
"""

[output=unchanged]
[findings]
PDF202: Lines 1-2: Docstring is empty
```

Absent docstrings and later string expressions are not reported:

```pydocfmt-example
[input]
def undocumented():
    pass


def not_docstring():
    value = 1
    """"""


class Client:
    def refresh(self):
        self.timeout = 30
        """"""

[output=unchanged]
```

## Options
None.
