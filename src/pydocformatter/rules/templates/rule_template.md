# rule-name (CODE)

Fix is always available. (Use `Fix is usually available.`, `Fix is sometimes available.`, or `Fix is not available.` when that matches the rule metadata.)

(Only if rule has `setting_effects` like ignored or disabled:) Rule is ignored if `docstring-convention` is `google` or `numpy`.

(Only if rule has `incompatible_with`:) Rule is incompatible with `CODE`.

## What it does
Describe the rule's check in one or two short paragraphs.

## Why is this useful?
Explain why the rule improves readability, consistency, compatibility, or safety.

## Ruff compatibility
Describe how this rule complements, replaces, or differs from relevant Ruff rules. Use "None." if there is no relevant Ruff interplay.

## Example
This line says something about the following example:

```pydocfmt-example
[settings]
line-length = 72

[input]
# Example that triggers the rule.

[output]
# Preferred formatting. This output MUST be the actual tested output of applying the rule to the given input.
```

Use `[output=unchanged]` instead of `[output]` when the exact input is expected to remain unchanged. Add a `[findings]` section after `[output]` or `[output=unchanged]` only when applying the rule is expected to leave non-fixed findings (e.g. each line under `[findings]` is something like `PDF106: 2` or `PDF001: 3-4, 8`):

```pydocfmt-example
[input]
# Example that triggers a non-fixable finding.

[output=unchanged]
[findings]
CODE101: 1-2, 7
```

## Options
- `related-setting`
