"""PCF005 comment-ascii-only rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF005CommentAsciiOnly(RuleBase):
    """Rule implementation for PCF005.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF005"),
        name="comment-ascii-only",
        message="Comment contains non-ASCII characters",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for comments containing non-ASCII source characters.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PCF_definition.PCF.require_data(context)
        return tuple(
            rule_violations.diagnostic(
                cls.meta,
                (comment.range.start.line,),
                instance_message=f"Comment contains non-ASCII character {source_text.first_non_ascii_code_point(comment.text)}",
            )
            for comment in data.comments
            if not comment.text.isascii()
        )
