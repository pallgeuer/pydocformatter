# FAQ

## Is pydocformatter a general Python formatter?

No, pydocformatter formats Python docstrings and comments. Use it with a Python code formatter or linter such as Ruff for ordinary code layout.

## Does pydocformatter auto-detect docstring conventions?

No, set `docstring-convention` explicitly to `none`, `pep257`, `google`, `numpy`, or `rest`. Currently, it is not possible for different files of a project to specify a different docstring convention.

## Why are some rules not enabled by broad selectors?

Broad selectors such as `ALL`, `PDF`, or `PDF5` intentionally skip some rules that are policy-heavy, convention-dependent, or noisy in existing projects. There are two separate mechanisms:

- `require-explicit` keeps listed rules out of broad selections until the exact rule code is selected, for example with `select = ["PDF705"]` or `extend-select = ["PDF705"]`. Clearing or changing `require-explicit` changes which rules broad selectors can enable.
- `docstring-convention` can mark a rule as `Ignored` or `Disabled` for a convention. `Ignored` means broad selectors skip the rule under that convention, but exact rule-code selection in `select` or `extend-select` restores it. Some rules are `Ignored` for every convention, so they behave like exact-code opt-ins even though they are not controlled by `require-explicit`. `Disabled` means the rule is inapplicable for that convention and remains off even when selected exactly.

## Can pydocformatter run without configuration?

Yes, `pydocfmt check` works with defaults, and all settings can be customized on the command line. It is recommended however to configure pydocformatter statically in your `pyproject.toml` when you need project-specific selection, formatting, or file-discovery behavior.

## Why did a rule report a finding without fixing it?

Some findings are diagnostic-only. Others are fixable only when pydocformatter can prove that the source rewrite preserves the intended docstring or comment semantics.
