# Rule Selection Specification

This document specifies how `pydocfmt` discovers rule definitions and resolves rule-selection settings.

## Rule Definitions

Rules live under `pydocformatter.rules.definitions`.

Each implemented rule should be defined in its own module, grouped by prefix:

```text
src/pydocformatter/rules/definitions/PDF/PDF001_reflow_required.py
```

The module registers exactly one `RuleBase` subclass with `@register_rule`. The class defines static metadata:

- `code`: Full rule code, such as `"PDF001"`.
- `prefix`: Alphabetic rule prefix derived from `code`, such as `"PDF"`.
- `number`: Numeric rule suffix derived from `code`, such as `1`.
- `name`: Stable machine-readable rule name, such as `"reflow-required"`.
- `message`: Default diagnostic message. It may include format fields such as `{section}` for per-finding message customization.
- `fixable`: Whether the rule is inherently fixable in at least some situations.

No rule application or fix method interface is specified yet. That interface will be added when rule execution is implemented.

## Collection

`pydocformatter.rules.collection.collect_rules()` imports every module below `rules/definitions/**` and returns a `RuleCollection` built from decorated rule classes.

The initial catalog intentionally contains no implemented rules. With the default settings, an empty catalog resolves to an empty active ruleset without errors.

Rule codes are the canonical lookup keys. Each rule code belongs to the alphabetic prefix at the start of the code, such as `PDF` for `PDF001`.

## Selector Grammar

Rule selectors are:

- `ALL`: Matches all collected rules.
- Full rule code: `PDF001`.
- Prefix: `PDF`.
- Prefix plus leading digits: `PDF10`, matching rules whose full code starts with that string.

Selectors are case-sensitive. Selectors outside this grammar, or selectors that match no collected rule, are treated as operational errors. The command reports them, resolves the affected selector to no rules, and continues.

## Selection

Global enabled rules are resolved as:

```text
(select + extend-select) - ignore
```

Rules remain in deterministic rule-code order.

Per-file ignores are resolved from `per-file-ignores` and `extend-per-file-ignores` after global selection. A selected ruleset exposes path-specific selection so future formatter code can apply file-specific rule choices without changing settings resolution again.

## Fixability

Effective fixability is resolved as:

```text
(fixable + extend-fixable) - unfixable
```

This result is intersected with the rule definition's inherent `fixable` value. Settings cannot make an inherently unfixable rule fixable.

A selector in `fixable` or `extend-fixable` that matches only inherently unfixable rules is reported as an operational error unless the selector is `ALL`. The default `fixable = ["ALL"]` must not warn merely because some collected rules are unfixable.

## CLI Rule Explanations

A future Ruff-style command may expose rule explanations, similar to `ruff rule`. The intended source is the collected rule metadata plus rule class documentation, with text and JSON output formats. This command is not part of the current implementation.
