# Rule selection specification

This document specifies how `pydocfmt` discovers rule definitions and resolves rule-selection, per-file-ignore, and fixability settings, and how rule selection information is exposed via the CLI.

## Ruff compatibility deltas

- **D1: Rule catalog and selector prefixes.**
  pydocformatter has its own rule catalog and requires selectors to use complete pydocformatter rule prefixes such as `PDF` or `PCF`. The selector `P` does not match `PDF` or `PCF` rules.
- **D2: Supported settings.**
  pydocformatter implements `select`, `ignore`, `extend-select`, `per-file-ignores`, `extend-per-file-ignores`, `fixable`, `unfixable`, and `extend-fixable`. Ruff settings that have no pydocformatter equivalent, such as deprecated `extend-ignore`, preview-rule settings, fix-safety settings, and `external`, are outside this compatibility surface.
- **D3: Selector errors.**
  pydocformatter records selector validation problems as operational errors so one run can report all rule-selection issues together. Ruff may fail earlier while parsing or resolving its own configuration.
- **D4: Fixability selector validation.**
  pydocformatter reports an operational error when a `fixable` or `extend-fixable` selector matches only rules whose `FixAvailability` is `Never`. Ruff accepts such selectors and simply has no fix to apply for those rules.
- **D5: Command-line comma-list whitespace.**
  pydocformatter strips whitespace around entries in dedicated command-line comma-list options, so `--select "PDF200, PDF110"` is accepted as `PDF200` and `PDF110`. Ruff rejects whitespace-containing selector entries such as ` F841`.

## Rule definitions

Rules and rule categories live under `pydocformatter.rules.definitions`. Importing `pydocformatter.rules.collection` imports each category module before its rule modules and builds the default `RULE_COLLECTION`.

Each rule category is a `RuleCategoryBase` subclass in a module named after its rule-code prefix, with adjacent category documentation:

```text
src/pydocformatter/rules/definitions/PDF/PDF.py
src/pydocformatter/rules/definitions/PDF/PDF.md
```

The class is also named after the prefix and defines `RuleCategoryMetadata` containing its `prefix`, user-facing `name`, and optional `url`. `RuleCategoryBase` rejects missing or invalid metadata at class definition time and provides `ordered_rules()` and `ordered_code_class_map()` views.

Each implemented rule is collected as one `RuleBase` subclass, normally in a module grouped by prefix:

```text
src/pydocformatter/rules/definitions/PDF/PDF101_docstring_reflow.py
```

Rule classes register with their category through `@register_rule_to(PDF)`. Rule selection uses the rule's `meta` class attribute, a `RuleMetadata` record containing:

- `code`: A `RuleCode`, such as `PDF101`.
- `name`: A stable machine-readable name, such as `docstring-reflow`.
- `message`: The default diagnostic message shown in rule listings and findings.
- `fix_availability`: A `FixAvailability` value describing whether automatic fixes are `Always`, `Usually`, `Sometimes`, or `Never` available at the rule level. `Always` means every finding has a fix. `Usually` means every semantic violation kind has a correction, although instance-specific safety can prevent a fix. `Sometimes` means at least one semantic violation kind is intentionally diagnostic-only while another has a fix. `Never` means the rule is diagnostic-only.
- `stable_since`: The pydocformatter version in which the rule became stable.
- `setting_effects`: Immutable metadata mapping resolved setting fields and triggering values to `Ignored` or `Disabled` selection effects.
- `incompatible_with`: An immutable tuple of `RuleCode` values for rules that cannot be selected together with this rule.
- `check_kind`: A `RuleCheckKind` value used to distinguish standard source-check rules from suppression-audit rules during rule collection and execution ordering.

`RuleBase` rejects subclasses without `meta`, or with non-`RuleMetadata` metadata, at class definition time. `RuleMetadata` rejects non-`RuleCode` codes, non-`FixAvailability` fix availability values, non-`RuleCheckKind` check kinds, empty names, messages, or stable versions, malformed setting-effect records, malformed incompatibility tuples, and duplicate incompatible codes. Category registration rejects rules whose code prefix differs from the category prefix and rejects duplicate rule codes from different classes.

## Rule codes

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

