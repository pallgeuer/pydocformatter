# property-docstring-starts-with-verb (PDF311)

Fix is not available.

## What it does
Checks property-like method docstring summaries whose first summary word is one of the verbs that usually describe a function action: `return`, `returns`, `get`, `gets`, `yield`, `yields`, `fetch`, `fetches`, `retrieve`, or `retrieves`.

The first summary word is normalized by removing non-alphanumeric characters and lowercasing before it is compared with the disallowed verb list. This catches forms such as `Returns`, `returns`, `"Returns"`, and `Returns:`.

PDF311 uses the parsed top-level summary block. It skips non-property functions, test functions named `runTest` or starting with `test`, empty docstrings, docstrings without a parsed summary, and parser-recognized structures such as sections, reST fields under the reST convention, headings, lists, doctests, code fences, block quotes, tables, directives, literal blocks, and verbatim blocks.

Property-like functions are functions decorated by a name listed in `docstring-property-decorators`, direct calls to one of those names, or accessor decorators whose final dotted component is `getter`, `setter`, or `deleter`. Dotted configured names also match import aliases and builtins resolved statically by LibCST; unqualified configured names are syntactic-only. Accessor decorators remain property-like even when the configured name list is empty.

## Why is this useful?
Property docstrings usually read better as data descriptions than as function actions. For example, `The configured timeout.` describes the attribute-like value more directly than `Returns the configured timeout.`

## Ruff compatibility
This rule replaces Ruff's `D421`. Like Ruff, it checks property-like function docstrings for a small fixed verb list and supports configured property decorators. Unlike Ruff, pydocformatter uses its parsed summary target, so parser-recognized non-summary structures are protected. PDF311 also follows pydocformatter's test-function carve-out and skips property functions named `runTest` or starting with `test`; Ruff D421 can still report those property docstrings.

## Examples
PDF311 reports property docstrings that start with disallowed verbs:

```pydocfmt-example
[input]
class Client:
    @property
    def endpoint(self):
        """Returns the configured endpoint."""

[output=unchanged]
[findings]
PDF311: Line 4: Property docstring first word 'Returns' should not be a verb
```

Property docstrings with attribute-style summaries are accepted:

```pydocfmt-example
[input]
class Client:
    @property
    def endpoint(self):
        """The configured endpoint."""

[output=unchanged]
```

The disallowed verb comparison is intentionally narrow. It catches the configured verb spellings after simple normalization, but accepts other first words:

```pydocfmt-example
[input]
class Client:
    @property
    def endpoint(self):
        """'Returns' the configured endpoint."""

    @property
    def timeout(self):
        """Fetch status."""

    @property
    def label(self):
        """Getter display label."""

[output=unchanged]
[findings]
PDF311: Line 4: Property docstring first word 'Returns' should not be a verb
PDF311: Line 8: Property docstring first word 'Fetch' should not be a verb
```

Configured property decorators unwrap direct calls and can match import aliases for dotted configured names. Accessor decorators are always property-like:

```pydocfmt-example
[settings]
docstring-property-decorators = ["project.Property"]

[input]
class Client:
    @property
    def builtin(self):
        """Returns builtin property value."""

    @project.Property(read_only=True)
    def endpoint(self):
        """Gets the configured endpoint."""

    @endpoint.getter
    def endpoint(self):
        """Returns the accessor endpoint."""

[output=unchanged]
[findings]
PDF311: Line 8: Property docstring first word 'Gets' should not be a verb
PDF311: Line 12: Property docstring first word 'Returns' should not be a verb
```

Static decorator names that look similar to property decorators are not treated as properties unless they are configured exactly:

```pydocfmt-example
[input]
class Client:
    @project.property
    def endpoint(self):
        """Returns the configured endpoint."""

[output=unchanged]
```

Test-like property functions and non-property functions are skipped:

```pydocfmt-example
[input]
class Client:
    @property
    def test_endpoint(self):
        """Returns a test endpoint."""

    @property
    def runTest(self):
        """Returns a unittest endpoint."""

    def endpoint(self):
        """Returns the configured endpoint."""

[output=unchanged]
```

Parser-recognized structures are protected. Disabling the matching parser setting can make the same text become a summary target:

```pydocfmt-example
[settings]
docstring-parse-headings = false

[input]
class Client:
    @property
    def heading(self):
        """Returns
        =======
        """

[output=unchanged]
[findings]
PDF311: Line 4: Property docstring first word 'Returns' should not be a verb
```

The active convention controls which convention-specific structures are protected. reStructuredText fields are not summaries under the reST convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    @property
    def endpoint(self):
        """:returns: configured endpoint"""

[output=unchanged]
```

## Options
- `docstring-property-decorators`: Function decorator names that make PDF311 treat a function as property-like. Calls are unwrapped before matching, dotted names also match import aliases and builtins resolved statically by LibCST, and unqualified names are syntactic-only.
