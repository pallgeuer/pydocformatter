from __future__ import annotations

import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF506MissingExceptionDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF506"),
        name="missing-exception-documentation",
        message="Raised exception is missing docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for directly raised exceptions missing from docs."""
        findings: list[RuleFinding] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            documented_names = tuple(
                entry.name for entry in value_documentation.documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False) if entry.name is not None
            )
            if not missing_documentation.should_check_missing_documentation(
                definition, docstring, context=context, has_relevant_documentation=value_documentation.has_exception_documentation(docstring)
            ):
                continue
            seen: list[str] = []
            for raised in facts.raised_exceptions:
                if any(value_documentation.exception_names_match(raised.name, seen_name) for seen_name in seen):
                    continue
                seen.append(raised.name)
                if not any(value_documentation.exception_names_match(raised.name, documented_name) for documented_name in documented_names):
                    findings.append(RuleFinding(rule=cls.meta, line_numbers=raised.line_numbers, instance_message=f"Raised exception '{raised.name}' is missing docstring documentation"))
        return tuple(findings)
