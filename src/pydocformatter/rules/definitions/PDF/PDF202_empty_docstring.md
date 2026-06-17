# empty-docstring (PDF202)

Fix is not available.

## What it does
Checks for module, class, and function docstrings whose evaluated value contains no non-whitespace content.

The rule reports empty simple docstrings and empty concatenated docstrings. It does not report absent docstrings or string expressions that are not the first statement in a documentable body.

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

Absent docstrings and later string expressions are not reported:

```pydocfmt-example
[input]
def undocumented():
    pass


def not_docstring():
    value = 1
    """"""

[output=unchanged]
```

## Options
None.
