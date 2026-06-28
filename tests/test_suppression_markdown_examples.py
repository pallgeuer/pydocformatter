import pathlib
import tomllib

import pydocformatter.formatter as formatter
import pydocformatter.rules.documentation as rule_documentation
import pydocformatter.rules.models as rule_models
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli import global_args, settings_check
from pydocformatter.rules.codes import RuleCode

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUPPRESSIONS_PATH = ROOT / "docs" / "rule_suppressions.md"


def test_suppression_markdown_examples_match_formatter_behavior() -> None:
    """Execute structured suppression guide examples against the formatter."""
    markdown = SUPPRESSIONS_PATH.read_text(encoding="utf-8")
    examples = rule_documentation.parse_rule_markdown_examples(markdown, rule_code="SUPPRESSIONS")

    assert examples, "Expected at least one structured suppression guide example"
    for index, example in enumerate(examples, start=1):
        _validate_example_settings(index, example)
        settings = _settings_for_example(example)
        selection = rules_selection.select_rules(settings)
        assert selection.errors == (), f"suppression example {index}: unexpected rule selection errors: {selection.errors}"

        result = formatter.format_source(example.input_source, f"suppressions_example_{index}.py", settings=settings, rule_selection=selection, fix=True)

        assert result.errors == (), f"suppression example {index}: unexpected formatter errors: {result.errors}"
        assert result.new_source == example.output_source, f"suppression example {index}: output did not match documented output"
        assert _finding_key(result.unfixed_findings) == example.findings, f"suppression example {index}: unfixed findings did not match documented findings"


def _validate_example_settings(example_number: int, example: rule_documentation.RuleMarkdownExample) -> None:
    """Validate suppression guide examples declare explicit focused rule selection."""
    if not example.settings_text:
        raise AssertionError(f"suppression example {example_number}: expected [settings] with explicit select")
    try:
        settings = tomllib.loads(example.settings_text)
    except tomllib.TOMLDecodeError as error:
        raise AssertionError(f"suppression example {example_number}: invalid [settings] TOML: {error}") from error
    if "select" not in settings:
        raise AssertionError(f"suppression example {example_number}: expected explicit select setting")


def _settings_for_example(example: rule_documentation.RuleMarkdownExample) -> settings_check.CheckSettings:
    """Return resolved settings for one suppression guide example."""
    return settings_check.SETTINGS_SCHEMA.load(
        global_values=global_args.GlobalArgs(config_options=(example.settings_text,), isolated=True),
    )


def _finding_key(findings: tuple[rule_models.RuleFinding, ...]) -> tuple[tuple[RuleCode, tuple[int, ...], str], ...]:
    """Return the comparable shape for formatter findings."""
    return tuple((finding.rule.code, finding.line_numbers, finding.message) for finding in findings)
