# Checking

`pydocfmt check` reports formatting and documentation findings without changing files:

```bash
pydocfmt check
```

By default, pydocformatter discovers Python and Markdown files below the current directory using the configured include, exclude, gitignore, and force-exclude settings. In Markdown it checks supported `python`, `py`, and `python3` fenced blocks and reports diagnostics at their containing-file line numbers. The built-in Markdown extension is `.md`; additional extensions can be mapped explicitly. See [Markdown source](reference/markdown-source.md) for exact assignment, raw-line fence scope, and error behavior.

## Persistent cache

Selected disk files use persistent clean-proof caching by default. A warm proof is accepted only after the complete current file contents and all analysis semantics match, then pydocformatter skips parsing and rule execution. Disable it with `--no-cache`, choose a location with `--cache-dir PATH`, or print internal counters to stderr with `--cache-stats`.

The default `.pydocfmt_cache` directory contains hashes and metadata only. pydocformatter may create the configured cache directory, but its immediate parent must already exist as a directory. Otherwise it emits one warning and runs uncached without changing findings, fixes, or status. Run `pydocfmt clean` or `pydocfmt clean --cache-dir PATH` to remove verified pydocfmt-owned cache data. Cache writes, recovery, and cleanup are serialized with a retained native lock, and lookup or mutation never trusts a missing or symlinked ownership tag. See [Persistent cache](reference/cache.md) for invalidation, population, storage, cleanup, failure handling, trust, statistics, and performance details.

## Diagnostics

Diagnostics are grouped by file and include the rule code, affected line numbers, and message. Use `--output-file` to write diagnostics to a file:

```bash
pydocfmt check src --output-file pydocfmt.txt
```

## Exit codes and CI

`pydocfmt check` uses the following process statuses:

| Status | Meaning                                                                                                                                                       |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0`    | The command completed successfully with no remaining findings or processing errors. Fix mode may have changed files unless `--exit-non-zero-on-fix` was used. |
| `1`    | Findings or run-time processing errors remain, `--diff` found changes to preview, or `--fix --exit-non-zero-on-fix` changed files.                            |
| `2`    | The command could not start or complete its setup because of an invalid invocation, invalid configuration, file-selection failure, or output error.           |

The default read-only command is therefore suitable for CI:

```bash
pydocfmt check
```

Use `--exit-zero` for an advisory run that should report status-`1` findings, processing errors, or preview changes without failing the caller:

```bash
pydocfmt check --exit-zero
```

This option does not convert an invalid invocation or another status-`2` setup failure into success. It is mutually exclusive with `--exit-non-zero-on-fix`.

Fix mode normally returns `0` after it changes files when no findings or processing errors remain. Use the following form when a local automation should fail after making changes so that the caller reruns or stages them explicitly:

```bash
pydocfmt check --fix --exit-non-zero-on-fix
```

## Diff preview

`--diff` shows automatic fixes as a unified diff without writing files:

```bash
pydocfmt check --diff
```

It returns `1` when the diff is nonempty, even if applying those changes would resolve every finding. This makes `--diff` useful as a non-writing preview gate, while plain `pydocfmt check` remains the simplest enforcement command. See [Integrations](integrations.md) for copy-paste pre-commit and GitHub Actions configurations.

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
    # pydocfmt: ignore[summary-trailing-period]
    """Return a generated value"""
```

See [Rule suppressions](reference/rule-suppressions.md) for supported suppression forms.

## File preview

Use `--show-files` to inspect discovery decisions without formatting files:

```bash
pydocfmt check --show-files
```
