"""Tests for PCF103 rule-names-in-suppression-comments."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PCF.PCF103_rule_names_in_suppression_comments import PCF103RuleNamesInSuppressionComments
from pydocformatter.rules.models import FixAvailability


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


def format_pcf103(source: str, *, fix: bool = True, extra_select: tuple[str, ...] = (), unfixable: tuple[str, ...] = ()) -> formatter.FormatterResult:
    settings = CheckSettings(select=("PCF103", *extra_select), unfixable=unfixable)
    return pcf_helpers.format_pcf_settings(source, settings=settings, fix=fix)


def test_fixes_all_exact_pydocfmt_names_in_one_directive() -> None:
    source = "# pydocfmt: file-ignore[docstring-reflow, standalone-comment-formatting]  # reason\nvalue = 1\n"

    checked = format_pcf103(source, fix=False)
    fixed = format_pcf103(source)

    assert tuple((finding.line_numbers, finding.fixable) for finding in checked.unfixed_findings) == (((1,), True),)
    assert fixed.new_source == "# pydocfmt: file-ignore[PDF101, PCF000]  # reason\nvalue = 1\n"
    assert fixed.fixed_findings[PCF103RuleNamesInSuppressionComments.meta] == 1


def test_semantic_aliases_retain_the_first_source_occurrence() -> None:
    name_first = format_pcf103("# pydocfmt: ignore[docstring-reflow, PDF101]\nvalue = 1\n")
    code_first = format_pcf103("# pydocfmt: ignore[PDF101, docstring-reflow]\nvalue = 1\n")

    assert name_first.new_source == "# pydocfmt: ignore[PDF101]\nvalue = 1\n"
    assert code_first.new_source == "# pydocfmt: ignore[PDF101]\nvalue = 1\n"


def test_preserves_unrelated_syntax_during_policy_only_fix() -> None:
    source = "#  PYDOCFMT : FILE-IGNORE [ docstring-reflow ,bad!, ] rationale\nvalue = 1\n"

    result = format_pcf103(source)

    assert result.new_source == "#  PYDOCFMT : FILE-IGNORE [ PDF101 ,bad!, ] rationale\nvalue = 1\n"


def test_targeted_fix_preserves_unsafe_empty_segments_and_eof_without_final_newline() -> None:
    source = "value = 1  # pydocfmt: ignore[, docstring-reflow,, PDF101,]"

    result = format_pcf103(source)

    assert result.new_source == "value = 1  # pydocfmt: ignore[, PDF101,,]"


def test_does_not_apply_suppression_representation_policy_to_pydocfmt_range_directives() -> None:
    source = "# pydocfmt: disable[docstring-reflow]\nvalue = 1\n# pydocfmt: enable[docstring-reflow]\n"

    result = format_pcf103(source)

    assert result.new_source == source
    assert result.unfixed_findings == ()


def test_leaves_broad_unknown_and_invalid_pydocfmt_tokens_alone() -> None:
    source = "# pydocfmt: ignore[ALL, PDF, PDF6, unknown-rule, bad!]\nvalue = 1\n"

    result = format_pcf103(source, fix=False)

    assert result.unfixed_findings == ()


def test_reports_unknown_and_invalid_tokens_only_through_pcf101() -> None:
    source = "# pydocfmt: ignore[unknown-rule, bad!]\nvalue = 1\n"

    result = format_pcf103(source, fix=False, extra_select=("PCF101",))

    assert tuple(str(finding.rule.code) for finding in result.unfixed_findings) == ("PCF101", "PCF101")


def test_reports_name_shaped_ruff_tokens_for_every_supported_action_without_fixes() -> None:
    source = "# ruff: ignore[unused-import, F401]\n# ruff: file-ignore[ambiguous-variable-name]\n# ruff: disable[too-many-arguments]\n# ruff: enable[unused-variable]\n"

    result = format_pcf103(source)

    assert result.new_source == source
    assert tuple((finding.line_numbers, finding.fixable) for finding in result.unfixed_findings) == (((1,), False), ((2,), False), ((3,), False), ((4,), False))


def test_permits_broad_ruff_code_selectors() -> None:
    source = "# ruff: ignore[F, PLR, ALL]\n"

    result = format_pcf103(source)

    assert result.new_source == source
    assert result.unfixed_findings == ()


def test_configured_unfixable_selection_retains_the_local_policy_finding_in_fix_mode() -> None:
    source = "# pydocfmt: ignore[docstring-reflow]\n"

    result = format_pcf103(source, unfixable=("PCF103",))

    assert result.new_source == source
    assert tuple((finding.rule, finding.fixable) for finding in result.unfixed_findings) == ((PCF103RuleNamesInSuppressionComments.meta, False),)


def test_leaves_ruff_codes_and_unclassifiable_tokens_alone() -> None:
    source = "# ruff: ignore[F401, unsafe/token]\n"

    result = format_pcf103(source, fix=False)

    assert result.unfixed_findings == ()


def test_rule_metadata_and_default_explicit_selection() -> None:
    default_selection = rules_selection.select_rules(CheckSettings())
    category_selection = rules_selection.select_rules(CheckSettings(select=("PCF",)))
    code_selection = rules_selection.select_rules(CheckSettings(select=("PCF103",)))
    name_selection = rules_selection.select_rules(CheckSettings(select=("rule-names-in-suppression-comments",)))
    reduced_require_explicit = tuple(selector for selector in CheckSettings().require_explicit if selector != "PCF103")
    broad_selection = rules_selection.select_rules(CheckSettings(select=("PCF",), require_explicit=reduced_require_explicit))

    assert PCF103RuleNamesInSuppressionComments.meta.fix_availability is FixAvailability.SOMETIMES
    assert PCF103RuleNamesInSuppressionComments.meta not in tuple(rule.rule for rule in default_selection.rules)
    assert PCF103RuleNamesInSuppressionComments.meta not in tuple(rule.rule for rule in category_selection.rules)
    assert PCF103RuleNamesInSuppressionComments.meta in tuple(rule.rule for rule in code_selection.rules)
    assert PCF103RuleNamesInSuppressionComments.meta in tuple(rule.rule for rule in name_selection.rules)
    assert PCF103RuleNamesInSuppressionComments.meta in tuple(rule.rule for rule in broad_selection.rules)
    assert broad_selection.errors == ()


def test_finding_can_be_suppressed_by_code_or_name() -> None:
    by_code_source = "# pydocfmt: ignore[PCF103, docstring-reflow]\n"
    by_name_source = "# pydocfmt: ignore[rule-names-in-suppression-comments, docstring-reflow]\n"
    by_code = format_pcf103(by_code_source)
    by_name = format_pcf103(by_name_source)

    assert by_code.new_source == by_code_source
    assert by_name.new_source == by_name_source
    assert by_code.unfixed_findings == ()
    assert by_name.unfixed_findings == ()


def test_pcf100_then_policy_fix_and_pcf101_audit_converge_on_refreshed_source() -> None:
    source = "# PYDOCFMT : IGNORE [ docstring-reflow, PDF101, ]\nvalue = 1\n"

    result = format_pcf103(source, extra_select=("PCF100", "PDF101", "PCF101"))

    assert result.new_source == "# pydocfmt: ignore[PDF101]\nvalue = 1\n"
    assert result.fixed_findings[PCF103RuleNamesInSuppressionComments.meta] == 1
    assert tuple((str(finding.rule.code), finding.message) for finding in result.unfixed_findings) == (("PCF101", "Suppression selector 'PDF101' did not suppress any findings"),)


def test_policy_fix_preserves_unrelated_duplicates_unless_pcf100_is_selected() -> None:
    source = "# pydocfmt: ignore[docstring-reflow, future-rule, future-rule, PDF, PDF]\n"

    policy_only = format_pcf103(source)
    with_normalization = format_pcf103(source, extra_select=("PCF100",))

    assert policy_only.new_source == "# pydocfmt: ignore[PDF101, future-rule, future-rule, PDF, PDF]\n"
    assert with_normalization.new_source == "# pydocfmt: ignore[PDF101, future-rule, PDF]\n"
