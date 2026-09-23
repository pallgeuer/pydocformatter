# Canonical demonstration

This demonstration shows the boundary between general Python formatting, documentation formatting, and human authorship. Ruff owns ordinary Python linting and layout, while pydocformatter owns the selected docstring and comment policies. The articles on [safe docstring formatting](articles/why-docstrings-are-hard-to-format-safely.md) and [tool ownership in a Ruff project](articles/docstring-formatting-in-a-ruff-project.md) explain why this boundary matters and how to adopt it.

## Configuration

The focused rule selection keeps the demonstration readable. A normal project can omit `select` to start from pydocformatter's broader defaults.

<!-- canonical-demo-config:start -->

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

<!-- canonical-demo-config:end -->

Run the tools independently so each owns its intended source:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pydocfmt check --diff
```

To use Black instead of the Ruff formatter, keep Ruff as the linter, replace the `ruff format` command with `black --check .`, and align its line length:

<!-- canonical-demo-black:start -->

```toml
[tool.black]
line-length = 88
```

<!-- canonical-demo-black:end -->

Do not alternate Black and the Ruff formatter over the same files. Both are general Python formatters; pydocformatter complements either one.

## Source transformation

The deliberately dense function combines Google-style parameter documentation, a long summary, protected doctest and fenced-code examples, a reStructuredText math directive, inline markup with a URL, a standalone comment, and a trailing comment. The compact code inside the fence is intentionally unusual so preservation is visible.

````pydocfmt-example
[settings]
line-length = 88
select = ["PDF101", "PDF203", "PDF500", "PCF000", "PCF001", "PCF002"]
docstring-convention = "google"
comment-join-standalone-lines = true

[input=demo.py]
"""Report rendering helpers."""


def render_report(items, base_url, retry_limit):
    """Builds a report from the requested items and returns a link that callers can use to retrieve the rendered document without additional state.

    Args:
        items: Items to include in the report.
        base_url: Base URL used to construct the report link for callers in every deployment environment where reports can be published.

    Examples:
        The doctest stays literal:

        >>> render_report(["alpha"], "https://example.com/reports", 2)
        'https://example.com/reports/latest'

        ```python
        result=render_report(["alpha"],"https://example.com/reports",2)
        ```

        .. math::

            total = successful + failed

        See [the deployment guide](https://example.com/docs/deployment?region=eu&mode=preview) before publishing.
    """
    # Keep retry attempts bounded so temporary rendering failures do not hold a worker indefinitely while other reports are waiting to run.
    return f"{base_url}/latest"  # Return the stable report location to callers after rendering succeeds so they do not need to reconstruct it.

[output]
"""Report rendering helpers."""


def render_report(items, base_url, retry_limit):
    """Builds a report from the requested items and returns a link that callers can use
    to retrieve the rendered document without additional state.

    Args:
        items: Items to include in the report.
        base_url: Base URL used to construct the report link for callers in every
            deployment environment where reports can be published.

    Examples:
        The doctest stays literal:

        >>> render_report(["alpha"], "https://example.com/reports", 2)
        'https://example.com/reports/latest'

        ```python
        result=render_report(["alpha"],"https://example.com/reports",2)
        ```

        .. math::

            total = successful + failed

        See [the deployment guide](https://example.com/docs/deployment?region=eu&mode=preview) before publishing.
    """
    # Keep retry attempts bounded so temporary rendering failures do not hold a worker
    # indefinitely while other reports are waiting to run.

    # Return the stable report location to callers after rendering succeeds so they do
    # not need to reconstruct it.
    return f"{base_url}/latest"

[findings]
PDF203: Lines 5-6: Docstring summary spans 2 lines and does not fit on one line
PDF500: Line 4: Function parameter 'retry_limit' is missing docstring documentation
````

[`PDF101`](rules/docstring-reflow.md) reflows the summary, parameter description, and surrounding prose. [`PCF000`](rules/standalone-comment-formatting.md) wraps the standalone comment, while [`PCF002`](rules/trailing-comment-extraction.md) moves and wraps the safe trailing explanation. The doctest, fenced code, math directive, and complete inline link remain unchanged.

[`PDF203`](rules/summary-too-long.md) still reports the two-line summary because shortening authored prose requires judgment. [`PDF500`](rules/missing-parameter-documentation.md) still reports `retry_limit` because a formatter cannot invent its description safely.

## Complete diff

This is the complete unified diff produced by the tested transformation above:

<!-- canonical-demo-diff:start -->

```diff
--- before/demo.py
+++ after/demo.py
@@ -5 +5,2 @@
-    """Builds a report from the requested items and returns a link that callers can use to retrieve the rendered document without additional state.
+    """Builds a report from the requested items and returns a link that callers can use
+    to retrieve the rendered document without additional state.
@@ -9 +10,2 @@
-        base_url: Base URL used to construct the report link for callers in every deployment environment where reports can be published.
+        base_url: Base URL used to construct the report link for callers in every
+            deployment environment where reports can be published.
@@ -27,2 +29,6 @@
-    # Keep retry attempts bounded so temporary rendering failures do not hold a worker indefinitely while other reports are waiting to run.
-    return f"{base_url}/latest"  # Return the stable report location to callers after rendering succeeds so they do not need to reconstruct it.
+    # Keep retry attempts bounded so temporary rendering failures do not hold a worker
+    # indefinitely while other reports are waiting to run.
+
+    # Return the stable report location to callers after rendering succeeds so they do
+    # not need to reconstruct it.
+    return f"{base_url}/latest"
```

<!-- canonical-demo-diff:end -->

Apply the safe changes with `uv run pydocfmt check --fix`, then revise the summary and document `retry_limit` before enabling the read-only check in CI. See [Checking](checking.md) for exit behavior, [Integrations](integrations.md) for pre-commit, CI, and editor workflows, and [Docstring formatting in a Ruff project](articles/docstring-formatting-in-a-ruff-project.md) for the complete division of responsibilities.
