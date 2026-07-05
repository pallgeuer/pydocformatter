# rule-name (CODE)

Fix is always available. (Use `Fix is usually available.`, `Fix is sometimes available.`, or `Fix is not available.` when that matches the rule metadata.)

(Only if rule has `setting_effects` like ignored or disabled:) Rule is ignored if `docstring-convention` is `google` or `numpy`.

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
[settings]
line-length = 72

[input]
# Example that triggers the rule.

[output]
# Preferred formatting. This output MUST be the actual tested output of applying the rule to the given input.
```

Use `[output=unchanged]` instead of `[output]` when the exact input is expected to remain unchanged. Add a `[findings]` section after `[output]` or `[output=unchanged]` only when applying the rule is expected to leave non-fixed findings (e.g. each line under `[findings]` is something like `PDF110: Line 2` or `PDF101: Lines 3-4, 8`):

```pydocfmt-example
[input]
# Example that triggers a non-fixable finding.

[output=unchanged]
[findings]
CODE101: Lines 1-2, 7
```

Use `[input=package/module.py]` instead of `[input]` only when the example's behavior depends on the source display path:

```pydocfmt-example
[input=package/module.py]
# Path-sensitive example that triggers the rule.

[output=unchanged]
[findings]
CODE101: Line 1: Example path-sensitive finding
```

## Options
List only settings that materially change this rule's user-visible behavior, such as ignored state, finding targets, fix output, or examples. Do not list settings only because shared category preparation reads them. Group setting families like `docstring-parse-*` when every setting has the same effect for this rule. Use `None.` when no setting is directly material.

- `related-setting`: Describe the behavior this setting changes for this rule.
