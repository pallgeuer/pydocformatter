"""Attribute inventory and documented attribute comparison helpers."""

from __future__ import annotations

import dataclasses
import os
import pathlib
from collections.abc import Mapping

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.definition import RuleContext


@dataclasses.dataclass(frozen=True)
class InventoryAttribute:
    """One inventory attribute target relevant to attribute documentation rules.

    Attributes:
        name (str): Attribute target name used for docstring comparison.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the attribute assignment.
        info (PDF_definition.AttributeInfo): Assignment inventory record that supplied this target.
    """

    name: str
    line_numbers: tuple[int, ...]
    info: PDF_definition.AttributeInfo


@dataclasses.dataclass(frozen=True)
class DocumentedAttribute:
    """One parsed attribute name from owner docstring documentation.

    Attributes:
        name (str): Attribute name as written in the docstring.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the documented entry.
    """

    name: str
    line_numbers: tuple[int, ...]


def inventory_attributes(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo, *, include_instance: bool) -> tuple[InventoryAttribute, ...]:
    """Return first-seen inventory attribute targets for an owner.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class whose attribute inventory should be collected.
        include_instance (bool): Whether supported `self.*` assignments from `__init__` should be included for class
            owners.

    Returns:
        tuple[InventoryAttribute, ...]: Unique attribute targets in first-seen order.
    """
    attributes: list[InventoryAttribute] = []
    seen: set[str] = set()
    for attribute in data.attributes_for(owner):
        if attribute.instance and not include_instance:
            continue
        for name, line_numbers in zip(attribute.targets, attribute.target_line_numbers, strict=True):
            if name in seen:
                continue
            seen.add(name)
            attributes.append(InventoryAttribute(name=name, line_numbers=line_numbers, info=attribute))
    return tuple(attributes)


def documented_attributes(docstring: PDF_definition.DocstringInfo) -> tuple[DocumentedAttribute, ...]:
    """Return comparable attribute names parsed from an owner docstring.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed module or class docstring to inspect for attribute entries.

    Returns:
        tuple[DocumentedAttribute, ...]: Documented attribute names with diagnostic line targets.
    """
    attributes: list[DocumentedAttribute] = []
    for entry in docstring.structure.entries:
        if entry.kind is not PDF_definition.DocstringEntryKind.ATTRIBUTE:
            continue
        line = docstring.structure.lines[entry.start_line]
        line_numbers = PDF_definition.docstring_line_numbers(docstring, line)
        for name in entry.names:
            if name:
                attributes.append(DocumentedAttribute(name=name, line_numbers=line_numbers))
    return tuple(attributes)


def attached_attribute_docstrings_by_name(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo) -> Mapping[str, tuple[PDF_definition.DocstringInfo, ...]]:
    """Return attached attribute docstrings for an owner indexed by target name.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class whose adjacent attribute docstrings should be indexed.

    Returns:
        Mapping[str, tuple[PDF_definition.DocstringInfo, ...]]: Attribute names mapped to attached docstrings
            documenting them.
    """
    return data.attached_attribute_docstrings_by_name(owner)


def documented_attribute_names(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo) -> frozenset[str]:
    """Return owner and attached docstring attribute names for an owner.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class whose documented attribute names should be collected.

    Returns:
        frozenset[str]: Names documented either in the owner docstring or by attached attribute docstrings.
    """
    names: set[str] = set(attached_attribute_docstrings_by_name(data, owner))
    owner_docstring = data.docstring_for(owner)
    if owner_docstring is not None:
        names.update(attribute.name for attribute in documented_attributes(owner_docstring))
    return frozenset(names)


def has_attribute_documentation(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo) -> bool:
    """Return whether an owner has any recognized attribute documentation.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class whose documentation should be inspected.

    Returns:
        bool: Whether the owner has attached attribute docstrings, attribute entries, or an attribute section.
    """
    if attached_attribute_docstrings_by_name(data, owner):
        return True
    owner_docstring = data.docstring_for(owner)
    if owner_docstring is None:
        return False
    return bool(documented_attributes(owner_docstring)) or any(section.name.lower() in {"attribute", "attributes"} for section in owner_docstring.structure.sections)


