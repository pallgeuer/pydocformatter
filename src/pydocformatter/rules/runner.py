"""Rule check and fix pass execution.

Attributes:
    MAX_FIX_ITERATIONS (int): Upper bound on repeated fix passes, preventing cyclic or non-converging rules from running
        indefinitely.
    UTF8_BOM (str): Unicode byte order mark removed before parsing so reported source positions align with user-visible
        text.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import collections
import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING, NamedTuple

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules import line_targets, suppressions
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.models import RuleCheckKind, RuleFinding


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.cli.settings_check import CheckSettings
    from pydocformatter.rules.codes import RuleCode
    from pydocformatter.rules.collection import RuleCollection
    from pydocformatter.rules.definition import RuleBase, RuleCategoryBase
    from pydocformatter.rules.models import RuleMetadata
    from pydocformatter.rules_selection import RuleExecutionPlan, SelectedRule
    from pydocformatter.source_path import SourcePathContext


MAX_FIX_ITERATIONS = 30
UTF8_BOM = "\ufeff"


@dataclasses.dataclass(frozen=True)
class RuleRunResult:
    """Result of running selected rules against one parsed module.

    Attributes:
        source (str): Exact final source before any LibCST rendering normalization.
        fixed_findings (tuple[RuleFinding, ...]): Findings fixed during the run.
        unfixed_findings (tuple[RuleFinding, ...]): Findings still present after checking the final module.
        source_changed (bool): Whether the exact final source differs from the initial source.
        errors (tuple[str, ...]): Operational errors raised by rule preparation, checking, or fixing.
    """

    source: str
    fixed_findings: tuple[RuleFinding, ...]
    unfixed_findings: tuple[RuleFinding, ...]
    source_changed: bool
    errors: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class _PreparedCategory:
    """Prepared category prefix, context, shared data, and suppression ranges for one module."""

    context: RuleCategoryContext
    data: object | None
    prefix: str
    suppression_expression_ranges: frozenset[cst_metadata.CodeRange]


@dataclasses.dataclass(frozen=True)
class _ModulePassContext:
    """Shared source and metadata for one module state."""

    module: cst.Module
    metadata_wrapper: cst_metadata.MetadataWrapper
    positions: Mapping[cst.CSTNode, cst_metadata.CodeRange]
    source: str
    source_lines: tuple[str, ...]
    line_bounds: source_text.LineBounds
    suppression_index: suppressions.SuppressionIndex


@dataclasses.dataclass(frozen=True)
class _ModuleSourceSeed:
    """Parsed module, exact source, and proven LibCST position mapping."""

    module: cst.Module
    source: str
    offset_map: source_text.SourceOffsetMap


class _SourceAlignmentError(Exception):
    """Raised when LibCST-rendered positions cannot map safely to exact source."""


class _FixPassResult(NamedTuple):
    """Validated source seed, findings, and change state produced by one fix pass."""

    source_seed: _ModuleSourceSeed
    findings: tuple[RuleFinding, ...]
    changed: bool


def run_rule_plan(
    module: cst.Module, *, path: str, settings: CheckSettings, line_ending: str, execution_plan: RuleExecutionPlan, fix: bool, source_path: SourcePathContext, source: str | None = None
) -> RuleRunResult:
    """Run one fully resolved rule plan against a parsed module.

    Args:
        module (cst.Module): Parsed module to check or transform.
        path (str): Display path used for diagnostics and operational errors.
        settings (CheckSettings): Effective settings for the current source.
        line_ending (str): Line ending used for generated replacement text.
        execution_plan (RuleExecutionPlan): Final ordered rules and their collection.
        fix (bool): Whether enabled fixes should be applied before the final check.
        source_path (SourcePathContext): Precomputed path semantics shared with cache identity.
        source (str | None): Exact original source when available.

    Returns:
        RuleRunResult: Final source, findings, change state, and operational errors.
    """
    errors: list[str] = []
    selected_rules = execution_plan.selected_rules
    selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selected_rules}
    fixed_findings: list[RuleFinding] = []
    last_iteration_findings: tuple[RuleFinding, ...] = ()
    reached_iteration_limit = False
    repeated_source_iterations: tuple[int, int] | None = None
    initial_source = _module_aligned_source(source) if source is not None else None
    if initial_source is None:
        source_seed = _module_source_seed(module)
    else:
        try:
            source_seed = _module_source_seed(module, source=initial_source)
        except _SourceAlignmentError as error:
            return RuleRunResult(source=initial_source, fixed_findings=(), unfixed_findings=(), source_changed=False, errors=(_source_alignment_error(path, error),))
    initial_source_seed = source_seed

    def run_check_pass(check_module: cst.Module, check_errors: list[str], *, check_source_seed: _ModuleSourceSeed) -> tuple[RuleFinding, ...]:
        return _run_check_pass(
            check_module,
            path=path,
            settings=settings,
            line_ending=line_ending,
            execution_plan=execution_plan,
            selected_rule_by_code=selected_rule_by_code,
            errors=check_errors,
            source_seed=check_source_seed,
            source_path=source_path,
        )

    if fix:
        precheck_errors: list[str] = []
        precheck_findings = run_check_pass(module, precheck_errors, check_source_seed=source_seed)
        if not precheck_errors and not any(finding.fixable for finding in precheck_findings):
            return RuleRunResult(source=source_seed.source, fixed_findings=(), unfixed_findings=precheck_findings, source_changed=False, errors=())

        source_iterations = {source_seed.source: (0, 0)}
        for iteration in range(1, MAX_FIX_ITERATIONS + 1):
            try:
                pass_result = _run_fix_pass(
                    module,
                    path=path,
                    settings=settings,
                    line_ending=line_ending,
                    execution_plan=execution_plan,
                    selected_rule_by_code=selected_rule_by_code,
                    errors=errors,
                    source_seed=source_seed,
                    source_path=source_path,
                )
            except _SourceAlignmentError as error:
                return RuleRunResult(
                    source=initial_source_seed.source, fixed_findings=(), unfixed_findings=precheck_findings, source_changed=False, errors=(*errors, _source_alignment_error(path, error))
                )
            source_seed = pass_result.source_seed
            module = source_seed.module
            fixed_findings.extend(pass_result.findings)
            last_iteration_findings = pass_result.findings
            if not pass_result.changed:
                break
            if (previous_source_state := source_iterations.get(source_seed.source)) is not None:
                previous_iteration, surviving_finding_count = previous_source_state
                repeated_source_iterations = (previous_iteration, iteration)
                del fixed_findings[surviving_finding_count:]
                break
            source_iterations[source_seed.source] = (iteration, len(fixed_findings))
        else:
            reached_iteration_limit = True

    unfixed_findings = run_check_pass(module, errors, check_source_seed=source_seed)

    if repeated_source_iterations is not None and any(finding.fixable for finding in unfixed_findings):
        errors.append(
            _fix_repeated_source_error(
                path,
                first_iteration=repeated_source_iterations[0],
                repeated_iteration=repeated_source_iterations[1],
                last_iteration_findings=last_iteration_findings,
                unfixed_findings=unfixed_findings,
            )
        )
    elif reached_iteration_limit and any(finding.fixable for finding in unfixed_findings):
        errors.append(_fix_iteration_limit_error(path, last_iteration_findings=last_iteration_findings, unfixed_findings=unfixed_findings))

    return RuleRunResult(
        source=source_seed.source, fixed_findings=tuple(fixed_findings), unfixed_findings=unfixed_findings, source_changed=source_seed.source != initial_source_seed.source, errors=tuple(errors)
    )


def _run_fix_pass(
    module: cst.Module,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    execution_plan: RuleExecutionPlan,
    selected_rule_by_code: dict[RuleCode, SelectedRule],
    errors: list[str],
    source_path: SourcePathContext,
    source_seed: _ModuleSourceSeed | None = None,
) -> _FixPassResult:
    """Run one ordered pass of effectively fixable rules."""
    pass_findings: list[RuleFinding] = []
    changed = False
    pass_context: _ModulePassContext | None = None
    current_source_seed = source_seed if source_seed is not None else _module_source_seed(module)
    for category_class in execution_plan.collection.categories:
        category_rule_classes = tuple(
            rule_class
            for rule_class in category_class.ordered_rules()
            if rule_class.meta.code in selected_rule_by_code and rule_class.meta.check_kind == RuleCheckKind.STANDARD and selected_rule_by_code[rule_class.meta.code].fixable
        )
        if not category_rule_classes:
            continue
        prepared_category, pass_context = _prepare_category(
            category_class,
            module,
            pass_context,
            path=path,
            settings=settings,
            line_ending=line_ending,
            rule_collection=execution_plan.collection,
            errors=errors,
            source_seed=current_source_seed,
            source_path=source_path,
        )
        if prepared_category is None:
            continue
        source_line_count = len(prepared_category.context.source_lines)
        for rule_class in category_rule_classes:
            if prepared_category.context.module is not module:
                prepared_category, pass_context = _prepare_category(
                    category_class,
                    module,
                    pass_context,
                    path=path,
                    settings=settings,
                    line_ending=line_ending,
                    rule_collection=execution_plan.collection,
                    errors=errors,
                    source_seed=current_source_seed,
                    source_path=source_path,
                )
                if prepared_category is None:
                    break
                source_line_count = len(prepared_category.context.source_lines)
            try:
                context = _rule_context(prepared_category)
                reported_violations = rule_class.violations(context)
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} automatic fix failed: {error}")
                continue

            validated_violations = _validated_rule_violations(rule_class, reported_violations, path=path, operation="automatic fix", source_line_count=source_line_count, errors=errors)
            if not validated_violations:
                continue
            if pass_context is None:
                errors.append(f"{path}: {rule_class.meta.code} automatic fix lost source context")
                continue
            unsuppressed_violations = pass_context.suppression_index.filter_violations(
                validated_violations, active_category_prefix=prepared_category.prefix, authorized_expression_ranges=prepared_category.suppression_expression_ranges
            ).violations
            fixable_violations = tuple(violation for violation in unsuppressed_violations if violation.finding.fixable)
            if not fixable_violations:
                continue
            planned_changes = _planned_source_changes_for_violations(rule_class, fixable_violations, path=path, source_line_count=source_line_count, errors=errors)
            if planned_changes is None:
                continue
            try:
                applied_changes = rule_edits.apply_context_source_changes(prepared_category.context, planned_changes)
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} automatic fix failed: {error}")
                continue
            fixed_source_seed = _module_source_seed_for_parsed_source(applied_changes.module, applied_changes.source)
            fixed_findings = tuple(violation.finding for violation in fixable_violations)
            result_changed = applied_changes.source != prepared_category.context.source
            if result_changed != bool(fixed_findings):
                errors.append(f"{path}: {rule_class.meta.code} automatic fix must change source if and only if it reports fixed findings")
                continue
            if result_changed:
                current_source_seed = fixed_source_seed
                module = current_source_seed.module
                pass_context = None
                pass_findings.extend(fixed_findings)
                changed = True
    return _FixPassResult(source_seed=current_source_seed, findings=tuple(pass_findings), changed=changed)


def _run_check_pass(
    module: cst.Module,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    execution_plan: RuleExecutionPlan,
    selected_rule_by_code: dict[RuleCode, SelectedRule],
    errors: list[str],
    source_path: SourcePathContext,
    source_seed: _ModuleSourceSeed | None = None,
) -> tuple[RuleFinding, ...]:
    """Run one ordered read-only pass of all selected rules."""
    findings: list[RuleFinding] = []
    used_selector_keys: set[suppressions.SuppressionSelectorKey] = set()
    pass_context: _ModulePassContext | None = None
    selected_standard_rule_codes = frozenset(selected_rule.rule.code for selected_rule in selected_rule_by_code.values() if selected_rule.rule.check_kind == RuleCheckKind.STANDARD)
    suppression_audit_rules = tuple(selected_rule for selected_rule in selected_rule_by_code.values() if selected_rule.rule.check_kind == RuleCheckKind.SUPPRESSION_AUDIT)
    for category_class in execution_plan.collection.categories:
        category_rules = tuple((rule_class, selected_rule_by_code[rule_class.meta.code]) for rule_class in category_class.ordered_rules() if rule_class.meta.code in selected_rule_by_code)
        if not category_rules:
            continue
        prepared_category, pass_context = _prepare_category(
            category_class,
            module,
            pass_context,
            path=path,
            settings=settings,
            line_ending=line_ending,
            rule_collection=execution_plan.collection,
            errors=errors,
            source_seed=source_seed,
            source_path=source_path,
        )
        if prepared_category is None:
            continue
        source_line_count = len(prepared_category.context.source_lines)
        for rule_class, selected_rule in category_rules:
            if rule_class.meta.check_kind != RuleCheckKind.STANDARD:
                continue
            try:
                context = _rule_context(prepared_category)
                reported_violations = rule_class.violations(context)
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} check failed: {error}")
                continue
            validated_violations = _validated_rule_violations(rule_class, reported_violations, path=path, operation="check", source_line_count=source_line_count, errors=errors)
            if pass_context is None:
                errors.append(f"{path}: {rule_class.meta.code} check lost source context")
                continue
            suppression_result = pass_context.suppression_index.filter_violations(
                validated_violations, active_category_prefix=prepared_category.prefix, authorized_expression_ranges=prepared_category.suppression_expression_ranges
            )
            used_selector_keys.update(suppression_result.used_selector_keys)
            findings.extend(_apply_effective_fixability(violation.finding, selected_rule=selected_rule) for violation in suppression_result.violations)
    if suppression_audit_rules and pass_context is not None:
        rule_class_by_code = {rule_class.meta.code: rule_class for category_class in execution_plan.collection.categories for rule_class in category_class.ordered_rules()}
        source_line_count = len(pass_context.source_lines)
        for selected_rule in suppression_audit_rules:
            audit_findings = pass_context.suppression_index.unused_findings(frozenset(used_selector_keys), selected_rule_codes=selected_standard_rule_codes, rule=selected_rule.rule)
            audit_violations = tuple(rule_violations.RuleViolation(finding=finding) for finding in audit_findings)
            validated_violations = _validated_rule_violations(
                rule_class_by_code[selected_rule.rule.code], audit_violations, path=path, operation="check", source_line_count=source_line_count, errors=errors
            )
            audit_filter_result = pass_context.suppression_index.filter_violations(validated_violations, active_category_prefix=selected_rule.rule.code.prefix)
            findings.extend(_apply_effective_fixability(violation.finding, selected_rule=selected_rule) for violation in audit_filter_result.violations)
    return tuple(findings)


def _prepare_category(
    category_class: type[RuleCategoryBase],
    module: cst.Module,
    pass_context: _ModulePassContext | None,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    rule_collection: RuleCollection,
    errors: list[str],
    source_seed: _ModuleSourceSeed | None = None,
    source_path: SourcePathContext,
) -> tuple[_PreparedCategory | None, _ModulePassContext | None]:
    """Run one category preprocessor and return its shared data."""
    current_pass_context: _ModulePassContext | None = None
    try:
        current_pass_context = _pass_context_for(module, pass_context, source_seed=source_seed, collection=rule_collection)
        context = _category_context(current_pass_context, path=path, source_path=source_path, settings=settings, line_ending=line_ending)
        data = category_class.prepare(context)
        return _PreparedCategory(
            context=context, data=data, prefix=category_class.meta.prefix, suppression_expression_ranges=frozenset(category_class.suppression_expression_ranges(data))
        ), current_pass_context
    except Exception as error:
        errors.append(f"{path}: {category_class.meta.prefix} category preparation failed: {error}")
        return None, current_pass_context


def _pass_context_for(module: cst.Module, pass_context: _ModulePassContext | None, *, collection: RuleCollection, source_seed: _ModuleSourceSeed | None = None) -> _ModulePassContext:
    """Return shared source and metadata for the current module state."""
    if pass_context is not None and pass_context.module is module:
        return pass_context
    current_source_seed = source_seed if source_seed is not None and source_seed.module is module else _module_source_seed(module)
    source = current_source_seed.source
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    positions = current_source_seed.offset_map.positions(metadata_wrapper.resolve(cst_metadata.PositionProvider))
    source_lines = tuple(source_text.source_lines(source))
    suppression_index = suppressions.suppression_index(module, positions=positions, source_lines=source_lines, collection=collection)
    return _ModulePassContext(
        module=module,
        metadata_wrapper=metadata_wrapper,
        positions=positions,
        source=source,
        source_lines=source_lines,
        line_bounds=source_text.line_bounds_from_lines(source_lines),
        suppression_index=suppression_index,
    )


def _module_source_seed(module: cst.Module, *, source: str | None = None) -> _ModuleSourceSeed:
    """Return a module seed with positions proven to map onto exact source."""
    rendered_source = module.code
    exact_source = rendered_source if source is None else source
    try:
        offset_map = source_text.source_offset_map(module, exact_source, rendered_source=rendered_source)
    except ValueError as error:
        raise _SourceAlignmentError(str(error)) from None
    return _ModuleSourceSeed(module=module, source=exact_source, offset_map=offset_map)


def _module_source_seed_for_parsed_source(module: cst.Module, source: str) -> _ModuleSourceSeed:
    """Return a source seed for a module parsed from the supplied exact source."""
    rendered_source = module.code
    try:
        offset_map = source_text.source_offset_map_for_parsed_source(module, source, rendered_source=rendered_source)
    except ValueError as error:
        raise _SourceAlignmentError(str(error)) from None
    return _ModuleSourceSeed(module=module, source=source, offset_map=offset_map)


def _source_alignment_error(path: str, error: _SourceAlignmentError) -> str:
    """Return one operational error for unsafe exact-source alignment."""
    return f"{path}: Exact source could not be aligned safely with LibCST rendering: {error}"


def _module_aligned_source(source: str) -> str:
    """Return source text aligned with LibCST module source positions."""
    aligned_source = source.removeprefix(UTF8_BOM)
    if aligned_source.endswith("\r") and not aligned_source.endswith("\r\n"):
        return aligned_source[:-1]
    return aligned_source


def _category_context(pass_context: _ModulePassContext, *, path: str, source_path: SourcePathContext, settings: CheckSettings, line_ending: str) -> RuleCategoryContext:
    """Build a category context from shared source and metadata."""
    return RuleCategoryContext(
        path=path,
        source_path=source_path,
        settings=settings,
        module=pass_context.module,
        metadata_wrapper=pass_context.metadata_wrapper,
        positions=pass_context.positions,
        line_ending=line_ending,
        source=pass_context.source,
        source_lines=pass_context.source_lines,
        line_bounds=pass_context.line_bounds,
    )


def _rule_context(prepared_category: _PreparedCategory) -> RuleContext:
    """Build a rule context for the current module."""
    category_context = prepared_category.context
    return RuleContext(
        path=category_context.path,
        source_path=category_context.source_path,
        settings=category_context.settings,
        module=category_context.module,
        metadata_wrapper=category_context.metadata_wrapper,
        positions=category_context.positions,
        line_ending=category_context.line_ending,
        source=category_context.source,
        source_lines=category_context.source_lines,
        line_bounds=category_context.line_bounds,
        category_data=prepared_category.data,
    )


def _validated_rule_violations(rule_class: type[RuleBase], violations: object, *, path: str, operation: str, source_line_count: int, errors: list[str]) -> tuple[rule_violations.RuleViolation, ...]:
    """Validate violations returned by a rule hook or synthesized by the runner."""
    if not isinstance(violations, tuple):
        errors.append(f"{path}: {rule_class.meta.code} {operation} returned non-tuple violations")
        return ()
    validated_violations: list[rule_violations.RuleViolation] = []
    for violation in violations:
        if not isinstance(violation, rule_violations.RuleViolation) or violation.finding.rule != rule_class.meta:
            errors.append(f"{path}: {rule_class.meta.code} {operation} returned a violation for a different rule or an invalid violation")
            return ()
        validated_violations.append(violation)
    validated = tuple(validated_violations)
    try:
        finding_fixabilities = tuple(violation.finding.fixable for violation in validated)
    except ValueError as error:
        errors.append(f"{path}: {rule_class.meta.code} {operation} returned a finding with unresolved fixability: {error}")
        return ()
    # Rule hooks can only hit this by bypassing RuleViolation construction; keep the runner boundary hardened.
    if not all((violation.fix is not None) == fixable for violation, fixable in zip(validated, finding_fixabilities, strict=True)):
        errors.append(f"{path}: {rule_class.meta.code} {operation} returned a violation whose fix does not match finding fixability")
        return ()
    invalid_findings = tuple(violation.finding for violation in validated if _finding_has_line_outside_source(violation.finding, source_line_count=source_line_count))
    if invalid_findings:
        errors.append(f"{path}: {rule_class.meta.code} {operation} returned a finding outside the source line range")
        return ()
    return validated


def _planned_source_changes_for_violations(
    rule_class: type[RuleBase], violations: tuple[rule_violations.RuleViolation, ...], *, path: str, source_line_count: int, errors: list[str]
) -> tuple[rule_edits.PlannedSourceChange, ...] | None:
    """Build and validate source changes for unsuppressed fixable violations."""
    planned_changes: list[rule_edits.PlannedSourceChange] = []
    for violation in violations:
        if violation.fix is None:
            errors.append(f"{path}: {rule_class.meta.code} automatic fix returned a fixable violation without a source fix")
            return None
        try:
            violation_changes = violation.fix.planned_changes()
        except Exception as error:
            errors.append(f"{path}: {rule_class.meta.code} automatic fix failed: {error}")
            return None
        if not _violation_fix_changes_are_valid(violation, violation_changes, source_line_count=source_line_count):
            errors.append(f"{path}: {rule_class.meta.code} automatic fix returned source changes whose line targets do not match the finding")
            return None
        planned_changes.extend(violation_changes)
    return tuple(planned_changes)


def _violation_fix_changes_are_valid(violation: rule_violations.RuleViolation, changes: tuple[rule_edits.PlannedSourceChange, ...], *, source_line_count: int) -> bool:
    """Return whether one violation's planned changes match its finding targets."""
    if not changes:
        return False
    if any(_change_has_line_outside_source(change, source_line_count=source_line_count) for change in changes):
        return False
    change_lines = _line_number_set(tuple(line_number for change in changes for line_number in change.line_numbers))
    finding_lines = _line_number_set(violation.finding.line_numbers)
    if change_lines != finding_lines:
        return False
    change_suppression_targets = _line_target_set(tuple(target for change in changes for target in change.suppression_line_numbers))
    finding_suppression_targets = _line_target_set(violation.finding.suppression_line_numbers)
    return change_suppression_targets == finding_suppression_targets


