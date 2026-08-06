"""Shared helpers for docstring statement spacing rule tests."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PDF.PDF import PDF
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


def contexts(source: str, *, rule_code: str) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source.

    Args:
        source (str): Python source text to parse.
        rule_code (str): Rule code selected in the generated settings.

    Returns:
        Category and rule contexts with prepared PDF data.
    """
    return rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=CheckSettings(select=(rule_code,)))


def format_source(source: str, *, rule_code: str, fix: bool = True) -> formatter.FormatterResult:
    """Format source with one selected rule.

    Args:
        source (str): Python source text to format.
        rule_code (str): Rule code selected in the generated settings.
        fix (bool): Whether automatic fixes should be applied.

    Returns:
        Formatter result for the supplied source.
    """
    settings = CheckSettings(select=(rule_code,))
    return formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=fix)
