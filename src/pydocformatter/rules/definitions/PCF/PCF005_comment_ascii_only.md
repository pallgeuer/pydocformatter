# comment-ascii-only (PCF005)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

## What it does
Reports Python comments whose source text contains literal non-ASCII characters. The rule checks standalone comments, trailing comments, shebangs, encoding cookies, type comments, and tool directives.

Only the comment token is checked. Non-ASCII characters in strings or other Python source are outside the scope of this rule, and ASCII escape spellings such as `\xe9` inside comments are accepted because the comment source itself is ASCII-only.

The rule is diagnostic-only. It does not try to escape or transliterate comments because comments may be prose, machine-readable directives, or temporarily disabled code.

## Why is this useful?
Some projects require ASCII-only source files for portability, encoding compatibility, or review consistency. Reporting non-ASCII comments makes those violations visible without guessing the intended replacement text.

## Ruff compatibility
None.

## Examples
Literal non-ASCII comments are reported without automatic changes:

```pydocfmt-example
[input]
# café
value = 1  # naïve

[output=unchanged]
[findings]
PCF005: Line 1: Comment contains non-ASCII character U+00E9
PCF005: Line 2: Comment contains non-ASCII character U+00EF
```

All comment forms are checked, including tool directives and type comments:

```pydocfmt-example
[input]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
value = 1  # type: inté
# noqa: café
# pylint: disable=line-too-longé

[output=unchanged]
[findings]
PCF005: Line 3: Comment contains non-ASCII character U+00E9
PCF005: Line 4: Comment contains non-ASCII character U+00E9
PCF005: Line 5: Comment contains non-ASCII character U+00E9
```

Non-ASCII characters outside comments are ignored, and comments that use ASCII-only escape spellings are unchanged:

```pydocfmt-example
[input]
text = "# café is string data"
# caf\xe9 is ASCII source

[output=unchanged]
```

ASCII-only comments are unchanged:

```pydocfmt-example
[input]
# cafe
value = 1  # naive

[output=unchanged]
```

## Options
None.
