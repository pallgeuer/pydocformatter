# summary-first-word-capitalization (PDF304)

Fix is sometimes available.

## What it does
Checks docstring summaries whose first word starts with a lowercase ASCII letter when that word can be safely interpreted as ordinary ASCII prose. This includes module, class, function, method, and attached attribute docstrings.

PDF304 checks the first non-adornment line of the parsed top-level summary block, including summaries in multiline docstrings. It skips empty docstrings, docstrings without a parsed summary, parser-recognized structures, all-uppercase words, mixed-case words, non-ASCII starts, numeric starts, and words containing characters other than lowercase ASCII letters or apostrophes after the first character. This means `return` and `don't` can be fixed, while `"return"`, `(return)`, `return:`, `return_value`, `return-value`, `iOS`, and `eBay` are left alone. When fixing, it uppercases only the first character of the first word.

Unsafe source mappings are reported but not changed. This includes summaries whose first logical line is formed from concatenated strings or escaped newline text, because changing only one apparent word could require rewriting source text that does not map cleanly to that logical word.

With heading parsing enabled, underlined title-style content is a heading and is skipped. With heading parsing disabled, the first non-adornment summary line is checked.

## Why is this useful?
Consistent summary capitalization makes docstrings scan like complete prose.

## Ruff compatibility
This rule replaces Ruff's `D403`. Unlike Ruff, it applies to all parsed docstring summaries, not only functions and methods. Like Ruff, it only fixes ASCII words that can be capitalized safely.

## Examples
PDF304 capitalizes a safe function summary first word:

```pydocfmt-example
[input]
def value():
    """return the value."""

[output]
def value():
    """Return the value."""
```

It also capitalizes safe summary first words in module, class, and attached attribute docstrings:

```pydocfmt-example
[input]
"""module defaults."""

class Client:
    """client configuration."""

    timeout = 30
    """request timeout in seconds."""

[output]
"""Module defaults."""

class Client:
    """Client configuration."""

    timeout = 30
    """Request timeout in seconds."""
```

Multiline docstrings are checked when their first parsed block is a summary:

```pydocfmt-example
[input]
def value():
    """return the value.

    More details follow.
    """

[output]
def value():
    """Return the value.

    More details follow.
    """
```

Other safe ASCII first words are fixed in the same narrow way:

```pydocfmt-example
[input]
def question():
    """return?"""

def contraction():
    """don't return."""

def raw_pattern():
    r"""return \d+ values."""

[output]
def question():
    """Return?"""

def contraction():
    """Don't return."""

def raw_pattern():
    r"""Return \d+ values."""
```

Words that are already capitalized, mixed-case, all-uppercase, non-ASCII, numeric, or punctuated in unsafe ways are skipped:

```pydocfmt-example
[input]
def capitalized():
    """Return the value."""

def acronym():
    """HTTP value."""

def platform():
    """iOS device."""

def non_ascii():
    """\u00e9clair value."""

def quoted():
    """"return" value."""

def snake_case():
    """return_value."""

[output=unchanged]
```

Unsafe source mappings are reported but not fixed, while safe instances in the same file are still fixed:

```pydocfmt-example
[input]
def safe():
    """return the value."""

def escaped():
    """return the value\ncontinued."""

[output]
def safe():
    """Return the value."""

def escaped():
    """return the value\ncontinued."""
[findings]
PDF304: Line 5: Docstring summary first word 'return' should be capitalized
```

Parser-recognized non-summary structures are not checked:

```pydocfmt-example
[input]
def field():
    """:return: field summary"""

[output=unchanged]
```

Parser-recognized structures are protected. Disabling the matching parser setting can make the same text become a summary target:

```pydocfmt-example
[settings]
docstring-parse-headings = false

[input]
def value():
    """title
    =====
    """

[output]
def value():
    """Title
    =====
    """
```

## Options
- `docstring-parse-*`: Controls whether generic structures such as headings, lists, doctests, code fences, block quotes, tables, directives, and literal blocks are protected from summary-style checks.
