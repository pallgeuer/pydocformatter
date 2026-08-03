"""Attribute inventory and documented attribute comparison helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli import settings_check
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_sections, documentation_order, missing_documentation


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.models as rule_models
    from pydocformatter.rules.definition import RuleContext


@dataclasses.dataclass(frozen=True)
class InventoryAttribute:
    """One inventory attribute target relevant to attribute documentation rules.

    Attributes:
        name (str): Attribute target name used for docstring comparison.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the attribute assignment.
        annotated_info (PDF_definition.AttributeInfo | None): First real annotated assignment for type comparison and
            safe type insertion.
        has_attachable_assignment (bool): Whether any real assignment for the name can own an attached docstring.
    """

    name: str
    line_numbers: tuple[int, ...]
    annotated_info: PDF_definition.AttributeInfo | None
    has_attachable_assignment: bool


@dataclasses.dataclass(frozen=True)
class DocumentedAttribute:
    """One parsed attribute name from owner docstring documentation.

    Attributes:
        name (str): Attribute name as written in the docstring.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the documented entry.
    """

    name: str
    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class AttributeOrderIssue:
    """One documented attribute that appears after a later source attribute.

    Attributes:
        documented_attribute (DocumentedAttribute): Late documentation occurrence that should move earlier.
        inventory_attribute (InventoryAttribute): Inventory attribute matched by the late documentation occurrence.
        preceding_inventory_attribute (InventoryAttribute): Highest-ranked inventory attribute documented earlier.
    """

    documented_attribute: DocumentedAttribute
    inventory_attribute: InventoryAttribute
    preceding_inventory_attribute: InventoryAttribute


def inventory_attributes(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo, *, include_instance: bool) -> tuple[InventoryAttribute, ...]:
    """Return first-seen inventory attribute targets for an owner.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class whose attribute inventory should be collected.
        include_instance (bool): Whether initializer assignments and literal slot declarations should be included for
            class owners.

    Returns:
        tuple[InventoryAttribute, ...]: Unique attribute targets in first-seen order.
    """
    first_targets: dict[str, tuple[int, ...]] = {}
    annotated_infos: dict[str, PDF_definition.AttributeInfo] = {}
    attachable_names: set[str] = set()
    for attribute in data.attributes_for(owner):
        if attribute.instance and not include_instance:
            continue
        for name, line_numbers in zip(attribute.targets, attribute.target_line_numbers, strict=True):
            first_targets.setdefault(name, line_numbers)
            if attribute.origin is not PDF_definition.AttributeOrigin.SLOT_DECLARATION:
                attachable_names.add(name)
                if isinstance(attribute.node, cst.AnnAssign):
                    annotated_infos.setdefault(name, attribute)
    return tuple(
        InventoryAttribute(name=name, line_numbers=line_numbers, annotated_info=annotated_infos.get(name), has_attachable_assignment=name in attachable_names)
        for name, line_numbers in first_targets.items()
    )


def documented_attributes(docstring: PDF_definition.DocstringInfo) -> tuple[DocumentedAttribute, ...]:
    """Return comparable attribute names parsed from an owner docstring.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed module or class docstring to inspect for attribute entries.

    Returns:
        tuple[DocumentedAttribute, ...]: Documented attribute names with diagnostic line targets.
    """
    return _documented_attributes(docstring, include_type_fields=True)


def value_documented_attributes(docstring: PDF_definition.DocstringInfo) -> tuple[DocumentedAttribute, ...]:
    """Return attribute names backed by value or description-bearing entries.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed owner docstring to inspect for attribute value entries.

    Returns:
        tuple[DocumentedAttribute, ...]: Attribute names documented by value entries rather than type-only fields.
    """
    return _documented_attributes(docstring, include_type_fields=False)


def attribute_order_issues(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo) -> tuple[AttributeOrderIssue, ...]:
    """Return documented attributes that do not follow first-seen source order.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared definitions, attributes, and docstrings for the current file.
        owner (PDF_definition.DefinitionInfo): Module or class whose inventory supplies the canonical order.
        docstring (PDF_definition.DocstringInfo): Owner docstring whose value-bearing attribute entries are checked.

    Returns:
        tuple[AttributeOrderIssue, ...]: Late first occurrences paired with their matched and highest-ranked preceding
            inventory attributes.
    """
    return documentation_order.order_issues(
        inventory_attributes(data, owner, include_instance=True),
        value_documented_attributes(docstring),
        ordered_key=lambda attribute: attribute.name,
        documented_key=lambda attribute: attribute.name,
        issue_factory=AttributeOrderIssue,
    )


def _documented_attributes(docstring: PDF_definition.DocstringInfo, *, include_type_fields: bool) -> tuple[DocumentedAttribute, ...]:
    """Return documented attribute names with optional reST type-only fields."""
    attributes: list[DocumentedAttribute] = []
    for entry in docstring.structure.entries:
        if entry.kind is not PDF_definition.DocstringEntryKind.ATTRIBUTE or (not include_type_fields and docstring_sections.is_rest_type_field(entry.field_name)):
            continue
        line = docstring.structure.lines[entry.start_line]
        line_numbers = PDF_definition.docstring_line_numbers(docstring, line)
        attributes.extend(DocumentedAttribute(name=name, line_numbers=line_numbers) for name in entry.names if name)
    return tuple(attributes)


def documented_attribute_names(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo) -> frozenset[str]:
    """Return owner and attached docstring attribute names for an owner.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        owner (PDF_definition.DefinitionInfo): Module or class whose documented attribute names should be collected.

    Returns:
        frozenset[str]: Names documented either in the owner docstring or by attached attribute docstrings.
    """
    names: set[str] = set(data.attached_attribute_docstrings_by_name(owner))
    owner_docstring = data.docstring_for(owner)
    if owner_docstring is not None:
        names.update(attribute.name for attribute in value_documented_attributes(owner_docstring))
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
    if data.attached_attribute_docstrings_by_name(owner):
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
    targets.extend(PDF_definition.docstring_physical_line_numbers(docstring) for docstring in data.attached_attribute_docstrings_by_name(owner).get(attribute_name, ()))
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
        return missing_documentation.is_public_module_path(context.source_path)
    return missing_documentation.is_public_definition(owner)


def is_private_attribute_name(name: str) -> bool:
    """Return whether an attribute name is private for missing-attribute checks.

    Args:
        name (str): Attribute target name to classify.

    Returns:
        bool: Whether the name is underscore-prefixed and therefore not required by missing-attribute rules.
    """
    return name.startswith("_")


def missing_attribute_violations(
    data: PDF_definition.PDFCategoryData, *, context: RuleContext, meta: rule_models.RuleMetadata, owner_kind: PDF_definition.DefinitionKind, owner_label: str, include_instance: bool
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for inventory attributes missing documentation.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        context (RuleContext): Current file context with convention and missing-documentation settings.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose owners should be checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        include_instance (bool): Whether initializer assignments and literal slot declarations should be required for
            class owners.

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
                    meta, attribute.line_numbers, suppression_line_numbers=suppression_targets, instance_message=f"{owner_label} attribute '{attribute.name}' is missing docstring documentation"
                )
            )
    return tuple(violations)


def extraneous_attribute_violations(
    data: PDF_definition.PDFCategoryData, *, meta: rule_models.RuleMetadata, owner_kind: PDF_definition.DefinitionKind, owner_label: str, include_instance: bool
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for docstring attributes absent from inventory.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose docstrings should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        include_instance (bool): Whether initializer assignments and literal slot declarations count as class inventory.

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
            violations.append(rule_violations.diagnostic(meta, attribute.line_numbers, instance_message=f"{owner_label} docstring documents attribute '{attribute.name}' that is not present"))
    return tuple(violations)


def duplicate_attribute_violations(
    data: PDF_definition.PDFCategoryData, *, meta: rule_models.RuleMetadata, owner_kind: PDF_definition.DefinitionKind, owner_label: str, include_instance: bool
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for attached docstrings duplicated by owner attribute docs.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose duplicated docs should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        include_instance (bool): Whether attached docstrings owned by initializer assignments participate in duplicate
            checks.

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
        attached_docstrings = data.attached_attribute_docstrings_by_name(definition)
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


def _attached_attribute_docstring_name_pairs(data: PDF_definition.PDFCategoryData, owner: PDF_definition.DefinitionInfo) -> tuple[tuple[str, PDF_definition.DocstringInfo], ...]:
    """Return attached attribute docstrings by source order and target order."""
    pairs: list[tuple[str, PDF_definition.DocstringInfo]] = []
    for docstring in data.docstrings:
        docstring_owner = docstring.owner
        if not isinstance(docstring_owner, PDF_definition.AttributeInfo):
            continue
        if docstring_owner.parent is not owner:
            continue
        pairs.extend((name, docstring) for name in dict.fromkeys(docstring_owner.targets))
    return tuple(pairs)


def private_owner_attribute_violations(
    data: PDF_definition.PDFCategoryData, *, meta: rule_models.RuleMetadata, owner_kind: PDF_definition.DefinitionKind, owner_label: str
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for private attributes documented in owner docstrings.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose owner docstrings should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Private owner-docstring attribute documentation diagnostics.
    """
    violations: list[rule_violations.RuleViolation] = []
    for definition in data.definitions:
        if definition.kind is not owner_kind:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None:
            continue
        for attribute in documented_attributes(docstring):
            if not is_private_attribute_name(attribute.name):
                continue
            violations.append(rule_violations.diagnostic(meta, attribute.line_numbers, instance_message=f"{owner_label} docstring documents private attribute '{attribute.name}'"))
    return tuple(violations)


