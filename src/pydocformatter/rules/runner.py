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
from typing import TYPE_CHECKING

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
    from pydocformatter.rules_selection import RuleSelection, SelectedRule


MAX_FIX_ITERATIONS = 20
UTF8_BOM = "\ufeff"


@dataclasses.dataclass(frozen=True)
class RuleRunResult:
    """Result of running selected rules against one parsed module.

    Attributes:
        module (cst.Module): Final module after all selected fix passes.
        fixed_findings (tuple[RuleFinding, ...]): Findings fixed during the run.
        unfixed_findings (tuple[RuleFinding, ...]): Findings still present after checking the final module.
        source_changed (bool): Whether any fix pass changed the source.
        errors (tuple[str, ...]): Operational errors raised by rule preparation, checking, or fixing.
    """

    module: cst.Module
    fixed_findings: tuple[RuleFinding, ...]
    unfixed_findings: tuple[RuleFinding, ...]
    source_changed: bool
    errors: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class _PreparedCategory:
    """Prepared category context and optional shared data for one module."""

    context: RuleCategoryContext
    data: object | None


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
    """Trusted source text for one parsed module object."""

    module: cst.Module
    source: str


def run_rules(module: cst.Module, *, path: str, settings: CheckSettings, line_ending: str, rule_selection: RuleSelection, fix: bool, source: str | None = None) -> RuleRunResult:
    """Run selected rule fixes and checks against one parsed module.

    Args:
        module (cst.Module): Parsed LibCST module to check or transform.
        path (str): Display path used for per-file ignores, diagnostics, and operational errors.
        settings (CheckSettings): Resolved settings for the current source.
        line_ending (str): Line ending sequence to use for generated replacement text.
        rule_selection (RuleSelection): Globally selected rules and per-file ignores for this run.
        fix (bool): Whether enabled fixes should be applied before the final check pass.
        source (str | None): Original source text aligned with `module`, used for source-range edits when available.

    Returns:
        RuleRunResult: Final module, fixed and unfixed findings, source-change flag, and operational errors.
    """
    errors: list[str] = []
    selected_rules = rule_selection.for_path(path)
    selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selected_rules}
    fixed_findings: list[RuleFinding] = []
    last_iteration_findings: tuple[RuleFinding, ...] = ()
    reached_iteration_limit = False
    source_changed = False
    source_seed = _ModuleSourceSeed(module=module, source=_module_aligned_source(source)) if source is not None else None

    def run_check_pass(check_module: cst.Module, check_errors: list[str]) -> tuple[RuleFinding, ...]:
        return _run_check_pass(
            check_module,
            path=path,
            settings=settings,
            line_ending=line_ending,
            rule_selection=rule_selection,
            selected_rule_by_code=selected_rule_by_code,
            errors=check_errors,
            source_seed=source_seed,
        )

    if fix:
        precheck_errors: list[str] = []
        precheck_findings = run_check_pass(module, precheck_errors)
        if not precheck_errors and not any(finding.fixable for finding in precheck_findings):
            return RuleRunResult(module=module, fixed_findings=(), unfixed_findings=precheck_findings, source_changed=False, errors=())

        for _ in range(1, MAX_FIX_ITERATIONS + 1):
            module, iteration_findings, changed = _run_fix_pass(
                module, path=path, settings=settings, line_ending=line_ending, rule_selection=rule_selection, selected_rule_by_code=selected_rule_by_code, errors=errors, source_seed=source_seed
            )
            fixed_findings.extend(iteration_findings)
            last_iteration_findings = iteration_findings
            source_changed = source_changed or changed
            if not changed:
                break
        else:
            reached_iteration_limit = True

    unfixed_findings = run_check_pass(module, errors)

    if reached_iteration_limit and any(finding.fixable for finding in unfixed_findings):
        errors.append(_fix_iteration_limit_error(path, last_iteration_findings=last_iteration_findings, unfixed_findings=unfixed_findings))

    return RuleRunResult(module=module, fixed_findings=tuple(fixed_findings), unfixed_findings=unfixed_findings, source_changed=source_changed, errors=tuple(errors))


def _run_fix_pass(
    module: cst.Module,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    rule_selection: RuleSelection,
    selected_rule_by_code: dict[RuleCode, SelectedRule],
    errors: list[str],
    source_seed: _ModuleSourceSeed | None = None,
) -> tuple[cst.Module, tuple[RuleFinding, ...], bool]:
    """Run one ordered pass of effectively fixable rules."""
    pass_findings: list[RuleFinding] = []
    changed = False
    pass_context: _ModulePassContext | None = None
    for category_class in rule_selection.collection.categories:
        category_rule_classes = tuple(
            rule_class
            for rule_class in category_class.ordered_rules()
            if rule_class.meta.code in selected_rule_by_code and rule_class.meta.check_kind == RuleCheckKind.STANDARD and selected_rule_by_code[rule_class.meta.code].fixable
        )
        if not category_rule_classes:
            continue
        prepared_category, pass_context = _prepare_category(
            category_class, module, pass_context, path=path, settings=settings, line_ending=line_ending, rule_collection=rule_selection.collection, errors=errors, source_seed=source_seed
        )
        if prepared_category is None:
            continue
        source_line_count = len(prepared_category.context.source_lines)
        for rule_class in category_rule_classes:
            if prepared_category.context.module is not module:
                prepared_category, pass_context = _prepare_category(
                    category_class, module, pass_context, path=path, settings=settings, line_ending=line_ending, rule_collection=rule_selection.collection, errors=errors, source_seed=source_seed
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
            unsuppressed_violations = pass_context.suppression_index.filter_violations(validated_violations).violations
            fixable_violations = tuple(violation for violation in unsuppressed_violations if violation.finding.fixable)
            if not fixable_violations:
                continue
            planned_changes = _planned_source_changes_for_violations(rule_class, fixable_violations, path=path, source_line_count=source_line_count, errors=errors)
            if planned_changes is None:
                continue
            try:
                fixed_module = rule_edits.apply_context_source_changes(prepared_category.context, planned_changes)
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} automatic fix failed: {error}")
                continue
            fixed_findings = tuple(violation.finding for violation in fixable_violations)
            try:
                result_changed = fixed_module.code != prepared_category.context.source
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} automatic fix source generation failed: {error}")
                continue
            if result_changed != bool(fixed_findings):
                errors.append(f"{path}: {rule_class.meta.code} automatic fix must change source if and only if it reports fixed findings")
                continue
            if result_changed:
                module = fixed_module
                pass_context = None
                pass_findings.extend(fixed_findings)
                changed = True
    return module, tuple(pass_findings), changed