`RuleCollection` stores category classes in deterministic prefix order in `categories`, exposes the same order through `category_class`, and flattens their rules into deterministic rule-code order in `rules` and `rule_class`.

Collection behavior:

- Every collected object must inherit from `RuleCategoryBase`; rules cannot be registered directly with a registry or collection.
- Duplicate category prefixes are rejected unless they refer to the same category class.
- Categories expose their rules in rule-code order and allow idempotent re-registration of the same rule class.
- `matching_rules(selector)` returns matching rule classes in collection order.
- `matching_rules_exist(selector)` returns whether any collected rule matches the selector.
- Incompatibility declarations must reference collected rules, cannot reference the declaring rule itself, and must be declared mutually by both rules.

Built-in categories use the default registry through `@register_rule_category`, and their rules use `@register_rule_to(category)`. Tests and custom rule packages can use an isolated `RuleRegistry` with `register_rule_category_to(registry)`, pass that registry to `import_package_rule_categories`, then call `RuleCollection.from_registry(registry)`.

Definition package loading validates the complete built-in layout: the definitions package contains only category packages; each category package is flat and contains a matching prefix-named category module and class; each rule module contains exactly one registered local rule whose code matches its filename and category; registered rules originate from and have modules in their category package; and every category and rule has adjacent Markdown documentation with no orphan Markdown files.

With default settings, a custom empty catalog resolves to an empty active ruleset without errors.

## Selector grammar

Rule selectors are:

- `ALL`: Matches all collected rules.
- Full rule code: `PDF101`.
- Complete prefix: `PDF`.
- Complete prefix plus leading digits: `PDF10`, matching rule codes whose numeric string starts with `10`.

Selectors are case-sensitive and must use complete rule prefixes. For example, `P` does not match rules with prefix `PDF`.

Selectors outside the grammar are operational errors. Selectors that match no collected rule are operational errors, except `ALL`, which may match an empty collection without error. Invalid or unknown selectors resolve to no rules and resolution continues.

## Source priority and specificity

Selection conflicts are resolved first by configuration source priority, then by selector specificity. Selector order inside one setting is not significant.

Source priority values:

- Defaults have priority `0`.
- Auto-discovered or explicit config-file settings have priority `1`.
- Inline `--config "<KEY> = <VALUE>"` settings have priority `2`.
- Dedicated command-line options have priority `3`.
- In-process field overrides used by tests and callers have priority `4`.

Specificity values:

- `ALL` has specificity `0`.
- Any other selector has specificity equal to `len(selector)`.

Resolution rule:

- The strongest matching enabling selector is compared with the strongest matching disabling selector.
- A selector with a higher source priority beats a selector with a lower source priority, even if the lower-priority selector is more specific.
- When both sides have the same source priority, the more specific selector wins.
- The disabling side wins equal-priority, equal-specificity ties.
- Lower-priority adjustment settings that do not participate in the final decision are still validated and can still produce operational errors.

Examples:

- `select = ["PDF14"]` and `ignore = ["PDF1"]` enables `PDF142`.
- `select = ["PDF1"]` and `ignore = ["PDF14"]` disables `PDF142` but can still enable `PDF150`.
- `select = ["PDF14"]` and `ignore = ["PDF14"]` disables `PDF142`.
- With default `select = ["ALL"]`, `extend-select = ["PDF14"]` and `ignore = ["PDF1"]` enables `PDF142` but disables `PDF150`.
- A command-line `--select PDF1` enables `PDF142` even when a lower-priority config file has `ignore = ["PDF142"]`.
- A command-line `--ignore PDF1` disables `PDF142` even when a lower-priority config file has `select = ["PDF142"]`.

## Setting effects

After normal `select` and `ignore` precedence is resolved, each selected rule's metadata is evaluated against the resolved `CheckSettings` values. Effects from all declared setting fields are combined:

- `Disabled` takes precedence over `Ignored`.
- `Ignored` removes a rule selected through `ALL`, a category prefix, or a partial selector, but any participating exact rule-code selector restores it, including one retained alongside a higher-priority broad `extend-select`.
- `Disabled` always removes a rule, including one selected by exact rule code.
- Convention `Ignored` effects can encode a profile's choice among antagonistic rules, including a choice to broadly select neither alternative.
- Configured `ignore` selectors and matching per-file ignores still suppress an exactly restored ignored rule.
- Setting effects do not change effective fixability.
- A metadata field name that is not present on `CheckSettings` is a programming error identifying the rule and unknown field.

