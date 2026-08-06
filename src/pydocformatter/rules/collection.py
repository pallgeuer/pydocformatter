"""Built-in rule collection loading.

Attributes:
    RULE_COLLECTION (RuleCollection): Process-wide built-in rule catalog populated from registered category packages at
        import time.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import enum
import inspect
import pkgutil
import importlib
import dataclasses
import importlib.resources
from collections.abc import Iterable
from types import ModuleType
from typing import TYPE_CHECKING, TypeVar

# First-party imports
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.definitions as rule_definitions
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode, RuleSelector
from pydocformatter.rules.definition import RuleBase, RuleCategoryBase
from pydocformatter.rules.registration import RuleError


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.registration import RuleRegistry


_BaseT = TypeVar("_BaseT")


class RuleSelectorResolutionKind(enum.Enum):
    """Classification of a collection-aware rule selector.

    Attributes:
        NAME: Registered exact rule name.
        CODE: Valid broad or exact code selector.
        UNKNOWN_NAME: Syntactically valid rule name absent from the collection.
        INVALID: Text matching neither selector grammar.
    """

    NAME = "name"
    CODE = "code"
    UNKNOWN_NAME = "unknown-name"
    INVALID = "invalid"


@dataclasses.dataclass(frozen=True)
class RuleSelectorResolution:
    """Collection-aware resolution of one original selector string.

    Attributes:
        kind (RuleSelectorResolutionKind): Syntactic and catalog classification.
        selector (RuleSelector | None): Existing code selector representation used for successful resolution.
        matching_rules (tuple[type[RuleBase], ...]): Collected rules covered by the resolved selector.
        exact_rule (type[RuleBase] | None): Concrete rule selected by an exact code or registered name.
    """

    kind: RuleSelectorResolutionKind
    selector: RuleSelector | None
    matching_rules: tuple[type[RuleBase], ...]
    exact_rule: type[RuleBase] | None


@dataclasses.dataclass(frozen=True, init=False)
class RuleCollection:
    """Collected pydocformatter rule category and rule classes.

    Attributes:
        categories (tuple[type[RuleCategoryBase], ...]): Registered rule categories in deterministic order.
        category_class (dict[str, type[RuleCategoryBase]]): Category classes indexed by rule-code prefix.
        rules (tuple[type[RuleBase], ...]): Registered rule classes in deterministic rule-code order.
        rule_class (dict[RuleCode, type[RuleBase]]): Rule classes indexed by full rule code.
        rule_class_by_name (dict[str, type[RuleBase]]): Rule classes indexed by canonical rule name in collection order.
    """

    categories: tuple[type[RuleCategoryBase], ...]
    category_class: dict[str, type[RuleCategoryBase]]
    rules: tuple[type[RuleBase], ...]
    rule_class: dict[RuleCode, type[RuleBase]]
    rule_class_by_name: dict[str, type[RuleBase]]

    def __init__(self, categories: Iterable[type[RuleCategoryBase]]) -> None:
        """Create a deterministically ordered rule collection from category classes.

        Args:
            categories (Iterable[type[RuleCategoryBase]]): Registered category classes to validate and index.

        Raises:
            RuleError: If a category is invalid, prefixes, rule codes, or rule names collide, an exact rule code is also
                a broad selector, or incompatibility metadata is inconsistent.
        """
        category_class_by_prefix: dict[str, type[RuleCategoryBase]] = {}
        for category in categories:
            if not isinstance(category, type) or not issubclass(category, RuleCategoryBase):
                raise RuleError(f"Collected rule category must inherit RuleCategoryBase: {category!r}")
            existing = category_class_by_prefix.get(category.meta.prefix)
            if existing is not None and existing is not category:
                raise RuleError(f"Duplicate rule category prefix: {category.meta.prefix}")
            category_class_by_prefix[category.meta.prefix] = category

        sorted_category_class = dict(sorted(category_class_by_prefix.items()))
        rule_class_by_code: dict[RuleCode, type[RuleBase]] = {}
        rule_class_by_name: dict[str, type[RuleBase]] = {}
        for category in sorted_category_class.values():
            for code, rule in category.ordered_code_class_map().items():
                if code in rule_class_by_code:
                    raise RuleError(f"Duplicate rule code: {code}")
                if rule.meta.name in rule_class_by_name:
                    raise RuleError(f"Duplicate rule name: {rule.meta.name}")
                rule_class_by_code[code] = rule
                rule_class_by_name[rule.meta.name] = rule

        object.__setattr__(self, "categories", tuple(sorted_category_class.values()))
        object.__setattr__(self, "category_class", sorted_category_class)
        object.__setattr__(self, "rules", tuple(rule_class_by_code.values()))
        object.__setattr__(self, "rule_class", rule_class_by_code)
        object.__setattr__(self, "rule_class_by_name", rule_class_by_name)

        self._validate_exact_rule_code_selectors()
        self._validate_rule_incompatibilities()

    def _validate_exact_rule_code_selectors(self) -> None:
        """Reject full rule codes that also select another collected rule."""
        for rule in self.rules:
            code = rule.meta.code
            matching_codes = tuple(matching_rule.meta.code for matching_rule in self.matching_rules(RuleSelector(code.tag)))
            if matching_codes != (code,):
                raise RuleError(f"Rule code {code} is also a broad selector matching: {', '.join(str(matching_code) for matching_code in matching_codes)}")

    @classmethod
    def from_registry(cls, registry: RuleRegistry) -> RuleCollection:
        """Create a rule collection from registered category classes.

        Args:
            registry (RuleRegistry): Mutable registry populated by rule category decorators.

        Returns:
            RuleCollection: Immutable indexed collection built from the registry's category classes.
        """
        return cls(registry.category_classes)

    def _validate_rule_incompatibilities(self) -> None:
        """Validate incompatibility metadata against the complete rule collection."""
        for rule in self.rules:
            code = rule.meta.code
            if code in rule.meta.incompatible_with:
                raise RuleError(f"Rule {code} cannot be incompatible with itself")
            for incompatible_code in rule.meta.incompatible_with:
                incompatible_rule = self.rule_class.get(incompatible_code)
                if incompatible_rule is None:
                    raise RuleError(f"Rule {code} is incompatible with unknown rule code {incompatible_code}")
                if code not in incompatible_rule.meta.incompatible_with:
                    raise RuleError(f"Rule incompatibility between {code} and {incompatible_code} must be declared by both rules")

    def matching_rules_exist(self, selector: RuleSelector) -> bool:
        """Return whether a selector matches at least one collected rule.

        Args:
            selector (RuleSelector): Parsed selector to compare against registered rule codes.

        Returns:
            bool: Whether the selector covers at least one rule in this collection.
        """
        return any(selector.selects_code(rule.meta.code) for rule in self.rules)

    def matching_rules(self, selector: RuleSelector) -> tuple[type[RuleBase], ...]:
        """Return collected rules matched by a selector.

        Args:
            selector (RuleSelector): Parsed selector to compare against registered rule codes.

        Returns:
            tuple[type[RuleBase], ...]: Rule classes covered by the selector in collection order.
        """
        return tuple(rule for rule in self.rules if selector.selects_code(rule.meta.code))

    def resolve_selector(self, selector: str) -> RuleSelectorResolution:
        """Resolve a rule name or code selector against this collection.

        Args:
            selector (str): Original case-sensitive selector text.

        Returns:
            RuleSelectorResolution: Classification and existing code-selector representation for the input.
        """
        if (rule_class := self.rule_class_by_name.get(selector)) is not None:
            code = rule_class.meta.code
            return RuleSelectorResolution(kind=RuleSelectorResolutionKind.NAME, selector=RuleSelector(code.tag), matching_rules=(rule_class,), exact_rule=rule_class)
        if RuleSelector.is_valid_tag(selector):
            code_selector = RuleSelector(selector)
            matching_rules = self.matching_rules(code_selector)
            exact_rule = self.rule_class.get(RuleCode(selector)) if RuleCode.is_valid_tag(selector) else None
            return RuleSelectorResolution(kind=RuleSelectorResolutionKind.CODE, selector=code_selector, matching_rules=matching_rules, exact_rule=exact_rule)
        if rule_models.is_valid_rule_name(selector):
            return RuleSelectorResolution(kind=RuleSelectorResolutionKind.UNKNOWN_NAME, selector=None, matching_rules=(), exact_rule=None)
        return RuleSelectorResolution(kind=RuleSelectorResolutionKind.INVALID, selector=None, matching_rules=(), exact_rule=None)


def import_package_rule_categories(*, package: ModuleType, registry: RuleRegistry | None = None) -> None:
    """Import and validate category modules followed by rule modules.

    Args:
        package (ModuleType): Rule definitions package containing one subpackage per rule category.
        registry (RuleRegistry | None): Registry expected to receive imported category classes.

    Raises:
        RuleError: If the package layout, category registration, rule modules, Markdown files, or incompatibility
            metadata are invalid.
    """
    if not hasattr(package, "__path__"):
        raise RuleError(f"Rule definitions package has no __path__: {package.__name__}")
    if registry is None:
        registry = rule_registration.DEFAULT_RULE_REGISTRY
    package_modules = tuple(pkgutil.iter_modules(path=package.__path__, prefix=f"{package.__name__}."))
    unexpected_modules = tuple(module.name for module in package_modules if not module.ispkg)
    if unexpected_modules:
        raise RuleError(f"Rule definitions package must contain only category packages, found modules: {', '.join(unexpected_modules)}")
    for category_package in package_modules:
        _import_rule_category_package(category_package.name, registry=registry)


def _import_rule_category_package(package_name: str, *, registry: RuleRegistry) -> None:
    """Import and validate one rule category package."""
    prefix = package_name.rpartition(".")[2]
    category_package = importlib.import_module(package_name)
    category_modules = tuple(pkgutil.iter_modules(path=category_package.__path__, prefix=f"{package_name}."))
    nested_packages = tuple(module.name for module in category_modules if module.ispkg)
    if nested_packages:
        raise RuleError(f"Rule category package {package_name} must not contain nested packages: {', '.join(nested_packages)}")

    module_by_basename = {module.name.rpartition(".")[2]: module.name for module in category_modules}
    category_module_name = f"{package_name}.{prefix}"
    if prefix not in module_by_basename:
        raise RuleError(f"Rule category package {package_name} must contain category module {category_module_name}")

    category_module = importlib.import_module(category_module_name)
    category_classes = _local_subclasses(category_module, RuleCategoryBase)
    if len(category_classes) != 1 or category_classes[0].__name__ != prefix:
        raise RuleError(f"{category_module_name} must define exactly one RuleCategoryBase subclass named {prefix}")
    if _local_subclasses(category_module, RuleBase):
        raise RuleError(f"Rule category module {category_module_name} must not define RuleBase subclasses")
    category_class = category_classes[0]
    if category_class.meta.prefix != prefix:
        raise RuleError(f"{category_module_name}.{prefix} prefix {category_class.meta.prefix!r} does not match package and module name {prefix!r}")
    if category_class not in registry.category_classes:
        raise RuleError(f"Rule category {category_module_name}.{prefix} is not registered with the rule registry")

    resources = importlib.resources.files(category_package)
    expected_markdown = {f"{prefix}.md"}
    if not resources.joinpath(f"{prefix}.md").is_file():
        raise RuleError(f"Rule category {category_module_name}.{prefix} is missing adjacent documentation {prefix}.md")

    discovered_rule_classes: set[type[RuleBase]] = set()
    for basename, module_name in sorted(module_by_basename.items()):
        if basename == prefix:
            continue
        module_code, separator, module_name_suffix = basename.partition("_")
        if not separator or not module_name_suffix or not RuleCode.is_valid_tag(module_code) or RuleCode(module_code).prefix != prefix:
            raise RuleError(f"Unexpected module in rule category package {package_name}: {module_name}")
        rule_module = importlib.import_module(module_name)
        if _local_subclasses(rule_module, RuleCategoryBase):
            raise RuleError(f"Rule module {module_name} must not define RuleCategoryBase subclasses")
        rule_classes = _local_subclasses(rule_module, RuleBase)
        if len(rule_classes) != 1:
            raise RuleError(f"Rule module {module_name} must define exactly one RuleBase subclass")
        rule_class = rule_classes[0]
        if rule_class.meta.code.tag != module_code:
            raise RuleError(f"Rule module {module_name} code {module_code!r} does not match rule code {rule_class.meta.code.tag!r}")
        if category_class.code_class_map.get(rule_class.meta.code) is not rule_class:
            raise RuleError(f"Rule {module_name}.{rule_class.__name__} is not registered with category {prefix}")
        expected_markdown.add(f"{basename}.md")
        if not resources.joinpath(f"{basename}.md").is_file():
            raise RuleError(f"Rule {module_name}.{rule_class.__name__} is missing adjacent documentation {basename}.md")
        discovered_rule_classes.add(rule_class)

    registered_rule_classes = set(category_class.code_class_map.values())
    unexpected_registered_rules = tuple(
        sorted(
            (rule_class for rule_class in registered_rule_classes if rule_class.__module__ != package_name and not rule_class.__module__.startswith(f"{package_name}.")),
            key=lambda rule_class: rule_class.meta.code,
        )
    )
    if unexpected_registered_rules:
        raise RuleError(
            f"Category {prefix} contains rules from outside package {package_name}: {', '.join(rule_class.__module__ + '.' + rule_class.__name__ for rule_class in unexpected_registered_rules)}"
        )
    missing_rule_modules = tuple(sorted(registered_rule_classes - discovered_rule_classes, key=lambda rule_class: rule_class.meta.code))
    if missing_rule_modules:
        raise RuleError(f"Category {prefix} contains registered rules without matching rule modules: {', '.join(str(rule_class.meta.code) for rule_class in missing_rule_modules)}")

    markdown_files = {resource.name for resource in resources.iterdir() if resource.is_file() and resource.name.endswith(".md")}
    orphan_markdown = tuple(sorted(markdown_files - expected_markdown))
    if orphan_markdown:
        raise RuleError(f"Rule category package {package_name} contains orphan Markdown files: {', '.join(orphan_markdown)}")


def _local_subclasses(module: ModuleType, base: type[_BaseT]) -> tuple[type[_BaseT], ...]:
    """Return subclasses of a base that are defined directly in a module."""
    return tuple(class_type for _, class_type in inspect.getmembers(module, inspect.isclass) if class_type.__module__ == module.__name__ and issubclass(class_type, base))


import_package_rule_categories(package=rule_definitions)
RULE_COLLECTION = RuleCollection.from_registry(rule_registration.DEFAULT_RULE_REGISTRY)
