from __future__ import annotations

import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF503ExtraneousReturnDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF503"),
        name="extraneous-return-documentation",
        message="Docstring has a return section for a function that does not return",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for return docs on functions without meaningful returns."""
        findings: list[RuleFinding] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            del definition
            if facts.meaningful_returns and not facts.any_yields:
                continue
            for entry in value_documentation.value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.RETURN):
                if facts.explicit_none_returns and not facts.any_yields and entry.has_content:
                    continue
                message = "Docstring has a return section for a generator; generator return values are stop values, not ordinary returns" if facts.any_yields else None
                findings.append(RuleFinding(rule=cls.meta, line_numbers=entry.line_numbers, instance_message=message))
        return tuple(findings)
