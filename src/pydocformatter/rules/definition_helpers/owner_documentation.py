"""Definition docstring presence helpers.

Attributes:
    MissingOwnerDocumentationEntity (TypeAlias): Supported owner kinds for missing docstring policies.
"""

from __future__ import annotations

import dataclasses
import pathlib
import typing

import libcst as cst

import pydocformatter.rules.definition_helpers.function_decorators as function_decorators
import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.definition import RuleContext

MissingOwnerDocumentationEntity = typing.Literal["package", "module", "class", "nested-class", "function", "method", "dunder-method", "init"]


@dataclasses.dataclass(frozen=True)
class MissingOwnerDocumentationPolicy:
    """Selection policy for one missing owner-docstring rule.

    Attributes:
        entity (MissingOwnerDocumentationEntity): Documentable entity type checked by the rule.
        public (bool): Whether the rule checks public or private entities.
    """

    entity: MissingOwnerDocumentationEntity
    public: bool


@dataclasses.dataclass(frozen=True)
class _PathPolicy:
    """Path classification shared across one missing owner-docstring rule run."""

    package: bool
    public: bool


def missing_owner_docstring_violations(
    data: PDF_definition.PDFCategoryData, *, context: RuleContext, meta: rule_models.RuleMetadata, policy: MissingOwnerDocumentationPolicy
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for definitions missing owner docstrings.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions and docstrings for the current file.
        context (RuleContext): Current file context used for path privacy and source positions.
        meta (rule_models.RuleMetadata): Rule metadata attached to diagnostics.
        policy (MissingOwnerDocumentationPolicy): Entity and public/private policy for this rule.

    Returns:
        Missing owner-docstring diagnostics for matching definitions.
    """
    path_policy = _path_policy(context.path)
    violations: list[rule_violations.RuleViolation] = []
    for definition in data.definitions:
        if data.docstring_for(definition) is not None or not _matches_policy(definition, context=context, path_policy=path_policy, policy=policy):
            continue
        line_numbers = _definition_line_numbers(definition, context=context)
        violations.append(rule_violations.diagnostic(meta, line_numbers, instance_message=_missing_docstring_message(definition, policy=policy)))
    return tuple(violations)


def _matches_policy(definition: PDF_definition.DefinitionInfo, *, context: RuleContext, path_policy: _PathPolicy, policy: MissingOwnerDocumentationPolicy) -> bool:
    """Return whether a definition is in scope for a missing owner-docstring rule."""
    if not _matches_entity(definition, path_policy=path_policy, entity=policy.entity):
        return False
    if function_decorators.function_missing_docstring_is_exempt(definition, context=context, settings=context.settings):
        return False
    return _is_public_owner(definition, path_policy=path_policy, policy=policy) is policy.public


def _matches_entity(definition: PDF_definition.DefinitionInfo, *, path_policy: _PathPolicy, entity: MissingOwnerDocumentationEntity) -> bool:
    """Return whether a definition has the entity shape targeted by a rule."""
    if entity == "package":
        return definition.kind is PDF_definition.DefinitionKind.MODULE and path_policy.package
    if entity == "module":
        return definition.kind is PDF_definition.DefinitionKind.MODULE and not path_policy.package
    if entity == "class":
        return definition.kind is PDF_definition.DefinitionKind.CLASS and _parent_kind(definition) is PDF_definition.DefinitionKind.MODULE
    if entity == "nested-class":
        return definition.kind is PDF_definition.DefinitionKind.CLASS and _has_class_api_owner_chain(definition.parent)
    if entity == "function":
        return definition.kind is PDF_definition.DefinitionKind.FUNCTION and _parent_kind(definition) is PDF_definition.DefinitionKind.MODULE
    if entity == "method":
        return definition.kind is PDF_definition.DefinitionKind.FUNCTION and _has_class_api_owner_chain(definition.parent) and not _is_dunder_method(definition) and definition.name != "__init__"
    if entity == "dunder-method":
        return definition.kind is PDF_definition.DefinitionKind.FUNCTION and _has_class_api_owner_chain(definition.parent) and _is_dunder_method(definition) and definition.name != "__init__"
    if entity == "init":
        return definition.kind is PDF_definition.DefinitionKind.FUNCTION and _has_class_api_owner_chain(definition.parent) and definition.name == "__init__"
    typing.assert_never(entity)


def _is_public_owner(definition: PDF_definition.DefinitionInfo, *, path_policy: _PathPolicy, policy: MissingOwnerDocumentationPolicy) -> bool:
    """Return whether a matching owner belongs to the public API."""
    if not path_policy.public:
        return False
    if definition.kind is PDF_definition.DefinitionKind.MODULE:
        return True
    if policy.entity == "dunder-method":
        return definition.parent is not None and missing_documentation.is_public_definition(definition.parent)
    return missing_documentation.is_public_definition(definition)


def _parent_kind(definition: PDF_definition.DefinitionInfo) -> PDF_definition.DefinitionKind | None:
    """Return a definition's parent kind."""
    return None if definition.parent is None else definition.parent.kind


def _has_class_api_owner_chain(definition: PDF_definition.DefinitionInfo | None) -> bool:
    """Return whether a class owner chain reaches the module without a function ancestor."""
    if definition is None or definition.kind is not PDF_definition.DefinitionKind.CLASS:
        return False
    current: PDF_definition.DefinitionInfo | None = definition
    while current is not None:
        if current.kind is PDF_definition.DefinitionKind.MODULE:
            return True
        if current.kind is not PDF_definition.DefinitionKind.CLASS:
            return False
        current = current.parent
    return False


def _path_policy(path: str) -> _PathPolicy:
    """Return package and visibility classification for one source path."""
    return _PathPolicy(package=_is_package_path(path), public=missing_documentation.is_public_module_path(path))


def _is_package_path(path: str) -> bool:
    """Return whether a path names a package initializer."""
    return pathlib.PurePath(path).stem == "__init__"


def _is_dunder_method(definition: PDF_definition.DefinitionInfo) -> bool:
    """Return whether a function definition has a dunder name."""
    return definition.name.startswith("__") and definition.name.endswith("__") and len(definition.name) > 4


def _definition_line_numbers(definition: PDF_definition.DefinitionInfo, *, context: RuleContext) -> tuple[int, ...]:
    """Return source lines occupied by the definition introducer."""
    if definition.kind is PDF_definition.DefinitionKind.MODULE:
        return (1,)
    code_range = context.positions[definition.node]
    if isinstance(definition.node, cst.ClassDef):
        return (code_range.start.line,)
    if isinstance(definition.node, cst.FunctionDef):
        return (code_range.start.line,)
    raise AssertionError(f"Unexpected missing owner-docstring node: {type(definition.node).__name__}")


def _missing_docstring_message(definition: PDF_definition.DefinitionInfo, *, policy: MissingOwnerDocumentationPolicy) -> str:
    """Return the diagnostic message for one missing owner docstring."""
    if policy.entity in {"package", "module"}:
        return f"{_visibility(policy)} {policy.entity} is missing docstring"
    if policy.entity == "init":
        return f"{_visibility(policy)} __init__ method '{definition.qualified_name}' is missing docstring"
    if policy.entity == "dunder-method":
        return f"{_visibility(policy)} dunder method '{definition.qualified_name}' is missing docstring"
    return f"{_visibility(policy)} {_entity_label(policy.entity)} '{_display_name(definition)}' is missing docstring"


def _visibility(policy: MissingOwnerDocumentationPolicy) -> str:
    """Return the message visibility label for a policy."""
    return "Public" if policy.public else "Private"


def _entity_label(entity: str) -> str:
    """Return a human-readable entity name."""
    return entity.replace("-", " ")


def _display_name(definition: PDF_definition.DefinitionInfo) -> str:
    """Return a diagnostic display name for one definition."""
    if definition.kind is PDF_definition.DefinitionKind.MODULE:
        return definition.name
    return definition.qualified_name
