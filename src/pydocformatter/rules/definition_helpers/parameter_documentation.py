"""Signature and documented parameter comparison helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.definition_helpers.decorators as decorator_helpers
from pydocformatter.rules.definition_helpers import docstring_sections, missing_documentation


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@dataclasses.dataclass(frozen=True)
class SignatureParameter:
    """One signature parameter relevant to parameter documentation rules.

    Attributes:
        name (str): Raw parameter name from the function signature.
        display_name (str): Name shown in user-facing diagnostics.
        comparison_name (str): Normalized name used to compare signature and docstring entries.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the parameter.
        implicit_receiver (bool): Whether this is an implicit `self` or `cls` receiver skipped by docs checks.
        unpacked (bool): Whether the parameter uses `Unpack[...]` documentation semantics.
        unpack_target_name (str | None): TypedDict or unpack target name used in diagnostics, if known.
    """

    name: str
    display_name: str
    comparison_name: str
    line_numbers: tuple[int, ...]
    implicit_receiver: bool
    unpacked: bool
    unpack_target_name: str | None


@dataclasses.dataclass(frozen=True)
class UnpackAnnotation:
    """Parsed information about a parameter annotation's Unpack usage.

    Attributes:
        unpacked (bool): Whether the annotation denotes an unpacked parameter.
        target_name (str | None): Extracted unpack target name, when the annotation exposes one.
    """

    unpacked: bool
    target_name: str | None


@dataclasses.dataclass(frozen=True)
class DocumentedParameter:
    """One parameter name parsed from a docstring entry.

    Attributes:
        name (str): Parameter name as written in the docstring.
        comparison_name (str): Normalized name used to match a signature parameter.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the docstring entry.
    """

    name: str
    comparison_name: str
    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class ParameterOrderIssue:
    """One documented parameter that appears after a later signature parameter.

    Attributes:
        documented_parameter (DocumentedParameter): Late documentation occurrence that should move earlier.
        signature_parameter (SignatureParameter): Signature parameter matched by the late documentation occurrence.
        preceding_signature_parameter (SignatureParameter): Highest-ranked signature parameter documented earlier.
    """

    documented_parameter: DocumentedParameter
    signature_parameter: SignatureParameter
    preceding_signature_parameter: SignatureParameter


def signature_parameters(definition: PDF_definition.DefinitionInfo, *, context: RuleContext) -> tuple[SignatureParameter, ...]:
    """Return comparable signature parameters for a function definition.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition whose LibCST parameters should be normalized.
        context (RuleContext): Current file context with position metadata for parameter line targets.

    Returns:
        tuple[SignatureParameter, ...]: Signature parameters in declaration order, including variadic and keyword-only
            parameters.
    """
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
    """Return same-module class-based TypedDict keys by TypedDict class name.

    Args:
        module (cst.Module): Parsed module to scan for class-based TypedDict declarations.

    Returns:
        dict[str, frozenset[str]]: TypedDict class names mapped to field names declared in the class body.
    """
    keys_by_name: dict[str, frozenset[str]] = {}
    for statement in module.body:
        if not isinstance(statement, cst.ClassDef) or not _is_typed_dict_class(statement):
            continue
        keys_by_name[statement.name.value] = frozenset(_typed_dict_class_keys(statement))
    return keys_by_name


def unpacked_keyword_parameters(parameters: tuple[SignatureParameter, ...]) -> tuple[SignatureParameter, ...]:
    """Return unpacked keyword-pack parameters from prepared signature parameters.

    Args:
        parameters (tuple[SignatureParameter, ...]): Normalized signature parameters to filter.

    Returns:
        tuple[SignatureParameter, ...]: Parameters displayed as `**...` and annotated with an unpack target.
    """
    return tuple(parameter for parameter in parameters if parameter.unpacked and parameter.display_name.startswith("**"))


def _signature_parameter(parameter: cst.Param, *, parameters: cst.Parameters, context: RuleContext, implicit_receiver_name: str | None, fallback_line: int) -> SignatureParameter:
    """Return normalized documentation metadata for one CST signature parameter."""
    unpack_annotation = _unpack_annotation(parameter.annotation)
    return SignatureParameter(
        name=parameter.name.value,
        display_name=_display_name(parameter, parameters),
        comparison_name=parameter_comparison_name(parameter.name.value),
        line_numbers=_parameter_line_numbers(parameter, context=context, fallback_line=fallback_line),
        implicit_receiver=parameter.name.value == implicit_receiver_name,
        unpacked=unpack_annotation.unpacked,
        unpack_target_name=unpack_annotation.target_name,
    )


def documented_parameters(docstring: PDF_definition.DocstringInfo) -> tuple[DocumentedParameter, ...]:
    """Return comparable parameter names parsed from a docstring.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to inspect for parameter entries.

    Returns:
        tuple[DocumentedParameter, ...]: Documented parameter names with comparison keys and diagnostic line targets.
    """
    parameters: list[DocumentedParameter] = []
    for entry in docstring.structure.entries:
        if entry.kind is not PDF_definition.DocstringEntryKind.PARAMETER:
            continue
        line = docstring.structure.lines[entry.start_line]
        line_numbers = PDF_definition.docstring_line_numbers(docstring, line)
        parameters.extend(DocumentedParameter(name=name, comparison_name=parameter_comparison_name(name), line_numbers=line_numbers) for name in entry.names if name)
    return tuple(parameters)


def parameter_order_issues(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> tuple[ParameterOrderIssue, ...]:
    """Return documented parameters that do not follow signature declaration order.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition whose signature provides the canonical order.
        docstring (PDF_definition.DocstringInfo): Parsed function docstring whose parameter entries should be checked.
        context (RuleContext): Current file context used to normalize signature parameters.

    Returns:
        tuple[ParameterOrderIssue, ...]: Late first occurrences paired with their matched and highest-ranked preceding
            signature parameters.
    """
    parameters_by_name = {parameter.comparison_name: (rank, parameter) for rank, parameter in enumerate(signature_parameters(definition, context=context))}
    seen_names: set[str] = set()
    greatest_rank_and_parameter: tuple[int, SignatureParameter] | None = None
    issues: list[ParameterOrderIssue] = []
    for documented_parameter in documented_parameters(docstring):
        ranked_parameter = parameters_by_name.get(documented_parameter.comparison_name)
        if ranked_parameter is None or documented_parameter.comparison_name in seen_names:
            continue
        seen_names.add(documented_parameter.comparison_name)
        rank, signature_parameter = ranked_parameter
        if greatest_rank_and_parameter is not None and rank < greatest_rank_and_parameter[0]:
            issues.append(ParameterOrderIssue(documented_parameter=documented_parameter, signature_parameter=signature_parameter, preceding_signature_parameter=greatest_rank_and_parameter[1]))
            continue
        greatest_rank_and_parameter = (rank, signature_parameter)
    return tuple(issues)


def parameter_comparison_name(name: str) -> str:
    """Return a docstring-comparison name without vararg marker stars.

    Args:
        name (str): Parameter name parsed from a signature or docstring entry.

    Returns:
        str: Name used to compare regular and variadic parameter spellings.
    """
    return name.lstrip("*")


def should_check_missing_parameters(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> bool:
    """Return whether missing parameter documentation should be checked for a docstring.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition that owns the docstring.
        docstring (PDF_definition.DocstringInfo): Parsed docstring to inspect for parameter documentation.
        context (RuleContext): Current file context with resolved missing-documentation settings.

    Returns:
        bool: Whether PDF500 should report missing parameters for this function.
    """
    return missing_documentation.should_check_missing_documentation(definition, docstring, context=context, has_relevant_documentation=has_parameter_documentation(docstring))


def has_parameter_documentation(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a docstring contains parameter documentation structures.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to inspect for parameter sections or entries.

    Returns:
        bool: Whether the docstring contains recognized parameter documentation.
    """
    return any(entry.kind is PDF_definition.DocstringEntryKind.PARAMETER for entry in docstring.structure.entries) or any(
        section.name.lower() in docstring_sections.PARAMETER_SECTION_NAMES for section in docstring.structure.sections
    )


