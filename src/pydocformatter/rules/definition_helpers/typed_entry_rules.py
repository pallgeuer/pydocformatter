"""Shared implementation for PDF7xx typed-entry documentation rules."""

# Future imports
from __future__ import annotations

# Standard library imports
import typing
import dataclasses

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definition_helpers.typed_documentation_models as typed_models
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleContext
from pydocformatter.rules.definition_helpers import docstring_conventions, typed_documentation
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


_TargetCollector = typing.Callable[[RuleContext], tuple[typed_models.TypedDocumentationTarget, ...]]
_RequiredTypePolicy = typing.Callable[[RuleContext, RuleMetadata, typed_models.TypedDocumentationSubject, str], tuple[rule_violations.RuleViolation, ...]]


@dataclasses.dataclass(frozen=True)
class _TypedDocumentationSubjectSpec:
    """Collector, diagnostic label, and required-type policy for one typed-entry subject.

    Attributes:
        collector (_TargetCollector): Target collector for the documented subject.
        label (str): Human-readable subject label used in diagnostics.
        required_type_policy (_RequiredTypePolicy): Required-type policy for the documented subject.
    """

    collector: _TargetCollector
    label: str
    required_type_policy: _RequiredTypePolicy


_SUPPORTED_CONVENTION_EFFECT = docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS)
_CONVENTION_OPT_IN_EFFECT = docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS, ignored=docstring_conventions.PARSED_CONVENTIONS)


def metadata(code: str, name: str, message: str, *, convention_opt_in: bool, incompatible_with: tuple[str, ...] = (), fix_availability: FixAvailability = FixAvailability.NEVER) -> RuleMetadata:
    """Return standard metadata for one PDF7xx typed-entry rule.

    Args:
        code (str): Rule code tag assigned to the concrete rule module.
        name (str): Stable kebab-case rule name exposed in docs and CLI output.
        message (str): Default diagnostic message for the rule.
        convention_opt_in (bool): Whether the rule should be ignored under every convention unless selected by exact
            code.
        incompatible_with (tuple[str, ...]): Rule code tags that cannot be selected with this rule.
        fix_availability (FixAvailability): Availability classification for safe automatic fixes.

    Returns:
        RuleMetadata: Complete rule metadata shared by the thin PDF7xx rule modules.
    """
    return RuleMetadata(
        code=RuleCode(code),
        name=name,
        message=message,
        fix_availability=fix_availability,
        stable_since="1.1.0",
        setting_effects=_CONVENTION_OPT_IN_EFFECT if convention_opt_in else _SUPPORTED_CONVENTION_EFFECT,
        incompatible_with=tuple(RuleCode(code) for code in incompatible_with),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )


def missing_description_violations(context: RuleContext, *, meta: RuleMetadata, subject: typed_models.TypedDocumentationSubject) -> tuple[rule_violations.RuleViolation, ...]:
    """Return missing-description violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data.
        meta (RuleMetadata): Metadata for the concrete PDF7xx missing-description rule.
        subject (typed_models.TypedDocumentationSubject): Logical subject key used to choose the target collector.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for entries without semantic descriptions.
    """
    spec = _SUBJECT_SPECS[subject]
    return typed_documentation.missing_description_violations(spec.collector(context), meta=meta, label=spec.label)


def required_type_violations(context: RuleContext, *, meta: RuleMetadata, subject: typed_models.TypedDocumentationSubject) -> tuple[rule_violations.RuleViolation, ...]:
    """Return required-type violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data and settings.
        meta (RuleMetadata): Metadata for the concrete PDF7xx required-type rule.
        subject (typed_models.TypedDocumentationSubject): Logical subject key used to choose the target collector.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for missing docstring types, with PDF713's enum-like
            class inversion applied.
    """
    spec = _SUBJECT_SPECS[subject]
    return spec.required_type_policy(context, meta, subject, spec.label)