## Global rule selection

Defaults:

- `select = ["ALL"]`
- `ignore = []`
- `extend-select = []`
- `require-explicit` defaults to the exact rule-code selectors in the runtime `DEFAULT_REQUIRE_EXPLICIT` setting.

Global enabled rules are resolved per rule:

- Use the resolved `select` value as the active rule-selection basis. The source priority of this `select` value is the active select priority.
- Keep `extend-select` only when its source priority is greater than or equal to the active select priority. Lower-priority `extend-select` settings are ignored.
- Keep `ignore` only when its source priority is greater than or equal to the active select priority. Lower-priority `ignore` settings are ignored.
- For each rule, track the strongest matching enabling selector by source priority and specificity.
- For each rule, track the strongest matching disabling selector by source priority and specificity.
- Select the rule only when the enabling selector strength is greater than the disabling selector strength.
- Resolve `require-explicit` as rule selectors. Any selected rule matched by `require-explicit` is removed unless an exact rule-code selector also participated in enabling it.

The output `rules` tuple preserves deterministic rule-code order after filtering.

`require-explicit` is intended for otherwise applicable rules that should remain available through exact selection without being enabled by broad selectors such as `ALL`, `PDF`, or `PCF`. For a rule matched by `require-explicit`, `select = ["ALL"]` does not enable it, while including the rule's exact code in `extend-select` enables it. Setting `require-explicit = []` removes this gate, but it does not override configured ignores, `Ignored` or `Disabled` setting effects, per-file ignores, or incompatibility resolution. Each built-in default entry changes broad selection in at least one settings profile where those independent gates permit the rule.

## Rule incompatibilities

After normal selection precedence, setting effects, and explicit-selection requirements are resolved, selected rule incompatibilities are resolved once for the complete settings profile:

- Rules are considered in deterministic `RuleCollection.rules` order.
- A rule is retained unless it is incompatible with an earlier retained rule.
- A discarded rule does not prevent a later compatible rule from being retained.
- Selector source priority and specificity do not override collection ordering during this final pass.
- Each discarded rule produces one operational error listing all earlier retained rules that conflict with it.
- Per-file ignores run later and do not restore rules discarded by incompatibility resolution.

The built-in opposing pairs (e.g. `PDF106`/`PDF107` and `PDF108`/`PDF109`) are mutually incompatible. Convention-specific setting effects keep every broad built-in convention profile conflict-free by selecting at most one rule from each incompatible pair; a profile may select neither alternative. Exact selection can restore ignored rules. Selecting both rules in either pair retains the lower ordered rule and reports the higher ordered rule as disabled.

`docstring-convention = "pep257"` is the default named convention profile. It does not parse Google sections, NumPy sections, or reStructuredText fields, and it applies PEP 257/pydocstyle-compatible broad-rule carve-outs. `docstring-convention = "none"` also avoids convention-specific parsing, but keeps the stricter generic no-convention rule profile for rules that can act without convention parsing.

## Per-file ignores

Defaults:

- `per-file-ignores = {}`
- `extend-per-file-ignores = {}`

Per-file ignores are resolved from `per-file-ignores` followed by `extend-per-file-ignores`. Both settings are TOML-style mappings from file patterns to lists of rule selectors.

Each field uses the resolved highest-priority value for that field. For example, a command-line `--per-file-ignores` value replaces configured `per-file-ignores`, while a command-line `--extend-per-file-ignores` value contributes through the separate extension field and does not replace configured `per-file-ignores`.

Each per-file ignore entry stores:

- `pattern`: The file pattern exactly as configured.
- `base_path`: The setting source base used for matching the pattern.
- `rule_codes`: The set of rule codes matched by the entry's selectors.
- `rule_specificities`: The strongest selector specificity for each matched rule code.

`RuleSelection.for_path(path)`:

- Converts `path` to a POSIX-style relative path from the per-file-ignore entry's `base_path`.
- Matches per-file ignore patterns with `GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False)`.
- Treats a leading `!` in the pattern as negation: the entry applies to files that do not match the pattern after `!` is removed.
- Removes any globally selected rule whose code is matched by a matching per-file-ignore entry.
- Does not compare per-file-ignore selector specificity against the selector that enabled the rule.

