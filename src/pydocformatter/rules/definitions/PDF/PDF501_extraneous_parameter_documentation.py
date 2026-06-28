"""PDF501 extraneous-parameter-documentation rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.parameter_documentation as parameter_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF501ExtraneousParameterDocumentation(RuleBase):
    """Rule implementation for PDF501.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF501"),
        name="extraneous-parameter-documentation",
        message="Docstring documents a parameter that is not in the function signature",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST)
                    ),
                ),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for documented parameters absent from the signature."""
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        typed_dict_keys_by_name: dict[str, frozenset[str]] | None = None
        for docstring in data.docstrings:
            definition = docstring.owner
            if not isinstance(definition, PDF_definition.DefinitionInfo) or definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
                continue
            signature_parameters = parameter_documentation.signature_parameters(definition, context=context)
            allowed_names = {parameter.comparison_name for parameter in signature_parameters}
            suppress_unknown_names = False
            for keyword_parameter in parameter_documentation.unpacked_keyword_parameters(signature_parameters):
                if keyword_parameter.unpack_target_name is None:
                    suppress_unknown_names = True
                    break
                if typed_dict_keys_by_name is None:
                    typed_dict_keys_by_name = parameter_documentation.typed_dict_keys_by_name(context.module)
                if keyword_parameter.unpack_target_name not in typed_dict_keys_by_name:
                    suppress_unknown_names = True
                    break
                allowed_names.update(typed_dict_keys_by_name[keyword_parameter.unpack_target_name])
            if suppress_unknown_names:
                continue
            for parameter in parameter_documentation.documented_parameters(docstring):
                if parameter.comparison_name not in allowed_names:
                    violations.append(
                        rule_violations.diagnostic(cls.meta, parameter.line_numbers, instance_message=f"Docstring documents parameter '{parameter.name}' that is not in the function signature")
                    )
        return tuple(violations)
