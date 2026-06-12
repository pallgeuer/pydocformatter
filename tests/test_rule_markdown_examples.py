import tomllib

import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
import pydocformatter.rules.models as rule_models
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli import global_args, settings_check
from pydocformatter.rules.codes import RuleCode

_RULE_SELECTION_SETTING_KEYS = frozenset(definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.group == settings_check.SettingsGroup.RULE_SELECTION)


def _rule_cases() -> tuple[tuple[str, type[object]], ...]:
    """Return built-in rule cases for pytest parametrization."""
    return tuple((rule_class.meta.code.tag, rule_class) for rule_class in rule_collection.RULE_COLLECTION.rules)


@pytest.mark.parametrize(("rule_code", "rule_class"), _rule_cases())
def test_rule_markdown_examples_match_rule_implementation(rule_code: str, rule_class: type[object]) -> None:
    """Execute every structured rule Markdown example against the documented rule."""
    markdown = rule_documentation.load_rule_explanation(rule_class)
    examples = rule_documentation.parse_rule_markdown_examples(markdown, rule_code=rule_code)
    assert examples, f"{rule_code}: expected at least one structured pydocfmt-example block"

    for index, example in enumerate(examples, start=1):
        _validate_rule_selection_settings(rule_code, index, example)
        settings = _settings_for_example(rule_code, example)
        selection = rules_selection.select_rules(settings)
        assert selection.errors == (), f"{rule_code} example {index}: unexpected rule selection errors: {selection.errors}"

        result = formatter.format_source(example.input_source, f"{rule_code}_example_{index}.py", settings=settings, rule_selection=selection, fix=True)

        assert result.errors == (), f"{rule_code} example {index}: unexpected formatter errors: {result.errors}"
        assert result.new_source == example.output_source, f"{rule_code} example {index}: output did not match documented output"
        assert _finding_key(result.unfixed_findings) == example.findings, f"{rule_code} example {index}: unfixed findings did not match documented findings"


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
PDF001: 5-3
```
""",
            rule_code="PDF001",
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


def _finding_key(findings: tuple[rule_models.RuleFinding, ...]) -> tuple[tuple[RuleCode, tuple[int, ...]], ...]:
    """Return the comparable shape for formatter findings."""
    return tuple((finding.rule.code, finding.line_numbers) for finding in findings)
