# Checking

`pydocfmt check` reports formatting and documentation findings without changing files:

```bash
pydocfmt check
```

By default, pydocformatter discovers Python files below the current directory using the configured include, exclude, gitignore, and force-exclude settings.

## Diagnostics

Diagnostics are grouped by file and include the rule code, affected line numbers, and message. Use `--output-file` to write diagnostics to a file:

```bash
pydocfmt check src --output-file pydocfmt.txt
```

## Exit codes

The command exits with a non-zero status when findings are reported or operational errors occur. Use `--exit-zero` when pydocformatter should report findings without failing the calling process:

```bash
pydocfmt check --exit-zero
```

## Diff preview

`--diff` shows automatic fixes as a unified diff without writing files:

```bash
pydocfmt check --diff
```

## Rule selection

Use selectors to enable or ignore rules:

```bash
pydocfmt check --select PDF --ignore PDF300
```

See [Rule selection](reference/rule-selection.md) for the full selector model.

## Suppressions

Source suppressions silence specific findings when a rule should not apply to a line or file:

```python
def generated_value():
    # pydocfmt: ignore[PDF300]
    """return a generated value"""
```

See [Rule suppressions](reference/rule-suppressions.md) for supported suppression forms.

## File preview

Use `--show-files` to inspect discovery decisions without formatting files:

```bash
pydocfmt check --show-files
```
