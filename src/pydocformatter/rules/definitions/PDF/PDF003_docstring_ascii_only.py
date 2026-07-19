"""PDF003 docstring-ascii-only rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.definitions.PDF.PDF002_docstring_backslash_raw_prefix as PDF002
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import source_text, string_literals
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF003DocstringAsciiOnly(RuleBase):
    """Rule implementation for PDF003.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF003"),
        name="docstring-ascii-only",
        message="Docstring source contains non-ASCII characters",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for docstring source containing non-ASCII characters.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return tuple(violation for docstring in _candidate_docstrings(context) if (violation := _violation_for_docstring(docstring, context=context)) is not None)


def _candidate_docstrings(context: RuleContext) -> tuple[PDF_definition.DocstringInfo, ...]:
    """Return docstrings whose source contains literal non-ASCII characters."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(docstring for docstring in data.docstrings if not docstring.source.isascii())


def _violation_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_violations.RuleViolation | None:
    """Return a fixable or non-fixable violation for one non-ASCII docstring."""
    planned_change = _planned_change_for_docstring(docstring, context=context)
    return rule_violations.violation_for_optional_planned_source_change(
        PDF003DocstringAsciiOnly.meta,
        planned_change,
        line_numbers=_line_numbers(docstring),
        instance_message=f"Docstring source contains non-ASCII character {source_text.first_non_ascii_code_point(docstring.source)}",
    )


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return a source change for one safely renderable docstring."""
    rendered = _rendered_docstring(docstring, line_ending=context.line_ending)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered), line_numbers=_line_numbers(docstring), suppression_line_numbers=())


def _rendered_docstring(docstring: PDF_definition.DocstringInfo, *, line_ending: str) -> str | None:
    """Return ASCII-only source for a simple docstring when value-preserving."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    body_source = string_literals.simple_string_body_source(docstring.node)
    if body_source is None or body_source.isascii():
        return None
    if "\\" in body_source and (PDF002.reportable_backslash_line_numbers(docstring) or "r" in docstring.node.prefix.lower()):
        return None
    fragments = string_literals.value_fragments_for_simple_string(docstring.node, line_ending=line_ending)
    if fragments is None:
        return None
    rendered_fragments = tuple(_ascii_fragment(fragment, quote=docstring.node.quote, line_ending=line_ending) for fragment in fragments)
    prefix = _ascii_prefix(docstring.node.prefix)
    if prefix is None:
        return None
    return string_literals.render_simple_string_from_fragments(docstring.node, rendered_fragments, expected_value=docstring.value, prefix=prefix)


def _ascii_fragment(fragment: string_literals.StringValueFragment, *, quote: str, line_ending: str) -> string_literals.StringValueFragment:
    """Return a source fragment with an ASCII-only spelling."""
    if fragment.source.isascii():
        return fragment
    source = string_literals.serialize_string_body(fragment.value, quote=quote, line_ending=line_ending, escape_non_ascii=True)
    return string_literals.StringValueFragment(value=fragment.value, source=source)


def _ascii_prefix(prefix: str) -> str | None:
    """Return a prefix usable for ASCII escaping, or None if unsupported."""
    if "r" not in prefix.lower():
        return prefix
    if any(char.lower() not in {"r", "u"} for char in prefix):
        return None
    return "".join(char for char in prefix if char.lower() != "r")


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return source line numbers covered by a docstring expression."""
    return tuple(line.line_number for line in docstring.physical_lines)
