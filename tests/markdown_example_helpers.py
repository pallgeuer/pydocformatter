"""Test adapters for executable structured Markdown examples."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter import formatter, rules_selection
from pydocformatter.cli import global_args, settings_check


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.codes import RuleCode
    from pydocformatter.rules.models import RuleFinding


@dataclasses.dataclass(frozen=True)
class MarkdownExampleOutcome:
    """Resolved state and formatter results for one Markdown example.

    Attributes:
        label (str): Human-readable example identifier used in assertion failures.
        example (rule_documentation.RuleMarkdownExample): Parsed source, output, settings, and findings contract.
        path (str): Synthetic or documented source path used for rule selection and formatting.
        settings (settings_check.CheckSettings): Isolated settings resolved from the example and test-owned overrides.
        selection (rules_selection.RuleSelection): Rules selected under the resolved settings for the example path.
        check_result (formatter.FormatterResult): Read-only formatter result for the documented input.
    """

    label: str
    example: rule_documentation.RuleMarkdownExample
    path: str
    settings: settings_check.CheckSettings
    selection: rules_selection.RuleSelection
    check_result: formatter.FormatterResult


def execute_markdown_example(
    example: rule_documentation.RuleMarkdownExample, *, label: str, fallback_path: str, field_overrides: settings_check.CheckSettingsOverrides | None = None
) -> MarkdownExampleOutcome:
    """Execute and verify one structured Markdown formatter example.

    Args:
        example (rule_documentation.RuleMarkdownExample): Parsed example contract to execute.
        label (str): Identifier included in assertion messages.
        fallback_path (str): Source path used when the example does not document one.
        field_overrides (settings_check.CheckSettingsOverrides | None): Test-owned setting overrides applied after the
            documented settings.

    Returns:
        Resolved settings, selection, and verified check result.
    """
    path = example.path if example.path is not None else fallback_path
    config_options = (example.settings_text,) if example.settings_text else ()
    settings = settings_check.SETTINGS_SCHEMA.load(
        global_values=global_args.GlobalArgs(config_options=config_options, isolated=True), field_overrides=field_overrides or settings_check.CheckSettingsOverrides()
    )
    selection = rules_selection.select_rules(settings)
    assert selection.errors == (), f"{label}: unexpected rule selection errors: {selection.errors}"

    check_result = formatter.format_source(example.input_source, path, settings=settings, rule_selection=selection, fix=False)
    assert check_result.errors == (), f"{label}: unexpected check errors: {check_result.errors}"

    fix_result = formatter.format_source(example.input_source, path, settings=settings, rule_selection=selection, fix=True)
    assert fix_result.errors == (), f"{label}: unexpected formatter errors: {fix_result.errors}"
    assert fix_result.new_source == example.output_source, f"{label}: output did not match documented output"
    assert _finding_key(fix_result.unfixed_findings) == example.findings, f"{label}: unfixed findings did not match documented findings"
    return MarkdownExampleOutcome(label=label, example=example, path=path, settings=settings, selection=selection, check_result=check_result)


def _finding_key(findings: tuple[RuleFinding, ...]) -> tuple[tuple[RuleCode, tuple[int, ...], str], ...]:
    """Return the documented comparison shape for formatter findings."""
    return tuple((finding.rule.code, finding.line_numbers, finding.message) for finding in findings)
