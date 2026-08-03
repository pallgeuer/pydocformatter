# malformed-rest-directive-introducer (PDF418)

Fix is not available.

## What it does

Checks high-confidence reStructuredText directive introducers that end with exactly one colon instead of the required two. PDF418 always recognizes the current Sphinx version directives `version-added`, `version-changed`, `version-deprecated`, and `version-removed` together with the retained aliases `versionadded`, `versionchanged`, `deprecated`, and `versionremoved`, case-insensitively. It also recognizes every namespaced directive type containing `:`. Other syntactically valid directive names are reported only when the next nonblank line is more indented and therefore supplies structural evidence of a directive body. This conservative boundary avoids treating arbitrary `.. name: prose` lines as directives.

Directive types use one or more Unicode word-character components separated by isolated `-`, `_`, `+`, `.`, or `:` characters; a component cannot start or end with a separator. One optional ASCII space may separate the directive name from either the valid `::` delimiter or malformed `:` delimiter. Both delimiters must be followed by an ASCII space, tab, or the end of the logical line. Consequently, `.. note::text` and `.. note:text` are ordinary text rather than directive openers.

Malformed directive blocks are protected from docstring reflow and other nested convention parsing even when PDF418 is not selected. The parser records them in primary and attached attribute docstrings whenever `docstring-parse-directives` is enabled. PDF418 is diagnostic-only because inserting a colon can change rendered documentation semantics and should remain an explicit author decision.

## Why is this useful?

A missing colon prevents reStructuredText and Sphinx from interpreting the directive, which can silently turn admonitions, version notices, and domain objects into ordinary prose.

## Ruff compatibility

Ruff has no direct equivalent.

## Examples

A version directive with one trailing colon is reported without being rewritten:

```pydocfmt-example
[settings]
docstring-parse-directives = true

[input]
def connect():
    """Open a connection.

    .. version-added : 1.0
    """

[output=unchanged]
[findings]
PDF418: Line 4: reStructuredText directive 'version-added' must be followed by two colons
```

An arbitrary directive name is reported when an indented body establishes its structural intent:

```pydocfmt-example
[settings]
docstring-parse-directives = true

[input]
def connect():
    """Open a connection.

    .. caution:
        The caller owns the returned connection.
    """

[output=unchanged]
[findings]
PDF418: Line 4: reStructuredText directive 'caution' must be followed by two colons
```

A valid namespaced directive remains unchanged:

```pydocfmt-example
[settings]
docstring-parse-directives = true

[input]
def connect():
    """Open a connection.

    .. py:function :: connect()
    """

[output=unchanged]
```

An arbitrary one-colon name without an indented body remains ordinary prose and is not reported:

```pydocfmt-example
[input]
def connect():
    """Open a connection.

    .. caution: ordinary explanatory text
    """

[output=unchanged]
```

Disabling directive parsing disables both malformed-directive protection and PDF418 selection:

```pydocfmt-example
[settings]
docstring-parse-directives = false

[input]
def connect():
    """Open a connection.

    .. versionadded: 1.0
    """

[output=unchanged]
```

## Options

- `docstring-parse-directives`: Enables directive parsing and this diagnostic; setting it to `false` disables PDF418.
