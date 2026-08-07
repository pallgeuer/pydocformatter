"""PDF306 parameter-documentation-too-generic rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_sections, docstring_source, documentation_style, parameter_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


_VARIADIC_SEQUENCE_MODIFIERS = ("extra", "additional")


def _variadic_generic_sequences(base_sequences: tuple[tuple[str, ...], ...]) -> frozenset[tuple[str, ...]]:
    """Return generic phrase sequences with supported determiners and modifiers."""
    sequences: set[tuple[str, ...]] = set()
    for sequence in base_sequences:
        sequences.add(sequence)
        sequences.add(("the", *sequence))
        for modifier in _VARIADIC_SEQUENCE_MODIFIERS:
            sequences.add((modifier, *sequence))
            sequences.add(("the", modifier, *sequence))
    return frozenset(sequences)


_POLICY = documentation_style.DocumentedValueStylePolicy(nouns=frozenset(("argument", "parameter", "value")), message_subject="parameter")
_POSITIONAL_VARIADIC_GENERIC_SEQUENCES = _variadic_generic_sequences((
    ("arg",),
    ("args",),
    ("argument",),
    ("arguments",),
    ("positional", "arg"),
    ("positional", "args"),
    ("positional", "argument"),
    ("positional", "arguments"),
))
_KEYWORD_VARIADIC_GENERIC_SEQUENCES = _variadic_generic_sequences((
    ("arg",),
    ("args",),
    ("argument",),
    ("arguments",),
    ("kwarg",),
    ("kwargs",),
    ("keyword", "arg"),
    ("keyword", "args"),
    ("keyword", "argument"),
    ("keyword", "arguments"),
))


@rule_registration.register_rule_to(PDF)
class PDF306ParameterDocumentationTooGeneric(RuleBase):
    """Rule implementation for PDF306.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF306"),
        name="parameter-documentation-too-generic",
        message="Parameter documentation is too generic",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for parameter documentation that only restates the parameter name.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        targets: list[documentation_style.DocumentedValueTarget] = []
        for docstring in data.docstrings:
            definition = docstring.owner
            if not isinstance(definition, PDF_definition.DefinitionInfo) or definition.kind is not PDF_definition.DefinitionKind.FUNCTION:
                continue
            signature_parameters = {parameter.comparison_name: parameter for parameter in parameter_documentation.signature_parameters(definition, context=context) if not parameter.implicit_receiver}
            for entry in docstring.structure.entries:
                if entry.kind is not PDF_definition.DocstringEntryKind.PARAMETER or len(entry.names) != 1 or not entry.description or _is_rest_type_entry(entry):
                    continue
                line = docstring.structure.lines[entry.start_line]
                signature_parameter = signature_parameters.get(parameter_documentation.parameter_comparison_name(entry.names[0], convention=docstring.structure.convention))
                targets.append(
                    documentation_style.DocumentedValueTarget(
                        name=entry.names[0],
                        description=entry.description,
                        line_numbers=docstring_source.docstring_line_numbers(docstring, line),
                        extra_generic_sequences=_extra_generic_sequences(signature_parameter),
                    )
                )
        return documentation_style.too_generic_violations(tuple(targets), rule=cls.meta, policy=_POLICY)


def _is_rest_type_entry(entry: PDF_definition.DocstringEntry) -> bool:
    """Return whether a parsed entry came from a reST parameter type field."""
    return docstring_sections.is_rest_type_field(entry.field_name)


def _extra_generic_sequences(signature_parameter: parameter_documentation.SignatureParameter | None) -> frozenset[tuple[str, ...]]:
    """Return parameter-kind-specific generic phrase sequences."""
    if signature_parameter is None:
        return frozenset()
    if signature_parameter.display_name.startswith("**"):
        return _KEYWORD_VARIADIC_GENERIC_SEQUENCES
    if signature_parameter.display_name.startswith("*"):
        return _POSITIONAL_VARIADIC_GENERIC_SEQUENCES
    return frozenset()
