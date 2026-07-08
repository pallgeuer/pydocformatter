"""Base classes and execution contexts for rules.

Attributes:
    CategoryDataT (TypeVar): Prepared category data type returned by a concrete rule category.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import inspect
import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.models import RuleCategoryMetadata, RuleCheckKind, RuleMetadata
from pydocformatter.utils import misc


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.codes import RuleCode
    from pydocformatter.rules.violations import RuleViolation

CategoryDataT = TypeVar("CategoryDataT")


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


@dataclasses.dataclass(frozen=True)
class RuleContext(RuleCategoryContext):
    """Read-only source and category context supplied to one rule.

    Attributes:
        category_data (object | None): Shared data prepared by the rule category for this module.
    """

    category_data: object | None


class RuleBase:
    """Base class for implemented pydocformatter rules.

    Attributes:
        meta (ClassVar[RuleMetadata]): Rule metadata supplied by concrete rule classes.
        code (str): Alias for the full rule code tag.
        prefix (str): Alias for the rule-code prefix.
        number_str (str): Alias for the zero-padded rule number string.
        number (int): Alias for the integer rule number.
        name (str): Alias for the rule name.
        message (str): Alias for the default diagnostic message.
        fix_availability (FixAvailability): Alias for the rule-level automatic fix availability.
        stable_since (str): Alias for the pydocformatter version in which the rule became stable.
        setting_effects (tuple[RuleSettingEffects, ...]): Alias for selection effects driven by resolved settings.
        incompatible_with (tuple[RuleCode, ...]): Alias for rule codes that cannot be selected with this rule.
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
        """Require implemented rule classes to define metadata and the current rule API."""
        super().__init_subclass__()
        if "meta" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define RuleMetadata as 'meta'")
        if not isinstance(cls.meta, RuleMetadata):
            raise TypeError(f"{cls.__name__}.meta must be a RuleMetadata instance")
        violations_hook = cls.__dict__.get("violations")
        if cls.meta.check_kind == RuleCheckKind.STANDARD and violations_hook is None:
            raise TypeError(f"{cls.__name__} must define violations()")
        if violations_hook is not None:
            _validate_violations_hook(cls, violations_hook)

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[RuleViolation, ...]:
        """Return canonical violations for the current source.

        Args:
            context (RuleContext): Parsed source, settings, category data, and effective fix mode for the current file.

        Returns:
            tuple[RuleViolation, ...]: Violations reported by this rule before suppression filtering.
        """
        del context
        return ()


def _validate_violations_hook(rule_class: type[RuleBase], hook: object) -> None:
    """Validate the classmethod shape expected by the rule runner."""
    if not isinstance(hook, classmethod):
        raise TypeError(f"{rule_class.__name__}.violations must be a @classmethod accepting context")
    if not callable(hook.__func__):
        raise TypeError(f"{rule_class.__name__}.violations must be callable")
    bound_hook = cast("Any", hook).__get__(None, rule_class)
    if not callable(bound_hook):
        raise TypeError(f"{rule_class.__name__}.violations must be callable")
    try:
        signature = inspect.signature(bound_hook)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{rule_class.__name__}.violations signature could not be inspected: {error}") from None
    parameters = tuple(signature.parameters.values())
    if (
        len(parameters) != 1
        or parameters[0].kind not in {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
        or parameters[0].name != "context"
        or parameters[0].default is not inspect.Parameter.empty
    ):
        raise TypeError(f"{rule_class.__name__}.violations must accept exactly one required positional argument named context")


class RuleCategoryBase(Generic[CategoryDataT]):
    """Base class for pydocformatter rule categories.

    Attributes:
        meta (ClassVar[RuleCategoryMetadata]): Category metadata supplied by concrete category classes.
        code_class_map (ClassVar[dict[RuleCode, type[RuleBase]]]): Registered rules indexed by rule code.
        prefix (str): Alias for the category rule-code prefix.
        name (str): Alias for the category name.
        url (str | None): Alias for the optional category documentation URL.
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
        """Return registered rules in deterministic rule-code order.

        Returns:
            tuple[type[RuleBase], ...]: Rule classes registered to this category sorted by rule code.
        """
        return tuple(rule_class for _, rule_class in sorted(cls.code_class_map.items()))

    @classmethod
    def ordered_code_class_map(cls) -> dict[RuleCode, type[RuleBase]]:
        """Return registered rules indexed in deterministic rule-code order.

        Returns:
            dict[RuleCode, type[RuleBase]]: Rule-code mapping sorted by code for stable collection and display.
        """
        return dict(sorted(cls.code_class_map.items()))

    @classmethod
    def prepare(cls, context: RuleCategoryContext) -> CategoryDataT | None:
        """Return optional read-only data shared by this category's rules for one module.

        Args:
            context (RuleCategoryContext): Parsed module, source text, settings, and category-selected rule classes.

        Returns:
            CategoryDataT | None: Category-specific prepared data, or None when the category has no shared preparation.
        """
        del context
        return None
