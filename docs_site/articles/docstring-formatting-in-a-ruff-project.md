# What should format Python docstrings in a Ruff project?

Ruff and pydocformatter work at different layers. Ruff can own ordinary Python linting, source layout, and optionally Python examples embedded in docstrings. pydocformatter can own the selected docstring and comment prose policies, structured documentation, and rule-level safe fixes. Authors remain responsible for documentation that requires domain knowledge.

## Assign one owner to each concern

Overlapping tools are predictable when a project decides which result each tool owns.

| Concern                                             | Primary owner  | Reason                                                                             |
|-----------------------------------------------------|----------------|------------------------------------------------------------------------------------|
| Imports, unused names, syntax errors, and code lint | Ruff linter    | These are ordinary Python diagnostics                                              |
| Expression and statement layout                     | Ruff formatter | This is general Python source formatting                                           |
| Python examples embedded in docstrings              | Ruff formatter | Ruff exposes opt-in formatting for recognized doctests, fences, and directives     |
| Docstring and comment prose                         | pydocformatter | Its rules reflow prose while respecting supported structured boundaries            |
| Convention sections and code/documentation matches  | pydocformatter | Its selected rules understand entries, signatures, returns, yields, and exceptions |
| Missing explanations or ambiguous wording           | Author         | A formatter cannot infer the intended API contract safely                          |

The boundary is a project policy, not a claim that the tools never overlap. Ruff exposes pydocstyle-derived `D` rules, pydoclint-derived `DOC` rules, and comment-related policies. Use the [Ruff rule links](../rules/ruff-rule-links.md) to disable duplicate checks deliberately.

## Use aligned configuration

This focused configuration is shared with the tested [canonical demonstration](../demonstration.md#configuration). The narrow pydocformatter selection keeps the example readable; an adopting project can omit `select` to begin with the broader defaults or choose rules through its own migration review.

<!-- ruff-article-config:start -->

```toml
[tool.ruff]
line-length = 88

[tool.ruff.format]
docstring-code-format = true

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]

[tool.pydocfmt]
line-length = 88
select = ["PDF101", "PDF203", "PDF500", "PCF000", "PCF001", "PCF002"]

[tool.pydocfmt.docstring]
convention = "google"

[tool.pydocfmt.comment]
join-standalone-lines = true
```

<!-- ruff-article-config:end -->

Ruff documents [`docstring-code-format`](https://docs.astral.sh/ruff/formatter/#docstring-formatting) as an opt-in formatter feature for recognized Python doctests, Markdown fences, reStructuredText literal blocks, and code directives. pydocformatter protects those structures from ordinary prose reflow. With this configuration, Ruff may format the Python inside an example and pydocformatter may format the prose around it without assigning the same transformation to both tools.

The canonical demonstration runs pydocformatter in isolation so its complete diff shows only pydocformatter changes. A combined toolchain can additionally change embedded Python through Ruff.

## Check each layer independently

Keep the read-only commands separate so a failure identifies its owner:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pydocfmt check --diff
```

`ruff check` reports ordinary lint findings, `ruff format --check` verifies general layout, and `pydocfmt check --diff` previews documentation fixes while still reporting changes that require authorship. Once the selected policies are accepted, a deliberate local fix sequence is:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pydocfmt check --fix
```

Running Ruff lint fixes before the Ruff formatter follows Ruff's [documented integration order](https://docs.astral.sh/ruff/integrations/). Running pydocformatter last gives the documentation-specific rules the final say over their assigned prose and comment regions. Review the pydocformatter diff before making this sequence routine, and keep CI read-only as described in [Integrations](../integrations.md).

## Avoid duplicate policy

Two tools reporting the same condition create noise even when they agree. Two tools rewriting the same source region can create churn when they do not. Before enabling the combined checks:

1. Decide whether pydocformatter or Ruff owns each overlapping `D`, `DOC`, and comment policy.
2. Align shared line length, indentation, and line-ending settings where both tools expose them.
3. Enable Ruff's embedded-code formatting only when Ruff should own those examples.
4. Run both read-only checks over the existing repository and tune selection before applying fixes.
5. Apply reviewed changes, then require the same read-only commands in pre-commit or CI.

The [comparison](../comparison.md#ruff) explains the capability boundary, while the [canonical demonstration](../demonstration.md) makes the pydocformatter fix/authorship boundary concrete.

## Use Black as an alternative, not a second formatter

If a project already uses Black, keep Ruff as the linter, let Black own general Python layout, and do not also run `ruff format` over the same files. Align the shared width:

```toml
[tool.black]
line-length = 88
```

The read-only pipeline then becomes:

```bash
uv run ruff check .
uv run black --check .
uv run pydocfmt check --diff
```

See the [Black comparison](../comparison.md#black) for the narrower boundary. The same pydocformatter adoption workflow and overlap review still apply.

## Continue the evaluation

Read [Why Python docstrings are harder to format safely](why-docstrings-are-hard-to-format-safely.md) for the design constraints behind conservative documentation fixes. Then use the [demonstration](../demonstration.md), [migration workflow](../tutorial.md#adopting-in-an-existing-codebase), and [integration recipes](../integrations.md) to test the toolchain in a repository. [PyPI](https://pypi.org/project/pydocformatter/) and the [repository README](../project/readme.md) provide installation and project-level reference points.