def should_check_missing_attributes(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo, *, context: RuleContext) -> bool:
    """Return whether a missing-attribute rule should inspect an owner.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class whose attributes might require documentation.
        context (RuleContext): Current file context with resolved missing-documentation settings.

    Returns:
        bool: Whether missing-attribute checks should report for this owner.

    Raises:
        AssertionError: If settings contain an unexpected missing-documentation policy value.
    """
    if context.settings.docstring_missing_documentation_public_only and not is_public_attribute_owner(owner, context=context):
        return False
    has_relevant_documentation = has_attribute_documentation(data, owner)
    if has_relevant_documentation:
        return True
    owner_docstring = data.docstring_for(owner)
    if owner_docstring is None:
        return False
    policy = context.settings.docstring_missing_documentation
    if policy is settings_check.DocstringMissingDocumentation.HAS_SECTION:
        return False
    if policy is settings_check.DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS:
        return missing_documentation.has_more_than_summary(owner_docstring)
    if policy is settings_check.DocstringMissingDocumentation.ALL_DOCSTRINGS:
        return True
    raise AssertionError(f"Unexpected missing-documentation policy: {policy}")


def missing_suppression_targets(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo, attribute_name: str) -> tuple[tuple[int, ...], ...]:
    """Return docstring line targets that can suppress a missing attribute finding.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class that owns the missing attribute.
        attribute_name (str): Attribute name whose attached docstrings should also suppress the finding.

    Returns:
        tuple[tuple[int, ...], ...]: Owner and attached docstring physical line groups accepted by suppressions.
    """
    targets: list[tuple[int, ...]] = []
    owner_docstring = data.docstring_for(owner)
    if owner_docstring is not None:
        targets.append(PDF_definition.docstring_physical_line_numbers(owner_docstring))
    targets.extend(PDF_definition.docstring_physical_line_numbers(docstring) for docstring in attached_attribute_docstrings_by_name(data, owner).get(attribute_name, ()))
    return tuple(dict.fromkeys(targets))


def is_public_attribute_owner(owner: PDF_definition.DefinitionInfo, *, context: RuleContext) -> bool:
    """Return whether an attribute owner is public for missing-attribute checks.

    Args:
        owner (PDF_definition.DefinitionInfo): Module or class definition that owns attribute inventory entries.
        context (RuleContext): Current file context used to evaluate module path privacy.

    Returns:
        bool: Whether broad public-only missing-attribute checks should inspect this owner.
    """
    if owner.kind is PDF_definition.DefinitionKind.MODULE:
        return _is_public_module_path(context.path)
    return missing_documentation.is_public_definition(owner)


def is_private_attribute_name(name: str) -> bool:
    """Return whether an attribute name is private for missing-attribute checks.

    Args:
        name (str): Attribute target name to classify.

    Returns:
        bool: Whether the name is underscore-prefixed and therefore not required by missing-attribute rules.
    """
    return name.startswith("_")


def _is_public_module_path(path: str) -> bool:
    """Return whether a source path names a public module or package."""
    if os.path.exists(path):
        return not any(part.startswith("_") for part in _existing_module_path_parts(path))
    return not any(part.startswith("_") for part in _synthetic_module_path_parts(path))


def _existing_module_path_parts(path: str) -> tuple[str, ...]:
    """Return module path parts from an existing file's package suffix."""
    pure_path = pathlib.PurePath(path)
    parts: list[str] = []
    stem = pure_path.stem
    if stem != "__init__":
        parts.append(stem)
    parent = pathlib.Path(path).resolve().parent
    while (parent / "__init__.py").exists():
        parts.append(parent.name)
        parent = parent.parent
    return tuple(reversed(parts))


def _synthetic_module_path_parts(path: str) -> tuple[str, ...]:
    """Return module path parts from a non-existing display path."""
    pure_path = pathlib.PurePath(path)
    module_parts: list[str] = []
    path_parts = tuple(part for part in pure_path.parts if part not in {"", ".", "..", pure_path.anchor})
    for index, part in enumerate(path_parts):
        if index == len(path_parts) - 1:
            stem = pathlib.PurePath(part).stem
            if stem != "__init__":
                module_parts.append(stem)
            continue
        module_parts.append(part)
    return tuple(module_parts)


