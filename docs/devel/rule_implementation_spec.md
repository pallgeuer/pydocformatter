# Rule implementation specification

This document specifies how pydocformatter rule categories, rule implementations, adjacent rule documentation, and rule tests are structured.

## Rule identity and layout

Rule categories live under `src/pydocformatter/rules/definitions/<PREFIX>/`. Each category package contains a prefix-named category module, adjacent category documentation, and zero or more rule modules:

```text
src/pydocformatter/rules/definitions/PDF/PDF.py
src/pydocformatter/rules/definitions/PDF/PDF.md
src/pydocformatter/rules/definitions/PDF/PDF101_docstring_reflow.py
src/pydocformatter/rules/definitions/PDF/PDF101_docstring_reflow.md
```

Category modules define exactly one `RuleCategoryBase` subclass named after the prefix and register it with `@rule_registration.register_rule_category`. Rule modules define exactly one local `RuleBase` subclass, define no category class, and register the rule with `@rule_registration.register_rule_to(<CATEGORY>)`.

Rule module stems use `<CODE>_<rule_name_with_underscores>`. Rule class names use `<CODE><RuleNamePartsCapitalized>`. Rule metadata names use stable kebab-case. Built-in rule file stems, class names, metadata names, and Markdown headings must agree.

Rule code prefixes and numeric ranges are documented in each category document. `docs/public/ruff_rule_links.md` is the user-facing Ruff-rule mapping.

## Metadata and selection contract

Every rule class defines `meta = RuleMetadata(...)` with:

- `code`: A `RuleCode` matching the module stem and category prefix.
- `name`: Stable kebab-case public rule name.
- `message`: Default diagnostic message.
- `fix_availability`: `FixAvailability.ALWAYS`, `USUALLY`, `SOMETIMES`, or `NEVER`.
- `stable_since`: The pydocformatter version where the rule is stable.
- `setting_effects`: A tuple, explicitly `()` when empty.
- `incompatible_with`: A tuple, explicitly `()` when empty.
- `check_kind`: The rule execution kind.
- `cache_behavior`: An intentional persistent-cache dependency declaration. Built-in file-local rules pass `cache_behavior=RuleCacheBehavior.FILE_LOCAL` directly to `RuleMetadata(...)`; omitting the argument fails closed as uncacheable.

Rule incompatibilities must be declared on both rules. Rule collection rejects one-sided, self-referential, unknown, or duplicate incompatibilities.

After normal selector precedence and selection gates are applied, incompatible rules are ranked by their effective selector source priority and specificity. A stronger rule silently overrides weaker incompatible rules. Equal-strength conflicts retain the earlier rule in collection order and produce an operational error. Resolution considers the complete incompatibility graph strongest-first before restoring normal collection order for execution.

Setting effects describe selection behavior only. Use `Disabled` when a resolved setting value leaves the rule without a meaningful target and exact selection must not restore it. Use `Ignored` when a settings profile declines the rule's policy but exact selection may restore it. For `docstring-convention`, this includes choosing among mutually incompatible alternatives: a convention may broadly select either alternative or neither, and every current convention may legitimately decline the same alternative. Every broad built-in convention profile must remain conflict-free. A rule disabled under every convention is unreachable and invalid. A setting effect must name a resolved `CheckSettings` field.

Use the default `require-explicit` setting when a broadly applicable rule should require explicit selection independently of convention because it is unusually strict, noisy, or project-specific. Separate `Disabled` effects may still remove the rule under convention values where it has no meaningful target. Every default entry must be the effective broad-selection blocker in at least one otherwise applicable built-in settings profile. Do not add a rule removed by every convention merely to label its effective opt-in behavior; generated rule documentation identifies that state as `Convention opt-in`.

## Rule execution contract

Standard rules implement:

```python
@classmethod
def violations(cls, context: RuleContext) -> tuple[RuleViolation, ...]: ...
```

`violations()` must be a class method accepting exactly one required positional argument named `context`. Suppression-audit rules may omit `violations()` when the runner synthesizes their findings.

Rule code reads source state from `RuleContext`. Category-level shared data is prepared by `RuleCategoryBase.prepare()` and exposed through `context.category_data`; categories that provide typed data should also provide a checked accessor such as `PDF.require_data(context)` or `PCF.require_data(context)`.

Categories whose source directives may cover complete string expressions override `RuleCategoryBase.suppression_expression_ranges()` and return the exact line-and-column `CodeRange` values eligible for that category. The default is no expanded expression coverage. Derive these ranges from the same prepared category data that identifies the semantic expressions instead of independently approximating their syntax in the suppression parser. The suppression parser discovers prefix-neutral candidate ranges, and the runner authorizes them only while filtering the active category.

Cacheable rule finding and error behavior may depend only on source bytes, effective settings classified as direct analysis values, the final ordered rule codes, `context.source_path`, engine identity, and the concrete line ending. Rule code receives the complete `CheckSettings`, but a cacheable rule must not make finding or error existence depend on excluded run controls, discovery inputs, raw selection values, configuration provenance, or fixability. A rule that reads other project files, environment variables, clocks, random state, subprocess output, network data, mutable global state, or another excluded input must remain `UNCACHEABLE` until that dependency has a canonical invalidation fingerprint. New dependency kinds must be documented and tested before cacheability is enabled.

Configured fixability remains available to the runner for finding labels and repair decisions, but it is not part of final rule-code identity. Persistent proofs are populated only for finding-free, error-free on-disk source states, so a reusable proof has no finding whose label or fix behavior could change. If future behavior makes fixability affect whether a finding or analysis error exists, its identity treatment and invalidation tests must change with that behavior.

Category `prepare()` data is read-only for the current module. If a fix changes the module, the runner prepares fresh category data for the new module state before later rules rely on it.

