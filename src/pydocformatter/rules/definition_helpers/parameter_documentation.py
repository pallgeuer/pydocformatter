from __future__ import annotations

import dataclasses

import libcst as cst

import pydocformatter.rules.definition_helpers.decorators as decorator_helpers
import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition import RuleContext


@dataclasses.dataclass(frozen=True)
class SignatureParameter:
    """One signature parameter relevant to parameter documentation rules."""

    name: str
    display_name: str
    comparison_name: str
    line_numbers: tuple[int, ...]
    implicit_receiver: bool
    unpacked: bool
    unpack_target_name: str | None


@dataclasses.dataclass(frozen=True)
class UnpackAnnotation:
    """Parsed information about a parameter annotation's Unpack usage."""

    unpacked: bool
    target_name: str | None


@dataclasses.dataclass(frozen=True)
class DocumentedParameter:
    """One parameter name parsed from a docstring entry."""

    name: str
    comparison_name: str
    line_numbers: tuple[int, ...]


def signature_parameters(definition: PDF_definition.DefinitionInfo, *, context: RuleContext) -> tuple[SignatureParameter, ...]:
    """Return comparable signature parameters for a function definition."""
    if definition.parameters is None or not isinstance(definition.node, cst.FunctionDef):
        return ()
    raw_parameters = [*definition.parameters.posonly_params, *definition.parameters.params]
    if isinstance(definition.parameters.star_arg, cst.Param):
        raw_parameters.append(definition.parameters.star_arg)
    raw_parameters.extend(definition.parameters.kwonly_params)
    if isinstance(definition.parameters.star_kwarg, cst.Param):
        raw_parameters.append(definition.parameters.star_kwarg)
    implicit_receiver_name = _implicit_receiver_name(definition)
    fallback_line = context.positions[definition.node].start.line
    return tuple(
        _signature_parameter(parameter, parameters=definition.parameters, context=context, implicit_receiver_name=implicit_receiver_name, fallback_line=fallback_line) for parameter in raw_parameters
    )


def typed_dict_keys_by_name(module: cst.Module) -> dict[str, frozenset[str]]:
    """Return same-module class-based TypedDict keys by TypedDict class name."""
    keys_by_name: dict[str, frozenset[str]] = {}
    for statement in module.body:
        if not isinstance(statement, cst.ClassDef) or not _is_typed_dict_class(statement):
            continue
        keys_by_name[statement.name.value] = frozenset(_typed_dict_class_keys(statement))
    return keys_by_name


def unpacked_keyword_parameters(parameters: tuple[SignatureParameter, ...]) -> tuple[SignatureParameter, ...]:
    """Return unpacked keyword-pack parameters from prepared signature parameters."""
    return tuple(parameter for parameter in parameters if parameter.unpacked and parameter.display_name.startswith("**"))


def _signature_parameter(
    parameter: cst.Param,
    *,
    parameters: cst.Parameters,
    context: RuleContext,
    implicit_receiver_name: str | None,
    fallback_line: int,
) -> SignatureParameter:
    unpack_annotation = _unpack_annotation(parameter.annotation)
    return SignatureParameter(
        name=parameter.name.value,
        display_name=_display_name(parameter, parameters),
        comparison_name=_comparison_name(parameter.name.value),
        line_numbers=_parameter_line_numbers(parameter, context=context, fallback_line=fallback_line),
        implicit_receiver=parameter.name.value == implicit_receiver_name,
        unpacked=unpack_annotation.unpacked,
        unpack_target_name=unpack_annotation.target_name,
    )


def documented_parameters(docstring: PDF_definition.DocstringInfo) -> tuple[DocumentedParameter, ...]:
    """Return comparable parameter names parsed from a docstring."""
    parameters: list[DocumentedParameter] = []
    for entry in docstring.structure.entries:
        if entry.kind is not PDF_definition.DocstringEntryKind.PARAMETER:
            continue
        line = docstring.structure.lines[entry.start_line]
        line_numbers = PDF_definition.docstring_line_numbers(docstring, line)
        for name in entry.names:
            if name:
                parameters.append(DocumentedParameter(name=name, comparison_name=_comparison_name(name), line_numbers=line_numbers))
    return tuple(parameters)