def _implicit_receiver_name(definition: PDF_definition.DefinitionInfo) -> str | None:
    """Return an implicit `self` or `cls` receiver name for instance or class methods."""
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
    """Return whether decorators include a staticmethod marker."""
    return any((name := decorator_helpers.decorator_qualified_name(decorator.decorator)) is not None and name.rpartition(".")[2] == "staticmethod" for decorator in decorators)


def _unpack_annotation(annotation: cst.Annotation | None) -> UnpackAnnotation:
    """Return unpack metadata parsed from a real or stringized annotation."""
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
    """Return unpack metadata for a parsed annotation expression."""
    if not isinstance(expression, cst.Subscript):
        return UnpackAnnotation(unpacked=False, target_name=None)
    value = expression.value
    if not _is_unpack_value(value):
        return UnpackAnnotation(unpacked=False, target_name=None)
    return UnpackAnnotation(unpacked=True, target_name=_unpack_target_name(expression))


def _is_unpack_value(expression: cst.BaseExpression) -> bool:
    """Return whether an expression names `Unpack` from typing or typing_extensions."""
    if isinstance(expression, cst.Name):
        return expression.value == "Unpack"
    if isinstance(expression, cst.Attribute):
        return expression.attr.value == "Unpack" and _expression_name(expression.value) in {"typing", "typing_extensions"}
    return False


