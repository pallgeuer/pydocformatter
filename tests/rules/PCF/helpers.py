import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding


def format_pcf(
    source: str,
    *,
    fix: bool = True,
    line_length: int = 88,
    line_ending: LineEnding = LineEnding.AUTO,
    indent_width: int = 4,
    url_aware_wrapping: bool = True,
    comment_join_standalone_lines: bool = False,
    comment_format_list_items: bool = True,
    comment_preserve_headings: bool = True,
    comment_preserve_doctests: bool = True,
    comment_preserve_code_fences: bool = True,
    comment_format_block_quotes: bool = True,
    comment_preserve_tables: bool = True,
    comment_preserve_directives: bool = True,
    comment_detect_code: bool = False,
    comment_detect_statements: bool = True,
    comment_detect_expressions: bool = False,
) -> formatter.FormatterResult:
    settings = CheckSettings(
        select=("PCF",),
        line_length=line_length,
        line_ending=line_ending,
        indent_width=indent_width,
        url_aware_wrapping=url_aware_wrapping,
        comment_join_standalone_lines=comment_join_standalone_lines,
        comment_format_list_items=comment_format_list_items,
        comment_preserve_headings=comment_preserve_headings,
        comment_preserve_doctests=comment_preserve_doctests,
        comment_preserve_code_fences=comment_preserve_code_fences,
        comment_format_block_quotes=comment_format_block_quotes,
        comment_preserve_tables=comment_preserve_tables,
        comment_preserve_directives=comment_preserve_directives,
        comment_detect_code=comment_detect_code,
        comment_detect_statements=comment_detect_statements,
        comment_detect_expressions=comment_detect_expressions,
    )
    return format_pcf_settings(source, settings=settings, fix=fix)


def format_pcf_settings(source: str, *, settings: CheckSettings, fix: bool = True) -> formatter.FormatterResult:
    return formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=fix)
