# Future imports
from __future__ import annotations

# Standard library imports
import typing
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import pytest
import libcst.metadata as cst_metadata


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules import suppressions
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleCategoryContext
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleFinding, RuleMetadata
from pydocformatter.source_path import SourcePathContext
from tests import rule_helpers


def test_planned_source_changes_apply_edits_and_create_violations() -> None:
    module = cst.parse_module("value = 1\n")
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    changes = (
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 8), end=cst_metadata.CodePosition(1, 9)), "2"), line_numbers=(1,), suppression_line_numbers=((2,),)
        ),
    )

    result = rule_edits.apply_source_edits(module, tuple(change.edit for change in changes))
    violations = rule_violations.violations_for_planned_source_changes(rule, changes)

    assert result.module.code == "value = 2\n"
    assert result.source == "value = 2\n"
    assert tuple(violation.finding for violation in violations) == (RuleFinding(rule=rule, line_numbers=(1,), suppression_line_numbers=((2,),), instance_fixable=None),)
    assert (violations[0].fix.planned_changes() if violations[0].fix is not None else ()) == changes


def test_grouped_planned_source_changes_create_one_violation() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    changes = (
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 1)), "x"), line_numbers=(1,), suppression_line_numbers=((10,),)
        ),
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 1)), "y"), line_numbers=(2,), suppression_line_numbers=((20,),)
        ),
    )

    violation = rule_violations.violation_for_grouped_planned_source_changes(rule, changes)

    assert violation.finding == RuleFinding(rule=rule, line_numbers=(1, 2), suppression_line_numbers=((10,), (20,)), instance_fixable=None)
    assert (violation.fix.planned_changes() if violation.fix is not None else ()) == changes


def test_sometimes_fixable_planned_source_changes_infer_fixable_instance() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    changes = (
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""), line_numbers=(1,), suppression_line_numbers=()
        ),
    )

    violations = rule_violations.violations_for_planned_source_changes(rule, changes)

    assert tuple(violation.finding.instance_fixable for violation in violations) == (True,)


def test_usually_fixable_planned_source_changes_infer_fixable_instance() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    changes = (
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""), line_numbers=(1,), suppression_line_numbers=()
        ),
    )

    violations = rule_violations.violations_for_planned_source_changes(rule, changes)

    assert tuple(violation.finding.instance_fixable for violation in violations) == (True,)


def test_diagnostic_helper_infers_nonfixable_instance_for_conditional_rules() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    violation = rule_violations.diagnostic(rule, (1,))

    assert not violation.finding.fixable
    assert violation.fix is None


def test_diagnostic_helper_rejects_always_fixable_rules() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    with pytest.raises(ValueError, match="Always-fixable rules must attach a source fix"):
        rule_violations.diagnostic(rule, (1,))


def test_optional_planned_source_change_helper_validates_diagnostic_lines() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    with pytest.raises(ValueError, match="must specify line_numbers"):
        rule_violations.violation_for_optional_planned_source_change(rule, None)


def test_optional_planned_source_change_helper_rejects_mismatched_lines() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    change = rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""), line_numbers=(1,), suppression_line_numbers=()
    )

    with pytest.raises(ValueError, match="line_numbers must match"):
        rule_violations.violation_for_optional_planned_source_change(rule, change, line_numbers=(2,))


def test_optional_planned_source_change_helper_uses_planned_suppression_targets() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    change = rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""), line_numbers=(1,), suppression_line_numbers=((2,),)
    )

    violation = rule_violations.violation_for_optional_planned_source_change(rule, change)

    assert violation.finding.line_numbers == (1,)
    assert violation.finding.suppression_line_numbers == ((2,),)


def test_optional_planned_source_change_helper_rejects_mismatched_suppression_targets() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    change = rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""), line_numbers=(1,), suppression_line_numbers=((2,),)
    )

    with pytest.raises(ValueError, match="suppression targets must match"):
        rule_violations.violation_for_optional_planned_source_change(rule, change, suppression_line_numbers=((3,),))