def _unpack_target_name(expression: cst.Subscript) -> str | None:
    """Return the single subscript target name inside an `Unpack[...]` annotation."""
    if len(expression.slice) != 1:
        return None
    subscript_slice = expression.slice[0].slice
    if not isinstance(subscript_slice, cst.Index):
        return None
    return _expression_name(subscript_slice.value)


def _is_typed_dict_class(node: cst.ClassDef) -> bool:
    """Return whether a class directly bases itself on `TypedDict`."""
    return any(_is_typed_dict_value(base.value) for base in node.bases)


def _is_typed_dict_value(expression: cst.BaseExpression) -> bool:
    """Return whether an expression names `TypedDict` from typing or typing_extensions."""
    if isinstance(expression, cst.Name):
        return expression.value == "TypedDict"
    if isinstance(expression, cst.Attribute):
        return expression.attr.value == "TypedDict" and _expression_name(expression.value) in {"typing", "typing_extensions"}
    return False


def _typed_dict_class_keys(node: cst.ClassDef) -> tuple[str, ...]:
    """Return annotated key names declared directly in a class-based TypedDict body."""
    if not isinstance(node.body, cst.IndentedBlock):
        return ()
    keys: list[str] = []
    for statement in node.body.body:
        if not isinstance(statement, cst.SimpleStatementLine):
            continue
        keys.extend(small_statement.target.value for small_statement in statement.body if isinstance(small_statement, cst.AnnAssign) and isinstance(small_statement.target, cst.Name))
    return tuple(keys)


def _expression_name(expression: cst.BaseExpression) -> str | None:
    """Return a bare name expression value."""
    if isinstance(expression, cst.Name):
        return expression.value
    return None


def _display_name(parameter: cst.Param, parameters: cst.Parameters) -> str:
    """Return the parameter spelling used in diagnostics, including vararg markers."""
    name = parameter.name.value
    if isinstance(parameters.star_arg, cst.Param) and parameter is parameters.star_arg:
        return f"*{name}"
    if isinstance(parameters.star_kwarg, cst.Param) and parameter is parameters.star_kwarg:
        return f"**{name}"
    return name


def _parameter_line_numbers(parameter: cst.Param, *, context: RuleContext, fallback_line: int) -> tuple[int, ...]:
    """Return the source line for a parameter name or the definition fallback line."""
    position = context.positions.get(parameter.name)
    return (fallback_line,) if position is None else (position.start.line,)
