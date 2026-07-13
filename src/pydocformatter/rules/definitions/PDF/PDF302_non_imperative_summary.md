# non-imperative-summary (PDF302)

Fix is not available.

Rule is ignored if `docstring-convention` is `google`.

## What it does
Checks function and method docstring summaries whose first summary word is known to be non-imperative.

The first summary word is normalized by removing non-alphanumeric characters and lowercasing before it is compared with the known non-imperative word list. This catches forms such as `Returns`, `returns`, `"Returns"`, and `Returns:`. Unknown words are accepted rather than guessed.

PDF302 uses the parsed top-level summary block. It skips module and class docstrings, test functions named `runTest` or starting with `test`, property-like functions, empty docstrings, docstrings without a parsed summary, and parser-recognized structures such as sections, reST fields under the reST convention, headings, lists, doctests, code fences, block quotes, tables, directives, literal blocks, and verbatim blocks. With heading parsing enabled, underlined title-style content is a heading and is skipped. With heading parsing disabled, the first non-adornment summary line is checked.

## Why is this useful?
Imperative summaries are the conventional style for many Python APIs because they describe what calling the function does.

## Ruff compatibility
This rule replaces Ruff's `D401`. Like Ruff, it is ignored by default for the Google convention and skips test and property functions. pydocformatter's `docstring-property-decorators` setting controls which decorators mark functions as property-like.

## Examples
PDF302 reports non-imperative function summaries and leaves source unchanged:

```pydocfmt-example
[input]
def value():
    """Returns the value."""

[output=unchanged]
[findings]
PDF302: Line 2: Docstring summary first word 'Returns' is not imperative
```

Normalization makes capitalization and simple surrounding punctuation irrelevant:

```pydocfmt-example
[input]
def lower():
    """returns the value."""

def quoted():
    """'Returns' the value."""

[output=unchanged]
[findings]
PDF302: Line 2: Docstring summary first word 'returns' is not imperative
PDF302: Line 5: Docstring summary first word ''Returns'' is not imperative
```

Imperative summaries and unknown first words are accepted:

```pydocfmt-example
[input]
def value():
    """Return the value."""

def object_summary():
    """Widget object."""

[output=unchanged]
```

The rule applies only to non-test, non-property functions and methods:

```pydocfmt-example
[input]
"""Returns module value."""

class Value:
    """Returns class value."""

    @property
    def current(self):
        """Returns the current value."""

    def test_value(self):
        """Returns a test value."""

    def value(self):
        """Returns the stored value."""

[output=unchanged]
[findings]
PDF302: Line 14: Docstring summary first word 'Returns' is not imperative
```

The `docstring-property-decorators` setting controls which decorator names make functions property-like. Replacing the setting can make a built-in `@property` method subject to PDF302 while skipping a project-specific property decorator:

```pydocfmt-example
[settings]
docstring-property-decorators = ["project.Property"]

[input]
class Value:
    @property
    def current(self):
        """Returns the current value."""

    @project.Property
    def custom(self):
        """Returns the custom value."""

[output=unchanged]
[findings]
PDF302: Line 4: Docstring summary first word 'Returns' is not imperative
```

Parser-recognized structures are protected. Disabling the matching parser setting can make the same text become a summary target:

```pydocfmt-example
[settings]
docstring-parse-headings = false

[input]
def value():
    """Returns
    =======
    """

[output=unchanged]
[findings]
PDF302: Line 2: Docstring summary first word 'Returns' is not imperative
```

## Options
- `docstring-property-decorators`: Function decorator names that make PDF302 skip a function as property-like. Calls are unwrapped before matching, dotted names also match import aliases and builtins resolved statically by LibCST, and unqualified names are syntactic-only.
