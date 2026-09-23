# Why Python docstrings are harder to format safely

A Python formatter normally works with syntax: expressions, statements, delimiters, and indentation. A docstring adds several other concerns inside one string literal. It is runtime data, human prose, structured API documentation, and often a container for examples or markup. Safe formatting requires knowing which concern owns each region and where automation must stop.

## A docstring has several representations

[PEP 257](https://peps.python.org/pep-0257/) defines a docstring as a string literal in a documentation position and describes its high-level structure. Python then exposes the evaluated string through an object's [`__doc__` attribute](https://docs.python.org/3/reference/datamodel.html). Those views are related but not identical:

- Source contains quote styles, prefixes, escapes, indentation, and sometimes adjacent literals.
- The evaluated value contains the documentation text seen by Python and documentation tools.
- Rendered documentation may interpret Markdown, reStructuredText, doctests, or a structured docstring convention.

Changing source spelling can leave the evaluated value unchanged. Reflowing a paragraph intentionally changes its whitespace. A formatter therefore cannot apply one blanket definition of "semantic preservation" to every docstring edit.

pydocformatter distinguishes source-literal normalization from documentation formatting. Source rewrites that require value equivalence preserve the evaluated docstring value. Documentation rules can deliberately change prose whitespace or structure, but only within the selected rule's documented scope. The exact public guarantees are recorded in [Versioning](../versioning.md#fix-guarantees).

## Prose is not just prose

An apparent paragraph may sit beside content whose whitespace and punctuation carry syntax. The [canonical demonstration](../demonstration.md#source-transformation) deliberately combines several examples:

```text
Args:
    base_url: Base URL used to construct the report link.

>>> render_report(["alpha"], "https://example.com/reports", 2)

.. math::

    total = successful + failed
```

The argument entry has convention-defined indentation. The doctest has executable prompts and expected output. The directive owns an indented body. A fenced block, table, URL, equation, list, or inline markup span introduces other boundaries. Treating the whole string as an ordinary paragraph would corrupt some of those structures.

pydocformatter parses supported PEP 257, Google, NumPy, and reStructuredText structures before reflowing prose. Recognized doctests, code fences, directives, literal blocks, tables, and similar regions are protected from ordinary paragraph formatting. Settings make these parsing decisions explicit because projects may use the same punctuation for different purposes.

## Documentation also describes code

Docstrings do more than contain text. A structured function docstring can claim which parameters exist, whether a value is returned or yielded, and which exceptions can escape. Class documentation can describe attributes and methods. These relationships are not questions of line wrapping.

A documentation tool needs both views:

- The parsed Python definition and body establish what the code contains.
- The selected docstring convention establishes what the documentation claims.

This is why a missing parameter description can be diagnosed precisely but should not usually be invented automatically. The formatter can identify the gap; only the author knows the parameter's contract. The [rule catalog](../rules.md) separates diagnostic policy from fix availability for this reason.

## The useful boundary for automation

The safest division is based on whether the intended replacement is mechanically determined.

| Situation                                      | Automatic action                                              | Human responsibility                                |
|------------------------------------------------|---------------------------------------------------------------|-----------------------------------------------------|
| A prose paragraph exceeds the configured width | Reflow it around protected structures                         | Confirm that the wording still communicates clearly |
| Docstring quotes or blank lines violate policy | Normalize the exact source layout                             | Choose the project policy through rule selection    |
| A safe trailing explanation exceeds the width  | Move and wrap it as a standalone comment                      | Review whether it belongs in code or documentation  |
| A summary remains too long after reflow        | Report the diagnostic                                         | Shorten or rewrite the sentence                     |
| A parameter has no documentation               | Report the signature/documentation mismatch                   | Write an accurate description                       |
| Source mapping or reconstruction is ambiguous  | Skip the unsafe fix while retaining the applicable diagnostic | Simplify the source or make the intended change     |

This boundary lets a project automate deterministic cleanup without silently manufacturing API promises.

## Safety is an observable process

"Safe" is useful only when it maps to behavior a project can inspect and test. pydocformatter applies planned edits to exact source ranges, rejects overlapping changes, reparses rewritten Python, and requires a successful fix run to reach a fixed point. A second run with the same version, settings, selected rules, and source produces no further changes.

For supported Python fences inside Markdown, surrounding content is retained. If a changed fence cannot be reconstructed and validated, the complete Markdown file is rolled back instead of being partially updated. These guarantees do not mean that prose formatting leaves every `__doc__` byte unchanged; they define where intentional documentation changes are allowed and how unsafe source changes are refused.

See [Formatting](../formatting.md#safety-model) for the user workflow and [Versioning](../versioning.md#fix-guarantees) for the compatibility contract.

## Adopt the boundary deliberately

Start with read-only feedback and make the automation boundary visible:

```bash
uv run pydocfmt check
uv run pydocfmt check --diff
```

Review the proposed source changes and the findings left for authors. Apply selected safe fixes locally only after the rule set and configuration match the project:

```bash
uv run pydocfmt check --fix
uv run pydocfmt check
```

The [canonical demonstration](../demonstration.md) executes this boundary against real formatter behavior, including protected content, a complete diff, applied fixes, and remaining diagnostics. For tool ownership around that boundary, continue with [Docstring formatting in a Ruff project](docstring-formatting-in-a-ruff-project.md). The [comparison](../comparison.md) covers alternative documentation tools, while [PyPI](https://pypi.org/project/pydocformatter/) and the [repository README](../project/readme.md) provide the shortest installation and project overview.
