# docstring-literal-normalization (PDF000)

Fix is usually available.

## What it does
Checks docstring literals that can be normalized without changing their evaluated value. The rule replaces implicitly concatenated string literals with one triple-double-quoted string literal and converts normal whitespace escapes such as `\n` and `\t` to literal whitespace where this is safe.

A docstring is only the first string-valued expression in a module, class, or function body. PDF000 therefore applies to module, class, function, async function, and method docstrings, but it does not apply to assigned strings, later string expressions, or f-string expressions that are not string-valued docstrings.

The replacement is value-preserving and keeps reusable source spellings for individual string characters where possible. Raw-string prefixes, quote style, component-literal boundaries, backslash continuations, parentheses around the expression, and comments between component literals may disappear because the rule emits one simple literal. Surrounding Python syntax, such as enclosing parentheses and single-line suites, is retained.

## Why is this useful?
Implicitly concatenated docstrings have source-level boundaries that do not exist in the runtime docstring value. Escaped whitespace such as `\n` has logical line structure that does not appear as physical source lines. Normalizing these forms first gives later docstring formatting rules a single literal with explicit source lines to inspect and rewrite, which avoids ambiguous edits around adjacent string tokens, comments between tokens, and hidden line breaks.

## Ruff compatibility
None. Ruff can flag some implicit string concatenation patterns in other contexts, but PDF000 is specific to Python docstring ownership and rewrites only recognized docstrings.

## Example
The canonical concatenation case is a function docstring composed of adjacent string literals:

```python
def function():
    "First part. " "Second part."
```

Applying this rule produces:

```python
def function():
    """First part. Second part."""
```

Normal whitespace escape spellings are converted to literal whitespace when the value stays unchanged:

```python
def function():
    """First line.\n\tIndented second line."""
```

Applying this rule produces:

```python
def function():
    """First line.
	Indented second line."""
```

Reusable escape spellings and non-ASCII code points are preserved where possible, so ASCII-compatible source output stays ASCII-compatible without canonicalizing the exact escape form:

```python
# -*- coding: ascii -*-
"\u00e9" "\u20ac" "\U0001f600"
```

Applying this rule produces:

```python
# -*- coding: ascii -*-
"""\u00e9\u20ac\U0001f600"""
```

Parentheses and surrounding statement layout are retained while the complete concatenated string expression is replaced. Comments and backslash continuations between component literals disappear with those source-level boundaries:

```python
def function():
    (
        r"first\n"  # source comment
        " second" \
        "\tthird"
    )
```

Applying this rule produces:

```python
def function():
    (
        """first\\n second\tthird"""
    )
```

Module, class, and function docstrings are all handled in the same pass, including docstrings in single-line suites:

```python
"module " "doc"

class Client:
    "client " "doc"

    def close(self): "close " "client"; return None
```

Applying this rule produces:

```python
"""module doc"""

class Client:
    """client doc"""

    def close(self): """close client"""; return None
```

Only a string-valued first expression in a module, class, or function body is a docstring. Concatenated strings used elsewhere, f-string expressions, raw strings containing literal backslash text, and already-normal simple docstrings are unchanged:

```python
def documented():
    """Already simple."""
    label = "first " "second"

def formatted():
    f"first" "second"

def undocumented():
    initialize()
    "not " "a docstring"
```

Applying this rule produces the same source.

## Options
None.