def _line_number_set(line_numbers: tuple[int, ...]) -> frozenset[int]:
    """Return the normalized set of one line-number target."""
    return frozenset(line_targets.normalize_line_numbers(line_numbers, "Rule violation line numbers"))


def _line_target_set(line_number_targets: tuple[tuple[int, ...], ...]) -> frozenset[tuple[int, ...]]:
    """Return the normalized set of line-number target tuples."""
    return frozenset(line_targets.normalize_line_number_targets(line_number_targets, "Rule violation line-number targets", "Rule violation line-number target"))


def _finding_has_line_outside_source(finding: RuleFinding, *, source_line_count: int) -> bool:
    """Return whether a finding targets a line outside the current source."""
    return _has_line_outside_source(finding.suppression_targets, source_line_count=source_line_count)


def _change_has_line_outside_source(change: rule_edits.PlannedSourceChange, *, source_line_count: int) -> bool:
    """Return whether a planned source change targets a line outside the current source."""
    return _has_line_outside_source((change.line_numbers, *change.suppression_line_numbers), source_line_count=source_line_count)


def _has_line_outside_source(line_number_targets: tuple[tuple[int, ...], ...], *, source_line_count: int) -> bool:
    """Return whether any line-number target points outside the current source."""
    return any(line_number > source_line_count for target in line_number_targets for line_number in target)