def test_line_targets_are_normalized_for_planned_change_findings_and_optional_arguments() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    change = rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""), line_numbers=(1, 1), suppression_line_numbers=((2, 2), (2,))
    )

    violation = rule_violations.violation_for_optional_planned_source_change(rule, change, line_numbers=(1, 1), suppression_line_numbers=((2, 2), (2,)))

    assert change.line_numbers == (1,)
    assert change.suppression_line_numbers == ((2,),)
    assert violation.finding.line_numbers == (1,)
    assert violation.finding.suppression_line_numbers == ((2,),)


def test_planned_source_change_rejects_invalid_line_targets() -> None:
    edit = rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), "")

    with pytest.raises(ValueError, match="must not be empty"):
        rule_edits.PlannedSourceChange(edit=edit, line_numbers=(), suppression_line_numbers=())
    with pytest.raises(ValueError, match="positive line numbers"):
        rule_edits.PlannedSourceChange(edit=edit, line_numbers=(0,), suppression_line_numbers=())
    with pytest.raises(TypeError, match="must contain integers"):
        rule_edits.PlannedSourceChange(edit=edit, line_numbers=typing.cast("typing.Any", (True,)), suppression_line_numbers=())
    with pytest.raises(ValueError, match="must not be empty"):
        rule_edits.PlannedSourceChange(edit=edit, line_numbers=(1,), suppression_line_numbers=((),))


def test_rule_finding_rejects_invalid_line_targets() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    with pytest.raises(ValueError, match="must not be empty"):
        RuleFinding(rule=rule, line_numbers=(), instance_fixable=None)
    with pytest.raises(ValueError, match="positive line numbers"):
        RuleFinding(rule=rule, line_numbers=(0,), instance_fixable=None)
    with pytest.raises(TypeError, match="must be a tuple"):
        RuleFinding(rule=rule, line_numbers=typing.cast("typing.Any", [1]), instance_fixable=None)
    with pytest.raises(TypeError, match="must contain integers"):
        RuleFinding(rule=rule, line_numbers=typing.cast("typing.Any", ("1",)), instance_fixable=None)
    with pytest.raises(TypeError, match="must contain integers"):
        RuleFinding(rule=rule, line_numbers=typing.cast("typing.Any", (True,)), instance_fixable=None)
    with pytest.raises(TypeError, match="suppression line-number targets must be a tuple"):
        RuleFinding(rule=rule, line_numbers=(1,), suppression_line_numbers=typing.cast("typing.Any", [(2,)]), instance_fixable=None)
    with pytest.raises(ValueError, match="must not be empty"):
        RuleFinding(rule=rule, line_numbers=(1,), suppression_line_numbers=((),), instance_fixable=None)
    with pytest.raises(ValueError, match="positive line numbers"):
        RuleFinding(rule=rule, line_numbers=(1,), suppression_line_numbers=((0,),), instance_fixable=None)
    with pytest.raises(TypeError, match="must contain integers"):
        RuleFinding(rule=rule, line_numbers=(1,), suppression_line_numbers=typing.cast("typing.Any", (("2",),)), instance_fixable=None)
    with pytest.raises(TypeError, match="must contain integers"):
        RuleFinding(rule=rule, line_numbers=(1,), suppression_line_numbers=typing.cast("typing.Any", ((True,),)), instance_fixable=None)


def test_rule_source_fix_rejects_invalid_change() -> None:
    with pytest.raises(TypeError, match="PlannedSourceChange"):
        rule_violations.RuleSourceFix.from_change(typing.cast("typing.Any", object()))
    with pytest.raises(TypeError, match="PlannedSourceChange"):
        rule_violations.RuleSourceFix(typing.cast("typing.Any", object()))


def test_suppression_index_filters_violations_and_reports_used_selector_keys() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF999"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    index = suppressions.SuppressionIndex(
        directives=(
            suppressions.SuppressionDirective(line=1, selectors=(suppressions.SuppressionSelector(text="PDF999", matched_codes=frozenset({rule.code}), coverage_lines=frozenset({1}), audit=True),)),
        )
    )
    suppressed_violation = rule_violations.diagnostic(rule, (1,))
    unsuppressed_violation = rule_violations.diagnostic(rule, (2,))

    result = index.filter_violations((suppressed_violation, unsuppressed_violation), active_category_prefix="PDF")

    assert result.violations == (unsuppressed_violation,)
    assert result.used_selector_keys == frozenset({(0, 0)})


