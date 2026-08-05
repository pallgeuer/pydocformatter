"""Typed docstring entry helpers for owning-docstring rules.

Attributes:
    TypedDocumentationSubject (TypeAlias): Documented subject groups dispatched by PDF7xx rules.
    TypedDocumentationTarget (TypeAlias): Code/documentation pair inspected by PDF7xx rules.
    TypedDocstringEntry (TypeAlias): Logical owning-docstring entry with optional type and description text.
    TypedDocstringTypeSource (TypeAlias): Docstring type spelling and its source location.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import typing
import operator

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.definition_helpers.typed_documentation_models as typed_models
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.definition_helpers import (
    attribute_documentation,
    docstring_sections,
    docstring_source,
    entry_completeness,
    parameter_documentation,
    rest_fields,
    section_edits,
    static_names,
    type_expressions,
    value_documentation,
)


if typing.TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.models import RuleMetadata


_YIELD_CONTAINER_NAMES = (
    "typing.Generator",
    "typing.Iterator",
    "typing.Iterable",
    "typing.AsyncGenerator",
    "typing.AsyncIterator",
    "typing.AsyncIterable",
    "collections.abc.Generator",
    "collections.abc.Iterator",
    "collections.abc.Iterable",
    "collections.abc.AsyncGenerator",
    "collections.abc.AsyncIterator",
    "collections.abc.AsyncIterable",
)

TypedDocumentationSubject = typed_models.TypedDocumentationSubject
TypedDocumentationTarget = typed_models.TypedDocumentationTarget
TypedDocstringEntry = typed_models.TypedDocstringEntry
TypedDocstringTypeSource = typed_models.TypedDocstringTypeSource


def missing_description_violations(targets: tuple[TypedDocumentationTarget, ...], *, meta: RuleMetadata, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return diagnostics for documented targets without prose descriptions.

    Args:
        targets (tuple[TypedDocumentationTarget, ...]): Code/documentation pairs to inspect.
        meta (RuleMetadata): Metadata for the PDF7xx rule reporting the findings.
        label (str): Human-readable target label used in per-instance diagnostic messages.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for entries that have no semantic description.
    """
    return sort_violations(
        rule_violations.diagnostic(meta, target.entry.line_numbers, instance_message=f"{label} '{target.name}' docstring entry is missing a description")
        for target in targets
        if target.entry.has_value_entry and not entry_completeness.has_prose_description(target.entry)
    )


