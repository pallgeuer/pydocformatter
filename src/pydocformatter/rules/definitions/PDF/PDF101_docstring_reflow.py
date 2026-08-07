"""PDF101 docstring-reflow rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_source, inline_markup, string_literals, text_layout
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF101DocstringReflow(RuleBase):
    """Rule implementation for PDF101.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF101"),
        name="docstring-reflow",
        message="Docstring chunk needs reflow",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for docstring reflow changes.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _docstring_violations(context)


@dataclasses.dataclass(frozen=True)
class _RegionReplacement:
    """One evaluated-value replacement with source spelling."""

    start_offset: int
    end_offset: int
    value_text: str
    source_text: str
    line_numbers: tuple[int, ...]


def _docstring_violations(context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return all docstring reflow violations and any available fixes."""
    data = PDF_definition.PDF.require_data(context)
    violations: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        violations.extend(_docstring_violations_for_literal(docstring, context=context))
    return tuple(violations)


def _docstring_violations_for_literal(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return safe aggregate and ambiguous-region violations for one literal."""
    if docstring.kind != PDF_definition.DocstringKind.SIMPLE or not isinstance(docstring.node, cst.SimpleString):
        return ()
    if not docstring.structure.reflow_regions:
        return ()
    source_map = docstring.source_map
    fragments = source_map.fragments if source_map is not None else tuple(string_literals.StringValueFragment(value=char, source=char) for char in docstring.value)
    fallback_prefix = docstring_source.docstring_canonical_margin(docstring, context=context)
    replacements: list[_RegionReplacement] = []
    ambiguous_violations: list[rule_violations.RuleViolation] = []
    unsafe_reflow_needed = False
    for region in docstring.structure.reflow_regions:
        result = _replacement_for_region(docstring, region, context=context, fallback_prefix=fallback_prefix, fragments=fragments, source_map=source_map)
        if result is None:
            continue
        replacement, ambiguous = result
        current = docstring.value[replacement.start_offset : replacement.end_offset]
        if replacement.value_text != current:
            if ambiguous:
                ambiguous_violations.append(rule_violations.diagnostic(PDF101DocstringReflow.meta, replacement.line_numbers))
            elif source_map is None or source_map.has_escaped_newline(region.start_offset, region.end_offset):
                unsafe_reflow_needed = True
            else:
                replacements.append(replacement)
    violations: list[rule_violations.RuleViolation] = []
    if replacements:
        value = docstring.value
        for replacement in reversed(replacements):
            value = f"{value[: replacement.start_offset]}{replacement.value_text}{value[replacement.end_offset :]}"
        line_numbers = tuple(sorted({line_number for replacement in replacements for line_number in replacement.line_numbers}))
        change = _planned_change_from_replacements(docstring, replacements, source_map=source_map, value=value)
        violations.append(rule_violations.violation_for_optional_planned_source_change(PDF101DocstringReflow.meta, change, line_numbers=line_numbers))
    violations.extend(ambiguous_violations)
    if unsafe_reflow_needed:
        violations.append(rule_violations.diagnostic(PDF101DocstringReflow.meta, tuple(line.line_number for line in docstring.physical_lines)))
    return tuple(violations)


def _replacement_for_region(
    docstring: PDF_definition.DocstringInfo,
    region: PDF_definition.ReflowRegion,
    *,
    context: RuleContext,
    fallback_prefix: str,
    fragments: tuple[string_literals.StringValueFragment, ...],
    source_map: string_literals.SimpleStringSourceMap | None,
) -> tuple[_RegionReplacement, bool] | None:
    """Return generated region text and whether its markup is ambiguous."""
    source_line_numbers = (
        tuple(line.line_number for line in docstring.physical_lines)
        if source_map is None
        else source_map.physical_line_numbers(region.start_offset, region.end_offset, first_line_number=docstring.range.start.line)
    )
    initial_base = _line_base_prefix(docstring, region.start_line, first_generated_line=True, fallback_prefix=fallback_prefix)
    subsequent_base = _line_base_prefix(docstring, region.start_line, first_generated_line=False, fallback_prefix=fallback_prefix)
    initial_width = context.settings.line_length - text_layout.display_width(initial_base, tab_width=context.settings.indent_width) - _opening_delimiter_width(docstring, region, context=context)
    subsequent_width = context.settings.line_length - text_layout.display_width(subsequent_base, tab_width=context.settings.indent_width)
    final_suffix_width = _closing_delimiter_width(docstring, region)
    width = min(initial_width, subsequent_width)
    if _should_split_entry_prefix(region, width=width, tab_width=context.settings.indent_width):
        wrapped, ambiguous = _wrapped_region_lines(
            docstring,
            region,
            initial_width=subsequent_width,
            subsequent_width=subsequent_width,
            final_suffix_width=final_suffix_width,
            initial_indent=region.subsequent_indent,
            subsequent_indent=region.subsequent_indent,
            tab_width=context.settings.indent_width,
            fragments=fragments,
            url_aware=context.settings.url_aware_wrapping,
        )
        if not wrapped:
            return None
        replacement = _render_region_replacement(
            docstring,
            region,
            wrapped=(string_literals.WrappedSourceLine(value=region.initial_indent.rstrip(), source=region.initial_indent.rstrip()), *wrapped),
            source_line_numbers=source_line_numbers,
            fallback_prefix=fallback_prefix,
            line_ending=context.line_ending,
        )
        return replacement, ambiguous
    wrapped, ambiguous = _wrapped_region_lines(
        docstring,
        region,
        initial_width=initial_width,
        subsequent_width=subsequent_width,
        final_suffix_width=final_suffix_width,
        initial_indent=region.initial_indent,
        subsequent_indent=region.subsequent_indent,
        tab_width=context.settings.indent_width,
        fragments=fragments,
        url_aware=context.settings.url_aware_wrapping,
    )
    if not wrapped:
        return None
    replacement = _render_region_replacement(docstring, region, wrapped=wrapped, source_line_numbers=source_line_numbers, fallback_prefix=fallback_prefix, line_ending=context.line_ending)
    return replacement, ambiguous


def _opening_delimiter_width(docstring: PDF_definition.DocstringInfo, region: PDF_definition.ReflowRegion, *, context: RuleContext) -> int:
    """Return physical source width before first generated value text."""
    if region.start_line != 0 or not isinstance(docstring.node, cst.SimpleString):
        return 0
    source_line = context.source_lines[docstring.range.start.line - 1]
    return text_layout.display_width(f"{source_line[: docstring.range.start.column]}{docstring.node.prefix}{docstring.node.quote}", tab_width=context.settings.indent_width)


def _closing_delimiter_width(docstring: PDF_definition.DocstringInfo, region: PDF_definition.ReflowRegion) -> int:
    """Return closing delimiter width when PDF101 keeps it on the final generated line."""
    if region.end_offset != len(docstring.value) or docstring_source.docstring_value_ends_with_newline(docstring) or not isinstance(docstring.node, cst.SimpleString):
        return 0
    return len(docstring.node.quote)


def _should_split_entry_prefix(region: PDF_definition.ReflowRegion, *, width: int, tab_width: int) -> bool:
    """Return whether an entry prefix should stand alone before wrapped description text."""
    if region.kind is not PDF_definition.DocstringBlockKind.SECTION_ENTRY:
        return False
    if text_layout.display_width(region.initial_indent, tab_width=tab_width) <= text_layout.display_width(region.subsequent_indent, tab_width=tab_width):
        return False
    # Move very long entry prefixes onto their own line when the first description line would have too little useful
    # room.
    return width - text_layout.display_width(region.initial_indent, tab_width=tab_width) < max(8, tab_width * 2)


def _wrapped_region_lines(
    docstring: PDF_definition.DocstringInfo,
    region: PDF_definition.ReflowRegion,
    *,
    initial_width: int,
    subsequent_width: int,
    final_suffix_width: int,
    initial_indent: str,
    subsequent_indent: str,
    tab_width: int,
    fragments: tuple[string_literals.StringValueFragment, ...],
    url_aware: bool,
) -> tuple[tuple[string_literals.WrappedSourceLine, ...], bool]:
    """Return normalized wrapped region lines and ambiguity state."""
    layout = _source_layout_segments(docstring, region, fragments=fragments)
    wrapped_lines: list[string_literals.WrappedSourceLine] = []
    for index, segment in enumerate(layout.segments):
        first_segment = index == 0
        last_segment = index == len(layout.segments) - 1
        segment_initial_indent = initial_indent if first_segment else subsequent_indent
        segment_initial_width = initial_width if first_segment else subsequent_width
        suffix_width = text_layout.display_width(segment.hard_break.source, tab_width=tab_width) if segment.hard_break is not None else final_suffix_width if last_segment else 0
        wrapped = string_literals.wrap_source_tokens(
            segment.scan.tokens,
            width=max(1, min(segment_initial_width, subsequent_width)),
            initial_indent=segment_initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
            initial_width=segment_initial_width,
            subsequent_width=subsequent_width,
            final_suffix_width=suffix_width,
            url_aware=url_aware,
        )
        if segment.hard_break is not None:
            final_line = wrapped[-1]
            wrapped = (*wrapped[:-1], string_literals.WrappedSourceLine(value=f"{final_line.value}{segment.hard_break.value}", source=f"{final_line.source}{segment.hard_break.source}"))
        wrapped_lines.extend(wrapped)
    return tuple(wrapped_lines), layout.rewrite_blocked


def _source_layout_segments(
    docstring: PDF_definition.DocstringInfo, region: PDF_definition.ReflowRegion, *, fragments: tuple[string_literals.StringValueFragment, ...]
) -> inline_markup.InlineLayoutScanResult:
    """Return line-scanned token segments split at semantic hard breaks."""
    lines: list[inline_markup.InlineLayoutLine] = []
    for region_line in region.lines:
        logical_line = docstring.structure.lines[region_line.line_index]
        line_fragments = fragments[region_line.start_offset : logical_line.end_offset]
        lines.append(
            inline_markup.InlineLayoutLine(
                fragments=line_fragments, content_end=region_line.end_offset - region_line.start_offset, has_following_newline=logical_line.end_offset < len(docstring.value)
            )
        )
    return inline_markup.scan_layout_lines(lines)


def _render_region_replacement(
    docstring: PDF_definition.DocstringInfo,
    region: PDF_definition.ReflowRegion,
    *,
    wrapped: tuple[string_literals.WrappedSourceLine, ...],
    source_line_numbers: tuple[int, ...],
    fallback_prefix: str,
    line_ending: str,
) -> _RegionReplacement:
    """Return replacement text for normalized wrapped region lines."""
    value_lines = [_raw_generated_line(docstring, region.start_line, line.value, first_generated_line=index == 0, fallback_prefix=fallback_prefix) for index, line in enumerate(wrapped)]
    source_lines = [_raw_generated_line(docstring, region.start_line, line.source, first_generated_line=index == 0, fallback_prefix=fallback_prefix) for index, line in enumerate(wrapped)]
    return _RegionReplacement(
        start_offset=region.start_offset, end_offset=region.end_offset, value_text="\n".join(value_lines), source_text=line_ending.join(source_lines), line_numbers=source_line_numbers
    )


def _planned_change_from_replacements(
    docstring: PDF_definition.DocstringInfo, replacements: list[_RegionReplacement], *, source_map: string_literals.SimpleStringSourceMap | None, value: str
) -> rule_edits.PlannedSourceChange | None:
    """Return a source edit after applying source-preserving replacements."""
    if not isinstance(docstring.node, cst.SimpleString) or source_map is None:
        return None
    body_source = source_map.body_source_with_replacements(
        tuple((replacement.start_offset, replacement.end_offset, replacement.source_text) for replacement in replacements), preserve_zero_value_source=False
    )
    rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, body_source, expected_value=value)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(sorted({line_number for replacement in replacements for line_number in replacement.line_numbers})),
        suppression_line_numbers=(),
    )


