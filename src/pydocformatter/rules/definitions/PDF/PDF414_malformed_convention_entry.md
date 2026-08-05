# malformed-convention-entry (PDF414)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
PDF414 reports high-confidence malformed entry syntax for the configured Google, NumPy, or reStructuredText convention:

- For Google sections, it detects an empty or unbalanced parenthesized type, an unbalanced method signature, and a missing colon between an entry head and its description. Unbalanced method signatures require the name to match a direct method of the documented class. Parameter, attribute, and other method candidates can be confirmed from the complete owning function or class inventory, including proven literal slot members, while a closed, balanced parenthesized head is also strong entry evidence and may contain nested parentheses, brackets, braces, or quoted delimiters. Exception entries can be recognized from one or more comma- or pipe-separated qualified names whose final components end in `Error`, `Exception`, or `Warning`.
- For NumPy sections, it detects an unbalanced method signature, a colon with no following type, and a missing colon between one or more entry names and a conservative type expression. Every check requires all recovered names to match the relevant parameter, attribute, or direct method inventory; proven literal slot members participate in the class attribute inventory. Type candidates are validated with an iterative token grammar before any general Python expression parsing, including for deeply nested candidates. Top-level line breaks are rejected, while line breaks inside brackets or parentheses and explicit backslash continuations remain valid.
- For reStructuredText fields, it detects a missing closing colon on a standard field name when the remaining text matches the field's expected arity. Named parameter, exception, and attribute fields require a credible first argument; exception arguments must use a conventional exception suffix. Owner-wide fields are reported only when no trailing text follows the field name. The rule also requires arguments on complete parameter, exception, and attribute fields and rejects arguments on complete owner-wide return fields. Yield fields intentionally allow both named and owner-wide forms. A parameter delimiter is repaired only after exactly one name in the malformed syntactic head matches the owning signature; any preceding inline type must be a complete conservative type expression, and owner names found only after non-type prose never select a repair location. Attribute delimiters require exactly one owner attribute match in the first head token because standard reStructuredText attribute fields do not support the same inline type form. Complete comma- or pipe-separated exception-name lists are repaired after the final name. Zero or multiple owner matches remain diagnostic-only.

The rule follows only the configured convention. It does not reinterpret syntax belonging to another convention. Candidates inside parser-recognized protected structures, such as code fences, doctests, directives, literal blocks, and list items, remain part of those structures rather than convention entries.

Malformed Google and NumPy candidates are reported only when their names or syntax provide strong evidence that they are intended entries. Ordinary prose and weak, unknown names are left alone. A malformed entry remains structural section or field content but is excluded from the semantic entry inventory, so it cannot incorrectly satisfy parameter, return, or exception documentation checks. Diagnosed lines are also excluded from PDF101 prose reflow, preventing an unrelated formatting fix from merging or rewriting uncertain entry syntax.

PDF414 inserts a missing Google or NumPy separator and closes a uniquely proven reStructuredText field head when the exact source span is safely mapped. Missing content, ambiguous field heads, required or unexpected field arguments, and unbalanced delimiters remain diagnostic because repairing them would require guessing.

## Why is this useful?
Malformed entries can silently disappear from generated documentation and semantic validation. A single missing colon can make real parameter documentation look like prose, while an invalid field argument can falsely appear to document an owner-wide value. Reporting only high-confidence defects exposes these mistakes without imposing convention grammar on unrelated narrative text.

## Ruff compatibility
None.

## Examples
PDF414 reports malformed Google parameter syntax:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert(value):
    """Convert a value.

    Args:
        value (int) The value.
    """

[output]
def convert(value):
    """Convert a value.

    Args:
        value (int): The value.
    """
```

PDF414 reports an explicitly empty Google type without rewriting it as an untyped entry:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert(value):
    """Convert a value.

    Args:
        value (  ): The value.
    """

[output=unchanged]
[findings]
PDF414: Line 5: Google docstring entry 'value' is missing its type inside parentheses
```

PDF414 can report distinct Google defects in the same docstring. Complete exception lists are retained in the finding:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def collect(value):
    """Collect a value.

    Args:
        value (list[str]: Value to collect.

    Raises:
        ValueError | pkg.CustomError Collection failed.
    """

[output]
def collect(value):
    """Collect a value.

    Args:
        value (list[str]: Value to collect.

    Raises:
        ValueError | pkg.CustomError: Collection failed.
    """

[findings]
PDF414: Line 5: Google docstring entry 'value' has an unbalanced parenthesized type
```

Method signatures are diagnosed separately from Google parenthesized types:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Coordinate operations.

    Methods:
        run(value: tuple[int, str]:
    """

    def run(self):
        pass

[output=unchanged]
[findings]
PDF414: Line 5: Google docstring method entry 'run' has an unbalanced signature
```

PDF414 reports both a missing NumPy separator and an explicitly empty type. Multi-name entries are diagnosed as one entry:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def combine(first, second):
    """Combine values.

    Parameters
    ----------
    first tuple[int, int]
    second :
    """

[output]
def combine(first, second):
    """Combine values.

    Parameters
    ----------
    first: tuple[int, int]
    second :
    """

[findings]
PDF414: Line 7: NumPy docstring entry 'second' is missing its type after the colon
```

PDF414 applies the argument contract only to standard reStructuredText fields. The named `yield` field in this example is valid:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def convert(value):
    """Convert a value.

    :param list[int] value Input data.
    :raises ValueError, TypeError Invalid data.
    :type: int
    :returns result: The result.
    :yield item: A later value.
    """

[output]
def convert(value):
    """Convert a value.

    :param list[int] value: Input data.
    :raises ValueError, TypeError: Invalid data.
    :type: int
    :returns result: The result.
    :yield item: A later value.
    """

[findings]
PDF414: Line 6: reST field ':type:' is missing its required argument
PDF414: Line 7: reST field ':returns:' has an unexpected argument
```

When more than one signature parameter appears in a malformed head, PDF414 reports the field without guessing where its argument ends:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def combine(first, second):
    """Combine values.

    :param first second Ambiguous description.
    """

[output=unchanged]
[findings]
PDF414: Line 4: reST field ':param:' is missing its closing colon
```

Weak entry-like prose is not enough to trigger PDF414. Here, `unknown` is not a function parameter and `Problem` is not a conventionally named exception:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def convert(value):
    """Convert a value.

    Args:
        unrelated prose about conversion.
        unknown (int: Ambiguous unknown text.

    Raises:
        Problem Ambiguous failure text.
    """

[output=unchanged]
```

Proven literal slot members supply the same class-attribute confidence as real assignments. Unknown prose-like names remain unreported:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Point:
    """Point.

    Attributes
    ----------
    x float
    stale int
    """

    __slots__ = ("x",)

[output]
class Point:
    """Point.

    Attributes
    ----------
    x: float
    stale int
    """

    __slots__ = ("x",)
```

## Options
None.