def required_type_violations(targets: tuple[TypedDocumentationTarget, ...], *, context: RuleContext, meta: RuleMetadata, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return diagnostics for documented targets without docstring types.

    Args:
        targets (tuple[TypedDocumentationTarget, ...]): Code/documentation pairs to inspect.
        context (RuleContext): Current source context used to construct safe source edits.
        meta (RuleMetadata): Metadata for the PDF7xx rule reporting the findings.
        label (str): Human-readable target label used in per-instance diagnostic messages.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for entries missing docstring type text.
    """
    return sort_violations(
        rule_violations.violation_for_optional_planned_source_change(
            meta, _planned_required_type_change(target, context=context), line_numbers=target.entry.line_numbers, instance_message=f"{label} '{target.name}' docstring entry is missing a type"
        )
        for target in targets
        if not target.entry.type_sources
    )


def forbidden_type_violations(
    targets: tuple[TypedDocumentationTarget, ...], *, context: RuleContext, meta: RuleMetadata, label: str, correction: typed_models.TypeRemovalCorrection
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return diagnostics for documented targets with docstring types.

    Args:
        targets (tuple[TypedDocumentationTarget, ...]): Code/documentation pairs to inspect.
        context (RuleContext): Current source context used to construct safe source edits.
        meta (RuleMetadata): Metadata for the PDF7xx rule reporting the findings.
        label (str): Human-readable target label used in per-instance diagnostic messages.
        correction (typed_models.TypeRemovalCorrection): Explicit policy controlling whether safe type removals are
            planned.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for entries that include forbidden docstring type text.
    """
    return sort_violations(
        rule_violations.violation_for_optional_planned_source_change(
            meta,
            _planned_forbidden_type_change(source, context=context) if correction is typed_models.TypeRemovalCorrection.REMOVE else None,
            line_numbers=source.line_numbers,
            instance_message=f"{label} '{target.name}' docstring entry should not include a type",
        )
        for target in targets
        for source in target.entry.type_sources
    )


def mismatch_violations(targets: tuple[TypedDocumentationTarget, ...], *, context: RuleContext, meta: RuleMetadata, label: str) -> tuple[rule_violations.RuleViolation, ...]:
    """Return diagnostics for conservative docstring/code annotation mismatches.

    Args:
        targets (tuple[TypedDocumentationTarget, ...]): Code/documentation pairs to compare.
        context (RuleContext): Current source context used for import-aware type comparison.
        meta (RuleMetadata): Metadata for the PDF7xx rule reporting the findings.
        label (str): Human-readable target label used in per-instance diagnostic messages.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Diagnostics for comparable docstring and code types with different
            AST shapes.
    """
    violations: list[rule_violations.RuleViolation] = []
    aliases = _module_type_aliases(context)
    for target in targets:
        if target.annotation_text is None:
            continue
        annotation_dump = type_expressions.comparable_type_dump(target.annotation_text, aliases=aliases)
        if annotation_dump is None:
            continue
        for source in target.entry.type_sources:
            documented_dump = type_expressions.comparable_type_dump(source.text, aliases=aliases)
            if documented_dump is None or documented_dump == annotation_dump:
                continue
            violations.append(rule_violations.diagnostic(meta, source.line_numbers, instance_message=f"{label} '{target.name}' docstring type does not match the annotation"))
    return sort_violations(violations)


def _planned_required_type_change(target: TypedDocumentationTarget, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a safe insertion of one missing docstring type from its code annotation."""
    annotation_text = target.annotation_text
    entry = target.entry
    if annotation_text is None or "\n" in annotation_text or "\r" in annotation_text:
        return None
    if entry.type_entry is not None:
        return _planned_empty_rest_type_change(entry, annotation_text, context=context)
    if entry.docstring.structure.convention is DocstringConvention.GOOGLE:
        return _planned_google_type_insertion(entry, annotation_text, context=context)
    if entry.docstring.structure.convention is DocstringConvention.REST:
        return _planned_rest_type_field_insertion(target, context=context)
    return None


def _planned_empty_rest_type_change(entry: TypedDocstringEntry, annotation_text: str, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a safe fill of one existing empty reStructuredText type field."""
    type_entry = entry.type_entry
    if type_entry is None or type_entry.end_line != type_entry.start_line + 1:
        return None
    line = entry.docstring.structure.lines[type_entry.start_line]
    stripped_end = len(line.text.rstrip(" \t"))
    separator = "" if stripped_end < len(line.text) else " "
    return section_edits.planned_line_text_change(entry.docstring, line, len(line.text), len(line.text), f"{separator}{annotation_text}", context=context, line_numbers=entry.line_numbers)


def _planned_google_type_insertion(entry: TypedDocstringEntry, annotation_text: str, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a safe parenthesized type insertion for one Google entry."""
    value_entry = entry.value_entry
    if value_entry is None or value_entry.type_edit_slot is None:
        return None
    slot = value_entry.type_edit_slot
    if slot.removal_start_column is not None or slot.removal_end_column is not None:
        return None
    line = entry.docstring.structure.lines[slot.line_index]
    return section_edits.planned_line_text_change(entry.docstring, line, slot.insertion_column, slot.insertion_column, f" ({annotation_text})", context=context, line_numbers=entry.line_numbers)


def _planned_rest_type_field_insertion(target: TypedDocumentationTarget, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a safe paired reStructuredText type-field insertion."""
    entry = target.entry
    value_entry = entry.value_entry
    if value_entry is None:
        return None
    line = entry.docstring.structure.lines[value_entry.start_line]
    if value_entry.end_line < len(entry.docstring.structure.lines):
        insertion_offset = entry.docstring.structure.lines[value_entry.end_line].start_offset
    elif entry.docstring.value.endswith("\n"):
        insertion_offset = len(entry.docstring.value)
    else:
        return None
    field = _rest_type_field(target, value_entry)
    if field is None:
        return None
    raw_prefix = line.raw_text[: line.text_raw_start_column]
    raw_text = f"{raw_prefix}{line.text_indent}{field}"
    return section_edits.planned_value_text_change(
        entry.docstring, insertion_offset, insertion_offset, f"{raw_text}\n", context=context, line_numbers=entry.line_numbers, source_text=f"{raw_text}{context.line_ending}"
    )


def _rest_type_field(target: TypedDocumentationTarget, value_entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical paired reStructuredText type field for one target."""
    annotation_text = target.annotation_text
    if annotation_text is None:
        return None
    if value_entry.kind is PDF_definition.DocstringEntryKind.PARAMETER:
        return f":type {parameter_documentation.parameter_comparison_name(target.name, convention=DocstringConvention.REST)}: {annotation_text}"
    if value_entry.kind is PDF_definition.DocstringEntryKind.RETURN:
        return f":rtype: {annotation_text}"
    if value_entry.kind is PDF_definition.DocstringEntryKind.YIELD:
        argument = f" {value_entry.field_argument.lstrip('*')}" if value_entry.field_argument else ""
        return f":ytype{argument}: {annotation_text}"
    if value_entry.kind is PDF_definition.DocstringEntryKind.ATTRIBUTE:
        return f":vartype {target.name.lstrip('*')}: {annotation_text}"
    return None


def _planned_forbidden_type_change(source: TypedDocstringTypeSource, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a safe removal of one forbidden Google or reStructuredText type."""
    docstring = source.docstring
    entry = source.entry
    if docstring.structure.convention is DocstringConvention.REST and docstring_sections.is_rest_type_field(entry.field_name):
        start_line = docstring.structure.lines[entry.start_line]
        start_offset = start_line.start_offset
        end_offset = docstring.structure.lines[entry.end_line].start_offset if entry.end_line < len(docstring.structure.lines) else len(docstring.value)
        return section_edits.planned_value_text_change(docstring, start_offset, end_offset, "", context=context, line_numbers=source.line_numbers)
    if docstring.structure.convention is not DocstringConvention.GOOGLE or entry.type_edit_slot is None:
        return None
    slot = entry.type_edit_slot
    if slot.removal_start_column is None or slot.removal_end_column is None:
        return None
    line = docstring.structure.lines[slot.line_index]
    return section_edits.planned_line_text_change(docstring, line, slot.removal_start_column, slot.removal_end_column, "", context=context, line_numbers=source.line_numbers)


def parameter_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Return documented parameter entries paired with signature annotations.

    Args:
        context (RuleContext): Current rule context with prepared PDF definitions and docstring structures.

    Returns:
        tuple[TypedDocumentationTarget, ...]: Parsed parameter docstring entries that correspond to real signature
            parameters.
    """
    return _cached_targets(context, TypedDocumentationSubject.PARAMETER, lambda: _collect_parameter_targets(context))


def return_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Return documented return entries paired with return annotations.

    Args:
        context (RuleContext): Current rule context with prepared function facts and docstring structures.

    Returns:
        tuple[TypedDocumentationTarget, ...]: Parsed return docstring entries for non-generator functions.
    """
    return _cached_targets(context, TypedDocumentationSubject.RETURN, lambda: _collect_return_targets(context))


def yield_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Return documented yield entries paired with recognized generator yield annotations.

    Args:
        context (RuleContext): Current rule context with prepared function facts and docstring structures.

    Returns:
        tuple[TypedDocumentationTarget, ...]: Parsed yield docstring entries for functions that contain yield
            expressions.
    """
    return _cached_targets(context, TypedDocumentationSubject.YIELD, lambda: _collect_yield_targets(context))


def class_attribute_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Return owner-docstring class attribute entries paired with assignment annotations.

    Args:
        context (RuleContext): Current rule context with prepared class definitions, attributes, and docstring
            structures.

    Returns:
        tuple[TypedDocumentationTarget, ...]: Parsed class docstring attribute entries that correspond to inventoried
            class attributes.
    """
    return _cached_targets(context, TypedDocumentationSubject.CLASS_ATTRIBUTE, lambda: _attribute_targets(context, owner_kind=PDF_definition.DefinitionKind.CLASS, include_instance=True))


def module_attribute_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Return owner-docstring module attribute entries paired with assignment annotations.

    Args:
        context (RuleContext): Current rule context with prepared module attributes and docstring structures.

    Returns:
        tuple[TypedDocumentationTarget, ...]: Parsed module docstring attribute entries that correspond to inventoried
            module attributes.
    """
    return _cached_targets(context, TypedDocumentationSubject.MODULE_ATTRIBUTE, lambda: _attribute_targets(context, owner_kind=PDF_definition.DefinitionKind.MODULE, include_instance=False))


def enum_like_class(definition: PDF_definition.DefinitionInfo, configured_bases: tuple[str, ...], *, context: RuleContext) -> bool:
    """Return whether a class directly inherits from a configured enum-like base.

    Args:
        definition (PDF_definition.DefinitionInfo): Class definition to classify syntactically.
        configured_bases (tuple[str, ...]): Direct base names that invert PDF713's class attribute type policy.
        context (RuleContext): Current source context used for import-aware matching.

    Returns:
        bool: Whether any direct class base matches the configured enum-like base names.
    """
    if not isinstance(definition.node, cst.ClassDef):
        return False
    return any(static_names.configured_expression_matches(base.value, configured_bases, context=context) for base in definition.node.bases)


def _attribute_targets(context: RuleContext, *, owner_kind: PDF_definition.DefinitionKind, include_instance: bool) -> tuple[TypedDocumentationTarget, ...]:
    """Return owner-docstring attribute entries for one owner kind."""
    data = PDF_definition.PDF.require_data(context)
    targets: list[TypedDocumentationTarget] = []
    for definition in data.definitions:
        if definition.kind is not owner_kind:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None:
            continue
        annotations = {
            attribute.name: _attribute_annotation_text(attribute.annotated_info, context=context)
            for attribute in attribute_documentation.inventory_attributes(data, definition, include_instance=include_instance)
        }
        targets.extend(
            TypedDocumentationTarget(name=entry.name, entry=entry, annotation_text=annotations[entry.name], owner=definition)
            for entry in _logical_entries(docstring, PDF_definition.DocstringEntryKind.ATTRIBUTE)
            if entry.name is not None and entry.name in annotations
        )
    return tuple(targets)


def _cached_targets(context: RuleContext, subject: TypedDocumentationSubject, collector: typing.Callable[[], tuple[TypedDocumentationTarget, ...]]) -> tuple[TypedDocumentationTarget, ...]:
    """Return cached typed documentation targets for one subject."""
    data = PDF_definition.PDF.require_data(context)
    cached_targets = data._typed_documentation_targets
    if cached_targets is None:
        cached_targets = {}
        object.__setattr__(data, "_typed_documentation_targets", cached_targets)
    targets = cached_targets.get(subject)
    if targets is None:
        targets = collector()
        cached_targets[subject] = targets
    return targets


def _module_type_aliases(context: RuleContext) -> type_expressions.TypeAliasMap:
    """Return cached module import aliases for type expression comparisons."""
    data = PDF_definition.PDF.require_data(context)
    aliases = data._type_aliases
    if aliases is None:
        aliases = type_expressions.module_type_aliases(context.module)
        object.__setattr__(data, "_type_aliases", aliases)
    return aliases


def _collect_parameter_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Collect documented parameter entries paired with signature annotations."""
    data = PDF_definition.PDF.require_data(context)
    targets: list[TypedDocumentationTarget] = []
    for definition in data.definitions:
        if definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None:
            continue
        entries = _logical_entries(docstring, PDF_definition.DocstringEntryKind.PARAMETER)
        annotations = {
            parameter.comparison_name: _annotation_text(_parameter_annotation(parameter.name, definition.parameters), context=context)
            for parameter in parameter_documentation.signature_parameters(definition, context=context)
            if not parameter.implicit_receiver
        }
        for entry in entries:
            if entry.name is None:
                continue
            comparison_name = parameter_documentation.parameter_comparison_name(entry.name, convention=entry.docstring.structure.convention)
            if comparison_name in annotations:
                targets.append(TypedDocumentationTarget(name=entry.name, entry=entry, annotation_text=annotations[comparison_name], owner=definition))
    return tuple(targets)


def _collect_return_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Collect documented return entries paired with return annotations."""
    targets: list[TypedDocumentationTarget] = []
    for definition, docstring, facts in value_documentation.documented_function_facts(context):
        if facts.any_yields:
            continue
        annotation_text = _annotation_text(definition.returns, context=context)
        targets.extend(
            TypedDocumentationTarget(name="return", entry=entry, annotation_text=annotation_text, owner=definition) for entry in _logical_entries(docstring, PDF_definition.DocstringEntryKind.RETURN)
        )
    return tuple(targets)


def _collect_yield_targets(context: RuleContext) -> tuple[TypedDocumentationTarget, ...]:
    """Collect documented yield entries paired with recognized generator yield annotations."""
    targets: list[TypedDocumentationTarget] = []
    for definition, docstring, facts in value_documentation.documented_function_facts(context):
        if not facts.any_yields:
            continue
        annotation_text = _yield_annotation_text(definition.returns, context=context)
        targets.extend(
            TypedDocumentationTarget(name="yield", entry=entry, annotation_text=annotation_text, owner=definition) for entry in _logical_entries(docstring, PDF_definition.DocstringEntryKind.YIELD)
        )
    return tuple(targets)


def _logical_entries(docstring: PDF_definition.DocstringInfo, kind: PDF_definition.DocstringEntryKind) -> tuple[TypedDocstringEntry, ...]:
    """Return logical entries, merging paired reST value and type fields."""
    if docstring.structure.convention is not DocstringConvention.REST:
        return tuple(logical_entry for entry in docstring.structure.entries if entry.kind is kind for logical_entry in _entries_from_raw(docstring, entry))
    pairing = rest_fields.pair_value_and_type_fields(docstring.structure.entries, kind)
    type_parts_by_value_order = {pair.value.order: pair.type for pair in pairing.pairs}
    logical: list[tuple[int, TypedDocstringEntry]] = []
    for value_part in pairing.value_parts:
        type_part = type_parts_by_value_order.get(value_part.order)
        logical.append((value_part.order, _merged_rest_entry(docstring, name=value_part.name, value_entry=value_part.entry, type_entry=type_part.entry if type_part is not None else None)))
    logical.extend((type_part.order, _merged_rest_entry(docstring, name=type_part.name, value_entry=None, type_entry=type_part.entry)) for type_part in pairing.orphan_types)
    return tuple(entry for _, entry in sorted(logical, key=operator.itemgetter(0)))


def _entries_from_raw(docstring: PDF_definition.DocstringInfo, entry: PDF_definition.DocstringEntry) -> tuple[TypedDocstringEntry, ...]:
    """Return logical entries from one parsed Google or NumPy entry."""
    names = entry.names or (None,)
    line_numbers = _entry_line_numbers(docstring, entry)
    type_sources = _type_sources(docstring, entry, fallback_line_numbers=line_numbers)
    return tuple(
        TypedDocstringEntry(name=name, type_sources=type_sources, description=entry.description, line_numbers=line_numbers, docstring=docstring, value_entry=entry, type_entry=None) for name in names
    )


def _merged_rest_entry(
    docstring: PDF_definition.DocstringInfo, *, name: str | None, value_entry: PDF_definition.DocstringEntry | None, type_entry: PDF_definition.DocstringEntry | None
) -> TypedDocstringEntry:
    """Return a logical reST entry from value and type fields."""
    source_entry = value_entry or type_entry
    if source_entry is None:
        raise ValueError("A reStructuredText logical entry requires a value or type field")
    source_line_numbers = _entry_line_numbers(docstring, source_entry)
    type_sources = (
        *(() if value_entry is None else _type_sources(docstring, value_entry, fallback_line_numbers=source_line_numbers)),
        *(() if type_entry is None else _type_sources(docstring, type_entry, fallback_line_numbers=_entry_line_numbers(docstring, type_entry))),
    )
    return TypedDocstringEntry(
        name=name,
        type_sources=type_sources,
        description=value_entry.description if value_entry is not None else "",
        line_numbers=source_line_numbers,
        docstring=docstring,
        value_entry=value_entry,
        type_entry=type_entry,
    )


def _type_sources(docstring: PDF_definition.DocstringInfo, entry: PDF_definition.DocstringEntry, *, fallback_line_numbers: tuple[int, ...]) -> tuple[TypedDocstringTypeSource, ...]:
    """Return concrete type spellings supplied by one parsed entry."""
    if entry.type_info is None or not entry.type_info.text.strip():
        return ()
    return (
        TypedDocstringTypeSource(
            text=entry.type_info.text.strip(),
            line_numbers=_entry_line_numbers(docstring, entry) if docstring_sections.is_rest_type_field(entry.field_name) else fallback_line_numbers,
            docstring=docstring,
            entry=entry,
        ),
    )


def _entry_line_numbers(docstring: PDF_definition.DocstringInfo, entry: PDF_definition.DocstringEntry) -> tuple[int, ...]:
    """Return source line numbers for one parsed docstring entry."""
    return docstring_source.docstring_line_numbers(docstring, docstring.structure.lines[entry.start_line])


def _parameter_annotation(name: str, parameters: cst.Parameters) -> cst.Annotation | None:
    """Return a signature parameter annotation by raw parameter name."""
    raw_parameters = [*parameters.posonly_params, *parameters.params]
    if isinstance(parameters.star_arg, cst.Param):
        raw_parameters.append(parameters.star_arg)
    raw_parameters.extend(parameters.kwonly_params)
    if isinstance(parameters.star_kwarg, cst.Param):
        raw_parameters.append(parameters.star_kwarg)
    for parameter in raw_parameters:
        if parameter.name.value == name:
            return parameter.annotation
    return None


def _annotation_text(annotation: cst.Annotation | None, *, context: RuleContext) -> str | None:
    """Return source text for an annotation, unwrapping stringized annotations."""
    if annotation is None:
        return None
    expression = annotation.annotation
    if isinstance(expression, cst.SimpleString):
        evaluated_value = expression.evaluated_value
        return evaluated_value if isinstance(evaluated_value, str) else None
    return context.module.code_for_node(expression)


def _attribute_annotation_text(attribute: PDF_definition.AttributeInfo | None, *, context: RuleContext) -> str | None:
    """Return annotation source text for an annotated attribute assignment."""
    if attribute is not None and isinstance(attribute.node, cst.AnnAssign):
        return _annotation_text(attribute.node.annotation, context=context)
    return None


def _yield_annotation_text(annotation: cst.Annotation | None, *, context: RuleContext) -> str | None:
    """Return the yield type from a recognized generator return annotation."""
    if annotation is None:
        return None
    expression = annotation.annotation
    stringized = False
    if isinstance(expression, cst.SimpleString):
        evaluated_value = expression.evaluated_value
        if not isinstance(evaluated_value, str):
            return None
        try:
            expression = cst.parse_expression(evaluated_value)
        except cst.ParserSyntaxError:
            return None
        stringized = True
    if not isinstance(expression, cst.Subscript) or len(expression.slice) not in {1, 2, 3}:
        return None
    if not _yield_container_matches(expression.value, context=context, stringized=stringized):
        return None
    first_slice = expression.slice[0].slice
    if not isinstance(first_slice, cst.Index):
        return None
    return context.module.code_for_node(first_slice.value)


def _yield_container_matches(expression: cst.BaseExpression, *, context: RuleContext, stringized: bool) -> bool:
    """Return whether an annotation container is a recognized yield container."""
    if not stringized:
        return static_names.configured_expression_name(expression, _YIELD_CONTAINER_NAMES, context=context) is not None
    source_name = static_names.expression_name(expression)
    if source_name is None:
        return False
    return _normalized_source_name(source_name, _module_type_aliases(context)) in _YIELD_CONTAINER_NAMES


def _normalized_source_name(source_name: str, aliases: type_expressions.TypeAliasMap) -> str:
    """Return source name with an unshadowed import alias root expanded."""
    root, dot, rest = source_name.partition(".")
    qualified_root = aliases.get(root, root)
    return f"{qualified_root}.{rest}" if dot else qualified_root


def sort_violations(violations: typing.Iterable[rule_violations.RuleViolation]) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations ordered by their reported source lines.

    Args:
        violations (typing.Iterable[rule_violations.RuleViolation]): Violations to order.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Violations sorted by finding line numbers.
    """
    return tuple(sorted(violations, key=lambda violation: violation.finding.line_numbers))
