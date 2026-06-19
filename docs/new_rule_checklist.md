# New Rule Checklist

Use this checklist when adding, renaming, renumbering, or substantially changing a rule. Most new rules only need the category-specific rule files, adjacent rule documentation, tests, `docs/formatting_rules.md`, and `CHANGELOG.md`; new categories and new settings require the extra sections below.

## Choose the Rule Identity

- Pick the rule category prefix and numeric range before writing code.
- Check the category documentation at `src/pydocformatter/rules/definitions/<PREFIX>/<PREFIX>.md` for the intended code ranges.
- Check `docs/formatting_rules.md` for nearby rules, Ruff overlap, and whether the rule should replace, complement, or intentionally avoid a Ruff rule.
- Decide the stable metadata values up front: code, kebab-case name, diagnostic message, fix availability, `stable_since`, setting effects, and incompatible rules.
- If the rule conflicts with another pydocformatter rule, update `incompatible_with` on both rules. Rule collection rejects one-sided or unknown incompatibilities.

## Implement the Rule

- Create `src/pydocformatter/rules/definitions/<PREFIX>/<CODE>_<rule_name_with_underscores>.py`.
- Define exactly one `RuleBase` subclass in the module.
- Name the class `<CODE><RuleNamePartsCapitalized>`, matching the file stem and metadata name.
- Register the class with `@rule_registration.register_rule_to(<CATEGORY>)`.
- Set `meta = RuleMetadata(...)` with explicit `setting_effects=()` and `incompatible_with=()` when they are empty.
- Implement `check()` for diagnostics and `fix()` only when the rule has automatic fixes.
- Use the category's prepared data accessor when one exists, such as `PDF.require_data(context)` or `PCF.require_data(context)`.
- Keep shared parsing, rendering, or source-edit behavior in the existing helper modules under `src/pydocformatter/rules/definition_helpers/` or `src/pydocformatter/rules/edits.py` when the behavior is reusable.
- If the rule changes function signatures, dataclass fields, enum values, or class attributes, update the affected docstrings in the same change.

## Touch Category Code Only When Needed

- Update `src/pydocformatter/rules/definitions/<PREFIX>/<PREFIX>.py` if the rule needs new shared category data, shared helper methods, parser outputs, enums, or source classification.
- Keep category `prepare()` data read-only for the current module.
- Add or update category-level tests when category parsing, preprocessing, or shared data changes.
- For a new category, create `src/pydocformatter/rules/definitions/<PREFIX>/__init__.py`, `<PREFIX>.py`, and `<PREFIX>.md`; register the category with `@rule_registration.register_rule_category`.

## Document the Rule Beside the Code

- Create `src/pydocformatter/rules/definitions/<PREFIX>/<CODE>_<rule_name_with_underscores>.md`.
- Start from `src/pydocformatter/rules/templates/rule_template.md`.
- Make the first heading exactly `# <rule-name> (<CODE>)`.
- Include the fix availability line that matches `RuleMetadata.fix_availability`.
- Document setting effects and incompatibilities when present.
- Include at least one structured `pydocfmt-example` block. `tests/test_rule_markdown_examples.py` executes every structured example against the implementation.
- Use `[output=unchanged]` when the output is identical to the input.
- Add a `[findings]` section only for findings that remain after fixing, and include the exact diagnostic message.
- Keep examples focused enough that failures point to the rule being documented.

## Update User-Facing Rule Tables

- Update `docs/formatting_rules.md`.
- Add the rule to the pydocformatter category table in code order.
- Fill in name, message, fixability, stable version, convention cells, conflicts, Ruff rule mapping, and a concise comment.
- If the rule replaces or changes guidance for a Ruff rule, update the Ruff Rules table too.
- If the rule introduces or materially changes configuration, update the Rule Configuration section and any affected README configuration text.
- Run the Markdown table tests after editing tables; table padding and metadata cells are checked.

## Update Settings When Needed

- Add new settings to the settings schema in `src/pydocformatter/cli/settings_check.py`.
- Add CLI/config wiring where appropriate in `src/pydocformatter/cli/`, `src/pydocformatter/settings.py`, and any relevant docs.
- Add setting effect metadata to rule definitions when a setting ignores or disables a rule.
- Update rule-selection behavior only when the existing generic setting-effect model is insufficient.
- Add settings tests in `tests/test_settings.py` and rule-selection tests in `tests/test_rules.py` when the setting affects enabled rules, fixability, or conflicts.

## Add Tests

- Add rule-specific tests under `tests/rules/<PREFIX>/test_<CODE>.py`.
- Update category aggregate tests such as `tests/rules/<PREFIX>/test_<PREFIX>.py` when the category-wide behavior or ordering changes.
- Cover diagnostics, fixes, no-op cases, settings interactions, edge cases, line endings when relevant, idempotence, and unsafe-fix behavior.
- Add helper tests under `tests/rules/definition_helpers/` when shared helper behavior changes.
- Add CLI tests when the rule affects `pydocfmt check`, `--show-rules`, `pydocfmt rule`, output messages, or selection behavior.
- Add or update Markdown example tests indirectly by ensuring the rule documentation examples are structured and executable.

## Update Release Notes

- Add a concise `CHANGELOG.md` entry under `## Unreleased`.
- Use the existing Added, Changed, Fixed, or Removed heading.
- Put rule additions under a short bold category such as `**Docstring formatting:**`, `**Rule documentation:**`, or `**Developer workflow:**`.
- If the exact wording of user-facing messages changes and tests fail only because of that wording, ask before reverting the wording.

## Verify

Run focused tests first, then broaden as needed:

```bash
uv run pytest tests/rules/<PREFIX>/test_<CODE>.py
uv run pytest tests/test_rules.py tests/test_formatting_rules_doc.py tests/test_rule_markdown_examples.py
uv run pytest
uv run mypy
uv run black --check .
uv run isort --check .
uv run pydocfmt check --legacy
```

Use narrower test commands while iterating when the changed surface is small. Run the full suite before finishing a broad rule, category parser, settings, or documentation-table change.

## Loader and Packaging Invariants

The built-in rule loader validates these details during tests:

- `src/pydocformatter/rules/definitions/` contains only category packages.
- Each category package contains a matching `<PREFIX>.py` category module and adjacent `<PREFIX>.md`.
- Rule modules are named `<CODE>_<suffix>.py`, where the code prefix matches the category package.
- Each rule module defines exactly one local `RuleBase` subclass and no category class.
- Each rule class is registered with its category.
- Each rule has adjacent Markdown with the same stem as the Python file.
- Orphan Markdown files in a category package are rejected.
- Built-in rule file stems, class names, metadata names, and Markdown headings must agree.
