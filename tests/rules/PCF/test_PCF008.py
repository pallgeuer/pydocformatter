"""Tests for PCF008 rule-codes-in-suppression-comments."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PCF.PCF008_rule_codes_in_suppression_comments import PCF008RuleCodesInSuppressionComments
from pydocformatter.rules.models import FixAvailability


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


def format_pcf008(source: str, *, fix: bool = True, extra_select: tuple[str, ...] = (), unfixable: tuple[str, ...] = ()) -> formatter.FormatterResult:
    settings = CheckSettings(select=("PCF008", *extra_select), unfixable=unfixable)
    return pcf_helpers.format_pcf_settings(source, settings=settings, fix=fix)


def test_fixes_all_exact_pydocfmt_codes_in_one_directive() -> None:
    source = "# pydocfmt: ignore[PDF101, PCF001]  # reason\nvalue = 1\n"

    checked = format_pcf008(source, fix=False)
    fixed = format_pcf008(source)

    assert tuple((finding.line_numbers, finding.fixable) for finding in checked.unfixed_findings) == (((1,), True),)
    assert fixed.new_source == "# pydocfmt: ignore[docstring-reflow, standalone-comment-formatting]  # reason\nvalue = 1\n"
    assert fixed.fixed_findings[PCF008RuleCodesInSuppressionComments.meta] == 1


def test_semantic_aliases_retain_the_first_source_occurrence() -> None:
    code_first = format_pcf008("# pydocfmt: ignore[PDF101, docstring-reflow]\nvalue = 1\n")
    name_first = format_pcf008("# pydocfmt: ignore[docstring-reflow, PDF101]\nvalue = 1\n")

    assert code_first.new_source == "# pydocfmt: ignore[docstring-reflow]\nvalue = 1\n"
    assert name_first.new_source == "# pydocfmt: ignore[docstring-reflow]\nvalue = 1\n"


def test_preserves_unrelated_syntax_during_policy_only_fix() -> None:
    source = "#  PYDOCFMT : IGNORE [ PDF101 ,bad!, ] rationale\nvalue = 1\n"

    result = format_pcf008(source)

    assert result.new_source == "#  PYDOCFMT : IGNORE [ docstring-reflow ,bad!, ] rationale\nvalue = 1\n"


def test_targeted_fix_preserves_unsafe_empty_segments_and_crlf_line_endings() -> None:
    source = "# pydocfmt: ignore[, PDF101,, docstring-reflow,]\r\nvalue = 1\r\n"

    result = format_pcf008(source)

    assert result.new_source == "# pydocfmt: ignore[, docstring-reflow,,]\r\nvalue = 1\r\n"


def test_does_not_apply_suppression_representation_policy_to_pydocfmt_range_directives() -> None:
    source = "# pydocfmt: disable[PDF101]\nvalue = 1\n# pydocfmt: enable[PDF101]\n"

    result = format_pcf008(source)

    assert result.new_source == source
    assert result.unfixed_findings == ()


def test_permits_broad_pydocfmt_selectors_and_ignores_unknown_or_invalid_tokens() -> None:
    source = "# pydocfmt: ignore[ALL, PDF, PDF6, unknown-rule, bad!]\nvalue = 1\n"

    result = format_pcf008(source, fix=False)

    assert result.unfixed_findings == ()


def test_reports_unknown_and_invalid_tokens_only_through_pcf006() -> None:
    source = "# pydocfmt: ignore[unknown-rule, bad!]\nvalue = 1\n"

    result = format_pcf008(source, fix=False, extra_select=("PCF006",))

    assert tuple(str(finding.rule.code) for finding in result.unfixed_findings) == ("PCF006", "PCF006")


def test_reports_code_shaped_ruff_tokens_for_every_supported_action_without_fixes() -> None:
    source = "# ruff: ignore[F401, unused-import]\n# ruff: file-ignore[E741]\n# ruff: disable[PLR0913]\n# ruff: enable[F841]\n"

    result = format_pcf008(source)

    assert result.new_source == source
    assert tuple((finding.line_numbers, finding.fixable) for finding in result.unfixed_findings) == (((1,), False), ((2,), False), ((3,), False), ((4,), False))


def test_permits_broad_ruff_code_selectors() -> None:
    source = "# ruff: ignore[F, PLR, ALL, unused-import]\n"

    result = format_pcf008(source)

    assert result.new_source == source
    assert result.unfixed_findings == ()


def test_reports_exact_ruff_codes_alongside_permitted_broad_selectors() -> None:
    source = "# ruff: ignore[F, F401, PLR, ALL, unused-import]\n"

    result = format_pcf008(source)

    assert result.new_source == source
    assert tuple((finding.line_numbers, finding.fixable) for finding in result.unfixed_findings) == (((1,), False),)


def test_reports_one_finding_per_affected_directive_across_fixable_and_diagnostic_only_cases() -> None:
    source = "# pydocfmt: ignore[PDF101, PCF001]\n# ruff: ignore[F401, E741]\n# pydocfmt: file-ignore[PCF002]\n"

    result = format_pcf008(source, fix=False)

    assert tuple((finding.line_numbers, finding.fixable) for finding in result.unfixed_findings) == (((1,), True), ((2,), False), ((3,), True))


def test_configured_unfixable_selection_retains_the_local_policy_finding_in_fix_mode() -> None:
    source = "# pydocfmt: ignore[PDF101]\n"

    result = format_pcf008(source, unfixable=("PCF008",))

    assert result.new_source == source
    assert tuple((finding.rule, finding.fixable) for finding in result.unfixed_findings) == ((PCF008RuleCodesInSuppressionComments.meta, False),)


def test_leaves_ruff_names_and_unclassifiable_tokens_alone() -> None:
    source = "# ruff: ignore[unused-import, unsafe/token]\n"

    result = format_pcf008(source, fix=False)

    assert result.unfixed_findings == ()


def test_rule_metadata_and_default_explicit_selection() -> None:
    default_selection = rules_selection.select_rules(CheckSettings())
    category_selection = rules_selection.select_rules(CheckSettings(select=("PCF",)))
    code_selection = rules_selection.select_rules(CheckSettings(select=("PCF008",)))
    name_selection = rules_selection.select_rules(CheckSettings(select=("rule-codes-in-suppression-comments",)))
    reduced_require_explicit = tuple(selector for selector in CheckSettings().require_explicit if selector != "PCF008")
    broad_selection = rules_selection.select_rules(CheckSettings(select=("PCF",), require_explicit=reduced_require_explicit))

    assert PCF008RuleCodesInSuppressionComments.meta.fix_availability is FixAvailability.SOMETIMES
    assert PCF008RuleCodesInSuppressionComments.meta not in tuple(rule.rule for rule in default_selection.rules)
    assert PCF008RuleCodesInSuppressionComments.meta not in tuple(rule.rule for rule in category_selection.rules)
    assert PCF008RuleCodesInSuppressionComments.meta in tuple(rule.rule for rule in code_selection.rules)
    assert PCF008RuleCodesInSuppressionComments.meta in tuple(rule.rule for rule in name_selection.rules)
    assert PCF008RuleCodesInSuppressionComments.meta in tuple(rule.rule for rule in broad_selection.rules)
    assert broad_selection.errors == ()


def test_finding_can_be_suppressed_by_code_or_name() -> None:
    by_code_source = "# pydocfmt: ignore[PCF008, PDF101]\n"
    by_name_source = "# pydocfmt: ignore[rule-codes-in-suppression-comments, PDF101]\n"
    by_code = format_pcf008(by_code_source)
    by_name = format_pcf008(by_name_source)

    assert by_code.new_source == by_code_source
    assert by_name.new_source == by_name_source
    assert by_code.unfixed_findings == ()
    assert by_name.unfixed_findings == ()


def test_pcf003_then_policy_fix_and_pcf006_audit_converge_on_refreshed_source() -> None:
    source = "# PYDOCFMT : IGNORE [ pdf101, docstring-reflow, ]\nvalue = 1\n"

    result = format_pcf008(source, extra_select=("PCF003", "PDF101", "PCF006"))

    assert result.new_source == "# pydocfmt: ignore[docstring-reflow]\nvalue = 1\n"
    assert result.fixed_findings[PCF008RuleCodesInSuppressionComments.meta] == 1
    assert tuple((str(finding.rule.code), finding.message) for finding in result.unfixed_findings) == (("PCF006", "Suppression selector 'docstring-reflow' did not suppress any findings"),)


def test_policy_fix_preserves_unrelated_duplicates_unless_pcf003_is_selected() -> None:
    source = "# pydocfmt: ignore[PDF101, future-rule, future-rule, PDF, PDF]\n"

    policy_only = format_pcf008(source)
    with_normalization = format_pcf008(source, extra_select=("PCF003",))

    assert policy_only.new_source == "# pydocfmt: ignore[docstring-reflow, future-rule, future-rule, PDF, PDF]\n"
    assert with_normalization.new_source == "# pydocfmt: ignore[docstring-reflow, future-rule, PDF]\n"
