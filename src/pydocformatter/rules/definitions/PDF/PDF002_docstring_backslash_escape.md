# docstring-backslash-escape (PDF002)

Fix is sometimes available.

## What it does
Checks recognized simple docstrings whose source body contains a backslash but whose string prefix is not raw. The rule applies to the first string-valued simple string expression in a module, class, function, async function, or method body. It skips already raw docstrings, docstrings with no source backslash, concatenated docstrings, and later string expressions.

The fix only adds an `r` prefix while leaving the quote style and body source unchanged. A finding is fixable only when that exact raw-prefixed spelling parses successfully and has the same evaluated docstring value. This is commonly safe for invalid escape spellings such as `\d` or `\w`, which already evaluate to literal backslash text.

Recognized escapes such as `\n`, `\t`, ASCII-valued `\x..`, `\u....`, `\U........`, `\N{...}`, and octal escapes, escaped quotes, escaped backslashes, backslash line continuations, raw-incompatible trailing backslashes, and `u`-prefixed strings with reportable backslashes are reported as non-fixable when adding the raw prefix would change the value or produce invalid syntax. Non-ASCII character escapes are not reported when they are the only backslash reason, because projects may intentionally use them to keep source ASCII-only. If one docstring mixes a suppressed non-ASCII character escape with another reportable backslash, PDF002 reports only the physical lines containing the reportable backslashes.

## Why is this useful?
Raw docstrings make literal backslashes in paths, regular expressions, and escaped markup visible in the source without relying on invalid or accidental escape interpretation.

## Ruff compatibility
This rule replaces Ruff's `D301`, while keeping automatic fixes value-preserving. Ruff can suggest raw docstrings for any backslash; PDF002 reports the same broad problem but fixes only the subset where adding `r` is safe.

## Example
Invalid escape spellings that already evaluate to literal backslash text are rewritten by adding a raw prefix:

```pydocfmt-example
[input]
def regex():
    """Match \d+ values."""

[output]
def regex():
    r"""Match \d+ values."""
```

The original quote style is preserved when adding the raw prefix, and simple-suite docstrings are handled the same way:

```pydocfmt-example
[input]
def regex():
    '''Match \d+ values.'''

def inline(): """Match \w+ values."""

[output]
def regex():
    r'''Match \d+ values.'''

def inline(): r"""Match \w+ values."""
```

Recognized escapes are reported but not fixed because a raw prefix would change the evaluated docstring value. The same is true for ASCII-valued hex, octal, and named Unicode escapes:

```pydocfmt-example
[input]
def line():
    """First\nSecond."""

def hex_escape():
    """Letter \x41."""

def octal_escape():
    """Letter \101."""

def named_escape():
    """Letter \N{LATIN CAPITAL LETTER A}."""

[output=unchanged]
[findings]
PDF002: Line 2: Docstring with backslashes should use a raw string prefix
PDF002: Line 5: Docstring with backslashes should use a raw string prefix
PDF002: Line 8: Docstring with backslashes should use a raw string prefix
PDF002: Line 11: Docstring with backslashes should use a raw string prefix
```

A manual fix is to spell the intended evaluated characters directly, removing the source backslashes that made the docstrings look like raw-string candidates:

```pydocfmt-example
[input]
def line():
    """First
Second."""

def hex_escape():
    """Letter A."""

def octal_escape():
    """Letter A."""

def named_escape():
    """Letter A."""

[output=unchanged]
```

Non-ASCII character escapes are not reported when they are the only backslash reason, because the escape may be the intended ASCII-only source spelling:

```pydocfmt-example
[input]
def hex_escape():
    """Letter \xe9."""

def unicode_escape():
    """Letter \u00e9."""

def large_unicode_escape():
    """Face \U0001f600."""

def named_escape():
    """Snowman \N{SNOWMAN}."""

def octal_escape():
    """No-break space \240."""

[output=unchanged]
```

A docstring with both a literal backslash spelling and a recognized escape is reported but not fixed, because adding `r` would preserve one part and change the other:

```pydocfmt-example
[input]
def mixed():
    """Match \d+ then\nNext."""

[output=unchanged]
[findings]
PDF002: Line 2: Docstring with backslashes should use a raw string prefix
```

A manual fix is to keep the literal backslash spelling in a raw docstring while spelling the newline as an actual line break:

```pydocfmt-example
[input]
def mixed():
    r"""Match \d+ then
Next."""

[output=unchanged]
```

Suppressed non-ASCII character escapes do not make the whole docstring clean when other reportable backslashes are present. The finding points only to the lines with the remaining reportable reasons:

```pydocfmt-example
[input]
def mixed():
    """Letter \u00e9.
    Match \d+.
    First\nSecond."""

[output=unchanged]
[findings]
PDF002: Lines 3-4: Docstring with backslashes should use a raw string prefix
```

Escaped delimiters, escaped backslashes, and backslash line continuations are also non-fixable:

```pydocfmt-example
[input]
def backslash():
    """C:\\temp."""

def delimiter():
    """Contains \"quote\"."""

def continuation():
    """first\
second"""

[output=unchanged]
[findings]
PDF002: Line 2: Docstring with backslashes should use a raw string prefix
PDF002: Line 5: Docstring with backslashes should use a raw string prefix
PDF002: Line 8: Docstring with backslashes should use a raw string prefix
```

A manual fix depends on the intended value: use raw strings for literal backslashes, remove unnecessary quote escapes, and replace line continuations with the value they actually produce:

```pydocfmt-example
[input]
def backslash():
    r"""C:\temp."""

def delimiter():
    """Contains "quote"."""

def continuation():
    """firstsecond"""

[output=unchanged]
```

`u`-prefixed docstrings are reported but not fixed, while uppercase raw prefixes are treated as already raw:

```pydocfmt-example
[input]
def unicode_prefix():
    u"""Match \d+ values."""

def raw_prefix():
    R"""Match \w+ values."""

[output=unchanged]
[findings]
PDF002: Line 2: Docstring with backslashes should use a raw string prefix
```

A manual fix is to choose the raw prefix directly when Python 2 compatibility spelling is not needed:

```pydocfmt-example
[input]
def unicode_prefix():
    r"""Match \d+ values."""

def raw_prefix():
    R"""Match \w+ values."""

[output=unchanged]
```

Already raw docstrings, docstrings without backslashes, concatenated docstrings, and later string expressions are unchanged:

```pydocfmt-example
[input]
def raw():
    r"""Match \d+ values."""

def plain():
    """No escapes."""

def concatenated():
    ("Match " "\d+")

def not_docstring():
    value = 1
    """Match \d+ values."""

[output=unchanged]
```

## Options
None.
