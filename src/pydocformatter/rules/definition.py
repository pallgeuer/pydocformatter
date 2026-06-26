"""Base classes and execution contexts for rules."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING, ClassVar

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.utils.misc as misc
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.models import RuleCategoryMetadata, RuleFinding, RuleMetadata

if TYPE_CHECKING:
    from pydocformatter.cli.settings_check import CheckSettings
    from pydocformatter.rules.suppressions import SuppressionIndex


@dataclasses.dataclass(frozen=True)
class RuleCategoryContext:
    """Read-only source context supplied to a rule category preprocessor.

    Attributes:
        path (str): Display path for diagnostics and path-sensitive settings.
        settings (CheckSettings): Resolved check settings for `path`.
        module (cst.Module): Parsed LibCST module currently being checked or fixed.
        metadata_wrapper (cst_metadata.MetadataWrapper): Metadata wrapper for resolving LibCST providers.
        positions (Mapping[cst.CSTNode, cst_metadata.CodeRange]): Position metadata for nodes in `module`.
        line_ending (str): Line ending to use for generated source text.
        source (str): Current module source aligned with `module`.
        source_lines (tuple[str, ...]): Current source split into physical lines.
        line_bounds (source_text.LineBounds | None): Cached source offset lookup table, if available.
        suppression_index (SuppressionIndex | None): Parsed pydocformatter suppression directives for this source state.
    """

    path: str
    settings: CheckSettings
    module: cst.Module
    metadata_wrapper: cst_metadata.MetadataWrapper
    positions: Mapping[cst.CSTNode, cst_metadata.CodeRange]
    line_ending: str
    source: str
    source_lines: tuple[str, ...]
    line_bounds: source_text.LineBounds | None = dataclasses.field(kw_only=True)
    suppression_index: SuppressionIndex | None = dataclasses.field(kw_only=True)


@dataclasses.dataclass(frozen=True)
class RuleContext(RuleCategoryContext):
    """Read-only source and category context supplied to one rule.

    Attributes:
        category_data (object | None): Shared data prepared by the rule category for this module.
        effectively_fixable (bool): Whether this rule may apply fixes in the current run.
    """

    category_data: object | None
    effectively_fixable: bool


@dataclasses.dataclass(frozen=True)
class RuleFixResult:
    """Result returned by one rule automatic-fix attempt.

    Attributes:
        module (cst.Module): Module after applying the rule's fixes.
        fixed_findings (tuple[RuleFinding, ...]): Findings fixed by the returned module.
    """

    module: cst.Module
    fixed_findings: tuple[RuleFinding, ...] = ()


class RuleBase:
    """Base class for implemented pydocformatter rules.

    Attributes:
        meta (ClassVar[RuleMetadata]): Rule metadata supplied by concrete rule classes.
        code: Alias for the full rule code tag.
        prefix: Alias for the rule-code prefix.
        number_str: Alias for the zero-padded rule number string.
        number: Alias for the integer rule number.
        name: Alias for the rule name.
        message: Alias for the default diagnostic message.
        fix_availability: Alias for the rule-level automatic fix availability.
        stable_since: Alias for the pydocformatter version in which the rule became stable.
        setting_effects: Alias for selection effects driven by resolved settings.
        incompatible_with: Alias for rule codes that cannot be selected with this rule.
    """

    meta: ClassVar[RuleMetadata]

    code = misc.alias_to_class_field("meta.code.tag")
    prefix = misc.alias_to_class_field("meta.code.prefix")
    number_str = misc.alias_to_class_field("meta.code.number_str")
    number = misc.alias_to_class_field("meta.code.number")
    name = misc.alias_to_class_field("meta.name")
    message = misc.alias_to_class_field("meta.message")
    fix_availability = misc.alias_to_class_field("meta.fix_availability")
    stable_since = misc.alias_to_class_field("meta.stable_since")
    setting_effects = misc.alias_to_class_field("meta.setting_effects")
    incompatible_with = misc.alias_to_class_field("meta.incompatible_with")

    def __init_subclass__(cls) -> None:
        """Require implemented rule classes to define metadata."""
        super().__init_subclass__()
        if "meta" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define RuleMetadata as 'meta'")
        if not isinstance(cls.meta, RuleMetadata):
            raise TypeError(f"{cls.__name__}.meta must be a RuleMetadata instance")

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for the current source without modifying it."""
        del context
        return ()

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Return the source after applying this rule's available automatic fixes."""
        return RuleFixResult(module=context.module)


class RuleCategoryBase:
    """Base class for pydocformatter rule categories.

    Attributes:
        meta (ClassVar[RuleCategoryMetadata]): Category metadata supplied by concrete category classes.
        code_class_map (ClassVar[dict[RuleCode, type[RuleBase]]]): Registered rules indexed by rule code.
        prefix: Alias for the category rule-code prefix.
        name: Alias for the category name.
        url: Alias for the optional category documentation URL.
    """

    meta: ClassVar[RuleCategoryMetadata]
    code_class_map: ClassVar[dict[RuleCode, type[RuleBase]]]

    prefix = misc.alias_to_class_field("meta.prefix")
    name = misc.alias_to_class_field("meta.name")
    url = misc.alias_to_class_field("meta.url")

    def __init_subclass__(cls) -> None:
        """Require category metadata and create isolated rule registration state."""
        super().__init_subclass__()
        if "meta" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define RuleCategoryMetadata as 'meta'")
        if not isinstance(cls.meta, RuleCategoryMetadata):
            raise TypeError(f"{cls.__name__}.meta must be a RuleCategoryMetadata instance")
        cls.code_class_map = {}

    @classmethod
    def ordered_rules(cls) -> tuple[type[RuleBase], ...]:
        """Return registered rules in deterministic rule-code order."""
        return tuple(rule_class for _, rule_class in sorted(cls.code_class_map.items()))

    @classmethod
    def ordered_code_class_map(cls) -> dict[RuleCode, type[RuleBase]]:
        """Return registered rules indexed in deterministic rule-code order."""
        return dict(sorted(cls.code_class_map.items()))

    @classmethod
    def prepare(cls, context: RuleCategoryContext) -> object | None:
        """Return optional read-only data shared by this category's rules for one module."""
        del context
        return None