def _run_check_pass(
    module: cst.Module,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    rule_selection: RuleSelection,
    selected_rule_by_code: dict[RuleCode, SelectedRule],
    errors: list[str],
    source_seed: _ModuleSourceSeed | None = None,
) -> tuple[RuleFinding, ...]:
    """Run one ordered read-only pass of all selected rules."""
    findings: list[RuleFinding] = []
    used_selector_keys: set[suppressions.SuppressionSelectorKey] = set()
    pass_context: _ModulePassContext | None = None
    selected_standard_rule_codes = frozenset(selected_rule.rule.code for selected_rule in selected_rule_by_code.values() if selected_rule.rule.check_kind == RuleCheckKind.STANDARD)
    suppression_audit_rules = tuple(selected_rule for selected_rule in selected_rule_by_code.values() if selected_rule.rule.check_kind == RuleCheckKind.SUPPRESSION_AUDIT)
    for category_class in rule_selection.collection.categories:
        category_rules = tuple((rule_class, selected_rule_by_code[rule_class.meta.code]) for rule_class in category_class.ordered_rules() if rule_class.meta.code in selected_rule_by_code)
        if not category_rules:
            continue
        prepared_category, pass_context = _prepare_category(
            category_class, module, pass_context, path=path, settings=settings, line_ending=line_ending, rule_collection=rule_selection.collection, errors=errors, source_seed=source_seed
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
            suppression_result = pass_context.suppression_index.filter_violations(validated_violations)
            used_selector_keys.update(suppression_result.used_selector_keys)
            findings.extend(_apply_effective_fixability(violation.finding, selected_rule=selected_rule) for violation in suppression_result.violations)
    if suppression_audit_rules and pass_context is not None:
        rule_class_by_code = {rule_class.meta.code: rule_class for category_class in rule_selection.collection.categories for rule_class in category_class.ordered_rules()}
        source_line_count = len(pass_context.source_lines)
        for selected_rule in suppression_audit_rules:
            audit_findings = pass_context.suppression_index.unused_findings(frozenset(used_selector_keys), selected_rule_codes=selected_standard_rule_codes, rule=selected_rule.rule)
            audit_violations = tuple(rule_violations.RuleViolation(finding=finding) for finding in audit_findings)
            validated_violations = _validated_rule_violations(
                rule_class_by_code[selected_rule.rule.code], audit_violations, path=path, operation="check", source_line_count=source_line_count, errors=errors
            )
            audit_filter_result = pass_context.suppression_index.filter_violations(validated_violations)
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
) -> tuple[_PreparedCategory | None, _ModulePassContext | None]:
    """Run one category preprocessor and return its shared data."""
    current_pass_context: _ModulePassContext | None = None
    try:
        current_pass_context = _pass_context_for(module, pass_context, source_seed=source_seed, collection=rule_collection)
        context = _category_context(current_pass_context, path=path, settings=settings, line_ending=line_ending)
        return _PreparedCategory(context=context, data=category_class.prepare(context)), current_pass_context
    except Exception as error:
        errors.append(f"{path}: {category_class.meta.prefix} category preparation failed: {error}")
        return None, current_pass_context


def _pass_context_for(module: cst.Module, pass_context: _ModulePassContext | None, *, collection: RuleCollection, source_seed: _ModuleSourceSeed | None = None) -> _ModulePassContext:
    """Return shared source and metadata for the current module state."""
    if pass_context is not None and pass_context.module is module:
        return pass_context
    source = source_seed.source if source_seed is not None and source_seed.module is module else module.code
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    positions = metadata_wrapper.resolve(cst_metadata.PositionProvider)
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


def _module_aligned_source(source: str) -> str:
    """Return source text aligned with LibCST module source positions."""
    aligned_source = source.removeprefix(UTF8_BOM)
    if aligned_source.endswith("\r") and not aligned_source.endswith("\r\n"):
        return aligned_source[:-1]
    return aligned_source


def _category_context(pass_context: _ModulePassContext, *, path: str, settings: CheckSettings, line_ending: str) -> RuleCategoryContext:
    """Build a category context from shared source and metadata."""
    return RuleCategoryContext(
        path=path,
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
    likely_findings = last_iteration_findings + tuple(finding for finding in unfixed_findings if finding.fixable)
    details: dict[RuleMetadata, set[int]] = collections.defaultdict(set)
    for finding in likely_findings:
        details[finding.rule].update(finding.line_numbers)
    likely_rules = ", ".join(f"{rule.code} lines {', '.join(map(str, sorted(lines))) or 'unknown'}" for rule, lines in sorted(details.items())) if details else "unknown"
    return f"{path}: Automatic fixes did not converge after {MAX_FIX_ITERATIONS} iterations; likely rules and lines: {likely_rules}"
