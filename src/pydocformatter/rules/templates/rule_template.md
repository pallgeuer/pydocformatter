# rule-name (CODE)

Fix is always available. (Use `Fix is usually available.`, `Fix is sometimes available.`, or `Fix is not available.` when that matches the rule metadata.)

(Only if rule has `setting_effects` like ignored or disabled:) Use one leading sentence that matches the metadata:

- Ignored only: "Rule is ignored if `docstring-convention` is `google` or `numpy`."
- Disabled only: "Rule is disabled if `docstring-convention` is `none` or `pep257`."
- Both disabled and ignored: "Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`."

(Only if rule is listed in the default `require-explicit` setting:) Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

(Only if rule has `incompatible_with`:) Rule is incompatible with `CODE`.

## What it does
Describe the rule's check in one or two short paragraphs.

## Why is this useful?
Explain why the rule improves readability, consistency, compatibility, or safety.

## Ruff compatibility
Describe how this rule complements, replaces, or differs from relevant Ruff rules. Use "None." if there is no relevant Ruff interplay.

## Examples
This line says something about the following example or examples:

```pydocfmt-example
[input]
# Example that triggers the rule.

[output]
# Preferred formatting. This output MUST be the actual tested output of applying the rule to the given input.
```

Add `[settings]` only when the setting context is pertinent to the applied rule or necessary to understand the scenario. Pertinent context includes the active convention or parser mode, a configured threshold or boundary, and a contrast referenced by the lead-in prose, even when the setting matches the current default. Do not require readers to know default setting values. Use `[output=unchanged]` instead of `[output]` when the exact input is expected to remain unchanged. Add a `[findings]` section after `[output]` or `[output=unchanged]` only when applying the rule is expected to leave non-fixed findings (e.g. each line under `[findings]` is something like `PDF110: Line 2` or `PDF101: Lines 3-4, 8`):

```pydocfmt-example
[input]
# Example that triggers a non-fixable finding.

[output=unchanged]
[findings]
CODE101: Lines 1-2, 7
```

Use `[input=package/module.py]` instead of `[input]` only when the path is pertinent to the rule or scenario, including public/private/package classification and examples whose point is behavior in a particular kind of path:

```pydocfmt-example
[input=package/module.py]
# Path-sensitive example that triggers the rule.

[output=unchanged]
[findings]
CODE101: Line 1: Example path-sensitive finding
```

## Options
Before writing this section, update `docs/devel/rule_settings_audit.md` with every setting the rule uses directly or through helpers. Then list only (but *exactly* all) settings from that audit that positively and directly change this rule's user-visible findings or fix output. Do not list rule-selection settings, global fixability settings, per-file settings, line-ending settings, `require-explicit`, `docstring-convention`, `docstring-parse-*`, or settings only read by shared category preparation. Use `None.` when no allowed setting is directly material.

- `related-setting`: Describe the behavior this setting changes for this rule.