def _apply_effective_fixability(finding: RuleFinding, *, selected_rule: SelectedRule) -> RuleFinding:
    """Apply configured effective fixability to one final finding."""
    return finding if selected_rule.fixable else dataclasses.replace(finding, instance_fixable=False)


def _fix_iteration_limit_error(path: str, *, last_iteration_findings: tuple[RuleFinding, ...], unfixed_findings: tuple[RuleFinding, ...]) -> str:
    """Return an operational error describing likely non-converging rules."""
    likely_rules = _likely_finding_details(last_iteration_findings, unfixed_findings=unfixed_findings)
    return f"{path}: Automatic fixes did not converge after {MAX_FIX_ITERATIONS} iterations; likely rules and lines: {likely_rules}"


def _fix_repeated_source_error(path: str, *, first_iteration: int, repeated_iteration: int, last_iteration_findings: tuple[RuleFinding, ...], unfixed_findings: tuple[RuleFinding, ...]) -> str:
    """Return an operational error describing a repeated automatic-fix source state."""
    likely_rules = _likely_finding_details(last_iteration_findings, unfixed_findings=unfixed_findings)
    cycle_length = repeated_iteration - first_iteration
    return f"{path}: Automatic fixes repeated a source state after {repeated_iteration} iterations (cycle length {cycle_length}); likely rules and lines: {likely_rules}"


def _likely_finding_details(last_iteration_findings: tuple[RuleFinding, ...], *, unfixed_findings: tuple[RuleFinding, ...]) -> str:
    """Return sorted rule and line details for likely non-converging findings."""
    likely_findings = last_iteration_findings + tuple(finding for finding in unfixed_findings if finding.fixable)
    details: dict[RuleMetadata, set[int]] = collections.defaultdict(set)
    for finding in likely_findings:
        details[finding.rule].update(finding.line_numbers)
    return ", ".join(f"{rule.code} lines {', '.join(map(str, sorted(lines))) or 'unknown'}" for rule, lines in sorted(details.items())) if details else "unknown"