Per-file-ignore bases follow file-selection glob bases: auto-discovered config patterns are relative to their config directory, and explicit config, inline config, and CLI patterns are relative to the current working directory.

Examples:

- `select = ["PDF14"]` with `per-file-ignores = {"tests/*.py" = ["PDF1"]}` removes `PDF142` for matching files.
- `select = ["PDF1"]` with `per-file-ignores = {"tests/*.py" = ["PDF14"]}` removes `PDF142` for matching files and keeps `PDF150`.
- `select = ["PDF14"]` with `per-file-ignores = {"tests/*.py" = ["PDF14"]}` removes `PDF142` for matching files.
- `select = ["PDF"]` with `per-file-ignores = {"!src/*.py" = ["PDF101"]}` removes `PDF101` everywhere except files matching `src/*.py`.
- A lower-priority config-file `per-file-ignores` entry still suppresses a rule selected by a higher-priority command-line `--select`; per-file ignores apply after global rule selection.

`pydocfmt check --show-rules` prints the global active rules and does not apply per-file ignores.

## Per-file settings boundary

Per-file settings are specified in [Settings specification](settings_spec.md). They are intentionally outside rule selection: they apply after global rule selection, do not re-run selector resolution, and cannot change which rules are active. `pydocfmt check --show-rules` therefore remains global/cwd-oriented and does not apply path-specific per-file setting overrides.

## CLI list options

Rule-selection CLI list options accept comma-separated selector values per option occurrence:

```bash
pydocfmt check --select PDF200,PDF110 --ignore PDF203
```

Whitespace around command-line comma-list entries is stripped before validation. This is a pydocformatter CLI parsing delta from Ruff, which treats the whitespace as part of the selector.

Repeated list option occurrences append values within the command-line layer:

```bash
pydocfmt check --select PDF200 --select PDF110
```

Repeated TOML-map option occurrences merge entries within the command-line layer. If the same pattern appears more than once in repeated `--per-file-ignores` or `--extend-per-file-ignores` values, the selector lists are appended:

```bash
pydocfmt check --per-file-ignores '{"tests/*.py" = ["PDF200"]}' --per-file-ignores '{"tests/*.py" = ["PDF110"]}'
```

As with other settings, the resolved command-line value for a field replaces lower-priority values for the same field.

## Fixability

Defaults:

- `fixable = ["ALL"]`
- `unfixable = []`
- `extend-fixable = []`

Effective fixability uses the same source-priority and specificity model as rule selection:

- Use the resolved `fixable` value as the active fixability basis. The source priority of this `fixable` value is the active fixable priority.
- Keep `extend-fixable` only when its source priority is greater than or equal to the active fixable priority. Lower-priority `extend-fixable` settings are ignored.
- Keep `unfixable` only when its source priority is greater than or equal to the active fixable priority. Lower-priority `unfixable` settings are ignored.
- For each rule, track the strongest matching fixable selector by source priority and specificity.
- For each rule, track the strongest matching unfixable selector by source priority and specificity.
- Treat the rule as configured-fixable only when the fixable selector strength is greater than the unfixable selector strength.
- Intersect configured fixability with the rule's `RuleMetadata.fix_availability`.

Settings cannot make a rule with `fix_availability = FixAvailability.NEVER` fixable. Rules with `FixAvailability.ALWAYS`, `FixAvailability.USUALLY`, and `FixAvailability.SOMETIMES` all have available fixes for selector purposes.

A selector in `fixable` or `extend-fixable` that matches only rules with no available fixes is an operational error unless the selector is `ALL`. This means the default `fixable = ["ALL"]` does not warn merely because some collected rules have `FixAvailability.NEVER`.

Examples:

- `fixable = ["PDF14"]` and `unfixable = ["PDF1"]` makes `PDF142` configured-fixable.
- `fixable = ["PDF1"]` and `unfixable = ["PDF14"]` makes `PDF142` configured-unfixable but can leave `PDF150` configured-fixable.
- `fixable = ["PDF14"]` and `unfixable = ["PDF14"]` makes `PDF142` configured-unfixable.
- A command-line `--fixable PDF1` makes `PDF142` configured-fixable even when a lower-priority config file has `unfixable = ["PDF142"]`.
- A command-line `--unfixable PDF1` makes `PDF142` configured-unfixable even when a lower-priority config file has `fixable = ["PDF142"]`.

