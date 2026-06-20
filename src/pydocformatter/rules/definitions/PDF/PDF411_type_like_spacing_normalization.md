# type-like-spacing-normalization (PDF411)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF411 reports parsed convention type-like tokens whose internal spacing can be safely normalized with Python expression parsing.

The fix applies only to already parsed Google, NumPy, and rest type slots, such as parameter, attribute, method, return, and yield types, plus rest `:type:`, `:rtype:`, `:ytype:`, and typed `:param Type name:` fields. It parses the token with `ast.parse(..., mode="eval")`, accepts only conservative type-like syntax, unparses the expression, and replaces the original token only when the generated spelling reparses to the same AST and differs only by whitespace.

The rule does not normalize arbitrary prose, narrative section fields, value-field descriptions, malformed entry-like text, continuation descriptions, string forward references, calls, dicts, sets, redundant parentheses, or unsupported expressions. Exception-list separators and backticks are owned by PDF410; PDF411 does not reinterpret exception lists as type unions. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Consistent internal spacing makes type-like docstring entries easier to scan while avoiding broad semantic type parsing or surprising prose rewrites.

## Ruff compatibility
None.

## Examples
PDF411 normalizes parsed Google type slots. This is the canonical case: the rule changes internal spacing inside recognized type tokens while leaving names, descriptions, section layout, and continuation text alone.

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg (Mapping[ str, Sequence[int  ]]): Input value.
            Continuation   spacing   stays   as written.

    Returns:
        dict[ str, object ]: Result.

    Yields:
        Iterator[ tuple[str, int  ] ]: Item.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg (Mapping[str, Sequence[int]]): Input value.
            Continuation   spacing   stays   as written.

    Returns:
        dict[str, object]: Result.

    Yields:
        Iterator[tuple[str, int]]: Item.
    """
```

PDF411 also applies to NumPy type-bearing entries, including parameter, return, yield, and method entries:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg : Mapping[ str, Sequence[int  ]]
        Input value.

    Returns
    -------
    dict[ str, object ]
        Result.

    Methods
    -------
    run : Callable[[], None  ]
        Run it.
    """

[output]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg : Mapping[str, Sequence[int]]
        Input value.

    Returns
    -------
    dict[str, object]
        Result.

    Methods
    -------
    run : Callable[[], None]
        Run it.
    """
```

PDF411 normalizes rest parameter type arguments and type fields, but leaves value-field prose alone:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :param Mapping[ str, object ] arg: Input value.
    :type arg: Sequence[ int | None  ]
    :param text: Mapping[ str, object ] in prose stays unchanged.
    :rtype: dict[ str, Sequence[int  ]]
    :ytype item: Iterator[ tuple[str, int  ] ]
    """

[output]
def value(arg):
    """Return the value.

    :param Mapping[str, object] arg: Input value.
    :type arg: Sequence[int | None]
    :param text: Mapping[ str, object ] in prose stays unchanged.
    :rtype: dict[str, Sequence[int]]
    :ytype item: Iterator[tuple[str, int]]
    """
```

PDF411 can normalize nested dotted names, unions, tuple/list subscript slices, `None`, and ellipses when the spelling change is whitespace-only:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg (pkg.types.Mapping[ str, tuple[list[int], ...] | None]): Input value.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg (pkg.types.Mapping[str, tuple[list[int], ...] | None]): Input value.
    """
```

PDF411 leaves unsupported or ambiguous type-like text unchanged. This includes string forward references, calls, dict-like expressions, malformed type expressions, and top-level tuple or list expressions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg ("ForwardRef"): Input value.
        factory (Factory[int]()): Input factory.
        mapping ({str: int}): Input mapping.
        malformed (Mapping[ str): Input mapping.

    Returns:
        [ int ]: Result.
    """

[output=unchanged]
```

PDF411 also leaves AST-equivalent but non-whitespace-only rewrites unchanged. For example, it will not remove redundant parentheses or rewrite subscript parentheses even though Python's AST can represent those forms equivalently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Returns
    -------
    (int)
        Result.

    Yields
    ------
    list[(str | int)]
        Item.
    """

[output=unchanged]
```

PDF411 does not normalize narrative fields or exception-list spelling. Narrative sections and value-field prose are not type slots, and exception-list separators or backticks are owned by PDF410:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Notes:
        topic (Mapping[ str, object ]): Prose note.

    Raises:
        `ValueError` | TypeError   : Bad value.
    """

[output=unchanged]
```

Parser protection settings control whether entry-like text inside protected structures is visible to PDF411:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-parse-literal-blocks = false

[input]
def value(arg):
    """Return the value.

    Args:
        Example::

            arg (Mapping[ str, object ]): Entry-like text.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        Example::

            arg (Mapping[str, object]): Entry-like text.
    """
```

PDF411 reports unsafe source mappings without applying a fix:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Args:\n"
     "    arg (Mapping[ str, object ]): Input value.")

[output=unchanged]
[findings]
PDF411: Lines 2-4: Docstring type-like token spacing should be normalized
```

PDF411 also reports a safely parsed type slot without fixing when the evaluated docstring text cannot be mapped back to an exact source span:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg (Mapping[\x20str, object ]): Input value.
    """

[output=unchanged]
[findings]
PDF411: Lines 2-6: Docstring type-like token spacing should be normalized
```

## Options
- `docstring-convention`: Controls whether Google sections, NumPy sections, or rest fields are recognized. Ignores PDF411 when set to `none` or `pep257`.
- `docstring-parse-*`: Parser protection settings can affect whether entry-like text inside structures such as code fences and literal blocks is opaque or can be parsed as convention entries.
