# Rule suppressions

This document specifies how pydocfmt source comments suppress pydocformatter rule findings and automatic fixes. Suppression payloads use pydocformatter rule selectors such as `PDF101`, `PDF`, `PCF001`, `PCF`, and `ALL`.

Rule suppression directives in source code filter both check findings and automatic fixes. A suppressed finding is not reported, and a suppressed fix is not applied.

## `# noqa`

Bare `# noqa` follows the conventional same-line shape used by Python tooling. It suppresses pydocfmt findings on the physical line where it appears. For PDF findings, an inline comment after any string token in a docstring expression covers the complete expression, including when more implicitly concatenated tokens follow on later lines. PCF findings remain line-local. Ordinary string expressions do not receive complete-expression PDF coverage, so directives on them retain normal same-line behavior.

Blanket `# noqa` is not audited by `PCF006`:

```pydocfmt-example
[settings]
select = ["PCF002", "PCF006"]

[input]
value = compute() # noqa

[output=unchanged]
```

Explicit `# noqa: ...` payloads suppress known pydocformatter selectors in the payload. Foreign codes are ignored by pydocfmt:

```pydocfmt-example
[settings]
select = ["PDF101", "PCF006"]
line-length = 48

[input]
"""This is a long module summary that needs wrapping into more than one physical line."""  # noqa: F401, PDF101

[output=unchanged]
```

Foreign-only `# noqa` payloads do not suppress pydocfmt findings:

```pydocfmt-example
[settings]
select = ["PDF101"]
line-length = 48

[input]
"""This is a long module summary that needs wrapping into more than one physical line."""  # noqa: F401

[output]
"""This is a long module summary that needs
wrapping into more than one physical line."""  # noqa: F401
```

A standalone `# noqa` above a docstring is still line-local. It does not attach to the following docstring:

```pydocfmt-example
[settings]
select = ["PDF101"]
line-length = 48

[input]
# noqa: PDF101
"""This is a long module summary that needs wrapping into more than one physical line."""

[output]
# noqa: PDF101
"""This is a long module summary that needs
wrapping into more than one physical line."""
```

Malformed or non-conventional `#noqa` comments are not source suppressions until `PCF003` normalizes them. In one fixing run, later rules still see the original source state, so a normalized directive suppresses later runs, not earlier findings in the same pass:

```pydocfmt-example
[settings]
select = ["PCF002", "PCF003"]

[input]
value = compute()#noqa

[output]
value = compute()  # noqa
```

## File-level `# pydocfmt`

Standalone `# pydocfmt: noqa` suppresses all pydocfmt findings in the file:

```pydocfmt-example
[settings]
select = ["PDF101", "PCF002", "PCF006"]
line-length = 48

[input]
# pydocfmt: noqa
def function():
    """This is a long summary that needs wrapping into more than one physical line."""

value = 1 # trailing

[output=unchanged]
```

Standalone `# pydocfmt: noqa: ...` and `# pydocfmt: file-ignore[...]` suppress matching selectors for the whole file, regardless of where the directive appears:

```pydocfmt-example
[settings]
select = ["PDF101", "PCF006"]
line-length = 48

[input]
def first():
    """This is a long summary that needs wrapping into more than one physical line."""

# pydocfmt: noqa: PDF101

def second():
    """This is another long summary that needs wrapping into more than one physical line."""

[output=unchanged]
```

Prefix selectors match all rules under that prefix:

```pydocfmt-example
[settings]
select = ["PDF101", "PDF104", "PCF006"]
line-length = 48

[input]
# pydocfmt: file-ignore[PDF]
def function():
    """   This is a long summary that needs wrapping into more than one physical line."""

[output=unchanged]
```

## Local `# pydocfmt: ignore[...]`

Standalone `# pydocfmt: ignore[...]` attaches to the immediately following physical line. For docstrings, the target is the following docstring expression when that line begins its first string token. A delimiter-only opening-parenthesis line does not attach the directive to string tokens on later lines. An attached directive also suppresses diagnostics semantically owned by that docstring, even when the diagnostic is reported on a signature or body line:

```pydocfmt-example
[settings]
select = ["PDF101", "PCF006"]
line-length = 48

[input]
def generated_function():
    # pydocfmt: ignore[PDF101]
    """This is a long generated summary that needs to stay on one physical source line."""

[output=unchanged]
```

```pydocfmt-example
[settings]
select = ["PDF502", "PCF006"]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def generated_function():
    # pydocfmt: ignore[PDF502]
    """Return a generated value."""
    return 1

[output=unchanged]
```

Adjacent local directives share one following target:

```pydocfmt-example
[settings]
select = ["PDF101", "PDF104", "PCF006"]
line-length = 48

[input]
def generated_function():
    # pydocfmt: ignore[PDF101]
    # pydocfmt: ignore[PDF104]
    """   This is a long generated summary that needs to stay on one physical source line."""

[output=unchanged]
```

For standalone comments, the target is the following contiguous standalone comment run:

```pydocfmt-example
[settings]
select = ["PCF001", "PCF006"]
line-length = 42

[input]
# pydocfmt: ignore[PCF001]
# This generated comment needs to stay exactly as emitted by the schema exporter.
# It is part of the same generated comment block.

[output=unchanged]
```

