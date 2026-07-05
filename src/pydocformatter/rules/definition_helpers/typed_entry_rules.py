"""Shared implementation for PDF7xx typed-entry documentation rules.

Attributes:
    TypedDocumentationSubject (TypeAlias): Supported typed-entry target groups dispatched by PDF7xx rule modules.
"""

from __future__ import annotations

import typing

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.typed_documentation as typed_documentation
import pydocformatter.rules.definition_helpers.typed_documentation_models as typed_models
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues

TypedDocumentationSubject = typed_models.TypedDocumentationSubject
_TargetCollector = typing.Callable[[RuleContext], tuple[typed_models.TypedDocumentationTarget, ...]]
_RequiredTypePolicy = typing.Callable[[RuleContext, RuleMetadata, TypedDocumentationSubject, str], tuple[rule_violations.RuleViolation, ...]]

_SUPPORTED_CONVENTION_EFFECT = (
    RuleSettingEffects(
        setting="docstring_convention",
        effects=(
            RuleSettingEffectValues(
                effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST)
            ),
        ),
    ),
)
_EXACT_OPT_IN_EFFECT = (
    RuleSettingEffects(
        setting="docstring_convention",
        effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=tuple(DocstringConvention)),),
    ),
)

_TARGET_COLLECTORS: dict[TypedDocumentationSubject, _TargetCollector] = {
    TypedDocumentationSubject.PARAMETER: typed_documentation.parameter_targets,
    TypedDocumentationSubject.RETURN: typed_documentation.return_targets,
    TypedDocumentationSubject.YIELD: typed_documentation.yield_targets,
    TypedDocumentationSubject.CLASS_ATTRIBUTE: typed_documentation.class_attribute_targets,
    TypedDocumentationSubject.MODULE_ATTRIBUTE: typed_documentation.module_attribute_targets,
}
_REQUIRED_TYPE_POLICIES: dict[TypedDocumentationSubject, _RequiredTypePolicy] = {}


def metadata(code: str, name: str, message: str, *, exact_opt_in: bool, incompatible_with: tuple[str, ...] = ()) -> RuleMetadata:
    """Return standard metadata for one PDF7xx typed-entry rule.

    Args:
        code (str): Rule code tag assigned to the concrete rule module.
        name (str): Stable kebab-case rule name exposed in docs and CLI output.
        message (str): Default diagnostic message for the rule.
        exact_opt_in (bool): Whether the rule should be ignored under every convention unless selected by exact code.
        incompatible_with (tuple[str, ...]): Rule code tags that cannot be selected with this rule.

    Returns:
        RuleMetadata: Complete rule metadata shared by the thin PDF7xx rule modules.
    """
    return RuleMetadata(
        code=RuleCode(code),
        name=name,
        message=message,
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=_EXACT_OPT_IN_EFFECT if exact_opt_in else _SUPPORTED_CONVENTION_EFFECT,
        incompatible_with=tuple(RuleCode(code) for code in incompatible_with),
        check_kind=RuleCheckKind.STANDARD,
    )


def missing_description_violations(context: RuleContext, *, meta: RuleMetadata, subject: TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return missing-description violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data.
        meta (RuleMetadata): Metadata for the concrete PDF7xx missing-description rule.
        subject (TypedDocumentationSubject): Logical subject key used to choose the target collector.
        label (str): Human-readable subject label used in diagnostics.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for entries without semantic descriptions.
    """
    return typed_documentation.missing_description_violations(_TARGET_COLLECTORS[subject](context), meta=meta, label=label)


def required_type_violations(context: RuleContext, *, meta: RuleMetadata, subject: TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return required-type violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data and settings.
        meta (RuleMetadata): Metadata for the concrete PDF7xx required-type rule.
        subject (TypedDocumentationSubject): Logical subject key used to choose the target collector.
        label (str): Human-readable subject label used in diagnostics.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for missing docstring types, with PDF713's enum-like
            class inversion applied.
    """
    policy = _REQUIRED_TYPE_POLICIES.get(subject, _standard_required_type_violations)
    return policy(context, meta, subject, label)


def _standard_required_type_violations(context: RuleContext, meta: RuleMetadata, subject: TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return required-type violations for subjects without special policy."""
    return typed_documentation.required_type_violations(_TARGET_COLLECTORS[subject](context), meta=meta, label=label)


def _class_attribute_required_type_violations(context: RuleContext, meta: RuleMetadata, subject: TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return class-attribute required-type violations with enum-like inversion."""
    del subject
    normal_targets = typed_documentation.class_attribute_targets(context)
    enum_targets = tuple(
        target
        for target in normal_targets
        if target.owner is not None and typed_documentation.enum_like_class(target.owner, context.settings.docstring_class_attribute_no_type_base_classes, context=context)
    )
    enum_entries = {id(target.entry) for target in enum_targets}
    violations: list[rule_violations.RuleViolation] = []
    violations.extend(typed_documentation.required_type_violations(tuple(target for target in normal_targets if id(target.entry) not in enum_entries), meta=meta, label=label))
    violations.extend(typed_documentation.forbidden_type_violations(enum_targets, meta=meta, label=label))
    return typed_documentation.sort_violations(violations)


_REQUIRED_TYPE_POLICIES.update({TypedDocumentationSubject.CLASS_ATTRIBUTE: _class_attribute_required_type_violations})


def forbidden_type_violations(context: RuleContext, *, meta: RuleMetadata, subject: TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return forbidden-type violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data.
        meta (RuleMetadata): Metadata for the concrete PDF7xx forbidden-type rule.
        subject (TypedDocumentationSubject): Logical subject key used to choose the target collector.
        label (str): Human-readable subject label used in diagnostics.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for entries with forbidden docstring type text.
    """
    return typed_documentation.forbidden_type_violations(_TARGET_COLLECTORS[subject](context), meta=meta, label=label)


def mismatch_violations(context: RuleContext, *, meta: RuleMetadata, subject: TypedDocumentationSubject, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return type-mismatch violations for one documented subject.

    Args:
        context (RuleContext): Current rule context with prepared PDF data.
        meta (RuleMetadata): Metadata for the concrete PDF7xx mismatch rule.
        subject (TypedDocumentationSubject): Logical subject key used to choose the target collector.
        label (str): Human-readable subject label used in diagnostics.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for conservative docstring/code type mismatches.
    """
    return typed_documentation.mismatch_violations(_TARGET_COLLECTORS[subject](context), context=context, meta=meta, label=label)
