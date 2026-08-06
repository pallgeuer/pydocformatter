# unused-suppression (PCF006)

Fix is not available.

## What it does

Reports audited pydocfmt suppression selectors that do not suppress any pydocfmt finding. It checks pydocfmt-owned directive forms, including local `# pydocfmt: ignore[...]` comments, file-level `# pydocfmt: noqa` comments, file-level `# pydocfmt: noqa: ...` comments, and file-level `# pydocfmt: file-ignore[...]` comments. It also checks known explicit pydocformatter selectors in bare `# noqa: ...` comments.

Each distinct normalized selector is evaluated independently. Repeated exact selectors are collapsed by first occurrence even in check-only runs, while overlapping selectors such as `PDF` and `PDF528` remain distinct. A directive with one used selector and one unused selector produces one PCF006 finding for the unused selector. Selectors for rules that are not selected in the current run are not reported as unused.

It also reports invalid or unknown selector payloads in pydocfmt suppression directives. Bare blanket `# noqa` directives and foreign codes in `# noqa: ...` directives are not checked by this rule. Comments with unrecognized pydocfmt actions, including `disable[...]` and `enable[...]`, are not suppression directives and are therefore not audited.

PCF006 findings are filtered through source suppressions like other pydocfmt findings, so pydocfmt selectors that include `PCF006` can suppress this rule's diagnostics.

The full rule-suppression contract, including target attachment rules and cross-rule examples, is documented in [Rule suppressions](../../../../../docs/public/rule_suppressions.md).

## Why is this useful?

Unused suppression comments hide intent and can make future checks harder to interpret. Reporting them keeps pydocfmt-specific suppressions tied to active findings.

## Ruff compatibility

This rule is analogous to Ruff's `RUF100` unused-`noqa` reporting for pydocfmt-specific suppressions, but it uses pydocfmt rule selectors and applies to pydocfmt's docstring and comment finding targets. Unlike Ruff's broad `noqa` audit, PCF006 intentionally ignores blanket `# noqa` comments and foreign codes in `# noqa: ...` payloads.

## Examples

In the canonical stale-selector case, an unregistered rule name in a pydocfmt suppression is reported as unknown:

```pydocfmt-example
[input]
# pydocfmt: ignore[not-a-rule]
# Short comment.

[output=unchanged]
[findings]
PCF006: Line 1: Unknown pydocfmt suppression selector 'not-a-rule'
```

Unknown code selectors, invalid selector syntax, and empty lists have distinct diagnostics:

```pydocfmt-example
[input]
# pydocfmt: file-ignore[PDF999]
# pydocfmt: ignore[bad!]
# pydocfmt: ignore[]
# Short comment.

[output=unchanged]
[findings]
PCF006: Line 1: Unknown pydocfmt suppression selector 'PDF999'
PCF006: Line 2: Invalid pydocfmt suppression selector 'bad!'
PCF006: Line 3: Invalid pydocfmt suppression selector ''
```

Repeated normalized selectors are audited once per directive, retaining the first canonical spelling for diagnostics:

```pydocfmt-example
[input]
# pydocfmt: ignore[PDF999, pdf999]
# pydocfmt: ignore[another-rule, ANOTHER-RULE]
# Short comment.

[output=unchanged]
[findings]
PCF006: Line 1: Unknown pydocfmt suppression selector 'PDF999'
PCF006: Line 2: Unknown pydocfmt suppression selector 'another-rule'
```

Foreign generic `noqa` codes and comments with unrecognized pydocfmt actions are outside the audit:

```pydocfmt-example
[input]
value = 1  # noqa: F401
# pydocfmt: disable[PDF101]  # Unsupported by pydocfmt.
other = 2
# pydocfmt: enable[PDF101]  # Unsupported by pydocfmt.

[output=unchanged]
```

For known selectors, PCF006 is selected together with the targeted rules. Each selector that matches an active finding receives usage credit; a selector matching no finding is reported as unused, while a selector for a rule absent from the active selection is not audited. Exact canonical codes and names are equivalent identities, so a code/name alias pair is audited once and retains the first spelling for diagnostics. Distinct overlapping scopes such as `PDF` and `PDF528` remain separate entries. The cross-rule executable examples in [Rule suppressions](../../../../../docs/public/rule_suppressions.md) show used, partially used, and suppressed PCF006 scenarios.

Deduplication is local to one directive, so equivalent selectors in separate directives are audited separately.

Known explicit pydocformatter selectors in `# noqa: ...` comments are checked when the targeted rule is selected, while blanket `# noqa` comments and foreign codes are ignored.

## Options

None.