## Operational errors

Rule selection is tolerant of selector errors. `select_rules()` accumulates nonfatal error strings and continues with invalid or unknown selectors resolving to no rules.

Current error wording:

- Invalid selector: `"{context} contains invalid selector: {selector}"`
- Unknown selector: `"{context} contains unknown selector: {selector}"`
- Fixability selector that only matches rules with no available fixes: `"{context} selector {selector!r} only matches rules with no available fixes"`
- Incompatible selected rule: `"Selected rule {rule} is incompatible with earlier selected rule[s] {conflicts}; {rule} has been disabled"`

Contexts include:

- `rule selection`
- `ignored rules`
- `fixable rules`
- `unfixable rules`
- `per-file ignores for {pattern!r}`

When `pydocfmt check --show-rules` sees rule-selection errors, it prints them before the rule list and exits with status `1`. Normal check execution includes these errors in grouped output handling.

## Resolved selection API

`select_rules(settings, collection=None)` resolves a `CheckSettings` object against a `RuleCollection`. If no collection is passed, it uses `pydocformatter.rules.collection.RULE_COLLECTION`. Callers can pass a `SettingsProfile` to preserve source bases and source priorities from configuration loading; when no profile or explicit field priorities are provided, all selectors are treated as coming from the same source priority.

It returns `RuleSelection`:

- `rules`: A tuple of `SelectedRule` objects in rule-code order.
- `per_file_ignores`: A tuple of resolved `PerFileRuleIgnore` objects.
- `errors`: A tuple of nonfatal operational error strings.
- `collection`: The collection used for resolution.

`SelectedRule` contains:

- `rule`: The rule's `RuleMetadata`.
- `fixable`: The effective fixability after configured and inherent fixability are combined.
- `enabled_priority`: The source priority of the selector that enabled the rule.
- `enabled_specificity`: The global selector specificity that enabled the rule.

`PerFileRuleIgnore` contains:

- `pattern`: The configured path pattern.
- `rule_codes`: A frozenset of matched rule codes.
- `rule_specificities`: A sorted tuple of `(RuleCode, specificity)` pairs.

`RuleSelection.for_path(path)` returns the selected rules after applying matching per-file ignores to the normalized path.

## CLI behavior

`pydocfmt check --show-rules`:

- Resolves rule selection using the loaded settings.
- Prints operational errors first, prefixed with `ERROR: `.
- Prints each globally active rule as `{code}{* if fixable} {name} ({message})`.
- Prints `No active rules.` when no global rules are selected.
- Exits with status `1` if rule-selection errors were reported, otherwise `0`.

Only global rule selection is displayed. Per-file ignores are intentionally not reflected in `--show-rules` output because they depend on a path.

## CLI rule explanations

`pydocfmt rule [RULE|--all]` exposes Ruff-style rule explanations.

- `RULE` must be an exact uppercase rule code, such as `PDF101`; rule names and lowercase codes are invalid.
- `--all` prints all collected rules in rule-code order and cannot be combined with `RULE`.
- `--output-format text` prints the adjacent Markdown rule document directly.
- `--output-format json` prints Ruff-style metadata for one rule, or a list of metadata objects with `--all`; its `explanation` field omits the Markdown title and fixability paragraph.

Rule documents live next to their rule definition modules with the same basename and a `.md` extension. For example, `src/pydocformatter/rules/definitions/PDF/PDF101_docstring_reflow.py` is documented by `src/pydocformatter/rules/definitions/PDF/PDF101_docstring_reflow.md`.

## CLI linter listing

`pydocfmt linter` exposes Ruff-style linter metadata translated from collected rule categories. The public command retains Ruff's terminology even though the internal model uses categories.

- Text output prints a right-aligned prefix/name table.
- JSON output prints a list of objects with `prefix`, `name`, and `url` when a URL is configured.
- The command reports metadata from `RuleCollection.categories` and does not resolve project configuration.
