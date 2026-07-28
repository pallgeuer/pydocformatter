"""PDF410 exception-entry-normalization rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_conventions, section_edits, unicode_safety
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF410ExceptionEntryNormalization(RuleBase):
    """Rule implementation for PDF410.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF410"),
        name="exception-entry-normalization",
        message="Docstring exception entry should use canonical spelling",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for non-canonical exception and warning entry spelling.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for exception and warning entry normalization."""
    data = PDF_definition.PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=rule)
        for entry in docstring.structure.entries:
            if not PDF_definition.is_exception_name_entry_kind(entry.kind):
                continue
            line = docstring.structure.lines[entry.start_line]
            canonical = _canonical_exception_or_warning_entry_line(docstring.structure.convention, line.text, entry)
            if canonical is None or canonical == line.text:
                continue
            message = "Docstring warning entry should use canonical spelling" if entry.kind is PDF_definition.DocstringEntryKind.WARNING else rule.message
            accumulator.add(line, 0, len(line.text), canonical, instance_message=message)
        results.extend(accumulator.results())
    return tuple(results)


def _canonical_exception_or_warning_entry_line(convention: DocstringConvention, text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical exception or warning entry line for a docstring convention."""
    if not entry.names or unicode_safety.has_nonstandard_whitespace_or_control(text):
        return None
    if convention is DocstringConvention.GOOGLE:
        return _canonical_google_exception_or_warning_entry_line(text, entry)
    if convention is DocstringConvention.NUMPY:
        return _canonical_numpy_exception_or_warning_entry_line(text, entry)
    if convention is DocstringConvention.REST:
        return _canonical_rest_exception_entry_line(text, entry)
    return None


def _canonical_google_exception_or_warning_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical Google exception or warning entry spelling."""
    if PDF_definition._match_google_entry(text) is not None:
        return None
    match = PDF_definition._match_generic_entry(text)
    if match is None or unicode_safety.has_nonstandard_whitespace_or_control(match.name):
        return None
    description = match.description.strip(ascii_whitespace.SPACE_AND_TAB)
    if description == ":" and text.rstrip(ascii_whitespace.SPACE_AND_TAB).endswith("::"):
        return None
    return f"{match.indent}{', '.join(entry.names)}:{f' {description}' if description else ''}"


def _canonical_numpy_exception_or_warning_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical NumPy exception or warning entry spelling."""
    entry_match = PDF_definition._NUMPY_EXCEPTION_ENTRY_RE.match(text)
    if entry_match is not None:
        if unicode_safety.has_nonstandard_whitespace_or_control(entry_match.group("name")):
            return None
        description = entry_match.group("description").strip(ascii_whitespace.SPACE_AND_TAB)
        return f"{entry_match.group('indent')}{', '.join(entry.names)}:{f' {description}' if description else ''}"
    if unicode_safety.has_nonstandard_whitespace_or_control(text.strip(ascii_whitespace.SPACE_AND_TAB)):
        return None
    indent = text[: len(text) - len(text.lstrip(ascii_whitespace.SPACE_AND_TAB))]
    return f"{indent}{', '.join(entry.names)}"


def _canonical_rest_exception_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical reStructuredText exception field spelling."""
    match = PDF_definition._REST_FIELD_RE.match(text)
    if match is None or entry.field_name is None or unicode_safety.has_nonstandard_whitespace_or_control(match.group("argument")):
        return None
    description = match.group("description").strip(ascii_whitespace.SPACE_AND_TAB)
    return f"{match.group('indent')}:{match.group('field')} {', '.join(entry.names)}:{f' {description}' if description else ''}"
