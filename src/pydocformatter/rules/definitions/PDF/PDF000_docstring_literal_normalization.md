# docstring-literal-normalization (PDF000)

Fix is usually available.

## What it does
Checks docstring literals that can be normalized without changing their evaluated value. The rule replaces implicitly concatenated string literals with one triple-double-quoted string literal, removes no-op `u`/`U` string prefixes, and converts normal whitespace escapes such as `\n` and `\t` to literal whitespace where this is safe.

A docstring is only the first string-valued expression in a module, class, or function body. PDF000 therefore applies to module, class, function, async function, and method docstrings, but it does not apply to assigned strings, later string expressions, or f-string expressions that are not string-valued docstrings.

The replacement is value-preserving and keeps reusable source spellings for individual string characters where possible. Plain Unicode string prefixes, raw-string prefixes, quote style, component-literal boundaries, backslash continuations, parentheses around the expression, and comments between component literals may disappear because the rule emits one simple literal. Surrounding Python syntax, such as enclosing parentheses and single-line suites, is retained.

## Why is this useful?
Implicitly concatenated docstrings have source-level boundaries that do not exist in the runtime docstring value. Escaped whitespace such as `\n` has logical line structure that does not appear as physical source lines. Normalizing these forms first gives later docstring formatting rules a single literal with explicit source lines to inspect and rewrite, which avoids ambiguous edits around adjacent string tokens, comments between tokens, and hidden line breaks.

## Ruff compatibility
None. Ruff can flag some implicit string concatenation patterns in other contexts, but PDF000 is specific to Python docstring ownership and rewrites only recognized docstrings.

## Example
The canonical concatenation case is a function docstring composed of adjacent string literals:

```pydocfmt-example
[input]
def function():
    "First part. " "Second part."

[output]
def function():
    """First part. Second part."""
```

Normal whitespace escape spellings are converted to literal whitespace when the value stays unchanged:

```pydocfmt-example
[input]
def function():
    """First line.\n\tIndented second line."""

[output]
def function():
    """First line.
	Indented second line."""
```

Plain Python 3 Unicode prefixes are removed because they do not affect the evaluated docstring value:

```pydocfmt-example
[input]
def function():
    u"""Summary."""

[output]
def function():
    """Summary."""
```

Reusable escape spellings and non-ASCII code points are preserved where possible, so ASCII-compatible source output stays ASCII-compatible without canonicalizing the exact escape form:

```pydocfmt-example
[input]
# -*- coding: ascii -*-
"\u00e9" "\u20ac" "\U0001f600"

[output]
# -*- coding: ascii -*-
"""\u00e9\u20ac\U0001f600"""
```

Parentheses and surrounding statement layout are retained while the complete concatenated string expression is replaced. Comments and backslash continuations between component literals disappear with those source-level boundaries:

```pydocfmt-example
[input]
def function():
    (
        r"first\n"  # source comment
        " second" \
        "\tthird"
    )

[output]
def function():
    (
        """first\\n second	third"""
    )
```

Module, class, and function docstrings are all handled in the same pass, including docstrings in single-line suites:

```pydocfmt-example
[input]
"module " "doc"

class Client:
    "client " "doc"

    def close(self): "close " "client"; return None

[output]
"""module doc"""

class Client:
    """client doc"""

    def close(self): """close client"""; return None
```

Only a string-valued first expression in a module, class, or function body is a docstring. Concatenated strings used elsewhere, f-string expressions, raw strings containing literal backslash text, and already-normal simple docstrings are unchanged:

```pydocfmt-example
[input]
def documented():
    """Already simple."""
    label = "first " "second"

def formatted():
    f"first" "second"

def undocumented():
    initialize()
    "not " "a docstring"

[output=unchanged]
```

## Options
None.
