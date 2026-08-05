"""Helpers for exercising PCF comment-formatting rules in tests."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import DEFAULT_COMMENT_TASK_MARKERS, CheckSettings, CommentTaskMarkerMode, LineEnding


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.settings import StringList


def format_pcf(  # ruff: ignore[too-many-arguments]
    source: str,
    *,
    fix: bool = True,
    line_length: int = 88,
    line_ending: LineEnding = LineEnding.AUTO,
    indent_width: int = 4,
    url_aware_wrapping: bool = True,
    comment_join_standalone_lines: bool = False,
    comment_format_list_items: bool = True,
    comment_task_marker_mode: CommentTaskMarkerMode = CommentTaskMarkerMode.NO_WRAP,
    comment_task_markers: StringList = DEFAULT_COMMENT_TASK_MARKERS,
    comment_preserve_headings: bool = True,
    comment_preserve_doctests: bool = True,
    comment_preserve_code_fences: bool = True,
    comment_format_block_quotes: bool = True,
    comment_preserve_tables: bool = True,
    comment_preserve_directives: bool = True,
    comment_trailing_extraction_syntax_aware: bool = True,
    comment_trailing_extraction_content_aware: bool = True,
    comment_detect_code: bool = False,
    comment_detect_statements: bool = True,
    comment_detect_expressions: bool = False,
) -> formatter.FormatterResult:
    """Format source with PCF rules and explicit comment settings.

    Args:
        source (str): Python source text to format.
        fix (bool): Whether selected PCF fixes should be applied before returning remaining findings.
        line_length (int): Target maximum line length used by comment wrapping rules.
        line_ending (LineEnding): Line-ending mode used when fixes rewrite source text.
        indent_width (int): Number of spaces represented by one indentation level for rewritten comments.
        url_aware_wrapping (bool): Whether wrapping should keep URL tokens intact.
        comment_join_standalone_lines (bool): Whether adjacent standalone comment lines may be joined before wrapping.
        comment_format_list_items (bool): Whether standalone comment list items should be recognized and formatted
            structurally.
        comment_task_marker_mode (CommentTaskMarkerMode): How recognized task-marker comments should be treated.
        comment_task_markers (StringList): Exact uppercase task-marker labels recognized before a colon.
        comment_preserve_headings (bool): Whether heading-like standalone comments should remain structurally protected.
        comment_preserve_doctests (bool): Whether doctest prompts inside comments should remain structurally protected.
        comment_preserve_code_fences (bool): Whether fenced code blocks inside comments should remain structurally
            protected.
        comment_format_block_quotes (bool): Whether standalone comment block quotes should be recognized and formatted
            structurally.
        comment_preserve_tables (bool): Whether table-like comment blocks should remain structurally protected.
        comment_preserve_directives (bool): Whether directive-like comment blocks should remain structurally protected.
        comment_trailing_extraction_syntax_aware (bool): Whether trailing-comment extraction should respect
            syntax-sensitive positions.
        comment_trailing_extraction_content_aware (bool): Whether trailing-comment extraction should respect comment
            content heuristics.
        comment_detect_code (bool): Whether standalone comments should be detected as disabled code.
        comment_detect_statements (bool): Whether standalone comments should be parsed as possible Python statements.
        comment_detect_expressions (bool): Whether standalone comments should be parsed as possible Python expressions.

    Returns:
        Formatting result containing rewritten source and any fixed or remaining findings.
    """
    settings = CheckSettings(
        select=("PCF",),
        line_length=line_length,
        line_ending=line_ending,
        indent_width=indent_width,
        url_aware_wrapping=url_aware_wrapping,
        comment_join_standalone_lines=comment_join_standalone_lines,
        comment_format_list_items=comment_format_list_items,
        comment_task_marker_mode=comment_task_marker_mode,
        comment_task_markers=comment_task_markers,
        comment_preserve_headings=comment_preserve_headings,
        comment_preserve_doctests=comment_preserve_doctests,
        comment_preserve_code_fences=comment_preserve_code_fences,
        comment_format_block_quotes=comment_format_block_quotes,
        comment_preserve_tables=comment_preserve_tables,
        comment_preserve_directives=comment_preserve_directives,
        comment_trailing_extraction_syntax_aware=comment_trailing_extraction_syntax_aware,
        comment_trailing_extraction_content_aware=comment_trailing_extraction_content_aware,
        comment_detect_code=comment_detect_code,
        comment_detect_statements=comment_detect_statements,
        comment_detect_expressions=comment_detect_expressions,
    )
    return format_pcf_settings(source, settings=settings, fix=fix)


def format_pcf_settings(source: str, *, settings: CheckSettings, fix: bool = True) -> formatter.FormatterResult:
    """Format source with caller-provided PCF check settings.

    Args:
        source (str): Python source text to format.
        settings (CheckSettings): Check settings that select PCF rules and configure comment formatting behavior.
        fix (bool): Whether selected fixes should be applied before returning remaining findings.

    Returns:
        Formatting result produced with the caller-provided settings.
    """
    return formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=fix)
