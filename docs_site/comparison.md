# Comparing pydocformatter with related tools

pydocformatter overlaps with several established Python tools, but it is not intended to replace every linter or general code formatter. The useful question is which tool should own each part of a project's documentation and formatting policy.

## Versions reviewed

This comparison covers [pydocformatter 1.2.0](https://pypi.org/project/pydocformatter/1.2.0/), [Ruff 0.16.6](https://pypi.org/project/ruff/0.16.6/), [pydocstyle 6.3.0](https://pypi.org/project/pydocstyle/6.3.0/), [docformatter 1.7.8](https://pypi.org/project/docformatter/1.7.8/), [Black 26.5.1](https://pypi.org/project/black/26.5.1/), and [pydoclint 0.9.1](https://pypi.org/project/pydoclint/0.9.1/). Follow the linked project documentation when evaluating later releases.

## Capability overview

The entries describe documented, built-in behavior rather than every result that might be possible through plugins or custom wrappers.

| Tool           | Primary role                             | Docstring prose and source layout                                        | Comment prose                            | Structured and semantic checks                                                   | Automatic changes                                 |
|----------------|------------------------------------------|--------------------------------------------------------------------------|------------------------------------------|----------------------------------------------------------------------------------|---------------------------------------------------|
| pydocformatter | Docstring and comment linter/formatter   | Reflows prose and normalizes source layout                               | Reflows standalone and trailing comments | Google, NumPy, reStructuredText, PEP 257, and signature/body relationships       | Rule-scoped fixes with explicit safety boundaries |
| Ruff           | General Python linter and code formatter | Normalizes code-level layout; optionally formats embedded Python code    | General spacing and lint policies        | `D` convention rules and preview `DOC` signature/body rules                      | Formatter plus fixes for supported lint rules     |
| pydocstyle     | Docstring convention checker             | Reports convention violations; no source formatter is documented         | Not a comment-prose formatter            | PEP 257, Google, and NumPy convention rules, including selected section checks   | No built-in source-rewrite command is documented  |
| docformatter   | PEP 257-oriented docstring formatter     | Wraps summaries and descriptions and normalizes docstring layout         | Not a comment-prose formatter            | Sphinx and Epytext field-list styles are currently recognized                    | In-place formatting or diff/check modes           |
| Black          | General Python code formatter            | Normalizes quotes, indentation, trailing whitespace, and edge whitespace | Does not format comment contents         | No docstring-section or documentation-to-signature checker                       | Whole-file code formatting                        |
| pydoclint      | Semantic docstring linter                | Reports findings; no prose formatter or source rewrite is documented     | Not a comment-prose formatter            | Google, NumPy, and Sphinx sections matched against signatures and implementation | Diagnostic and baseline workflows are documented  |

## Ruff

[Ruff](https://docs.astral.sh/ruff/) combines a broad Python linter with a Black-compatible code formatter. Its formatter owns ordinary expression and statement layout and can optionally format Python examples inside docstrings and Markdown; it does not document general docstring-prose reflow as a formatter responsibility. Ruff's linter includes stable [pydocstyle-derived `D` rules](https://docs.astral.sh/ruff/rules/#pydocstyle-d) and preview [pydoclint-derived `DOC` rules](https://docs.astral.sh/ruff/rules/#pydoclint-doc), with automatic fixes available for some rules.

Use Ruff and pydocformatter together when Ruff should own general Python code and pydocformatter should own docstring/comment prose and the selected documentation policy. Avoid duplicate diagnostics by following the [rule-by-rule Ruff mapping](rules/ruff-rule-links.md). Ruff's [formatter documentation](https://docs.astral.sh/ruff/formatter/) explains its embedded-code behavior and warns against running Black and the Ruff formatter interchangeably.

## pydocstyle

[pydocstyle](https://pydocstyle.readthedocs.io/en/latest/) is a static checker for Python docstring conventions. Its [error catalog](https://pydocstyle.readthedocs.io/en/latest/error_codes.html) covers missing docstrings, whitespace, quotes, summary content, section syntax, and missing argument descriptions. Its [usage reference](https://pydocstyle.readthedocs.io/en/latest/usage.html) documents selectable `pep257`, `numpy`, and `google` conventions and diagnostic exit statuses, but no source-rewrite command.

pydocformatter overlaps with many convention checks while adding prose/comment formatting, wider semantic documentation checks, and per-rule fixes. Projects migrating from pydocstyle should compare enabled rules rather than assume code-for-code compatibility.

## docformatter

[docformatter](https://docformatter.readthedocs.io/en/stable/) is an automatic formatter focused on PEP 257 docstring layout. Its [command reference](https://docformatter.readthedocs.io/en/stable/usage.html) documents summary and description wrapping, check, diff, and in-place modes. Its [configuration reference](https://docformatter.readthedocs.io/en/stable/configuration.html) currently identifies Sphinx and Epytext field-list styles as recognized, with NumPy and Google described as future styles.

pydocformatter adds ordinary comment formatting, Google/NumPy/reStructuredText structural models, rule-level diagnostics, and signature/body documentation checks. The two tools have different option and output models, so a project should choose one owner for overlapping docstring layout.

## Black

[Black](https://black.readthedocs.io/en/stable/) is an opinionated general Python code formatter. Its [current style](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#strings) normalizes docstring quotes, indentation, trailing whitespace, final blank lines, and one-line edge whitespace. Black explicitly [does not format comment contents](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#comments), and it does not document structured docstring or documentation-to-signature linting.

Use Black for ordinary Python layout and pydocformatter for docstring/comment prose and documentation checks. Align their line lengths and do not also run the Ruff formatter over the same files as an interchangeable second general formatter.

## pydoclint

[pydoclint](https://jsh9.github.io/pydoclint/) checks whether documented arguments, returns, yields, exceptions, and class attributes match signatures or implementation. It supports NumPy, Google, and Sphinx styles, and its [configuration reference](https://jsh9.github.io/pydoclint/config_options.html) documents semantic switches and baseline workflows for gradual adoption. Its documented interface is diagnostic rather than a prose formatter or automatic source rewriter.

pydocformatter covers many related semantic relationships while also formatting source and exposing fixes where a rewrite is safe. Ruff independently reimplements a subset of pydoclint's rules under its preview `DOC` family, so projects should decide which implementation owns overlapping checks.

## Choosing a toolchain

- Use Ruff or Black for ordinary Python code formatting.
- Add pydocformatter when docstring/comment prose, structured documentation, and conservative rule-level fixes should share one tool.
- Keep pydocstyle or pydoclint only for policies not covered by the selected pydocformatter rules, or while migrating incrementally.
- Do not enable equivalent checks in several tools unless duplicate diagnostics are intentional.

See the [canonical demonstration](demonstration.md) for a tested Ruff-first configuration and an end-to-end pydocformatter diff. [Docstring formatting in a Ruff project](articles/docstring-formatting-in-a-ruff-project.md) turns that boundary into a practical adoption workflow, while [Why Python docstrings are harder to format safely](articles/why-docstrings-are-hard-to-format-safely.md) explains the underlying design constraints.
