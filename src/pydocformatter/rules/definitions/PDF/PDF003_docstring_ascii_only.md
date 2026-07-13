# docstring-ascii-only (PDF003)

Fix is usually available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

## What it does
Reports docstring literals whose source text contains literal non-ASCII characters. Already escaped ASCII spellings such as `\xe9`, `\u00e9`, and `\U0001f600` are accepted because the source is ASCII-only.

For simple docstrings, the fix escapes literal non-ASCII characters while validating that the evaluated docstring value is unchanged. The fix preserves the quote style, preserves a `u` prefix, and removes a raw prefix only when the docstring body has no backslashes and the resulting non-raw string has the same value.

Docstrings are reported without a fix when automatic escaping could change the value or syntax. This includes concatenated docstrings, raw docstrings with backslashes, and non-raw docstrings whose existing backslashes are still actionable by PDF002 or would change value if the body were re-rendered.

## Why is this useful?
ASCII-only docstring source keeps files compatible with strict source encodings while preserving the runtime documentation text.

## Ruff compatibility
PDF003 intentionally cooperates with PDF002 by avoiding automatic fixes for docstrings whose source backslashes are still actionable by the raw-prefix rule.

## Examples
Literal non-ASCII source is escaped while preserving the evaluated docstring value:

```pydocfmt-example
[input]
def function():
    """Return café and 😀."""

[output]
def function():
    """Return caf\xe9 and \U0001f600."""
```

The fix preserves safe prefixes and quote delimiters, and can remove a raw prefix when there are no backslashes to preserve:

```pydocfmt-example
[input]
def unicode_prefix():
    u"""Return café."""

def raw_without_backslash():
    r'''Return naïve text.'''

[output]
def unicode_prefix():
    u"""Return caf\xe9."""

def raw_without_backslash():
    '''Return na\xefve text.'''
```

Multiline docstrings are fixed across all affected physical lines:

```pydocfmt-example
[input]
def function():
    """Return café.
    Snowman ☃."""

[output]
def function():
    """Return caf\xe9.
    Snowman \u2603."""
```

Already escaped ASCII source is unchanged:

```pydocfmt-example
[input]
def function():
    """Return caf\xe9 and \u2603."""

[output=unchanged]
```

Concatenated docstrings and other unsupported docstring shapes are reported but not fixed by this rule alone:

```pydocfmt-example
[input]
def function():
    ("Return café" " soon.")

[output=unchanged]
[findings]
PDF003: Line 2: Docstring source contains non-ASCII character U+00E9
```

Docstrings with backslash spellings that PDF002 can act on are reported but not fixed by PDF003:

```pydocfmt-example
[input]
def function():
    """Return café and \d."""

[output=unchanged]
[findings]
PDF003: Line 2: Docstring source contains non-ASCII character U+00E9
```

Docstrings with value-changing backslashes are also non-fixable because escaping the non-ASCII source while preserving the existing escape spelling could change the evaluated text:

```pydocfmt-example
[input]
def function():
    """Return café\nNext."""

[output=unchanged]
[findings]
PDF003: Line 2: Docstring source contains non-ASCII character U+00E9
```

When fixable and non-fixable docstrings appear together, PDF003 fixes only the value-preserving cases and leaves findings for the rest:

```pydocfmt-example
[input]
def fixed():
    """Return café."""

def unsafe():
    """Return café\nNext."""

[output]
def fixed():
    """Return caf\xe9."""

def unsafe():
    """Return café\nNext."""

[findings]
PDF003: Line 5: Docstring source contains non-ASCII character U+00E9
```

Only docstrings are checked. Non-ASCII source in ordinary strings, f-strings, and later string expressions is unchanged:

```pydocfmt-example
[input]
value = "café"

def function(value):
    f"café {value}"
    "café"

[output=unchanged]
```

## Options
None.