def missing_attribute_violations(
    data: PDF_definition.PDFCategoryData,
    *,
    context: RuleContext,
    meta: rule_models.RuleMetadata,
    owner_kind: PDF_definition.DefinitionKind,
    owner_label: str,
    include_instance: bool,
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for inventory attributes missing documentation.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        context (RuleContext): Current file context with convention and missing-documentation settings.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose owners should be checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        include_instance (bool): Whether supported `self.*` assignments from `__init__` should be required.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Missing-attribute diagnostics for the requested owner kind.
    """
    if docstring_conventions.missing_documentation_is_inert(context.settings.docstring_convention):
        return ()
    violations: list[rule_violations.RuleViolation] = []
    for definition in data.definitions:
        if definition.kind is not owner_kind or not should_check_missing_attributes(data, definition, context=context):
            continue
        documented_names = documented_attribute_names(data, definition)
        for attribute in inventory_attributes(data, definition, include_instance=include_instance):
            if is_private_attribute_name(attribute.name) or attribute.name in documented_names:
                continue
            suppression_targets = missing_suppression_targets(data, definition, attribute.name)
            violations.append(
                rule_violations.diagnostic(
                    meta,
                    attribute.line_numbers,
                    suppression_line_numbers=suppression_targets,
                    instance_message=f"{owner_label} attribute '{attribute.name}' is missing docstring documentation",
                )
            )
    return tuple(violations)


def extraneous_attribute_violations(
    data: PDF_definition.PDFCategoryData,
    *,
    meta: rule_models.RuleMetadata,
    owner_kind: PDF_definition.DefinitionKind,
    owner_label: str,
    include_instance: bool,
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for docstring attributes absent from inventory.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose docstrings should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        include_instance (bool): Whether supported `self.*` assignments from `__init__` count as class inventory.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Extraneous attribute documentation diagnostics.
    """
    violations: list[rule_violations.RuleViolation] = []
    for definition in data.definitions:
        if definition.kind is not owner_kind:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None:
            continue
        allowed_names = {attribute.name for attribute in inventory_attributes(data, definition, include_instance=include_instance)}
        for attribute in documented_attributes(docstring):
            if attribute.name in allowed_names:
                continue
            violations.append(
                rule_violations.diagnostic(
                    meta,
                    attribute.line_numbers,
                    instance_message=f"{owner_label} docstring documents attribute '{attribute.name}' that is not present",
                )
            )
    return tuple(violations)


def duplicate_attribute_violations(
    data: PDF_definition.PDFCategoryData,
    *,
    meta: rule_models.RuleMetadata,
    owner_kind: PDF_definition.DefinitionKind,
    owner_label: str,
    include_instance: bool,
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for attached docstrings duplicated by owner attribute docs.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose duplicated docs should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        include_instance (bool): Whether attached `self.*` docstrings from `__init__` participate in duplicate checks.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Duplicate attached-attribute documentation diagnostics.
    """
    violations: list[rule_violations.RuleViolation] = []
    for definition in data.definitions:
        if definition.kind is not owner_kind:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None:
            continue
        attached_docstrings = attached_attribute_docstrings_by_name(data, definition)
        if not attached_docstrings:
            continue
        for attribute in documented_attributes(docstring):
            for attached_docstring in attached_docstrings.get(attribute.name, ()):
                owner = attached_docstring.owner
                if isinstance(owner, PDF_definition.AttributeInfo) and owner.instance and not include_instance:
                    continue
                violations.append(
                    rule_violations.diagnostic(
                        meta,
                        PDF_definition.docstring_physical_line_numbers(attached_docstring),
                        instance_message=f"Attached docstring for {owner_label.lower()} attribute '{attribute.name}' duplicates {owner_label.lower()} docstring attribute documentation",
                    )
                )
    return tuple(violations)
