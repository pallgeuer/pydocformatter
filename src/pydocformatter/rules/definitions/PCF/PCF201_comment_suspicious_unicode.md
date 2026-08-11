# comment-suspicious-unicode (PCF201)

Fix is sometimes available.

## What it does

Reports an explicit set of suspicious Unicode controls, separators, bidi controls, and invisible formatting characters in literal Python comments. Standalone comments, trailing comments, shebangs, encoding cookies, type comments, and tool directives are all checked.

The following characters are reported wherever they occur:

- C0 controls U+0000-U+0008 and U+000B-U+001F, U+007F DELETE, and C1 controls U+0080-U+009F. Tab and line feed are deliberately excluded.
- U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR.
- Bidi controls U+061C, U+200E-U+200F, U+202A-U+202E, and U+2066-U+2069.
- Invisible format characters U+00AD, U+180E, U+200B, U+2060, U+206A-U+206F, and U+FEFF.

U+00A0 NO-BREAK SPACE, U+2007 FIGURE SPACE, and U+202F NARROW NO-BREAK SPACE are reported only after the first syntactic `#` while the comment payload is still in indentation. Indentation continues through whitespace until the first non-whitespace character. A second `#` is content, so a nonbreaking space after it is accepted.

The rule replaces each reportable indentation space with one ASCII space. Other suspicious characters are diagnostic-only. Repeated occurrences of one code point in one comment are grouped into one finding; separate comments produce separate findings.

Comments do not interpret Python string escapes. Text such as `\u202e` is ordinary ASCII notation and is not equivalent to the character it names.

## Why is this useful?

Invisible controls and bidi formatting can make comments misleading in editors and reviews. Visually indistinguishable nonbreaking indentation can also defeat ordinary comment formatting. The explicit policy and stable character names make diagnostics independent of the Python runtime's Unicode database.

## Ruff compatibility

PCF201 is related to Ruff's `RUF003` and `PLE2502`, `PLE2510`, `PLE2512`, `PLE2513`, `PLE2514`, and `PLE2515` rules, but has comment-specific scope and fix behavior.

## Examples

The canonical PCF201 fix replaces a leading no-break space after the syntactic hash:

```pydocfmt-example
[input]
# Comment text.

[output]
# Comment text.
```

All three indentation-only spaces are fixed in standalone and trailing comments:

```pydocfmt-example
[input]
# First comment.
value = 1  # Trailing comment.
# Third comment.

[output]
# First comment.
value = 1  # Trailing comment.
# Third comment.
```

Repeated bidi controls are grouped, while a different invisible character receives its own finding:

```pydocfmt-example
[input]
# abc‮def‮ and​word

[output=unchanged]
[findings]
PCF201: Line 1: Comment contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE
PCF201: Line 1: Comment contains suspicious Unicode character U+200B ZERO WIDTH SPACE
```

Shebangs, encoding cookies, type comments, and tool directives are checked rather than exempted as protected comment kinds:

```pydocfmt-example
[input]
#!/usr/bin/env‮python
# coding: utf-8​
value = 1  # type: int⁠
# noqa­

[output=unchanged]
[findings]
PCF201: Line 1: Comment contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE
PCF201: Line 2: Comment contains suspicious Unicode character U+200B ZERO WIDTH SPACE
PCF201: Line 3: Comment contains suspicious Unicode character U+2060 WORD JOINER
PCF201: Line 4: Comment contains suspicious Unicode character U+00AD SOFT HYPHEN
```

ASCII escape notation, interior nonbreaking prose spaces, and a nonbreaking space after a second hash are accepted:

```pydocfmt-example
[input]
# \u202e is notation.
# Keep these words together.
## Heading

[output=unchanged]
```

## Options

None.
