# placeholder-docstring (PDF213)

Fix is not available.

## What it does
Checks whether a complete evaluated docstring value is one of the configured placeholder markers. The default markers are `TODO`, `TBD`, `FIXME`, `pass`, `XXX`, `HACK`, `NotImplemented`, and `...`.

Word markers match ASCII case-insensitively after surrounding whitespace is removed. They may have a trailing run of periods, colons, semicolons, exclamation marks, or question marks, but may not contain additional words. The ellipsis marker matches only exact `...`.

Configured word markers must begin with an ASCII letter and may otherwise contain ASCII letters, digits, hyphens, and underscores. Changing the marker list replaces the defaults rather than extending them.

PDF213 checks primary module, class, function, and method docstrings plus supported attached module, class, and instance attribute docstrings. Matching uses the evaluated docstring value, so escape sequences and implicitly concatenated literals are handled as one value. Findings cover every physical line occupied by the complete literal.

## Why is this useful?
A placeholder satisfies Python's docstring syntax without supplying useful documentation. Reporting exact whole-docstring markers identifies unfinished documentation without flagging real prose that happens to mention a task marker.

## Ruff compatibility
PDF213 is related to Ruff's `D419`, which reports empty docstrings. Ruff does not report nonempty placeholder docstrings.

## Examples
PDF213 reports a configured marker with terminal punctuation:

```pydocfmt-example
[settings]
docstring-placeholder-markers = ["TODO", "NotImplemented", "..."]

[input]
def load():
    """TODO."""

[output=unchanged]
[findings]
PDF213: Line 2: Docstring is a placeholder
```

Additional prose prevents a match:

```pydocfmt-example
[settings]
docstring-placeholder-markers = ["TODO", "NotImplemented", "..."]

[input]
def load():
    """TODO: Describe retry behavior."""

[output=unchanged]
```

The marker inventory is configurable and matching preserves conventional configured spelling:

```pydocfmt-example
[settings]
docstring-placeholder-markers = ["WorkInProgress"]

[input]
def load():
    """workinprogress!"""

[output=unchanged]
[findings]
PDF213: Line 2: Docstring is a placeholder
```

Evaluated concatenated values are matched as one docstring, and the finding covers the complete expression:

```pydocfmt-example
[settings]
docstring-placeholder-markers = ["TODO"]

[input]
def load():
    ("TO"
     "DO!")

[output=unchanged]
[findings]
PDF213: Lines 2-3: Docstring is a placeholder
```

Supported attached attribute docstrings are checked as well:

```pydocfmt-example
[settings]
docstring-placeholder-markers = ["TODO"]

[input]
class Client:
    timeout = 30
    """TODO"""

[output=unchanged]
[findings]
PDF213: Line 3: Docstring is a placeholder
```

An empty marker inventory keeps the rule selectable but suppresses all placeholder findings:

```pydocfmt-example
[settings]
docstring-placeholder-markers = []

[input]
def load():
    """TODO"""

[output=unchanged]
```

## Options
- `docstring-placeholder-markers`: Configure the whole-docstring marker labels recognized as placeholders. An empty list suppresses findings without changing rule selection.
