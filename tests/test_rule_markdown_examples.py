import collections
import dataclasses
import tomllib

import libcst as cst
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
import pydocformatter.rules.line_endings as line_endings
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.runner as rule_runner
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli import global_args, settings_check
from pydocformatter.rules.codes import RuleCode

_RULE_SELECTION_SETTING_KEYS = frozenset(definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.group == settings_check.SettingsGroup.RULE_SELECTION)


@dataclasses.dataclass(frozen=True)
class _PreparedRuleMarkdownExample:
    """Shared prepared state for one structured rule Markdown example."""

    index: int
    example: rule_documentation.RuleMarkdownExample
    path: str
    settings: settings_check.CheckSettings
    selection: rules_selection.RuleSelection
    check_result: formatter.FormatterResult


def _rule_cases() -> tuple[tuple[str, type[object]], ...]:
    """Return built-in rule cases for pytest parametrization."""
    return tuple((rule_class.meta.code.tag, rule_class) for rule_class in rule_collection.RULE_COLLECTION.rules)


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
@pytest.mark.parametrize(("rule_code", "rule_class"), _rule_cases())
def test_rule_markdown_examples_match_rule_implementation(rule_code: str, rule_class: type[object]) -> None:
    """Execute every structured rule Markdown example against the documented rule."""
    prepared_examples = _prepared_rule_markdown_examples(rule_code, rule_class)

    for prepared in prepared_examples:
        result = formatter.format_source(prepared.example.input_source, prepared.path, settings=prepared.settings, rule_selection=prepared.selection, fix=True)

        assert result.errors == (), f"{rule_code} example {prepared.index}: unexpected formatter errors: {result.errors}"
        assert result.new_source == prepared.example.output_source, f"{rule_code} example {prepared.index}: output did not match documented output"
        assert _finding_key(result.unfixed_findings) == prepared.example.findings, f"{rule_code} example {prepared.index}: unfixed findings did not match documented findings"
        _assert_clean_example_has_no_hidden_fix_changes(rule_code, prepared)
        _assert_initial_check_findings_accounted_after_fixing(rule_code, prepared)


def _prepared_rule_markdown_examples(rule_code: str, rule_class: type[object]) -> tuple[_PreparedRuleMarkdownExample, ...]:
    """Return shared prepared state for all structured examples for one rule."""
    markdown = rule_documentation.load_rule_explanation(rule_class)
    examples = rule_documentation.parse_rule_markdown_examples(markdown, rule_code=rule_code)
    assert examples, f"{rule_code}: expected at least one structured pydocfmt-example block"

    prepared_examples: list[_PreparedRuleMarkdownExample] = []
    for index, example in enumerate(examples, start=1):
        _validate_rule_selection_settings(rule_code, index, example)
        settings = _settings_for_example(rule_code, example)
        selection = rules_selection.select_rules(settings)
        assert selection.errors == (), f"{rule_code} example {index}: unexpected rule selection errors: {selection.errors}"

        path = example.path or f"{rule_code}_example_{index}.py"
        check_result = formatter.format_source(example.input_source, path, settings=settings, rule_selection=selection, fix=False)
        assert check_result.errors == (), f"{rule_code} example {index}: unexpected check errors: {check_result.errors}"
        prepared_examples.append(_PreparedRuleMarkdownExample(index=index, example=example, path=path, settings=settings, selection=selection, check_result=check_result))
    return tuple(prepared_examples)


def _assert_clean_example_has_no_hidden_fix_changes(rule_code: str, prepared: _PreparedRuleMarkdownExample) -> None:
    """Check-clean documented examples must not be changed by a direct fix pass."""
    if any(finding.fixable for finding in prepared.check_result.unfixed_findings):
        return

    module = cst.parse_module(prepared.example.input_source)
    selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in prepared.selection.for_path(prepared.path)}
    errors: list[str] = []
    fixed_module, fixed_findings, source_changed = rule_runner._run_fix_pass(
        module,
        path=prepared.path,
        settings=prepared.settings,
        line_ending=line_endings.resolve_line_ending(prepared.example.input_source, line_ending=prepared.settings.line_ending),
        rule_selection=prepared.selection,
        selected_rule_by_code=selected_rule_by_code,
        errors=errors,
    )

    assert errors == [], f"{rule_code} example {prepared.index}: unexpected direct fix errors: {errors}"
    assert fixed_findings == (), f"{rule_code} example {prepared.index}: direct fix reported findings after a clean check"
    assert not source_changed, f"{rule_code} example {prepared.index}: direct fix changed source after a clean check"
    assert fixed_module.code == prepared.example.input_source, f"{rule_code} example {prepared.index}: direct fix returned different source after a clean check"


def _assert_initial_check_findings_accounted_after_fixing(rule_code: str, prepared: _PreparedRuleMarkdownExample) -> None:
    """Documented examples must account for every initial check finding as fixed or still unfixed."""
    line_ending = line_endings.resolve_line_ending(prepared.example.input_source, line_ending=prepared.settings.line_ending)
    module = cst.parse_module(prepared.example.input_source)
    fixed_result = rule_runner.run_rules(
        module, path=prepared.path, settings=prepared.settings, line_ending=line_ending, rule_selection=prepared.selection, fix=True, source=prepared.example.input_source
    )

    assert fixed_result.errors == (), f"{rule_code} example {prepared.index}: unexpected fix errors: {fixed_result.errors}"
    initial_finding_counts = collections.Counter(_finding_correspondence_key(prepared.check_result.unfixed_findings))
    accounted_finding_counts = collections.Counter(_finding_correspondence_key(fixed_result.fixed_findings + fixed_result.unfixed_findings))
    assert initial_finding_counts == accounted_finding_counts, f"{rule_code} example {prepared.index}: initial check findings were not accounted for as fixed or still unfixed"