def private_attached_attribute_violations(
    data: PDF_definition.PDFCategoryData, *, meta: rule_models.RuleMetadata, owner_kind: PDF_definition.DefinitionKind, owner_label: str, include_instance: bool
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for attached docstrings on private attributes.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose attached docs should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        include_instance (bool): Whether attached docstrings owned by initializer assignments participate in checks.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Private attached-attribute documentation diagnostics.
    """
    violations: list[rule_violations.RuleViolation] = []
    for definition in data.definitions:
        if definition.kind is not owner_kind:
            continue
        for name, docstring in _attached_attribute_docstring_name_pairs(data, definition):
            if not is_private_attribute_name(name):
                continue
            owner = docstring.owner
            if isinstance(owner, PDF_definition.AttributeInfo) and owner.instance and not include_instance:
                continue
            violations.append(
                rule_violations.diagnostic(
                    meta, PDF_definition.docstring_physical_line_numbers(docstring), instance_message=f"Private {owner_label.lower()} attribute '{name}' should not have an attached docstring"
                )
            )
    return tuple(violations)


def attribute_docstring_must_be_owner_violations(
    data: PDF_definition.PDFCategoryData, *, meta: rule_models.RuleMetadata, owner_kind: PDF_definition.DefinitionKind, owner_label: str, public: bool, include_instance: bool
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for attached attribute docstrings that should be owner documentation.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose attached docs should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        public (bool): Whether public attributes are reported instead of private attributes.
        include_instance (bool): Whether attached docstrings owned by initializer assignments participate in checks.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Placement diagnostics for attached attribute docstrings.
    """
    violations: list[rule_violations.RuleViolation] = []
    privacy_label = "Public" if public else "Private"
    for definition in data.definitions:
        if definition.kind is not owner_kind:
            continue
        for name, docstring in _attached_attribute_docstring_name_pairs(data, definition):
            if is_private_attribute_name(name) is public:
                continue
            owner = docstring.owner
            if isinstance(owner, PDF_definition.AttributeInfo) and owner.instance and not include_instance:
                continue
            violations.append(
                rule_violations.diagnostic(
                    meta,
                    PDF_definition.docstring_physical_line_numbers(docstring),
                    instance_message=f"{privacy_label} {owner_label.lower()} attribute '{name}' must use {owner_label.lower()} docstring documentation, not attached docstring",
                )
            )
    return tuple(violations)


def attribute_docstring_must_be_attached_violations(
    data: PDF_definition.PDFCategoryData, *, meta: rule_models.RuleMetadata, owner_kind: PDF_definition.DefinitionKind, owner_label: str, public: bool, include_instance: bool
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for owner attribute documentation that should be attached docstrings.

    Args:
        data (PDF_definition.PDFCategoryData): Prepared PDF definitions, attributes, and docstrings for the current
            file.
        meta (rule_models.RuleMetadata): Rule metadata to attach to diagnostics.
        owner_kind (PDF_definition.DefinitionKind): Definition kind, module or class, whose owner docstring should be
            checked.
        owner_label (str): Human-readable owner label used in diagnostic messages.
        public (bool): Whether public attributes are reported instead of private attributes.
        include_instance (bool): Whether initializer assignments that can own docstrings count as class inventory.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Placement diagnostics for owner docstring attribute documentation.
    """
    violations: list[rule_violations.RuleViolation] = []
    privacy_label = "Public" if public else "Private"
    for definition in data.definitions:
        if definition.kind is not owner_kind:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None:
            continue
        inventory_names = {attribute.name for attribute in inventory_attributes(data, definition, include_instance=include_instance) if attribute.has_attachable_assignment}
        for attribute in documented_attributes(docstring):
            if attribute.name not in inventory_names or is_private_attribute_name(attribute.name) is public:
                continue
            violations.append(
                rule_violations.diagnostic(
                    meta,
                    attribute.line_numbers,
                    instance_message=f"{privacy_label} {owner_label.lower()} attribute '{attribute.name}' must use attached docstring, not {owner_label.lower()} docstring documentation",
                )
            )
    return tuple(violations)