def should_check_missing_parameters(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> bool:
    """Return whether missing parameter documentation should be checked for a docstring."""
    return missing_documentation.should_check_missing_documentation(definition, docstring, context=context, has_relevant_documentation=has_parameter_documentation(docstring))


def has_parameter_documentation(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a docstring contains parameter documentation structures."""
    return any(entry.kind is PDF_definition.DocstringEntryKind.PARAMETER for entry in docstring.structure.entries) or any(
        section.name.lower() in docstring_sections.PARAMETER_SECTION_NAMES for section in docstring.structure.sections
    )


def _implicit_receiver_name(definition: PDF_definition.DefinitionInfo) -> str | None:
    if definition.parent is None or definition.parent.kind is not PDF_definition.DefinitionKind.CLASS or _is_staticmethod(definition.decorators):
        return None
    if definition.parameters is None:
        return None
    first_parameter = (*definition.parameters.posonly_params, *definition.parameters.params)[:1]
    if not first_parameter:
        return None
    name = first_parameter[0].name.value
    return name if name in {"self", "cls"} else None


def _is_staticmethod(decorators: tuple[cst.Decorator, ...]) -> bool:
    return any((name := decorator_helpers.decorator_qualified_name(decorator.decorator)) is not None and name.rpartition(".")[2] == "staticmethod" for decorator in decorators)


def _unpack_annotation(annotation: cst.Annotation | None) -> UnpackAnnotation:
    if annotation is None:
        return UnpackAnnotation(unpacked=False, target_name=None)
    expression = annotation.annotation
    if isinstance(expression, cst.SimpleString):
        evaluated_value = expression.evaluated_value
        if not isinstance(evaluated_value, str):
            return UnpackAnnotation(unpacked=False, target_name=None)
        try:
            expression = cst.parse_expression(evaluated_value)
        except cst.ParserSyntaxError:
            return UnpackAnnotation(unpacked=False, target_name=None)
    return _unpack_expression(expression)


def _unpack_expression(expression: cst.BaseExpression) -> UnpackAnnotation:
    if not isinstance(expression, cst.Subscript):
        return UnpackAnnotation(unpacked=False, target_name=None)
    value = expression.value
    if not _is_unpack_value(value):
        return UnpackAnnotation(unpacked=False, target_name=None)
    return UnpackAnnotation(unpacked=True, target_name=_unpack_target_name(expression))


def _is_unpack_value(expression: cst.BaseExpression) -> bool:
    if isinstance(expression, cst.Name):
        return expression.value == "Unpack"
    if isinstance(expression, cst.Attribute):
        return expression.attr.value == "Unpack" and _expression_name(expression.value) in {"typing", "typing_extensions"}
    return False


def _unpack_target_name(expression: cst.Subscript) -> str | None:
    if len(expression.slice) != 1:
        return None
    subscript_slice = expression.slice[0].slice
    if not isinstance(subscript_slice, cst.Index):
        return None
    return _expression_name(subscript_slice.value)


def _is_typed_dict_class(node: cst.ClassDef) -> bool:
    return any(_is_typed_dict_value(base.value) for base in node.bases)


def _is_typed_dict_value(expression: cst.BaseExpression) -> bool:
    if isinstance(expression, cst.Name):
        return expression.value == "TypedDict"
    if isinstance(expression, cst.Attribute):
        return expression.attr.value == "TypedDict" and _expression_name(expression.value) in {"typing", "typing_extensions"}
    return False


def _typed_dict_class_keys(node: cst.ClassDef) -> tuple[str, ...]:
    if not isinstance(node.body, cst.IndentedBlock):
        return ()
    keys: list[str] = []
    for statement in node.body.body:
        if not isinstance(statement, cst.SimpleStatementLine):
            continue
        for small_statement in statement.body:
            if isinstance(small_statement, cst.AnnAssign) and isinstance(small_statement.target, cst.Name):
                keys.append(small_statement.target.value)
    return tuple(keys)


def _expression_name(expression: cst.BaseExpression) -> str | None:
    if isinstance(expression, cst.Name):
        return expression.value
    return None


def _comparison_name(name: str) -> str:
    return name.lstrip("*")


def _display_name(parameter: cst.Param, parameters: cst.Parameters) -> str:
    name = parameter.name.value
    if isinstance(parameters.star_arg, cst.Param) and parameter is parameters.star_arg:
        return f"*{name}"
    if isinstance(parameters.star_kwarg, cst.Param) and parameter is parameters.star_kwarg:
        return f"**{name}"
    return name


def _parameter_line_numbers(parameter: cst.Param, *, context: RuleContext, fallback_line: int) -> tuple[int, ...]:
    position = context.positions.get(parameter.name)
    return (fallback_line,) if position is None else (position.start.line,)