def _line_base_prefix(docstring: PDF_definition.DocstringInfo, line_index: int, *, first_generated_line: bool, fallback_prefix: str) -> str:
    """Return the raw evaluated-value prefix before generated semantic text."""
    if line_index == 0 and first_generated_line:
        return docstring.structure.lines[0].raw_indent
    # Continuation output uses the existing body margin when available, while the first generated line above uses the
    # literal line itself.
    margin_line = docstring.structure.lines[line_index if line_index > 0 else min(1, len(docstring.structure.lines) - 1)]
    if margin_line.text_indent and margin_line.raw_indent.endswith(margin_line.text_indent):
        return margin_line.raw_indent[: -len(margin_line.text_indent)]
    if not margin_line.text_indent and margin_line.raw_indent:
        return margin_line.raw_indent
    return fallback_prefix


def _raw_generated_line(docstring: PDF_definition.DocstringInfo, line_index: int, generated_text: str, *, first_generated_line: bool, fallback_prefix: str) -> str:
    """Return generated evaluated-value text using the original raw leading whitespace when it can be mapped."""
    if line_index == 0 and first_generated_line:
        margin_line = docstring.structure.lines[0]
    else:
        margin_line = docstring.structure.lines[line_index if line_index > 0 else min(1, len(docstring.structure.lines) - 1)]
        if not margin_line.raw_indent and not margin_line.text_indent and fallback_prefix:
            return f"{fallback_prefix}{generated_text}"
    if not generated_text.startswith(margin_line.text_indent):
        return f"{fallback_prefix}{generated_text}"
    return f"{margin_line.raw_indent}{generated_text[len(margin_line.text_indent) :]}"