Rule code must not read or apply source suppressions. The runner filters suppressed violations, applies configured effective fixability, validates source-edit consistency, applies fixes, and accounts for fixed and unfixed findings.

## Violations and source fixes

Each rule issue is reported as one `RuleViolation`. Built-in rule modules and reusable rule-definition helpers construct violations through `pydocformatter.rules.violations` helpers instead of constructing `RuleFinding`, `RuleViolation`, or `RuleSourceFix` directly.

Use `rule_violations.diagnostic()` for diagnostic-only issues. Use `violation_for_planned_source_change()`, `violations_for_planned_source_changes()`, or `violation_for_optional_planned_source_change()` for issues backed by `PlannedSourceChange` source edits.

Findings and planned changes must use non-empty positive one-based source line targets that point into the current source. Suppression line targets must also be non-empty positive line-number tuples. For fixable violations, planned change line targets and suppression targets must match the finding targets.

Always-fixable rules must attach a source fix to every reported violation. Never-fixable rules must not attach source fixes. Usually-fixable and sometimes-fixable rules report per-instance fixability through the violation helpers.

Classify inherent fix availability by the rule's designed corrections, not by observed finding frequency. Use `USUALLY` when every semantic violation kind reported by the rule has a defined automatic correction, but an individual finding can remain non-fixable because conservative source mapping, content ambiguity, syntax validation, or value-preservation checks reject that instance. Use `SOMETIMES` when at least one semantic violation kind is intentionally diagnostic-only even for ordinary, exactly mapped source while another kind has a fix. Candidates that the rule skips, configured fixability selectors, and how often unusual source forms occur do not affect this classification.

Source fixes are planned source edits only. Rules do not return replacement LibCST modules, mutate the `RuleContext`, or apply edits themselves.

Canonical source-edit application returns `AppliedSourceChanges`, which retains both the reparsed LibCST module and the exact edited source. Production execution and direct-rule test helpers must consume this same result contract; callers must not substitute `module.code` when exact source can differ through LibCST normalization.

The rule runner may skip structural reparsing only when the module was parsed directly from the accompanying exact source. Arbitrary module/source pairs must be reparsed and structurally compared before rendered positions are mapped onto exact source.

Reusable parsing, rendering, and source-edit behavior belongs in existing helpers under `src/pydocformatter/rules/definition_helpers/` or `src/pydocformatter/rules/edits.py` when it has more than one rule-level use.

## Documentation and tests

Each built-in rule has adjacent Markdown documentation with the same stem as its Python file. Rule documents follow `src/pydocformatter/rules/templates/rule_template.md`; category documents follow `src/pydocformatter/rules/templates/rule_category_template.md`.

Each new or changed rule updates `docs/devel/rule_settings_audit.md`. Audit every setting read by the rule implementation, by category preparation data the rule consumes, and by helper functions called from the rule path. The audit's `Options settings to document` column is the source of truth for parseable setting bullets in the rule's `## Options` section.

Rule documents start with `# <rule-name> (<CODE>)`, include the fix availability sentence matching `RuleMetadata.fix_availability`, document setting effects and incompatibilities when present, and include focused structured `pydocfmt-example` blocks. Include `[settings]` or an `[input=PATH]` display path only when it is pertinent to the applied rule or necessary to understand the scenario. Pertinent context includes active conventions and parser modes, configured thresholds and boundaries, public/private/package classification, and contrasts referenced by the lead-in prose, even when a setting matches the current default. Do not require readers to know default setting values. Use `[output=unchanged]` when output equals input. Include `[findings]` only for findings that remain after fixing, with exact diagnostic messages.

Rule-specific tests live under `tests/rules/<PREFIX>/test_<CODE>.py`. Category parser or shared-data changes also update category aggregate tests such as `tests/rules/<PREFIX>/test_<PREFIX>.py`. Tests cover diagnostics, fixes, no-op cases, settings interactions, edge cases, line endings when relevant, idempotence, unsafe-fix behavior, and source-suppression behavior when applicable.

Direct rule-hook tests use the shared direct-rule helpers in `tests/rule_helpers.py`; those helpers validate returned violations and planned source changes through the runner contract before exposing findings or applying fixes.

CLI tests are required when a rule affects `pydocfmt check`, `--show-rules`, `pydocfmt rule`, output messages, or selection behavior. Settings tests and rule-selection tests are required when a rule introduces settings, setting effects, fixability behavior, or conflicts.

## Loader and verification invariants

The built-in loader validates that:

- `src/pydocformatter/rules/definitions/` contains only category packages.
- Each category package contains a matching `<PREFIX>.py` category module and adjacent `<PREFIX>.md`.
- Rule modules are named `<CODE>_<suffix>.py`, where the code prefix matches the category package.
- Each rule module defines exactly one local `RuleBase` subclass and no category class.
- Each rule class is registered with its category.
- Each rule has adjacent Markdown with the same stem as the Python file.
- Orphan Markdown files in a category package are rejected.

Rule implementation changes update `CHANGELOG.md` under `## Unreleased` when they are significant user-facing or developer-facing work. If a change modifies function signatures, dataclass fields, enum values, or class attributes, affected docstrings are updated in the same change.

Focused rule verification normally starts with:

```bash
uv run pytest tests/rules/<PREFIX>/test_<CODE>.py
uv run pytest tests/test_rules.py tests/test_formatting_rules_doc.py tests/test_rule_markdown_examples.py
```

Broader changes additionally run the relevant category tests, settings tests, CLI tests, full pytest suite, `uv run ruff check`, `uv run pydocfmt check`, `uv run ruff format --check`, and `uv run ty check` as appropriate. Pytest uses project-default multiprocessing through pytest-xdist; pass `-n 0` for serial debugging or focused runs where worker startup is slower.