def test_suppression_selector_uses_active_category_authorization_without_prefix_tagging() -> None:
    pdf_rule = RuleMetadata(
        code=RuleCode("PDF998"),
        name="test-pdf-rule",
        message="PDF message",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    pcf_rule = dataclasses.replace(pdf_rule, code=RuleCode("PCF998"), name="test-pcf-rule", message="PCF message")
    expression_range = cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(2, 1))
    selector = suppressions.SuppressionSelector(
        text="ALL", matched_codes=frozenset({pdf_rule.code, pcf_rule.code}), coverage_lines=frozenset({1}), audit=True, candidate_expression_ranges=(expression_range,)
    )
    index = suppressions.SuppressionIndex(directives=(suppressions.SuppressionDirective(line=1, selectors=(selector,)),))
    pdf_violation = rule_violations.diagnostic(pdf_rule, (1, 2))
    pcf_violation = rule_violations.diagnostic(pcf_rule, (2,))

    unauthorized_result = index.filter_violations((pdf_violation, pcf_violation), active_category_prefix="PDF")
    pdf_result = index.filter_violations((pdf_violation, pcf_violation), active_category_prefix="PDF", authorized_expression_ranges=frozenset((expression_range,)))
    pcf_result = index.filter_violations((pdf_violation, pcf_violation), active_category_prefix="PCF", authorized_expression_ranges=frozenset((expression_range,)))

    assert unauthorized_result.violations == (pdf_violation, pcf_violation)
    assert not unauthorized_result.used_selector_keys
    assert pdf_result.violations == (pcf_violation,)
    assert pdf_result.used_selector_keys == frozenset({(0, 0)})
    assert pcf_result.violations == (pdf_violation,)
    assert pcf_result.used_selector_keys == frozenset({(0, 0)})


def test_suppression_selector_requires_an_exact_authorized_expression_range() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF998"),
        name="test-pdf-rule",
        message="PDF message",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    candidate_range = cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 4), end=cst_metadata.CodePosition(2, 8))
    same_lines_different_columns = cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 8), end=cst_metadata.CodePosition(2, 12))
    selector = suppressions.SuppressionSelector(text="PDF998", matched_codes=frozenset((rule.code,)), coverage_lines=frozenset((2,)), audit=True, candidate_expression_ranges=(candidate_range,))
    finding = rule_violations.diagnostic(rule, (1, 2)).finding

    assert not selector.suppresses(finding, active_category_prefix="PDF", authorized_expression_ranges=frozenset((same_lines_different_columns,)))
    assert not selector.suppresses(finding, active_category_prefix="PCF", authorized_expression_ranges=frozenset((candidate_range,)))
    assert selector.suppresses(finding, active_category_prefix="PDF", authorized_expression_ranges=frozenset((candidate_range,)))


def test_directive_self_suppression_is_controlled_by_rule_metadata() -> None:
    disabled_rule = RuleMetadata(
        code=RuleCode("TST001"),
        name="test-rule",
        message="Test message",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    enabled_rule = dataclasses.replace(disabled_rule, allows_directive_self_suppression=True)
    selector = suppressions.SuppressionSelector(text="TST001", matched_codes=frozenset((disabled_rule.code,)), coverage_lines=frozenset((2,)), audit=True, directive_line=1)

    assert not selector.suppresses(rule_violations.diagnostic(disabled_rule, (1,)).finding, active_category_prefix="TST")
    assert selector.suppresses(rule_violations.diagnostic(enabled_rule, (1,)).finding, active_category_prefix="TST")


def test_suppression_source_collector_indexes_only_complete_string_expressions() -> None:
    component_count = 100
    source = "value = (\n" + '    "x"\n' * component_count + ")\n"
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module)
    collector = suppressions._SourceCollector(wrapper.resolve(cst_metadata.PositionProvider), tuple(source.splitlines(keepends=True)), rule_collection.RULE_COLLECTION)

    wrapper.module.visit(collector)
    components_by_end_line = suppressions._string_components_by_end_line(collector.string_components)
    ranges_by_start_line = suppressions._expression_ranges_by_start_line(collector.string_components)

    assert len(collector.string_components) == component_count
    assert sum(len(components) for components in components_by_end_line.values()) == component_count
    assert sum(len(ranges) for ranges in ranges_by_start_line.values()) == 1


