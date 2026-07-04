"""Shared helpers for docstring statement spacing rule tests."""

from __future__ import annotations

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF


def contexts(source: str, *, rule_code: str) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source.

    Args:
        source: Python source text to parse.
        rule_code: Rule code selected in the generated settings.

    Returns:
        Category and rule contexts with prepared PDF data.
    """
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=(rule_code,)),
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
        line_bounds=None,
    )
    return category, RuleContext(
        path=category.path,
        settings=category.settings,
        module=category.module,
        metadata_wrapper=category.metadata_wrapper,
        positions=category.positions,
        line_ending=category.line_ending,
        source=category.source,
        source_lines=category.source_lines,
        line_bounds=category.line_bounds,
        category_data=PDF.prepare(category),
    )


def format_source(source: str, *, rule_code: str, fix: bool = True) -> formatter.FormatterResult:
    """Format source with one selected rule.

    Args:
        source: Python source text to format.
        rule_code: Rule code selected in the generated settings.
        fix: Whether automatic fixes should be applied.

    Returns:
        Formatter result for the supplied source.
    """
    settings = CheckSettings(select=(rule_code,))
    return formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=fix)
