from __future__ import annotations

import dataclasses

import libcst as cst

import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition import RuleContext
from pydocformatter.rules.models import RuleFinding, RuleMetadata


@dataclasses.dataclass(frozen=True)
class SignatureParameter:
    """One signature parameter relevant to parameter documentation rules."""

    name: str
    display_name: str
    comparison_name: str
    line_numbers: tuple[int, ...]
    implicit_receiver: bool
    unpacked: bool


@dataclasses.dataclass(frozen=True)
class DocumentedParameter:
    """One parameter name parsed from a docstring entry."""

    name: str
    comparison_name: str
    line_numbers: tuple[int, ...]


def missing_parameter_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF500 findings for undocumented signature parameters."""
    data = PDF_definition.PDF.require_data(context)
    findings: list[RuleFinding] = []
    for definition in data.definitions:
        if definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None or not _should_check_missing_parameters(definition, docstring, context=context):
            continue
        documented_names = {parameter.comparison_name for parameter in documented_parameters(docstring)}
        for parameter in signature_parameters(definition, context=context):
            if parameter.implicit_receiver or parameter.unpacked or parameter.comparison_name in documented_names:
                continue
            findings.append(
                RuleFinding(
                    rule=rule,
                    line_numbers=parameter.line_numbers,
                    instance_message=f"Function parameter '{parameter.display_name}' is missing docstring documentation",
                )
            )
    return tuple(findings)


def extraneous_parameter_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF501 findings for documented names absent from the signature."""
    data = PDF_definition.PDF.require_data(context)
    findings: list[RuleFinding] = []
    for docstring in data.docstrings:
        definition = docstring.owner
        if definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
            continue
        signature_names = {parameter.comparison_name for parameter in signature_parameters(definition, context=context)}
        for parameter in documented_parameters(docstring):
            if parameter.comparison_name not in signature_names:
                findings.append(
                    RuleFinding(
                        rule=rule,
                        line_numbers=parameter.line_numbers,
                        instance_message=f"Docstring documents parameter '{parameter.name}' that is not in the function signature",
                    )
                )
    return tuple(findings)


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
        SignatureParameter(
            name=parameter.name.value,
            display_name=_display_name(parameter, definition.parameters),
            comparison_name=_comparison_name(parameter.name.value),
            line_numbers=_parameter_line_numbers(parameter, context=context, fallback_line=fallback_line),
            implicit_receiver=parameter.name.value == implicit_receiver_name,
            unpacked=_is_unpack_annotation(parameter.annotation),
        )
        for parameter in raw_parameters
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


def _should_check_missing_parameters(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> bool:
    return missing_documentation.should_check_missing_documentation(definition, docstring, context=context, has_relevant_documentation=_has_parameter_documentation(docstring))


def _has_parameter_documentation(docstring: PDF_definition.DocstringInfo) -> bool:
    return any(entry.kind is PDF_definition.DocstringEntryKind.PARAMETER for entry in docstring.structure.entries) or any(
        section.name.lower() in PDF_definition.PARAMETER_SECTION_NAMES for section in docstring.structure.sections
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
    return any((name := summary_style.decorator_qualified_name(decorator.decorator)) is not None and name.rpartition(".")[2] == "staticmethod" for decorator in decorators)


def _is_unpack_annotation(annotation: cst.Annotation | None) -> bool:
    if annotation is None:
        return False
    expression = annotation.annotation
    if isinstance(expression, cst.SimpleString):
        evaluated_value = expression.evaluated_value
        if not isinstance(evaluated_value, str):
            return False
        try:
            expression = cst.parse_expression(evaluated_value)
        except cst.ParserSyntaxError:
            return False
    return _is_unpack_expression(expression)


def _is_unpack_expression(expression: cst.BaseExpression) -> bool:
    if not isinstance(expression, cst.Subscript):
        return False
    value = expression.value
    if isinstance(value, cst.Name):
        return value.value == "Unpack"
    if isinstance(value, cst.Attribute):
        return value.attr.value == "Unpack" and _expression_name(value.value) in {"typing", "typing_extensions"}
    return False


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