def _standard_required_type_violations(context: RuleContext, meta: RuleMetadata, subject: typed_models.TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return required-type violations for subjects without special policy."""
    return typed_documentation.required_type_violations(_SUBJECT_SPECS[subject].collector(context), context=context, meta=meta, label=label)


def _class_attribute_required_type_violations(context: RuleContext, meta: RuleMetadata, subject: typed_models.TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return class-attribute required-type violations with enum-like inversion."""
    normal_targets = _SUBJECT_SPECS[subject].collector(context)
    enum_like_owner_by_id: dict[int, bool] = {}

    def target_owner_is_enum_like(target: typed_models.TypedDocumentationTarget) -> bool:
        owner = target.owner
        if owner is None:
            return False
        owner_id = id(owner)
        enum_like = enum_like_owner_by_id.get(owner_id)
        if enum_like is None:
            enum_like = typed_documentation.enum_like_class(owner, context.settings.docstring_class_attribute_no_type_base_classes, context=context)
            enum_like_owner_by_id[owner_id] = enum_like
        return enum_like

    enum_targets = tuple(target for target in normal_targets if target.entry.docstring.structure.convention is not DocstringConvention.NUMPY and target_owner_is_enum_like(target))
    enum_entries = {id(target.entry) for target in enum_targets}
    violations: list[rule_violations.RuleViolation] = []
    violations.extend(typed_documentation.required_type_violations(tuple(target for target in normal_targets if id(target.entry) not in enum_entries), context=context, meta=meta, label=label))
    violations.extend(typed_documentation.forbidden_type_violations(enum_targets, context=context, meta=meta, label=label, correction=typed_models.TypeRemovalCorrection.REMOVE))
    return typed_documentation.sort_violations(violations)


def forbidden_type_violations(context: RuleContext, *, meta: RuleMetadata, subject: typed_models.TypedDocumentationSubject) -> tuple[rule_violations.RuleViolation, ...]:
    """Return forbidden-type violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data.
        meta (RuleMetadata): Metadata for the concrete PDF7xx forbidden-type rule.
        subject (typed_models.TypedDocumentationSubject): Logical subject key used to choose the target collector.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for entries with forbidden docstring type text.
    """
    spec = _SUBJECT_SPECS[subject]
    return typed_documentation.forbidden_type_violations(spec.collector(context), context=context, meta=meta, label=spec.label, correction=typed_models.TypeRemovalCorrection.DIAGNOSTIC_ONLY)


def mismatch_violations(context: RuleContext, *, meta: RuleMetadata, subject: typed_models.TypedDocumentationSubject) -> tuple[rule_violations.RuleViolation, ...]:
    """Return type-mismatch violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data.
        meta (RuleMetadata): Metadata for the concrete PDF7xx mismatch rule.
        subject (typed_models.TypedDocumentationSubject): Logical subject key used to choose the target collector.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for conservative docstring/code type mismatches.
    """
    spec = _SUBJECT_SPECS[subject]
    return typed_documentation.mismatch_violations(spec.collector(context), context=context, meta=meta, label=spec.label)


_SUBJECT_SPECS: dict[typed_models.TypedDocumentationSubject, _TypedDocumentationSubjectSpec] = {
    typed_models.TypedDocumentationSubject.PARAMETER: _TypedDocumentationSubjectSpec(
        collector=typed_documentation.parameter_targets, label="Function parameter", required_type_policy=_standard_required_type_violations
    ),
    typed_models.TypedDocumentationSubject.RETURN: _TypedDocumentationSubjectSpec(
        collector=typed_documentation.return_targets, label="Function return", required_type_policy=_standard_required_type_violations
    ),
    typed_models.TypedDocumentationSubject.YIELD: _TypedDocumentationSubjectSpec(
        collector=typed_documentation.yield_targets, label="Function yield", required_type_policy=_standard_required_type_violations
    ),
    typed_models.TypedDocumentationSubject.CLASS_ATTRIBUTE: _TypedDocumentationSubjectSpec(
        collector=typed_documentation.class_attribute_targets, label="Class attribute", required_type_policy=_class_attribute_required_type_violations
    ),
    typed_models.TypedDocumentationSubject.MODULE_ATTRIBUTE: _TypedDocumentationSubjectSpec(
        collector=typed_documentation.module_attribute_targets, label="Module attribute", required_type_policy=_standard_required_type_violations
    ),
}