def test_parse_rule_markdown_examples_preserves_nested_shorter_fences() -> None:
    """Nested shorter code fences do not close the outer example block."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """````pydocfmt-example
[input]
# ```python
# value = 1
# ```

[output=unchanged]
````
""",
        rule_code="PCF001",
    )

    assert examples[0].input_source == "# ```python\n# value = 1\n# ```\n"


def test_parse_rule_markdown_examples_rejects_reversed_finding_ranges() -> None:
    """Finding ranges must not silently collapse to no lines."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="invalid reversed finding range"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Lines 5-3: Example message
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_rejects_mismatched_finding_line_labels() -> None:
    """Finding line labels must match singular and plural line references."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="expected 'Line'"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Lines 5: Example message
```
""",
            rule_code="PDF101",
        )

    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="expected 'Lines'"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 3-4: Example message
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_treats_degenerate_ranges_as_single_lines() -> None:
    """A degenerate finding range is singular because it expands to one line."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4-4: Example message
```
""",
        rule_code="PDF101",
    )

    assert examples[0].findings == ((RuleCode("PDF101"), (4,), "Example message"),)

    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="expected 'Line'"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Lines 4-4: Example message
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_requires_finding_messages() -> None:
    """Finding lines must include the exact expected message."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="invalid finding line"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4
```
""",
            rule_code="PDF101",
        )

    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="invalid finding line"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4: 
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_preserves_exact_finding_messages() -> None:
    """Finding messages are parsed exactly and duplicate finding locations are preserved."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4: First exact message
PDF101: Line 4: Second exact message: with colon
```
""",
        rule_code="PDF101",
    )

    assert examples[0].findings == (
        (RuleCode("PDF101"), (4,), "First exact message"),
        (RuleCode("PDF101"), (4,), "Second exact message: with colon"),
    )


def test_parse_rule_markdown_examples_rejects_output_matching_input() -> None:
    """Unchanged examples must use the explicit unchanged output marker."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match=r"use \[output=unchanged\]"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
value = "kept"

[output]
value = "kept"
```
""",
            rule_code="PDF000",
        )


def test_parse_rule_markdown_examples_preserves_section_source_text() -> None:
    """Section parsing keeps byte-relevant source text inside the section body."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
value = "kept"

[output]
value = "changed"
```
""",
        rule_code="PDF000",
    )

    assert examples[0].input_source == 'value = "kept"\n'
    assert examples[0].output_source == 'value = "changed"\n'


def test_parse_rule_markdown_examples_preserves_bracketed_input_source_lines() -> None:
    """Input-like bracketed source lines are not treated as invalid markers."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
[input_map]
value = "kept"

[output=unchanged]
```
""",
        rule_code="PDF000",
    )

    assert examples[0].input_source == '[input_map]\nvalue = "kept"\n'
    assert examples[0].output_source == examples[0].input_source


def test_parse_rule_markdown_examples_allows_input_paths() -> None:
    """An input marker can carry a path for path-sensitive rules."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input=package/__init__.py]
value = "kept"

[output=unchanged]
```
""",
        rule_code="PDF000",
    )

    assert examples[0].path == "package/__init__.py"


def test_parse_rule_markdown_examples_rejects_invalid_input_paths() -> None:
    """Input path markers must contain a non-empty display path without marker syntax."""
    for marker in ("[input=]", "[input = package/module.py]", "[input=package].py]"):
        with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match=r"invalid \[input=PATH\] marker"):
            rule_documentation.parse_rule_markdown_examples(
                f"""```pydocfmt-example
{marker}
value = "kept"

[output=unchanged]
```
""",
                rule_code="PDF000",
            )


def _validate_rule_selection_settings(rule_code: str, example_number: int, example: rule_documentation.RuleMarkdownExample) -> None:
    """Validate test-owned rule-selection settings are not overridden by examples."""
    if not example.settings_text:
        return
    try:
        settings = tomllib.loads(example.settings_text)
    except tomllib.TOMLDecodeError as error:
        raise AssertionError(f"{rule_code} example {example_number}: invalid [settings] TOML: {error}") from error
    rule_selection_settings = tuple(sorted(_RULE_SELECTION_SETTING_KEYS & settings.keys()))
    if rule_selection_settings:
        raise AssertionError(f"{rule_code} example {example_number}: rule-selection settings are controlled by the test: {', '.join(rule_selection_settings)}")


def _settings_for_example(rule_code: str, example: rule_documentation.RuleMarkdownExample) -> settings_check.CheckSettings:
    """Return resolved settings for one example, with only the documented rule selected."""
    config_options = (example.settings_text,) if example.settings_text else ()
    return settings_check.SETTINGS_SCHEMA.load(
        global_values=global_args.GlobalArgs(config_options=config_options, isolated=True),
        field_overrides=settings_check.CheckSettingsOverrides(select=(rule_code,)),
    )


def _finding_key(findings: tuple[rule_models.RuleFinding, ...]) -> tuple[tuple[RuleCode, tuple[int, ...], str], ...]:
    """Return the comparable shape for formatter findings."""
    return tuple((finding.rule.code, finding.line_numbers, finding.message) for finding in findings)


def _finding_correspondence_key(findings: tuple[rule_models.RuleFinding, ...]) -> tuple[tuple[RuleCode, tuple[int, ...], bool], ...]:
    """Return the comparable shape for check/fix correspondence."""
    return tuple((finding.rule.code, finding.line_numbers, finding.fixable) for finding in findings)