The comment target stops at blank lines, indentation changes, protected comments, and empty or hash-only comments. Here the local directive suppresses only the first comment run, so the later run is still formatted:

```pydocfmt-example
[settings]
select = ["PCF001"]
line-length = 42

[input]
# pydocfmt: ignore[PCF001]
# This generated comment needs to stay exactly as emitted by the schema exporter.

# This ordinary comment can still be wrapped by pydocfmt because it is a new run.

[output]
# pydocfmt: ignore[PCF001]
# This generated comment needs to stay exactly as emitted by the schema exporter.

# This ordinary comment can still be
# wrapped by pydocfmt because it is a new
# run.
```

For trailing comments, the target is the following physical line's trailing comment. This is the usual way to keep an explanatory trailing comment inline when `PCF004` would otherwise extract it:

```pydocfmt-example
[settings]
select = ["PCF004", "PCF006"]
line-length = 44

[input]
# pydocfmt: ignore[PCF004]
total = calculate_total(order)  # Generated field copy must stay near the assignment for the importer.

[output=unchanged]
```

Inline `# pydocfmt: ignore[...]` suppresses findings on its own physical line. For PDF findings, placing it after any component string token covers the complete implicitly concatenated docstring expression. The expression must be a recognized primary or supported attached attribute docstring; ordinary string expressions do not gain expanded coverage. This does not expand PCF coverage, and a standalone directive between string tokens remains line-local:

```pydocfmt-example
[settings]
select = ["PDF101", "PCF006"]
line-length = 48

[input]
"""This generated module summary must stay on one physical source line for the external checksum."""  # pydocfmt: ignore[PDF101] because generated

[output=unchanged]
```

The same whole-expression coverage applies before the final component token:

```pydocfmt-example
[settings]
select = ["PDF202", "PCF006"]

[input]
def generated_function():
    (""  # pydocfmt: ignore[PDF202]
     " ")

[output=unchanged]
```

## Selectors and audit behavior

Selector text is matched case-insensitively after directive normalization. Valid selector prefixes such as `PDF` and `PCF` match all selected rules under that prefix. `ALL` matches all selected pydocformatter rules.

`PCF006` audits pydocfmt directives and known explicit pydocformatter selectors in `# noqa: ...`. It does not audit blanket `# noqa`, foreign `# noqa` codes, or selectors for pydocformatter rules that are not selected in the current run.

An unused pydocfmt selector is reported when both `PCF006` and the targeted rule are selected:

```pydocfmt-example
[settings]
select = ["PCF001", "PCF006"]

[input]
# pydocfmt: ignore[PCF001]
# Short comment.

[output=unchanged]
[findings]
PCF006: Line 1: Suppression selector 'PCF001' did not suppress any findings
```

Each selector in a list is evaluated independently:

```pydocfmt-example
[settings]
select = ["PCF001", "PCF002", "PCF006"]
line-length = 42

[input]
# pydocfmt: ignore[PCF001, PCF002]
# This generated comment needs to stay exactly as emitted by the schema exporter.

[output=unchanged]
[findings]
PCF006: Line 1: Suppression selector 'PCF002' did not suppress any findings
```

Selectors for rules that are disabled in the current run are not reported as unused:

```pydocfmt-example
[settings]
select = ["PCF006"]
line-length = 48

[input]
# pydocfmt: ignore[PDF101]
"""This is a long module summary that needs wrapping into more than one physical line."""

[output=unchanged]
```

Known pydocformatter selectors in `# noqa: ...` are audited when explicit and unused:

```pydocfmt-example
[settings]
select = ["PCF002", "PCF006"]

[input]
value = compute()  # noqa: F401, PCF002

[output=unchanged]
[findings]
PCF006: Line 1: Suppression selector 'PCF002' did not suppress any findings
```

Invalid or unknown pydocfmt selector payloads are reported by `PCF006`:

```pydocfmt-example
[settings]
select = ["PCF006"]

[input]
# pydocfmt: ignore[not-a-rule]
# Short comment.

[output=unchanged]
[findings]
PCF006: Line 1: Invalid pydocfmt suppression selector 'NOT-A-RULE'
```

`PCF006` can itself be suppressed:

```pydocfmt-example
[settings]
select = ["PCF006"]

[input]
# pydocfmt: file-ignore[PCF006]
# pydocfmt: ignore[]
# Short comment.

[output=unchanged]
```

Unsupported range-style pydocfmt comments are protected comments, but they are not suppression directives:

```pydocfmt-example
[settings]
select = ["PDF101"]
line-length = 48

[input]
# pydocfmt: disable[PDF101]
"""This is a long module summary that needs wrapping into more than one physical line."""
# pydocfmt: enable[PDF101]

[output]
# pydocfmt: disable[PDF101]
"""This is a long module summary that needs
wrapping into more than one physical line."""
# pydocfmt: enable[PDF101]
```

## Suppressed fixes

Suppression filtering is per finding, not per rule. A local directive can suppress one occurrence of a rule while another occurrence is still fixed:

```pydocfmt-example
[settings]
select = ["PCF002", "PCF006"]

[input]
# pydocfmt: ignore[PCF002]
first = 1 # generated spacing
second = 2 # ordinary spacing

[output]
# pydocfmt: ignore[PCF002]
first = 1 # generated spacing
second = 2  # ordinary spacing
```
