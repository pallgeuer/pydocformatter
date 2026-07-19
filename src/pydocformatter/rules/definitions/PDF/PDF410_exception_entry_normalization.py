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
from pydocformatter.rules.definition_helpers import docstring_conventions, section_edits
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
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
        """Return violations for non-canonical exception entry spelling.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for exception entry normalization."""
    data = PDF_definition.PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        replacement_messages: list[str] = []
        unfixable_messages: list[str] = []
        for entry in docstring.structure.entries:
            if entry.kind is not PDF_definition.DocstringEntryKind.EXCEPTION:
                continue
            line = docstring.structure.lines[entry.start_line]
            canonical = _canonical_exception_entry_line(docstring.structure.convention, line.text, entry)
            if canonical is None or canonical == line.text:
                continue
            replacement = section_edits.text_replacement(line, 0, len(line.text), canonical)
            if replacement is None:
                unfixable_line_numbers.extend(section_edits.line_numbers(docstring, line))
                unfixable_messages.append(rule.message)
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(section_edits.line_numbers(docstring, line))
            replacement_messages.append(rule.message)
            section_edits.replace_value_line_span(value_lines, line, replacement, canonical)
        if not replacements and not unfixable_line_numbers:
            continue
        change = section_edits.planned_replacement_change(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)
        results.extend(
            section_edits.replacement_results(
                rule,
                replacement_line_numbers=replacement_line_numbers,
                unfixable_line_numbers=unfixable_line_numbers,
                change=change,
                replacement_messages=replacement_messages,
                unfixable_messages=unfixable_messages,
            )
        )
    return tuple(results)


def _canonical_exception_entry_line(convention: DocstringConvention, text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical exception entry line for a docstring convention."""
    if not entry.names:
        return None
    if convention is DocstringConvention.GOOGLE:
        return _canonical_google_exception_entry_line(text, entry)
    if convention is DocstringConvention.NUMPY:
        return _canonical_numpy_exception_entry_line(text, entry)
    if convention is DocstringConvention.REST:
        return _canonical_rest_exception_entry_line(text, entry)
    return None


def _canonical_google_exception_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical Google exception entry spelling."""
    if PDF_definition._GOOGLE_ENTRY_RE.match(text) is not None:
        return None
    match = PDF_definition._GENERIC_ENTRY_RE.match(text)
    if match is None:
        return None
    description = match.group("description").strip()
    if description == ":" and text.rstrip().endswith("::"):
        return None
    return f"{match.group('indent')}{', '.join(entry.names)}:{f' {description}' if description else ''}"


def _canonical_numpy_exception_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical NumPy exception entry spelling."""
    exception_match = PDF_definition._NUMPY_EXCEPTION_ENTRY_RE.match(text)
    if exception_match is not None:
        description = exception_match.group("description").strip()
        return f"{exception_match.group('indent')}{', '.join(entry.names)}:{f' {description}' if description else ''}"
    indent = text[: len(text) - len(text.lstrip(" \t"))]
    return f"{indent}{', '.join(entry.names)}"


def _canonical_rest_exception_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical reStructuredText exception field spelling."""
    match = PDF_definition._REST_FIELD_RE.match(text)
    if match is None or entry.field_name is None:
        return None
    description = match.group("description").strip()
    return f"{match.group('indent')}:{match.group('field')} {', '.join(entry.names)}:{f' {description}' if description else ''}"
