from __future__ import annotations

import collections
import dataclasses

import libcst as cst
import libcst.metadata as cst_metadata

from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleBase, RuleCategoryBase, RuleCategoryContext, RuleContext, RuleFixResult
from pydocformatter.rules.models import RuleCode, RuleFinding, RuleMetadata
from pydocformatter.rules_selection import RuleSelection, SelectedRule

MAX_FIX_ITERATIONS = 100


@dataclasses.dataclass(frozen=True)
class RuleRunResult:
    """Result of running selected rules against one parsed module."""

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


def run_rules(
    module: cst.Module,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    rule_selection: RuleSelection,
    fix: bool,
) -> RuleRunResult:
    """Run selected rule fixes and checks against one parsed module."""
    errors: list[str] = []
    selected_rules = rule_selection.for_path(path)
    selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selected_rules}
    fixed_findings: list[RuleFinding] = []
    last_iteration_findings: tuple[RuleFinding, ...] = ()
    reached_iteration_limit = False
    source_changed = False

    if fix:
        for iteration in range(1, MAX_FIX_ITERATIONS + 1):
            module, iteration_findings, changed = _run_fix_pass(
                module,
                path=path,
                settings=settings,
                line_ending=line_ending,
                rule_selection=rule_selection,
                selected_rule_by_code=selected_rule_by_code,
                errors=errors,
            )
            fixed_findings.extend(iteration_findings)
            last_iteration_findings = iteration_findings
            source_changed = source_changed or changed
            if not changed:
                break
        else:
            reached_iteration_limit = True

    unfixed_findings = _run_check_pass(
        module,
        path=path,
        settings=settings,
        line_ending=line_ending,
        rule_selection=rule_selection,
        selected_rule_by_code=selected_rule_by_code,
        errors=errors,
    )

    if reached_iteration_limit and any(finding.fixable for finding in unfixed_findings):
        errors.append(_fix_iteration_limit_error(path, last_iteration_findings=last_iteration_findings, unfixed_findings=unfixed_findings))

    return RuleRunResult(
        module=module,
        fixed_findings=tuple(fixed_findings),
        unfixed_findings=unfixed_findings,
        source_changed=source_changed,
        errors=tuple(errors),
    )


def _run_fix_pass(
    module: cst.Module,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    rule_selection: RuleSelection,
    selected_rule_by_code: dict[RuleCode, SelectedRule],
    errors: list[str],
) -> tuple[cst.Module, tuple[RuleFinding, ...], bool]:
    """Run one ordered pass of effectively fixable rules."""
    pass_findings: list[RuleFinding] = []
    changed = False
    for category_class in rule_selection.collection.categories:
        category_rules = tuple(
            (rule_class, selected_rule_by_code[rule_class.meta.code])
            for rule_class in category_class.ordered_rules()
            if rule_class.meta.code in selected_rule_by_code and selected_rule_by_code[rule_class.meta.code].fixable
        )
        if not category_rules:
            continue
        prepared_category = _prepare_category(category_class, module, path=path, settings=settings, line_ending=line_ending, errors=errors)
        if prepared_category is None:
            continue
        for rule_class, selected_rule in category_rules:
            if prepared_category.context.module is not module:
                prepared_category = _prepare_category(category_class, module, path=path, settings=settings, line_ending=line_ending, errors=errors)
                if prepared_category is None:
                    break
            try:
                context = _rule_context(prepared_category, effectively_fixable=selected_rule.fixable)
                fix_result = rule_class.fix(context)
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} automatic fix failed: {error}")
                continue
            if not isinstance(fix_result, RuleFixResult):
                errors.append(f"{path}: {rule_class.meta.code} automatic fix returned {type(fix_result).__name__}, expected RuleFixResult")
                continue
            if not isinstance(fix_result.module, cst.Module):
                errors.append(f"{path}: {rule_class.meta.code} automatic fix returned {type(fix_result.module).__name__}, expected LibCST Module")
                continue
            result_findings = _validated_rule_findings(rule_class, fix_result.fixed_findings, path=path, operation="automatic fix", errors=errors)
            try:
                result_changed = fix_result.module.code != module.code
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} automatic fix source generation failed: {error}")
                continue
            if result_changed != bool(result_findings):
                errors.append(f"{path}: {rule_class.meta.code} automatic fix must change source if and only if it reports fixed findings")
                continue
            if result_changed:
                module = fix_result.module
                pass_findings.extend(result_findings)
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
) -> tuple[RuleFinding, ...]:
    """Run one ordered read-only pass of all selected rules."""
    findings: list[RuleFinding] = []
    for category_class in rule_selection.collection.categories:
        category_rules = tuple((rule_class, selected_rule_by_code[rule_class.meta.code]) for rule_class in category_class.ordered_rules() if rule_class.meta.code in selected_rule_by_code)
        if not category_rules:
            continue
        prepared_category = _prepare_category(category_class, module, path=path, settings=settings, line_ending=line_ending, errors=errors)
        if prepared_category is None:
            continue
        for rule_class, selected_rule in category_rules:
            try:
                context = _rule_context(prepared_category, effectively_fixable=selected_rule.fixable)
                rule_findings = rule_class.check(context)
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} check failed: {error}")
                continue
            validated_findings = _validated_rule_findings(rule_class, rule_findings, path=path, operation="check", errors=errors)
            findings.extend(_apply_effective_fixability(finding, selected_rule=selected_rule) for finding in validated_findings)
    return tuple(findings)


