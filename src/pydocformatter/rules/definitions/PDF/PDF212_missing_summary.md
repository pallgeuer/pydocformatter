# missing-summary (PDF212)

Fix is not available.

## What it does
Checks nonempty docstrings that do not begin with a parsed top-level summary. It emits one finding for each affected docstring and does not modify the source.

The rule covers every primary docstring collected for a module, class, function, or method. It also covers supported PEP 258-style attribute docstrings attached to module variables, class variables, and instance attributes assigned in `__init__`. Additional string expressions and strings in unsupported attachment positions, such as a local variable or an instance attribute assigned in an ordinary method, are not docstrings and are not checked.

A summary must be the first nonblank top-level semantic block. A leading convention section or reStructuredText field is documentation body structure, not an owner summary. The same is true of enabled generic structures such as lists, headings, doctests, fenced code, block quotes, tables, directives, literal blocks, and indented verbatim blocks. Later prose is not promoted to a summary after one of these structures, even if it reads like a summary.

A lone colon-ended line is treated as a compact summary. Once another nonblank block follows it, however, it is a structural colon header rather than a summary. Empty and whitespace-only docstrings are deliberately excluded because `PDF202` reports them; absent docstrings are handled by the applicable `PDF6xx` presence rules.

PDF212 uses the semantic block tree prepared for the selected `docstring-convention` and `docstring-parse-*` settings. It neither guesses a different convention nor independently recognizes disabled structures. Disabling a parser can therefore expose its source text as ordinary summary prose, although another enabled parser can still classify the same text structurally. Malformed convention syntax can likewise be ordinary prose if neither the convention parser nor a generic parser recognizes it.

The diagnostic covers all physical source lines occupied by the docstring's string tokens and interstitial lines, including comments inside a concatenated string expression. Delimiter-only parenthesis lines are not included. A local suppression immediately before the line that begins the first string token or an inline suppression after any component string token can suppress the whole finding. A local suppression before a delimiter-only opening-parenthesis line and a standalone suppression between concatenated string tokens do not suppress the finding, even though the interstitial comment line remains part of the diagnostic span.

## Why is this useful?
A nonempty docstring can still omit the short opening description that tells readers what its owner represents or does. Reporting that omission distinguishes structurally incomplete documentation from an empty docstring.

## Ruff compatibility
No Ruff rule directly checks this condition. Ruff's `D419` is replaced by `PDF202`, which reports empty docstrings, while Ruff's summary-style rules check wording only after a summary exists.

## Examples
A Google-style parameter section without an opening summary is reported but not changed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def scale(value: float) -> float:
    """Args:
        value: Value to scale.
    """

[output=unchanged]
[findings]
PDF212: Lines 2-4: Docstring is missing a summary
```

An opening summary satisfies the rule:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def scale(value: float) -> float:
    """Scale a value.

    Args:
        value: Value to scale.
    """

[output=unchanged]
```

Leading generic structures and prose that follows them do not supply an owner summary:

```pydocfmt-example
[input]
def choices() -> tuple[str, ...]:
    """- `fast`
    - `safe`

    Return the supported choices.
    """

[output=unchanged]
[findings]
PDF212: Lines 2-6: Docstring is missing a summary
```

Convention selection controls whether convention-specific syntax is structural. A reStructuredText field is ordinary opening prose under the PEP 257 parser:

```pydocfmt-example
[settings]
docstring-convention = "pep257"

[input]
def scale(value: float) -> float:
    """:param value: Value to scale."""

[output=unchanged]
```

Supported attached attribute docstrings use the same summary definition as primary docstrings:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    timeout = 30
    """Notes:
        Used for every request.
    """

[output=unchanged]
[findings]
PDF212: Lines 3-5: Docstring is missing a summary
```

A single colon-ended line is accepted as a compact summary, while empty docstrings remain the responsibility of PDF202:

```pydocfmt-example
[input]
def label() -> str:
    """Result:"""


def pending() -> None:
    """   """

[output=unchanged]
```

Parser settings participate in summary detection. With list parsing disabled, the list-like text is ordinary opening prose and satisfies PDF212:

```pydocfmt-example
[settings]
docstring-parse-list-items = false

[input]
def mode() -> str:
    """- fast"""

[output=unchanged]
```

For concatenated docstrings, the finding spans the string tokens and the interstitial source between them:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def scale(value: float) -> float:
    ("Args:\n"
     # Keep the parameter description beside its heading.
     "    value: Value to scale.")

[output=unchanged]
[findings]
PDF212: Lines 2-4: Docstring is missing a summary
```

## Options
None.
