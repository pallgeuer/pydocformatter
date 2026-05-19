# Rule Selection Specification

This document specifies how `pydocfmt` discovers rule definitions and resolves rule-selection, per-file-ignore, and fixability settings.

## Rule Definitions

Rules live under `pydocformatter.rules.definitions`. Importing `pydocformatter.rules.collection` imports every module below that package and builds the default `RULE_COLLECTION`.

Each implemented rule should be defined as one `RuleBase` subclass, normally in a module grouped by prefix:

```text
src/pydocformatter/rules/definitions/PDF/PDF001_reflow_required.py
```

Rule classes register with `@register_rule` and define a `meta` class attribute containing `RuleMetadata`:

- `code`: A `RuleCode`, such as `PDF001`.
- `name`: A stable machine-readable name, such as `reflow-required`.
- `message`: The default diagnostic message. It may include format fields for per-finding customization.
- `fixable`: Whether the rule is inherently fixable in at least some situations.

`RuleBase` rejects subclasses without `meta`, or with non-`RuleMetadata` metadata, at class definition time. `RuleMetadata` rejects non-`RuleCode` codes and empty names or messages.

No rule application or fix method interface is specified yet. That interface will be added when rule execution is implemented.

## Rule Codes

Rule codes are the canonical lookup keys.

A valid rule code:

- Uses one or more uppercase ASCII letters followed by one or more digits.
- Does not start with the reserved selector tag `ALL`.
- Is parsed into `prefix`, `number_str`, and numeric `number`.

Examples:

- `PDF001` is valid with prefix `PDF`, number string `001`, and number `1`.
- `PCF100` is valid with prefix `PCF`, number string `100`, and number `100`.
- `bad`, `001`, and `ALL001` are invalid.

## Collection

`RuleCollection` stores rule classes in deterministic rule-code order in `rules`, and exposes the same order through the `rule_class` code-to-class mapping.

Collection behavior:

- Every collected object must inherit from `RuleBase`.
- Duplicate rule codes are rejected unless they refer to the same rule class.
- Re-registering the same rule class is allowed and deduplicated by code.
- `matching_rules(selector)` returns matching rule classes in collection order.
- `matching_rules_exist(selector)` returns whether any collected rule matches the selector.

Built-in rules use the default registry through `@register_rule`. Tests and custom rule packages can use an isolated `RuleRegistry` with `register_rule_to(registry)`, import the package, then call `registry.collection()`.

The current built-in catalog intentionally contains no implemented rules. With default settings, an empty catalog resolves to an empty active ruleset without errors.

## Selector Grammar

Rule selectors are:

- `ALL`: Matches all collected rules.
- Full rule code: `PDF001`.
- Complete prefix: `PDF`.
- Complete prefix plus leading digits: `PDF10`, matching rule codes whose numeric string starts with `10`.

Selectors are case-sensitive and must use complete rule prefixes. For example, `P` does not match rules with prefix `PDF`.

Selectors outside the grammar are operational errors. Selectors that match no collected rule are operational errors, except `ALL`, which may match an empty collection without error. Invalid or unknown selectors resolve to no rules and resolution continues.

## Specificity

Selection conflicts are resolved by selector specificity, not by selector order or configuration source.

Specificity values:

- `ALL` has specificity `0`.
- Any other selector has specificity equal to `len(selector)`.

Resolution rule:

- The most specific matching enabling selector is compared with the most specific matching disabling selector.
- The enabling side wins only if it is more specific.
- The disabling side wins equal-specificity ties.

Examples:

- `select = ["PDF14"]` and `ignore = ["PDF1"]` enables `PDF142`.
- `select = ["PDF1"]` and `ignore = ["PDF14"]` disables `PDF142` but can still enable `PDF150`.
- `select = ["PDF14"]` and `ignore = ["PDF14"]` disables `PDF142`.
- With default `select = ["ALL"]`, `extend-select = ["PDF14"]` and `ignore = ["PDF1"]` enables `PDF142` but disables `PDF150`.

## Global Rule Selection

Defaults:

- `select = ["ALL"]`
- `ignore = []`
- `extend-select = []`

Global enabled rules are resolved per rule:

- Combine `select` and `extend-select` into one enabling selector set.
- Resolve `ignore` as the disabling selector set.
- For each rule, track the strongest matching enabling selector specificity.
- For each rule, track the strongest matching disabling selector specificity.
- Select the rule only when the enabling specificity is greater than the disabling specificity.

The output `rules` tuple preserves deterministic rule-code order after filtering.

## Per-File Ignores

Defaults:

- `per-file-ignores = {}`
- `extend-per-file-ignores = {}`

Per-file ignores are resolved from `per-file-ignores` followed by `extend-per-file-ignores`. Both settings are TOML-style mappings from file patterns to lists of rule selectors.

Each per-file ignore entry stores:

- `pattern`: The file pattern exactly as configured.
- `rule_codes`: The set of rule codes matched by the entry's selectors.
- `rule_specificities`: The strongest selector specificity for each matched rule code.

`RuleSelection.for_path(path)`:

- Normalizes `path` with `os.path.normpath`.
- Converts absolute paths to paths relative to the current working directory when possible.
- Converts path separators to `/`.
- Matches per-file ignore patterns with `GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False)`.
- Removes a globally selected rule only when the matching per-file ignore specificity is greater than or equal to the global selector specificity that enabled the rule.

Examples:

- `select = ["PDF14"]` with `per-file-ignores = {"tests/*.py" = ["PDF1"]}` keeps `PDF142` for matching files.
- `select = ["PDF1"]` with `per-file-ignores = {"tests/*.py" = ["PDF14"]}` removes `PDF142` for matching files and keeps `PDF150`.
- `select = ["PDF14"]` with `per-file-ignores = {"tests/*.py" = ["PDF14"]}` removes `PDF142` for matching files.

`pydocfmt check --show-rules` prints the global active rules and does not apply per-file ignores.

## Fixability

Defaults:

- `fixable = ["ALL"]`
- `unfixable = []`
- `extend-fixable = []`

Effective fixability uses the same specificity model as rule selection:

- Combine `fixable` and `extend-fixable` into one enabling selector set.
- Resolve `unfixable` as the disabling selector set.
- For each rule, track the strongest matching fixable selector specificity.
- For each rule, track the strongest matching unfixable selector specificity.
- Treat the rule as configured-fixable only when the fixable specificity is greater than the unfixable specificity.
- Intersect configured fixability with the rule's inherent `RuleMetadata.fixable`.

Settings cannot make an inherently unfixable rule fixable.

A selector in `fixable` or `extend-fixable` that matches only inherently unfixable rules is an operational error unless the selector is `ALL`. This means the default `fixable = ["ALL"]` does not warn merely because some collected rules are inherently unfixable.

Examples:

- `fixable = ["PDF14"]` and `unfixable = ["PDF1"]` makes `PDF142` configured-fixable.
- `fixable = ["PDF1"]` and `unfixable = ["PDF14"]` makes `PDF142` configured-unfixable but can leave `PDF150` configured-fixable.
- `fixable = ["PDF14"]` and `unfixable = ["PDF14"]` makes `PDF142` configured-unfixable.

## Operational Errors

Rule selection is tolerant of selector errors. `select_rules()` accumulates nonfatal error strings and continues with invalid or unknown selectors resolving to no rules.

Current error wording:

- Invalid selector: `"{context} contains invalid selector: {selector}"`
- Unknown selector: `"{context} contains unknown selector: {selector}"`
- Fixability selector that only matches inherently unfixable rules: `"{context} selector {selector!r} only matches inherently unfixable rules"`

Contexts include:

- `rule selection`
- `ignored rules`
- `fixable rules`
- `unfixable rules`
- `per-file ignores for {pattern!r}`

When `pydocfmt check --show-rules` sees rule-selection errors, it prints them before the rule list and exits with status `1`. Normal check execution includes these errors in grouped output handling.

## Resolved Selection API

`select_rules(settings, collection=None)` resolves a `CheckSettings` object against a `RuleCollection`. If no collection is passed, it uses `pydocformatter.rules.collection.RULE_COLLECTION`.

It returns `RuleSelection`:

- `rules`: A tuple of `SelectedRule` objects in rule-code order.
- `per_file_ignores`: A tuple of resolved `PerFileRuleIgnore` objects.
- `errors`: A tuple of nonfatal operational error strings.
- `collection`: The collection used for resolution.

`SelectedRule` contains:

- `rule`: The rule's `RuleMetadata`.
- `fixable`: The effective fixability after configured and inherent fixability are combined.
- `enabled_specificity`: The global selector specificity that enabled the rule.

`PerFileRuleIgnore` contains:

- `pattern`: The configured path pattern.
- `rule_codes`: A frozenset of matched rule codes.
- `rule_specificities`: A sorted tuple of `(RuleCode, specificity)` pairs.

`RuleSelection.for_path(path)` returns the selected rules after applying matching per-file ignores to the normalized path.

## CLI Behavior

`pydocfmt check --show-rules`:

- Resolves rule selection using the loaded settings.
- Prints operational errors first, prefixed with `ERROR: `.
- Prints each globally active rule as `{code}{* if fixable} {name} ({message})`.
- Prints `No active rules.` when no global rules are selected.
- Exits with status `1` if rule-selection errors were reported, otherwise `0`.

Only global rule selection is displayed. Per-file ignores are intentionally not reflected in `--show-rules` output because they depend on a path.

## CLI Rule Explanations

A future Ruff-style command may expose rule explanations, similar to `ruff rule`. The intended source is the collected rule metadata plus rule class documentation, with text and JSON output formats. This command is not part of the current implementation.
