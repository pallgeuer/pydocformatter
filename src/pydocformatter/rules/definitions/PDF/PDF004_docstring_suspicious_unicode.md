# docstring-suspicious-unicode (PDF004)

Fix is sometimes available.

## What it does

Reports an explicit set of suspicious Unicode controls, separators, bidi controls, and invisible formatting characters in evaluated docstring values. The rule checks module, class, function, method, and attached attribute docstrings. Literal characters and Python escape spellings are treated equivalently, including across supported implicitly concatenated docstrings.

The following characters are reported wherever they occur:

- C0 controls U+0000–U+0008 and U+000B–U+001F, U+007F DELETE, and C1 controls U+0080–U+009F. Tab and line feed are deliberately excluded.
- U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR.
- Bidi controls U+061C, U+200E–U+200F, U+202A–U+202E, and U+2066–U+2069.
- Invisible format characters U+00AD, U+180E, U+200B, U+2060, U+206A–U+206F, and U+FEFF.

U+00A0 NO-BREAK SPACE, U+2007 FIGURE SPACE, and U+202F NARROW NO-BREAK SPACE are reported only in logical-line indentation. Indentation starts at the beginning of the evaluated value and after a carriage return or line feed, and continues through whitespace until the first non-whitespace character. These spaces are accepted and preserved after prose begins because they can intentionally keep words together.

The rule fixes reportable indentation spaces by replacing the exact literal character or escape spelling that produced each one with a single ASCII space. Other suspicious characters are diagnostic-only. Repeated occurrences of one code point on one physical source line are grouped into one finding.

Fixing is deliberately conservative. Every occurrence of a code point must map exactly through supported simple-string leaves; if any occurrence cannot be mapped, all occurrences of that code point in the docstring are combined into one non-fixable finding. Other exactly mapped code points in the same docstring can still be fixed or reported normally.

## Why is this useful?

Invisible controls and bidi formatting can make displayed documentation differ materially from its evaluated text or source spelling. Indentation made from visually similar nonbreaking spaces can also evade ordinary formatting checks. The explicit policy and stable character names make diagnostics independent of the Python runtime's Unicode database.

## Ruff compatibility

PDF004 is related to Ruff's `RUF002` and `PLE2502`, `PLE2510`, `PLE2512`, `PLE2513`, `PLE2514`, and `PLE2515` rules, but it is not equivalent to them. PDF004 checks evaluated docstring characters, including escape spellings, and uses an explicit project policy rather than confusable-character matching.

## Examples

PDF004 fix replaces an escaped no-break space in docstring indentation with an ASCII space:

```pydocfmt-example
[input]
def function():
    """Summary.
\u00a0Indented text."""

[output]
def function():
    """Summary.
 Indented text."""
```

Literal and escaped nonbreaking indentation spaces are fixed in simple and implicitly concatenated docstrings:

```pydocfmt-example
[input]
def literal_and_escaped():
    """Summary.
 First line.
\u202fSecond line."""

def concatenated():
    ("Summary.\n"
     "\N{NO-BREAK SPACE}Third line.")

[output]
def literal_and_escaped():
    """Summary.
 First line.
 Second line."""

def concatenated():
    ("Summary.\n"
     " Third line.")
```

Diagnostic-only characters are grouped by code point and physical source line:

```pydocfmt-example
[input]
def function():
    """Return abc\u202edef\u202e.
    Keep this\u200bword."""

[output=unchanged]
[findings]
PDF004: Line 2: Docstring contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE
PDF004: Line 3: Docstring contains suspicious Unicode character U+200B ZERO WIDTH SPACE
```

A fixable indentation space and a diagnostic-only character can be handled independently on the same line:

```pydocfmt-example
[input]
def function():
    """Summary.
\u00a0Indented\u2060text."""

[output]
def function():
    """Summary.
 Indented\u2060text."""

[findings]
PDF004: Line 3: Docstring contains suspicious Unicode character U+2060 WORD JOINER
```

Nonbreaking spaces within prose and backslash notation in raw docstrings are accepted:

```pydocfmt-example
[input]
def prose():
    """Keep no-break spacing."""

def notation():
    r"""The text \u202e is literal notation."""

[output=unchanged]
```

The rule also checks attached attribute docstrings:

```pydocfmt-example
[input]
timeout = 10
"""Request\u202etimeout."""

[output=unchanged]
[findings]
PDF004: Line 2: Docstring contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE
```

## Options

None.
