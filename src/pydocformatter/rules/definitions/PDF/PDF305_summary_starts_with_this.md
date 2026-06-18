# summary-starts-with-this (PDF305)

Fix is not available.

Rule is ignored if `docstring-convention` is `google` or `pep257`.

## What it does
Checks module, class, function, and method docstring summaries whose first normalized word is `this`.

PDF305 removes non-alphanumeric characters from the first summary word and lowercases it before comparing. This catches forms such as `This`, `this`, `THIS`, `"This"`, `` `This` ``, and `This:`, but it does not treat `ThisReturns`, `this_module`, or `This\u00e9` as the word `this`.

It skips empty docstrings, docstrings without a parsed summary, and parser-recognized structures such as sections, rest fields under the rest convention, headings, lists, doctests, code fences, block quotes, tables, directives, literal blocks, and verbatim blocks. With heading parsing enabled, underlined title-style content is a heading and is skipped. With heading parsing disabled, the first non-adornment summary line is checked.

## Why is this useful?
Summaries that begin with "This" are often indirect and can usually be rewritten more concisely around the action or object being documented.

## Ruff compatibility
This rule replaces Ruff's `D404`. Like Ruff, it applies to all definition docstrings and is ignored by default for the Google and PEP257 conventions.

PDF305 intentionally checks pydocformatter's parsed summary target instead of Ruff's raw trimmed docstring body token. This protects parser-recognized structures that are not prose summaries. It also treats tabs, newlines, and non-breaking spaces as word separators, so a summary that visibly starts with `This` is reported even when Ruff's ASCII-space-only token split would miss it.

## Example
PDF305 reports summaries that start with "This" and leaves source unchanged:

```pydocfmt-example
[input]
def value():
    """This returns the value."""

[output=unchanged]
[findings]
PDF305: Line 2: Docstring summary should not start with "This"
```

Normalization makes capitalization and simple surrounding punctuation irrelevant:

```pydocfmt-example
[input]
def lower():
    """this returns the value."""

def quoted():
    """"This" returns the value."""

def colon():
    """This: returns the value."""

[output=unchanged]
[findings]
PDF305: Line 2: Docstring summary should not start with "This"
PDF305: Line 5: Docstring summary should not start with "This"
PDF305: Line 8: Docstring summary should not start with "This"
```

The rule also applies to module and class docstrings:

```pydocfmt-example
[input]
"""This module returns values."""

class Value:
    """This class returns values."""

[output=unchanged]
[findings]
PDF305: Line 1: Docstring summary should not start with "This"
PDF305: Line 4: Docstring summary should not start with "This"
```

Other first words are accepted:

```pydocfmt-example
[input]
def value():
    """Return this value."""

def joined():
    """ThisReturns value."""

def module_name():
    """this_module value."""

[output=unchanged]
```

Parser-recognized structures are protected. Disabling the matching parser setting can make the same text become a summary target:

```pydocfmt-example
[settings]
docstring-parse-literal-blocks = false

[input]
def value():
    """This::
        value
    """

[output=unchanged]
[findings]
PDF305: Line 2: Docstring summary should not start with "This"
```

## Options
- `docstring-convention`: Ignores PDF305 for broad rule selections under the Google and PEP 257 conventions.
- `docstring-parse-*`: Controls whether generic structures such as headings, lists, doctests, code fences, block quotes, tables, directives, and literal blocks are protected from summary-style checks.
