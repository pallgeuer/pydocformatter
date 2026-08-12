## Summary

<!-- Explain the problem, the chosen solution, and the intended scope. -->

Closes #

<!-- Remove the line above when no issue applies. Link related or dependent work here as needed. -->

## User-visible behavior

<!-- Describe the relevant before-and-after behavior. Include concise examples for formatting, diagnostics, or CLI output. State "No user-visible change" for internal work. -->

## Implementation notes

<!-- Explain non-obvious design decisions, architecture boundaries, or follow-up work. Remove this section when the summary is sufficient. -->

## Compatibility and risks

<!-- Address changes to formatting, diagnostics, CLI behavior, configuration, rule selection, fixability, source preservation, or supported platforms. Explain migrations for breaking changes. Mention material performance or security considerations; otherwise state that none are known. -->

## Verification

<!-- Replace placeholders with the exact test paths or other commands used. For successful checks, "passed" is sufficient; do not paste full output. Include output only when it explains a failure, warning, skipped check, or other notable result. Use "Not applicable" with a brief reason where appropriate. -->

- Focused tests: `uv run pytest -n 0 <test paths or node IDs>` - Passed/Failed.
- Full fix stage: `uv run pre-commit run --all-files` - Passed/Failed.
- Full CI-equivalent checks: `uv run pre-commit run --all-files --hook-stage manual` - Passed/Failed.
- Documentation build: `uv run python tools/docs/generate_zensical.py`, then `uv run zensical build --strict -f zensical.generated.toml` - Passed/Failed.
- Manual or platform-specific checks: Passed/Not applicable.

## Documentation and changelog

<!-- List updated user documentation, specifications, rule documentation, docstrings, and CHANGELOG entries. Explain why no update is needed when behavior changes without documentation changes. -->

## Rule change checklist

<!-- Remove this section when the pull request does not add or change built-in rule behavior. -->

- [ ] I followed the [rule implementation specification](https://github.com/pallgeuer/pydocformatter/blob/main/docs/devel/rule_implementation_spec.md).
- [ ] Rule identity, metadata, registration, fix availability, setting effects, and incompatibilities are consistent.
- [ ] Adjacent rule or category documentation follows its template and contains executable examples with exact findings.
- [ ] `docs/devel/rule_settings_audit.md` covers all direct and helper-driven setting reads.
- [ ] Focused rule tests cover diagnostics, fixes or non-fixable behavior, no-op and edge cases, settings, idempotence, suppressions, and line endings where relevant.
- [ ] Category, selection, settings, formatter, and CLI tests are updated where the change crosses those boundaries.

## Final checklist

- [ ] The diff is focused and contains no unintended or generated files.
- [ ] Any new or changed behavior has appropriate automated tests.
- [ ] Any affected documentation and docstrings are updated.
- [ ] Any significant user-facing or developer-facing work is recorded under `CHANGELOG.md`'s Unreleased section.
- [ ] Any dependency changes include `pyproject.toml` and the corresponding `uv.lock` update.
- [ ] The reported verification passes on the final diff.
