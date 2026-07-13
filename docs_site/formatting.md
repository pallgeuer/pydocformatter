# Formatting

`pydocfmt check --fix` applies automatic fixes for selected rules, in addition to reporting all remaining findings (i.e. of non-auto-fixable rules or cases):

```bash
pydocfmt check --fix
```

The formatter targets docstrings and comments, and does not replace the use of a complete Python code formatter. Use pydocformatter alongside Ruff (with rule sets like `D` and `DOC` disabled) or another code formatter for expression and statement layout.

## Scope

pydocformatter can rewrite safely mapped docstring literals, standalone comments, trailing comments, directive comments, blank lines, quote placement, indentation, section spacing, and supported documentation entries.

Rules that cannot safely rewrite a finding still report diagnostics. The [Rules](rules.md) page shows fix availability for each rule.

## Safety model

Automatic fixes preserve evaluated docstring values where source rewriting would otherwise be ambiguous. pydocformatter skips fixes for docstrings that cannot be mapped back to source text safely, while still reporting the finding when the rule applies.

## Line endings and indentation

Line endings default to `auto`, which preserves the first detected line ending in each file. Indentation defaults to spaces with a width of four:

```toml
[tool.pydocfmt]
line-ending = "lf"
indent-style = "space"
indent-width = 4
```

## Formatting examples

Start with a docstring that needs summary cleanup, description wrapping, and argument description normalization:

```python
def describe_metric(name: str, value: float) -> str:
    """return a normalized metric label

    This description explains how the metric name and numeric value are combined into stable text for reports that compare multiple runs.

    Args:
        name: metric name
        value: measured value
    """
```

With `PDF101`, `PDF300`, `PDF304`, `PDF309`, and `PDF310` selected and a line length of 72, pydocformatter produces:

```python
def describe_metric(name: str, value: float) -> str:
    """Return a normalized metric label.

    This description explains how the metric name and numeric value are
    combined into stable text for reports that compare multiple runs.

    Args:
        name: Metric name.
        value: Measured value.
    """
```