def _prepare_category(category_class: type[RuleCategoryBase], module: cst.Module, *, path: str, settings: CheckSettings, line_ending: str, errors: list[str]) -> _PreparedCategory | None:
    """Run one category preprocessor and return its shared data."""
    try:
        context = _category_context(module, path=path, settings=settings, line_ending=line_ending)
        return _PreparedCategory(context=context, data=category_class.prepare(context))
    except Exception as error:
        errors.append(f"{path}: {category_class.meta.prefix} category preparation failed: {error}")
        return None


def _category_context(module: cst.Module, *, path: str, settings: CheckSettings, line_ending: str) -> RuleCategoryContext:
    """Build a category context and resolve source positions for its current module."""
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    positions = metadata_wrapper.resolve(cst_metadata.PositionProvider)
    return RuleCategoryContext(path=path, settings=settings, module=module, metadata_wrapper=metadata_wrapper, positions=positions, line_ending=line_ending)


def _rule_context(prepared_category: _PreparedCategory, *, effectively_fixable: bool) -> RuleContext:
    """Build a rule context for the current module."""
    category_context = prepared_category.context
    return RuleContext(
        path=category_context.path,
        settings=category_context.settings,
        module=category_context.module,
        metadata_wrapper=category_context.metadata_wrapper,
        positions=category_context.positions,
        line_ending=category_context.line_ending,
        category_data=prepared_category.data,
        effectively_fixable=effectively_fixable,
    )


def _validated_rule_findings(rule_class: type[RuleBase], findings: object, *, path: str, operation: str, errors: list[str]) -> tuple[RuleFinding, ...]:
    """Validate findings returned by a rule hook."""
    if not isinstance(findings, tuple):
        errors.append(f"{path}: {rule_class.meta.code} {operation} returned non-tuple findings")
        return ()
    if not all(isinstance(finding, RuleFinding) and finding.rule == rule_class.meta for finding in findings):
        errors.append(f"{path}: {rule_class.meta.code} {operation} returned a finding for a different rule or an invalid finding")
        return ()
    try:
        finding_fixabilities = tuple(finding.fixable for finding in findings)
    except ValueError as error:
        errors.append(f"{path}: {rule_class.meta.code} {operation} returned a finding with unresolved fixability: {error}")
        return ()
    if operation == "automatic fix" and not all(finding_fixabilities):
        errors.append(f"{path}: {rule_class.meta.code} automatic fix returned a non-fixable finding")
        return ()
    return findings


def _apply_effective_fixability(finding: RuleFinding, *, selected_rule: SelectedRule) -> RuleFinding:
    """Apply configured effective fixability to one final finding."""
    return finding if selected_rule.fixable else dataclasses.replace(finding, instance_fixable=False)


def _fix_iteration_limit_error(path: str, *, last_iteration_findings: tuple[RuleFinding, ...], unfixed_findings: tuple[RuleFinding, ...]) -> str:
    """Return an operational error describing likely non-converging rules."""
    likely_findings = last_iteration_findings + tuple(finding for finding in unfixed_findings if finding.fixable)
    details: dict[RuleMetadata, set[int]] = collections.defaultdict(set)
    for finding in likely_findings:
        details[finding.rule].update(finding.line_numbers)
    if details:
        likely_rules = ", ".join(f"{rule.code} lines {', '.join(map(str, sorted(lines))) or 'unknown'}" for rule, lines in sorted(details.items()))
    else:
        likely_rules = "unknown"
    return f"{path}: Automatic fixes did not converge after {MAX_FIX_ITERATIONS} iterations; likely rules and lines: {likely_rules}"
