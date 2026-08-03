"""Terminal punctuation violation helpers.

Attributes:
    TRAILING_PERIOD_POLICY (TerminalPunctuationPolicy): Shared classifications for rules that require a final period.
    TERMINAL_PUNCTUATION_POLICY (TerminalPunctuationPolicy): Shared classifications for rules that accept expressive
        sentence endings.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from collections.abc import Callable
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import ascii_whitespace


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    from pydocformatter.rules.models import RuleMetadata


@dataclasses.dataclass(frozen=True)
class TerminalPunctuationPolicy:
    """Policy for one terminal-punctuation rule.

    Attributes:
        valid_endings (str): Terminal characters accepted by the rule.
        replaceable_endings (str): Invalid terminal characters that can safely be replaced.
        nonfixable_endings (str): Terminal characters that should report but not be rewritten automatically.
        canonical_ending (str): Terminal punctuation inserted or substituted by automatic fixes.
    """

    valid_endings: str
    replaceable_endings: str
    nonfixable_endings: str
    canonical_ending: str

    def __post_init__(self) -> None:
        """Validate terminal-punctuation classifications and canonical output."""
        fields = {"valid_endings": self.valid_endings, "replaceable_endings": self.replaceable_endings, "nonfixable_endings": self.nonfixable_endings, "canonical_ending": self.canonical_ending}
        for name, value in fields.items():
            if not isinstance(value, str):
                raise TypeError(f"Terminal punctuation policy {name} must be a string")
        if len(self.canonical_ending) != 1:
            raise ValueError("Terminal punctuation policy canonical ending must be exactly one character")
        for name in ("valid_endings", "replaceable_endings", "nonfixable_endings"):
            value = fields[name]
            if len(value) != len(set(value)):
                raise ValueError(f"Terminal punctuation policy {name} must not contain duplicate characters")
        classifications = (("valid endings", set(self.valid_endings)), ("replaceable endings", set(self.replaceable_endings)), ("non-fixable endings", set(self.nonfixable_endings)))
        for index, (first_name, first) in enumerate(classifications):
            for second_name, second in classifications[index + 1 :]:
                if first & second:
                    raise ValueError(f"Terminal punctuation policy {first_name} and {second_name} must be disjoint")
        if self.canonical_ending not in self.valid_endings:
            raise ValueError("Terminal punctuation policy canonical ending must be included in valid endings")


TRAILING_PERIOD_POLICY = TerminalPunctuationPolicy(valid_endings=".", replaceable_endings=",;", nonfixable_endings=":?!\u2026", canonical_ending=".")
TERMINAL_PUNCTUATION_POLICY = TerminalPunctuationPolicy(valid_endings=".?!\u2026", replaceable_endings=",;", nonfixable_endings=":", canonical_ending=".")
_COMMA_INTRODUCED_BLOCK_KINDS = frozenset({
    PDF_definition.DocstringBlockKind.COLON_HEADER,
    PDF_definition.DocstringBlockKind.LIST_ITEM,
    PDF_definition.DocstringBlockKind.HEADING,
    PDF_definition.DocstringBlockKind.DOCTEST,
    PDF_definition.DocstringBlockKind.CODE_FENCE,
    PDF_definition.DocstringBlockKind.BLOCK_QUOTE,
    PDF_definition.DocstringBlockKind.TABLE,
    PDF_definition.DocstringBlockKind.DIRECTIVE,
    PDF_definition.DocstringBlockKind.DIRECTIVE_ISSUE,
    PDF_definition.DocstringBlockKind.LITERAL_BLOCK,
    PDF_definition.DocstringBlockKind.VERBATIM,
})


def comma_may_introduce_block(kind: PDF_definition.DocstringBlockKind | None) -> bool:
    """Return whether a block kind can be introduced by a terminal comma.

    Args:
        kind (PDF_definition.DocstringBlockKind | None): Following parsed block kind, if one exists.

    Returns:
        Whether the block should prevent automatic comma replacement.
    """
    return kind in _COMMA_INTRODUCED_BLOCK_KINDS


def violation(
    *, text: str, policy: TerminalPunctuationPolicy, rule: RuleMetadata, line_numbers: tuple[int, ...], planned_change: Callable[[str | None, str], rule_edits.PlannedSourceChange | None]
) -> rule_violations.RuleViolation | None:
    """Return one terminal-punctuation violation.

    Args:
        text (str): Target text whose terminal punctuation should be checked.
        policy (TerminalPunctuationPolicy): Valid, replaceable, and non-fixable terminal punctuation policy.
        rule (RuleMetadata): Rule metadata used for diagnostics and fixes.
        line_numbers (tuple[int, ...]): Source line numbers reported for the target text.
        planned_change (Callable[[str | None, str], rule_edits.PlannedSourceChange | None]): Callback that plans an
            insertion when the expected terminal character is None or a replacement otherwise.

    Returns:
        Terminal-punctuation violation, or None when the target text already complies.
    """
    trimmed = text.rstrip(ascii_whitespace.SPACE_AND_TAB)
    if not trimmed or trimmed.endswith(("\\", *policy.valid_endings)):
        return None
    if trimmed.endswith(tuple(policy.nonfixable_endings)):
        change = None
    elif trimmed.endswith(tuple(policy.replaceable_endings)):
        change = planned_change(trimmed[-1], policy.canonical_ending)
    else:
        change = planned_change(None, policy.canonical_ending)
    return rule_violations.violation_for_optional_planned_source_change(rule, change, line_numbers=line_numbers)