def test_suppression_string_indexes_retain_distinct_same_line_expressions() -> None:
    source = 'first = "a"; second = ("b" "c")\n'
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module)
    collector = suppressions._SourceCollector(wrapper.resolve(cst_metadata.PositionProvider), tuple(source.splitlines(keepends=True)), rule_collection.RULE_COLLECTION)

    wrapper.module.visit(collector)
    components_by_end_line = suppressions._string_components_by_end_line(collector.string_components)
    ranges_by_start_line = suppressions._expression_ranges_by_start_line(collector.string_components)

    assert tuple(len(components) for components in components_by_end_line.values()) == (3,)
    assert tuple(len(ranges) for ranges in ranges_by_start_line.values()) == (2,)


def test_empty_edits_return_original_module() -> None:
    module = cst.parse_module("x = 1\n")

    result = rule_edits.apply_source_edits(module, ())

    assert result.module is module
    assert result.source == "x = 1\n"


def test_multiple_unsorted_edits_support_unicode_and_adjacent_ranges() -> None:
    module = cst.parse_module("alpha = '\u03b1'\nbeta = 2\n")
    edits = (
        rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),
        rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 9), end=cst_metadata.CodePosition(1, 10)), "\u03c9"),
        rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 5)), "name"),
        rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 4), end=cst_metadata.CodePosition(2, 5)), ""),
    )

    result = rule_edits.apply_source_edits(module, edits)

    assert result.module.code == "name = 'ω'\ngamma= 2\n"
    assert result.source == "name = 'ω'\ngamma= 2\n"


def test_cached_source_and_line_bounds_apply_without_reading_module_code(mocker: MockerFixture) -> None:
    source = "alpha = 1\nbeta = 2\n"
    module = cst.parse_module(source)
    edits = (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),)
    lines = tuple(source_text.source_lines(source))

    def _unexpected_code_access(module: cst.Module) -> str:
        del module
        raise AssertionError("Module.code should not be read")

    mocker.patch.object(cst.Module, "code", new=property(_unexpected_code_access))
    result = rule_edits.apply_source_edits(module, edits, source=source, line_bounds=source_text.line_bounds_from_lines(lines))
    mocker.stopall()

    assert result.module.code == "alpha = 1\ngamma = 2\n"
    assert result.source == "alpha = 1\ngamma = 2\n"


def test_cached_source_and_line_bounds_must_be_provided_together() -> None:
    source = "alpha = 1\nbeta = 2\n"
    module = cst.parse_module(source)
    edits = (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),)
    line_bounds = source_text.line_bounds_from_lines(source_text.source_lines(source))

    with pytest.raises(ValueError, match="source and line_bounds must be provided together"):
        rule_edits.apply_source_edits(module, edits, source=source)
    with pytest.raises(ValueError, match="source and line_bounds must be provided together"):
        rule_edits.apply_source_edits(module, edits, line_bounds=line_bounds)


def test_context_source_changes_apply_cached_context_source_without_reading_module_code(mocker: MockerFixture) -> None:
    source = "alpha = 1\nbeta = 2\n"
    module = cst.parse_module(source)
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    lines = tuple(source_text.source_lines(source))
    context = RuleCategoryContext(
        path="example.py",
        source_path=SourcePathContext.for_path("example.py"),
        settings=CheckSettings(),
        module=module,
        metadata_wrapper=metadata_wrapper,
        positions=metadata_wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\n",
        source=source,
        source_lines=lines,
        line_bounds=source_text.line_bounds_from_lines(lines),
    )
    changes = (
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"), line_numbers=(2,), suppression_line_numbers=()
        ),
    )

    def _unexpected_code_access(module: cst.Module) -> str:
        del module
        raise AssertionError("Module.code should not be read")

    mocker.patch.object(cst.Module, "code", new=property(_unexpected_code_access))
    result = rule_edits.apply_context_source_changes(context, changes)
    mocker.stopall()

    assert result.module.code == "alpha = 1\ngamma = 2\n"
    assert result.source == "alpha = 1\ngamma = 2\n"


