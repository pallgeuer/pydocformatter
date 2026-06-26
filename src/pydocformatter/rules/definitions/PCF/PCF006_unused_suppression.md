# unused-suppression (PCF006)

Fix is not available.

## What it does
Reports audited pydocfmt suppression selectors that do not suppress any pydocfmt finding. It checks pydocfmt-owned directive forms, including local `# pydocfmt: ignore[...]` comments, file-level `# pydocfmt: noqa` comments, file-level `# pydocfmt: noqa: ...` comments, and file-level `# pydocfmt: file-ignore[...]` comments. It also checks known explicit pydocformatter selectors in bare `# noqa: ...` comments.

Each selector is evaluated independently. A directive with one used selector and one unused selector produces one PCF006 finding for the unused selector. Selectors for rules that are not selected in the current run are not reported as unused.

It also reports invalid or unknown selector payloads in pydocfmt suppression directives. Bare blanket `# noqa` directives and foreign codes in `# noqa: ...` directives are not checked by this rule. Unsupported range-style pydocfmt comments such as `# pydocfmt: disable[...]` and `# pydocfmt: enable[...]` are not suppression directives.

PCF006 findings are filtered through source suppressions like other pydocfmt findings, so pydocfmt selectors that include `PCF006` can suppress this rule's diagnostics.

The full source-suppression contract, including target attachment rules and cross-rule examples, is documented in `docs/suppressions.md`.

## Why is this useful?
Unused suppression comments hide intent and can make future checks harder to interpret. Reporting them keeps pydocfmt-specific suppressions tied to active findings.

## Ruff compatibility
This rule is analogous to Ruff's unused-`noqa` reporting for pydocfmt-specific suppressions, but it uses pydocfmt rule selectors and applies to pydocfmt's docstring and comment finding targets. Unlike Ruff's broad `noqa` audit, PCF006 intentionally ignores blanket `# noqa` comments and foreign codes in `# noqa: ...` payloads.

## Examples
When PCF006 is selected together with the rule targeted by a suppression, an unused selector is reported. For example, `# pydocfmt: ignore[PCF001]` above a short ordinary comment reports `Suppression selector 'PCF001' did not suppress any findings` when `PCF001` and `PCF006` are both selected.

Invalid selector syntax in pydocfmt directives is reported:

```pydocfmt-example
[input]
# pydocfmt: ignore[not-a-rule]
# Short comment.

[output=unchanged]
[findings]
PCF006: Line 1: Invalid pydocfmt suppression selector 'NOT-A-RULE'
```

Unknown but syntactically valid selectors are also reported:

```pydocfmt-example
[input]
# pydocfmt: file-ignore[PDF999]
value = 1

[output=unchanged]
[findings]
PCF006: Line 1: Unknown pydocfmt suppression selector 'PDF999'
```

Empty selector lists are invalid:

```pydocfmt-example
[input]
# pydocfmt: ignore[]
# Short comment.

[output=unchanged]
[findings]
PCF006: Line 1: Invalid pydocfmt suppression selector ''
```

Known explicit pydocformatter selectors in `# noqa` comments are checked when the targeted rule is selected, while foreign codes are ignored.

## Options
None.
