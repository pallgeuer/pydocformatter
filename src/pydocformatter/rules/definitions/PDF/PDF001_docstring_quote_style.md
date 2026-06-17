# docstring-quote-style (PDF001)

Fix is sometimes available.

## What it does
Checks recognized simple docstrings that do not use triple double quotes. The rule applies to the first string-valued simple string expression in a module, class, function, async function, or method body. It reports docstrings written with `"..."`, `'...'`, or `'''...'''` delimiters, and it skips docstrings that already use `"""`.

The fix rewrites the docstring delimiter to `"""` only when the rewritten literal has the same evaluated value. It preserves existing string prefixes such as `r`, `R`, and `u`, reuses existing body source when possible, and escapes delimiter collisions for non-raw strings when needed. Empty docstrings and simple-suite docstrings can be fixed the same way as ordinary indented docstrings.

Raw docstrings are only fixed when the body can be moved into triple double quotes without changing the value. In particular, a raw docstring whose body contains `"""` is reported as non-fixable because escaping those quotes would add backslashes to the evaluated raw-string value. Concatenated docstrings are skipped because PDF000 owns concatenation normalization.

## Why is this useful?
Using one docstring delimiter style keeps source formatting consistent and gives later docstring rules one predictable literal shape to inspect and rewrite.

## Ruff compatibility
This rule replaces Ruff's `D300`, but it applies to every non-`"""` simple docstring delimiter instead of only triple-single-quoted docstrings. Fixes are value-preserving; unsafe rewrites are reported as non-fixable findings.

## Example
Single-quoted, double-quoted, and triple-single-quoted docstrings are rewritten to triple double quotes:

```pydocfmt-example
[input]
"module doc"

class Client:
    'client doc'

    def close(self): '''close client'''

[output]
"""module doc"""

class Client:
    """client doc"""

    def close(self): """close client"""
```

Empty docstrings, `u`-prefixed docstrings, and simple-suite docstrings are normalized when the evaluated value is preserved:

```pydocfmt-example
[input]
''

class Empty:
    ''''''

def inline(): 'Inline doc.'

def unicode_prefix():
    u'''Caf\xe9.'''

[output]
""""""

class Empty:
    """"""

def inline(): """Inline doc."""

def unicode_prefix():
    u"""Caf\xe9."""
```

Non-raw delimiter collisions are escaped when that preserves the evaluated docstring value:

```pydocfmt-example
[input]
def quoted():
    '''Contains """ inside.'''

[output]
def quoted():
    """Contains \"\"\" inside."""
```

Literal unsupported escape spellings can still be fixed if reusing the same body spelling with triple double quotes preserves the evaluated value:

```pydocfmt-example
[input]
def function():
    '''Contains \z literally.'''

[output]
def function():
    """Contains \z literally."""
```

Raw docstrings are not rewritten when the target delimiter occurs in the body, because escaping it would change the value. The finding spans all physical lines occupied by the docstring:

```pydocfmt-example
[input]
def quoted():
    R'''First line.
    Contains """ delimiter.
    Done.'''

[output=unchanged]
[findings]
PDF001: Lines 2-4: Docstring should use triple double quotes
```

Docstrings that already use triple double quotes, concatenated docstrings, and later string expressions are unchanged:

```pydocfmt-example
[input]
"""module doc"""

def concatenated():
    ("first " "second")

def not_docstring():
    value = 1
    'not a docstring'

[output=unchanged]
```

## Options
None.
