"""Rule check and fix pass execution."""

from __future__ import annotations

import collections
import dataclasses
from collections.abc import Mapping

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.suppressions as suppressions
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.collection import RuleCollection
from pydocformatter.rules.definition import RuleBase, RuleCategoryBase, RuleCategoryContext, RuleContext, RuleFixResult
from pydocformatter.rules.models import RuleCheckKind, RuleFinding, RuleMetadata
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


def run_rules(
    module: cst.Module,
    *,
    path: str,
    settings: CheckSettings,
    line_ending: str,
    rule_selection: RuleSelection,
    fix: bool,
    source: str | None = None,
) -> RuleRunResult:
    """Run selected rule fixes and checks against one parsed module."""
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
        if _fixable_rules_have_explicit_checks(rule_selection=rule_selection, selected_rule_by_code=selected_rule_by_code):
            precheck_errors: list[str] = []
            precheck_findings = run_check_pass(module, precheck_errors)
            if not precheck_errors and not any(finding.fixable for finding in precheck_findings):
                return RuleRunResult(
                    module=module,
                    fixed_findings=(),
                    unfixed_findings=precheck_findings,
                    source_changed=False,
                    errors=(),
                )

        for iteration in range(1, MAX_FIX_ITERATIONS + 1):
            module, iteration_findings, changed = _run_fix_pass(
                module,
                path=path,
                settings=settings,
                line_ending=line_ending,
                rule_selection=rule_selection,
                selected_rule_by_code=selected_rule_by_code,
                errors=errors,
                source_seed=source_seed,
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

    return RuleRunResult(
        module=module,
        fixed_findings=tuple(fixed_findings),
        unfixed_findings=unfixed_findings,
        source_changed=source_changed,
        errors=tuple(errors),
    )


def _fixable_rules_have_explicit_checks(*, rule_selection: RuleSelection, selected_rule_by_code: dict[RuleCode, SelectedRule]) -> bool:
    """Return whether check findings can prove no selected fix hooks need to run."""
    for category_class in rule_selection.collection.categories:
        for rule_class in category_class.ordered_rules():
            selected_rule = selected_rule_by_code.get(rule_class.meta.code)
            if selected_rule is not None and selected_rule.fixable and "check" not in rule_class.__dict__:
                return False
    return True


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
        category_rules = tuple(
            (rule_class, selected_rule_by_code[rule_class.meta.code])
            for rule_class in category_class.ordered_rules()
            if rule_class.meta.code in selected_rule_by_code and selected_rule_by_code[rule_class.meta.code].fixable
        )
        if not category_rules:
            continue
        prepared_category, pass_context = _prepare_category(
            category_class, module, pass_context, path=path, settings=settings, line_ending=line_ending, rule_collection=rule_selection.collection, errors=errors, source_seed=source_seed
        )
        if prepared_category is None:
            continue
        for rule_class, selected_rule in category_rules:
            if prepared_category.context.module is not module:
                prepared_category, pass_context = _prepare_category(
                    category_class, module, pass_context, path=path, settings=settings, line_ending=line_ending, rule_collection=rule_selection.collection, errors=errors, source_seed=source_seed
                )
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
            if fix_result.module is module:
                result_changed = False
            else:
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
                pass_context = None
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
        for rule_class, selected_rule in category_rules:
            if rule_class.meta.check_kind != RuleCheckKind.STANDARD:
                continue
            try:
                context = _rule_context(prepared_category, effectively_fixable=selected_rule.fixable)
                rule_findings = rule_class.check(context)
            except Exception as error:
                errors.append(f"{path}: {rule_class.meta.code} check failed: {error}")
                continue
            validated_findings = _validated_rule_findings(rule_class, rule_findings, path=path, operation="check", errors=errors)
            if prepared_category.context.suppression_index is None:
                unsuppressed_findings = validated_findings
            else:
                suppression_result = prepared_category.context.suppression_index.filter_findings(validated_findings)
                used_selector_keys.update(suppression_result.used_selector_keys)
                unsuppressed_findings = suppression_result.findings
            findings.extend(_apply_effective_fixability(finding, selected_rule=selected_rule) for finding in unsuppressed_findings)
    if suppression_audit_rules and pass_context is not None:
        for selected_rule in suppression_audit_rules:
            audit_findings = pass_context.suppression_index.unused_findings(frozenset(used_selector_keys), selected_rule_codes=selected_standard_rule_codes, rule=selected_rule.rule)
            audit_filter_result = pass_context.suppression_index.filter_findings(audit_findings)
            findings.extend(_apply_effective_fixability(finding, selected_rule=selected_rule) for finding in audit_filter_result.findings)
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
        suppression_index=pass_context.suppression_index,
    )


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
        source=category_context.source,
        source_lines=category_context.source_lines,
        line_bounds=category_context.line_bounds,
        suppression_index=category_context.suppression_index,
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