def test_context_source_changes_retain_exact_source_normalized_by_libcst() -> None:
    source = 'def f():\n    """D."""\n\n \t#bad\n'
    module = cst.parse_module(source)
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    lines = tuple(source_text.source_lines(source))
    offset_map = source_text.source_offset_map(module, source)
    context = RuleCategoryContext(
        path="example.py",
        source_path=SourcePathContext.for_path("example.py"),
        settings=CheckSettings(),
        module=module,
        metadata_wrapper=metadata_wrapper,
        positions=offset_map.positions(metadata_wrapper.resolve(cst_metadata.PositionProvider)),
        line_ending="\n",
        source=source,
        source_lines=lines,
        line_bounds=source_text.line_bounds_from_lines(lines),
    )
    changes = (
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(4, 2), end=cst_metadata.CodePosition(4, 6)), "# good"), line_numbers=(4,), suppression_line_numbers=()
        ),
    )

    result = rule_edits.apply_context_source_changes(context, changes)

    assert result.source == 'def f():\n    """D."""\n\n \t# good\n'
    assert result.module.code == 'def f():\n    """D."""\n \t# good\n'


def test_context_source_changes_compute_missing_bounds_from_exact_source() -> None:
    source = "\fx = 1\n"
    context = dataclasses.replace(rule_helpers.direct_rule_category_context(source, settings=CheckSettings()), line_bounds=None)
    changes = (
        rule_edits.PlannedSourceChange(
            edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 5), end=cst_metadata.CodePosition(1, 6)), "2"), line_numbers=(1,), suppression_line_numbers=()
        ),
    )

    result = rule_edits.apply_context_source_changes(context, changes)

    assert result.source == "\fx = 2\n"
    assert result.module.code == "x = 2\n"


def test_cached_source_edits_support_no_final_newline() -> None:
    source = "alpha = 1\nbeta = 2"
    module = cst.parse_module(source)
    edits = (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 7), end=cst_metadata.CodePosition(2, 8)), "3"),)
    lines = tuple(source_text.source_lines(source))

    result = rule_edits.apply_source_edits(module, edits, source=source, line_bounds=source_text.line_bounds_from_lines(lines))

    assert result.module.code == "alpha = 1\nbeta = 3"
    assert result.source == "alpha = 1\nbeta = 3"


def test_overlapping_edits_are_rejected() -> None:
    module = cst.parse_module("value = 1\n")
    edits = (
        rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 5)), "name"),
        rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 4), end=cst_metadata.CodePosition(1, 7)), "x"),
    )

    with pytest.raises(ValueError, match="must not overlap"):
        rule_edits.apply_source_edits(module, edits)


def test_invalid_range_positions_are_rejected() -> None:
    module = cst.parse_module("x = 1\n")

    with pytest.raises(ValueError, match="line is outside"):
        rule_edits.apply_source_edits(module, (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(3, 0), end=cst_metadata.CodePosition(3, 0)), ""),))
    with pytest.raises(ValueError, match="column is outside"):
        rule_edits.apply_source_edits(module, (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 10), end=cst_metadata.CodePosition(1, 10)), ""),))


def test_replacement_must_produce_valid_python() -> None:
    module = cst.parse_module("x = 1\n")
    edit = rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 4), end=cst_metadata.CodePosition(1, 5)), "(")

    with pytest.raises(cst.ParserSyntaxError):
        rule_edits.apply_source_edits(module, (edit,))


def test_edits_preserve_crlf_parser_configuration() -> None:
    module = cst.parse_module("first = 1\r\nsecond = 2\r\n")
    edit = rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 6)), "renamed")

    result = rule_edits.apply_source_edits(module, (edit,))

    assert result.module.code == "first = 1\r\nrenamed = 2\r\n"
    assert result.source == "first = 1\r\nrenamed = 2\r\n"
