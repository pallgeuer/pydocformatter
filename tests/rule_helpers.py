"""Test adapters for direct rule API calls."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING, Any

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.runner as rule_runner
import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules import line_endings, suppressions
from pydocformatter.rules.definition import RuleCategoryBase, RuleCategoryContext, RuleContext
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.models import RuleFinding
from pydocformatter.source_path import SourcePathContext


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.cli.settings_check import CheckSettings
    from pydocformatter.rules.definition import RuleBase


@dataclasses.dataclass(frozen=True)
class DirectRuleFixOutcome:
    """Applied source-fix view used by focused rule tests.

    Attributes:
        module (cst.Module): Parsed module after direct rule fixes have been applied.
        source (str): Exact source after direct rule fixes have been applied.
        fixed_findings (tuple[RuleFinding, ...]): Findings associated with the violations whose source fixes were
            applied.
    """

    module: cst.Module
    source: str
    fixed_findings: tuple[RuleFinding, ...] = ()


def direct_rule_category_context(source: str, *, settings: CheckSettings, path: str = "example.py") -> RuleCategoryContext:
    """Return a production-equivalent category context for direct rule tests.

    Args:
        source (str): Python source text to parse and align.
        settings (CheckSettings): Resolved settings supplied to the category and rule.
        path (str): Display path and source-path input for the context.

    Returns:
        RuleCategoryContext: Parsed exact-source context with remapped positions and cached line bounds.
    """
    module = cst.parse_module(source)
    exact_source = rule_runner._module_aligned_source(source)
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    offset_map = source_text.source_offset_map(module, exact_source)
    source_lines = tuple(source_text.source_lines(exact_source))
    positions = offset_map.positions(metadata_wrapper.resolve(cst_metadata.PositionProvider))
    directive_indexes = suppressions.source_directive_indexes(module, positions=positions, source_lines=source_lines, collection=rule_collection.RULE_COLLECTION)
    return RuleCategoryContext(
        path=path,
        source_path=SourcePathContext.for_path(path),
        settings=settings,
        module=module,
        metadata_wrapper=metadata_wrapper,
        positions=positions,
        line_ending=line_endings.resolve_line_ending(source, line_ending=settings.line_ending),
        source=exact_source,
        source_lines=source_lines,
        line_bounds=source_text.line_bounds_from_lines(source_lines),
        bracket_directive_index=directive_indexes.bracket_directive_index,
    )


def direct_rule_context(category_context: RuleCategoryContext, *, category_data: object | None) -> RuleContext:
    """Return a rule context sharing one direct category context.

    Args:
        category_context (RuleCategoryContext): Exact-source category context to expose to the rule.
        category_data (object | None): Prepared category data attached to the rule context.

    Returns:
        RuleContext: Direct rule context sharing the supplied source and metadata.
    """
    return RuleContext(
        path=category_context.path,
        source_path=category_context.source_path,
        settings=category_context.settings,
        module=category_context.module,
        metadata_wrapper=category_context.metadata_wrapper,
        positions=category_context.positions,
        line_ending=category_context.line_ending,
        source=category_context.source,
        source_lines=category_context.source_lines,
        line_bounds=category_context.line_bounds,
        bracket_directive_index=category_context.bracket_directive_index,
        category_data=category_data,
    )


def prepared_direct_rule_contexts(category_class: type[RuleCategoryBase[Any]], source: str, *, settings: CheckSettings, path: str = "example.py") -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching direct category and prepared rule contexts.

    Args:
        category_class (type[RuleCategoryBase[Any]]): Rule category whose shared data should be prepared.
        source (str): Python source text to parse and align.
        settings (CheckSettings): Resolved settings supplied to the category and rule.
        path (str): Display path and source-path input for both contexts.

    Returns:
        tuple[RuleCategoryContext, RuleContext]: Matching category and prepared rule contexts.
    """
    category_context = direct_rule_category_context(source, settings=settings, path=path)
    return category_context, direct_rule_context(category_context, category_data=category_class.prepare(category_context))


def rule_findings(rule_class: type[RuleBase], context: RuleContext) -> tuple[RuleFinding, ...]:
    """Return findings from a rule's canonical violations.

    Args:
        rule_class (type[RuleBase]): Rule implementation to execute through the same validation path used by direct rule
            tests.
        context (RuleContext): Prepared rule context containing parsed source and any category data required by the
            rule.

    Returns:
        Public findings derived from the rule's validated violations.
    """
    return tuple(violation.finding for violation in validated_rule_violations(rule_class, context))


def rule_fix_result(rule_class: type[RuleBase], context: RuleContext) -> DirectRuleFixOutcome:
    """Apply unsuppressed source fixes from a rule's canonical violations.

    Args:
        rule_class (type[RuleBase]): Rule implementation whose fixable violations should be applied directly.
        context (RuleContext): Prepared rule context for the source module under test.

    Returns:
        Parsed module and exact source after applying all available direct rule fixes, together with the findings that
        were fixed.

    Raises:
        AssertionError: Raised when the rule runner rejects the planned source changes or reports validation errors.
    """
    fixable_violations = tuple(violation for violation in validated_rule_violations(rule_class, context) if violation.fix is not None)
    if not fixable_violations:
        return DirectRuleFixOutcome(module=context.module, source=context.source)
    errors: list[str] = []
    changes = rule_runner._planned_source_changes_for_violations(rule_class, fixable_violations, path=context.path, source_line_count=len(context.source_lines), errors=errors)
    if errors or changes is None:
        raise AssertionError("; ".join(errors) or "Direct rule test source-fix validation failed")
    applied_changes = rule_edits.apply_context_source_changes(context, changes)
    return DirectRuleFixOutcome(module=applied_changes.module, source=applied_changes.source, fixed_findings=tuple(violation.finding for violation in fixable_violations))


def validated_rule_violations(rule_class: type[RuleBase], context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations after applying runner validation used by direct rule tests.

    Args:
        rule_class (type[RuleBase]): Rule implementation whose raw violations should be validated.
        context (RuleContext): Prepared rule context used to call the rule's violations hook.

    Returns:
        Validated rule violations in the order produced by the rule implementation.

    Raises:
        AssertionError: Raised when runner validation reports malformed violations.
    """
    errors: list[str] = []
    violations = rule_runner._validated_rule_violations(
        rule_class, rule_class.violations(context), path=context.path, operation="direct rule test", source_line_count=len(context.source_lines), errors=errors
    )
    if errors:
        raise AssertionError("; ".join(errors))
    return violations
