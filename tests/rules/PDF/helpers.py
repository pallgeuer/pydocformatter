"""Shared test helpers for PDF rules."""

from __future__ import annotations

import typing

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF


class RuleFormatter(typing.Protocol):
    """Callable formatter helper for one default PDF rule code."""

    def __call__(self, source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
        """Format source with optional settings.

        Args:
            source: Python source text to format.
            settings: Explicit settings overriding the helper's default rule selection and docstring convention.
            fix: Whether automatic fixes should be applied.
        """


class RuleContextBuilder(typing.Protocol):
    """Callable context helper for one default PDF rule code."""

    def __call__(self, source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
        """Build matching category and rule contexts for source.

        Args:
            source: Python source text to parse.
            settings: Explicit settings overriding the helper's default rule selection and docstring convention.
        """


def formatter_for(rule_code: str, *, convention: DocstringConvention = DocstringConvention.GOOGLE) -> RuleFormatter:
    """Return a source formatter using one default PDF rule code.

    Args:
        rule_code: PDF rule code used when settings are not supplied.
        convention: Docstring convention used when settings are not supplied.

    Returns:
        Source formatter with the supplied default rule selection.
    """

    def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
        resolved_settings = CheckSettings(select=(rule_code,), docstring_convention=convention) if settings is None else settings
        return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)

    return format_source


def contexts_for(rule_code: str, *, convention: DocstringConvention = DocstringConvention.GOOGLE) -> RuleContextBuilder:
    """Return a context builder using one default PDF rule code.

    Args:
        rule_code: PDF rule code used when settings are not supplied.
        convention: Docstring convention used when settings are not supplied.

    Returns:
        Context builder with the supplied default rule selection.
    """

    def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
        module = cst.parse_module(source)
        wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
        category = RuleCategoryContext(
            path="example.py",
            settings=CheckSettings(select=(rule_code,), docstring_convention=convention) if settings is None else settings,
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

    return contexts
