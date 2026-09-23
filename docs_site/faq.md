# FAQ

## Is pydocformatter a general Python formatter?

No, pydocformatter formats Python docstrings and comments. Use it with a Python code formatter or linter such as Ruff for ordinary code layout.

## Why not just use Ruff?

[Ruff](https://docs.astral.sh/ruff/) is a general Python linter and code formatter. Its formatter can optionally format Python code examples inside docstrings, and its linter includes many docstring rules. pydocformatter instead concentrates on docstring and comment prose, structured convention sections, documentation-to-signature consistency, and rule-level safe fixes. Use the tools together when those responsibilities are useful; [Docstring formatting in a Ruff project](articles/docstring-formatting-in-a-ruff-project.md) gives a practical ownership model, the [Ruff comparison](comparison.md#ruff) explains the capability boundary, and the [Ruff rule links](rules/ruff-rule-links.md) page identifies overlapping policies that should not be enabled twice.

## How is this different from docformatter?

[docformatter](https://docformatter.readthedocs.io/en/stable/) formats docstrings and exposes options for their layout and wrapping. pydocformatter also formats comments, models Google, NumPy, and reStructuredText sections and entries, checks semantic documentation relationships, and reports each issue as a selectable rule with explicit fix availability. Evaluate both tools against the policy a project needs rather than assuming their output or options are interchangeable; see the [docformatter comparison](comparison.md#docformatter) for the sourced details.

## Does pydocformatter replace pydocstyle?

Not as a blanket compatibility claim. [pydocstyle](https://pydocstyle.readthedocs.io/en/latest/) is a static checker for Python docstring conventions, while pydocformatter combines lint diagnostics with automatic docstring and comment formatting and has its own rule catalog and selection model. A project can replace overlapping checks after comparing its enabled pydocstyle rules with the [pydocformatter rules](rules.md), or keep another checker for policies it still needs. Avoid enabling equivalent rules in multiple tools unless duplicate diagnostics are intentional, and see the [pydocstyle comparison](comparison.md#pydocstyle) for more context.

## Can I use pydocformatter with Black and Ruff?

Yes. Let Black or the [Ruff formatter](https://docs.astral.sh/ruff/formatter/) own ordinary Python expression and statement layout, and let pydocformatter own the selected docstring and comment policies. Align shared settings such as line length, indentation, and line endings, then disable overlapping Ruff `D`, `DOC`, and comment rules as directed by the [Ruff rule links](rules/ruff-rule-links.md). The [canonical demonstration](demonstration.md) shows a tested Ruff-first setup, and the [Black comparison](comparison.md#black) explains the alternative.

## How does pydocformatter compare with pydoclint?

[pydoclint](https://jsh9.github.io/pydoclint/) focuses on checking whether structured argument, return, yield, exception, and attribute documentation matches signatures or implementation. pydocformatter covers many related relationships while also formatting docstring and comment source and attaching safe fixes to individual rules. The [pydoclint comparison](comparison.md#pydoclint) describes the overlap and the reasons to avoid duplicate checks.

## Does pydocformatter support Google, NumPy, and reStructuredText docstrings?

Yes. Set `docstring-convention` to `google`, `numpy`, or `rest`; `pep257` and convention-neutral `none` modes are also available. Convention selection controls how structured sections, fields, entries, and applicable rules are interpreted.

## Will pydocformatter modify code examples or directives inside docstrings?

Recognized doctests, fenced code blocks, directives, literal blocks, and other protected structures are boundaries for prose reflow, so their contents are not treated as ordinary paragraphs. Selected rules may still normalize the surrounding docstring source and structure. Preview the exact result with `pydocfmt check --diff`, and see [Formatting](formatting.md) for the safety model and supported formatting scope.

## Which fixes are safe to run automatically in CI?

`pydocfmt check --fix` applies only fixes exposed by selected, effectively fixable rules and skips cases where the required rewrite cannot be established safely. Projects can narrow that set with `fixable`, `unfixable`, and their extension settings. Because formatting intentionally changes documentation whitespace and policy choices still belong to the project, the recommended CI command is the read-only `pydocfmt check`; apply reviewed fixes locally or use `--diff` as a non-writing preview. See [Exit codes and CI](checking.md#exit-codes-and-ci) and [Rule selection](reference/rule-selection.md).

## Does pydocformatter auto-detect docstring conventions?

No, set `docstring-convention` explicitly to `none`, `pep257`, `google`, `numpy`, or `rest`. Currently, it is not possible for different files of a project to specify a different docstring convention.

## Why are some rules not enabled by broad selectors?

Broad selectors such as `ALL`, `PDF`, or `PDF5` intentionally skip some rules that are policy-heavy, convention-dependent, or noisy in existing projects. There are two separate mechanisms:

- `require-explicit` keeps listed rules out of broad selections until the exact rule code is selected, for example with `select = ["PDF705"]` or `extend-select = ["PDF705"]`. Clearing or changing `require-explicit` changes which rules broad selectors can enable.
- `docstring-convention` can mark a rule as `Ignored` or `Disabled` for a convention. `Ignored` means broad selectors skip the rule under that convention, but exact rule-code selection in `select` or `extend-select` restores it. Some rules are `Ignored` for every convention, so they behave like exact-code opt-ins even though they are not controlled by `require-explicit`. `Disabled` means the rule is inapplicable for that convention and remains off even when selected exactly.

## Can pydocformatter run without configuration?

Yes, `pydocfmt check` works with defaults, and all settings can be customized on the command line. It is recommended however to configure pydocformatter statically in your `pyproject.toml` when you need project-specific selection, formatting, or file-discovery behavior.

## Which Python implementations are supported?

pydocformatter officially supports CPython 3.11 or newer. Compatibility with PyPy and GraalPy is intended but is not currently verified or guaranteed. LibCST's native parser does not publish binary wheels for these implementations, so installation may require an unverified source build. Jython and IronPython are unsupported.

## Can pydocformatter run on Windows or WSL?

Native Windows and WSL are unsupported. With CPython 3.11 or newer, pydocformatter supports Ubuntu 20.04 and newer and macOS 14 and newer, with best-effort support for other POSIX Linux systems.

## Why does pydocformatter need Git?

Git is needed only when the default gitignore-aware recursive file discovery checks accepted files inside a Git worktree. Install Git or pass `--no-respect-gitignore` to disable that filtering. Explicit file arguments and files outside Git worktrees do not invoke Git.

## Why did a rule report a finding without fixing it?

Some findings are diagnostic-only. Others are fixable only when pydocformatter can prove that the source rewrite preserves the intended docstring or comment semantics.
