"""PCF005 comment-ascii-only rule."""

from __future__ import annotations

import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF005CommentAsciiOnly(RuleBase):
    """Rule implementation for PCF005.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF005"),
        name="comment-ascii-only",
        message="Comment should contain only ASCII characters",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for comments containing non-ASCII source characters."""
        data = PCF_definition.PCF.require_data(context)
        return tuple(RuleFinding(rule=cls.meta, line_numbers=(comment.range.start.line,), instance_fixable=None) for comment in data.comments if not comment.text.isascii())
