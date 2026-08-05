# Future imports
from __future__ import annotations

# Standard library imports
import os
import re
import ast
import sys
import typing
import inspect
import pkgutil
import argparse
import tempfile
import importlib
import subprocess
import dataclasses
from io import StringIO
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter.settings as settings_core
import pydocformatter.rules.codes as rule_codes
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definitions as rule_definitions
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter import file_selection, rules_selection
from pydocformatter.cli import check
from pydocformatter.cli.global_args import GlobalArgs
from pydocformatter.cli.settings_check import SETTINGS_SCHEMA, CheckSettings, DocstringConvention
from pydocformatter.rules.codes import RuleCode, RuleSelector
from pydocformatter.rules.definition import RuleBase, RuleCategoryBase
from pydocformatter.rules.definition_helpers import docstring_conventions, typed_entry_rules
from pydocformatter.rules.models import FixAvailability, RuleCategoryMetadata, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if typing.TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations


EXPECTED_RULE_DOCUMENTATION_SECTIONS = ("What it does", "Why is this useful?", "Ruff compatibility", "Examples", "Options")
EXPECTED_RULE_CATEGORY_DOCUMENTATION_SECTIONS = ("What it does", "Why is this useful?", "Rules", "Related tooling", "Code ranges", "Options")


def _no_violations(cls: type[RuleBase], context: object) -> tuple[rule_violations.RuleViolation, ...]:
    """Return no violations for metadata-only sample rules."""
    del cls, context
    return ()


class PDFSampleCategory(RuleCategoryBase):
    meta = RuleCategoryMetadata(prefix="PDF", name="sample PDF", url=None)


class PCFSampleCategory(RuleCategoryBase):
    meta = RuleCategoryMetadata(prefix="PCF", name="sample PCF", url=None)


class PDFSpecificityCategory(RuleCategoryBase):
    meta = RuleCategoryMetadata(prefix="PDF", name="specificity PDF", url=None)


class PDFFixAvailabilityCategory(RuleCategoryBase):
    meta = RuleCategoryMetadata(prefix="PDF", name="fix availability PDF", url=None)


class TSTSettingEffectCategory(RuleCategoryBase):
    meta = RuleCategoryMetadata(prefix="TST", name="setting effects", url=None)


class TSTIncompatibilityCategory(RuleCategoryBase):
    meta = RuleCategoryMetadata(prefix="TST", name="incompatibilities", url=None)


class PDF101SampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF101"),
        name="docstring-reflow",
        message="Docstring chunk needs reflow",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class PDF110SampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF110"),
        name="summary-too-long",
        message="Docstring summary does not fit on one line",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class PDF142SampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF142"),
        name="specific-rule",
        message="Specific rule",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class PDF150SampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF150"),
        name="sibling-rule",
        message="Sibling rule",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class PDF160SometimesFixableSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF160"),
        name="sometimes-fixable-rule",
        message="Sometimes fixable rule",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class PDF170UsuallyFixableSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF170"),
        name="usually-fixable-rule",
        message="Usually fixable rule",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class PCF001SampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PCF001"),
        name="comment-reflow-required",
        message="Comment chunk needs reflow",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class TST001IgnoredSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("TST001"),
        name="ignored-by-setting",
        message="Ignored by setting",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),)),),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class TST002DisabledSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("TST002"),
        name="disabled-by-setting",
        message="Disabled by setting",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=(DocstringConvention.GOOGLE,)),)),
            RuleSettingEffects(setting="docstring_parse_tables", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(False,)),)),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class TST001FirstIncompatibleSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("TST001"),
        name="first-incompatible",
        message="First incompatible rule",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),)),),
        incompatible_with=(RuleCode("TST002"), RuleCode("TST004")),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class TST002SecondIncompatibleSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("TST002"),
        name="second-incompatible",
        message="Second incompatible rule",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(RuleCode("TST001"), RuleCode("TST003")),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class TST003ThirdIncompatibleSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("TST003"),
        name="third-incompatible",
        message="Third incompatible rule",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(RuleCode("TST002"), RuleCode("TST004")),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


class TST004FourthIncompatibleSampleRule(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("TST004"),
        name="fourth-incompatible",
        message="Fourth incompatible rule",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(RuleCode("TST001"), RuleCode("TST003")),
        check_kind=RuleCheckKind.STANDARD,
    )
    violations = classmethod(_no_violations)


rule_registration.register_rule_to(PDFSampleCategory)(PDF101SampleRule)
rule_registration.register_rule_to(PDFSampleCategory)(PDF110SampleRule)
rule_registration.register_rule_to(PCFSampleCategory)(PCF001SampleRule)
rule_registration.register_rule_to(PDFSpecificityCategory)(PDF142SampleRule)
rule_registration.register_rule_to(PDFSpecificityCategory)(PDF150SampleRule)
rule_registration.register_rule_to(PDFFixAvailabilityCategory)(PDF110SampleRule)
rule_registration.register_rule_to(PDFFixAvailabilityCategory)(PDF160SometimesFixableSampleRule)
rule_registration.register_rule_to(PDFFixAvailabilityCategory)(PDF170UsuallyFixableSampleRule)
rule_registration.register_rule_to(TSTSettingEffectCategory)(TST001IgnoredSampleRule)
rule_registration.register_rule_to(TSTSettingEffectCategory)(TST002DisabledSampleRule)
rule_registration.register_rule_to(TSTIncompatibilityCategory)(TST001FirstIncompatibleSampleRule)
rule_registration.register_rule_to(TSTIncompatibilityCategory)(TST002SecondIncompatibleSampleRule)
rule_registration.register_rule_to(TSTIncompatibilityCategory)(TST003ThirdIncompatibleSampleRule)
rule_registration.register_rule_to(TSTIncompatibilityCategory)(TST004FourthIncompatibleSampleRule)


def sample_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for selector tests."""
    return rule_collection.RuleCollection((PDFSampleCategory, PCFSampleCategory))


def specificity_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for selector specificity tests."""
    return rule_collection.RuleCollection((PDFSpecificityCategory,))


def fix_availability_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for rule-level fix availability tests."""
    return rule_collection.RuleCollection((PDFFixAvailabilityCategory,))


def setting_effect_collection() -> rule_collection.RuleCollection:
    """Return a synthetic collection for setting-effect tests."""
    return rule_collection.RuleCollection((TSTSettingEffectCategory,))


def incompatibility_collection() -> rule_collection.RuleCollection:
    """Return a synthetic collection for rule-incompatibility tests."""
    return rule_collection.RuleCollection((TSTIncompatibilityCategory,))


def markdown_level_two_headings(markdown: str) -> tuple[str, ...]:
    """Return all level-two heading text from a Markdown document."""
    return tuple(line.removeprefix("## ") for line in markdown.splitlines() if line.startswith("## "))


def _ast_call_name(node: ast.expr) -> str:
    """Return a dotted best-effort call name for static rule-source checks."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _ast_call_name(node.value)
        return f"{owner}.{node.attr}" if owner else node.attr
    return ""


def _define_synthetic_standard_rule(name: str, violations_hook: object) -> None:
    """Define a synthetic standard rule class for runtime contract tests."""
    type(
        name,
        (RuleBase,),
        {
            "__module__": __name__,
            "meta": RuleMetadata(
                code=RuleCode("PDF999"),
                name="synthetic-standard-rule",
                message="Synthetic standard rule",
                fix_availability=FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            ),
            "violations": violations_hook,
        },
    )


def _ignored_docstring_conventions(rule: RuleMetadata) -> frozenset[DocstringConvention]:
    """Return docstring conventions that ignore a rule unless it is selected exactly."""
    return frozenset(convention for convention in DocstringConvention if rule.setting_effect("docstring_convention", convention) is RuleSettingEffect.IGNORED)


def _disabled_docstring_conventions(rule: RuleMetadata) -> frozenset[DocstringConvention]:
    """Return docstring conventions that disable a rule even when it is selected exactly."""
    return frozenset(convention for convention in DocstringConvention if rule.setting_effect("docstring_convention", convention) is RuleSettingEffect.DISABLED)


def _setting_effect_values(effects: tuple[RuleSettingEffects, ...]) -> dict[RuleSettingEffect, tuple[DocstringConvention, ...]]:
    """Return docstring convention values keyed by effect kind."""
    assert len(effects) == 1
    assert effects[0].setting == "docstring_convention"
    return {effect_values.effect: tuple(typing.cast("DocstringConvention", value) for value in effect_values.values) for effect_values in effects[0].effects}


def _builtin_rule_incompatibility_pairs() -> tuple[tuple[RuleCode, RuleCode], ...]:
    """Return built-in incompatible rule pairs ordered as the rule collection resolves them."""
    rule_order = {rule_class.meta.code: index for index, rule_class in enumerate(rule_collection.RULE_COLLECTION.rules)}
    checked_pairs: set[frozenset[RuleCode]] = set()
    ordered_pairs: list[tuple[RuleCode, RuleCode]] = []
    for rule_class in rule_collection.RULE_COLLECTION.rules:
        for incompatible_code in rule_class.meta.incompatible_with:
            pair = frozenset((rule_class.meta.code, incompatible_code))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)
            first_code, second_code = tuple(sorted(pair, key=rule_order.__getitem__))
            ordered_pairs.append((first_code, second_code))
    return tuple(ordered_pairs)


BUILTIN_RULE_INCOMPATIBILITY_PAIRS = _builtin_rule_incompatibility_pairs()
BUILTIN_RULE_INCOMPATIBILITY_CASES = tuple(pytest.param(first_code, second_code, id=f"{first_code}-{second_code}") for first_code, second_code in BUILTIN_RULE_INCOMPATIBILITY_PAIRS)
UNPARSED_CONVENTIONS = frozenset(docstring_conventions.UNPARSED_CONVENTIONS)
PARSED_CONVENTIONS = frozenset(docstring_conventions.PARSED_CONVENTIONS)
DOCSTRING_CONVENTION_CASES = tuple(pytest.param(convention, id=convention.value) for convention in DocstringConvention)
IGNORED_DOCSTRING_CONVENTION_CASES = tuple(
    pytest.param(rule_class.meta.code.tag, convention, id=f"{rule_class.meta.code.tag}-{convention.value}")
    for rule_class in rule_collection.RULE_COLLECTION.rules
    for convention in sorted(_ignored_docstring_conventions(rule_class.meta), key=lambda item: item.value)
)
DISABLED_DOCSTRING_CONVENTION_CASES = tuple(
    pytest.param(rule_class.meta.code.tag, convention, id=f"{rule_class.meta.code.tag}-{convention.value}")
    for rule_class in rule_collection.RULE_COLLECTION.rules
    for convention in sorted(_disabled_docstring_conventions(rule_class.meta), key=lambda item: item.value)
)
CONVENTION_OPT_IN_RULE_CODES = tuple(
    rule_class.meta.code.tag
    for rule_class in rule_collection.RULE_COLLECTION.rules
    if _disabled_docstring_conventions(rule_class.meta) | _ignored_docstring_conventions(rule_class.meta) == frozenset(DocstringConvention)
)


def _write(path: Path, text: str = "x = 1\n") -> None:
    """Write a UTF-8 test fixture file, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _active_rule_tags_for_path(profile: typing.Any, path: Path) -> tuple[str, ...]:
    """Return active sample rule tags for a path after per-file ignores."""
    selection = rules_selection.select_rules(profile.settings, collection=sample_collection(), profile=profile)
    return tuple(rule.rule.code.tag for rule in selection.for_path(str(path)))


def _valid_rule_package_files(package_name: str) -> dict[str, str]:
    """Return files for one valid synthetic rule definitions package."""
    return {
        "__init__.py": "",
        "PDF/__init__.py": "",
        "PDF/PDF.py": (
            "import pydocformatter.rules.registration as rule_registration\n"
            "from pydocformatter.rules.definition import RuleCategoryBase\n"
            "from pydocformatter.rules.models import RuleCategoryMetadata\n\n"
            "@rule_registration.register_rule_category\n"
            "class PDF(RuleCategoryBase):\n"
            "    meta = RuleCategoryMetadata(prefix='PDF', name='test PDF', url=None)\n"
        ),
        "PDF/PDF.md": "# test PDF (PDF)\n",
        "PDF/PDF101_test.py": (
            "import pydocformatter.rules.registration as rule_registration\n"
            "from pydocformatter.rules.definition import RuleBase\n"
            "from pydocformatter.rules.codes import RuleCode\n"
            "from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata\n"
            f"from {package_name}.PDF.PDF import PDF\n\n"
            "@rule_registration.register_rule_to(PDF)\n"
            "class PDF101Test(RuleBase):\n"
            "    meta = RuleMetadata(code=RuleCode('PDF101'), name='test', message='Test', fix_availability=FixAvailability.ALWAYS, stable_since='1.0.0', setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)\n"
            "    @classmethod\n"
            "    def violations(cls, context):\n"
            "        del cls, context\n"
            "        return ()\n"
        ),
        "PDF/PDF101_test.md": "# test (PDF101)\n",
    }


INVALID_RULE_PACKAGE_CASES = (
    "stray definitions module",
    "nested category package",
    "missing category module",
    "wrong category class name",
    "category metadata prefix mismatch",
    "unregistered category",
    "unexpected category module",
    "rule module without name suffix",
    "reserved rule module code",
    "multiple rule classes",
    "rule module code mismatch",
    "unregistered rule",
    "missing category documentation",
    "missing rule documentation",
    "orphan documentation",
)


def _invalid_rule_package_files(valid_files: dict[str, str], case: str) -> tuple[dict[str, str], str]:
    """Return mutated synthetic package files and expected registration error text."""
    if case == "stray definitions module":
        return {**valid_files, "stray.py": ""}, "must contain only category packages"
    if case == "nested category package":
        return {**valid_files, "PDF/nested/__init__.py": ""}, "must not contain nested packages"
    if case == "missing category module":
        return {path: content for path, content in valid_files.items() if path != "PDF/PDF.py"}, "must contain category module"
    if case == "wrong category class name":
        return {**valid_files, "PDF/PDF.py": valid_files["PDF/PDF.py"].replace("class PDF", "class WrongPDF")}, "exactly one RuleCategoryBase subclass named PDF"
    if case == "category metadata prefix mismatch":
        return {**valid_files, "PDF/PDF.py": valid_files["PDF/PDF.py"].replace("prefix='PDF'", "prefix='PCF'")}, "does not match package and module name"
    if case == "unregistered category":
        return {**valid_files, "PDF/PDF.py": valid_files["PDF/PDF.py"].replace("@rule_registration.register_rule_category\n", "")}, "is not registered with the rule registry"
    if case == "unexpected category module":
        return {**valid_files, "PDF/helper.py": "value = 1\n"}, "Unexpected module in rule category package"
    if case == "rule module without name suffix":
        return {**valid_files, "PDF/PDF100.py": ""}, "Unexpected module in rule category package"
    if case == "reserved rule module code":
        return {**valid_files, "PDF/ALL001_test.py": ""}, "Unexpected module in rule category package"
    if case == "multiple rule classes":
        return {
            **valid_files,
            "PDF/PDF101_test.py": valid_files["PDF/PDF101_test.py"]
            + "\nclass PDF100Test(RuleBase):\n    meta = RuleMetadata(code=RuleCode('PDF100'), name='test-two', message='Test two', fix_availability=FixAvailability.ALWAYS, stable_since='1.0.0', setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)\n    @classmethod\n    def violations(cls, context):\n        del cls, context\n        return ()\n",
        }, "must define exactly one RuleBase subclass"
    if case == "rule module code mismatch":
        return {**valid_files, "PDF/PDF101_test.py": valid_files["PDF/PDF101_test.py"].replace("RuleCode('PDF101')", "RuleCode('PDF100')")}, "does not match rule code"
    if case == "unregistered rule":
        return {**valid_files, "PDF/PDF101_test.py": valid_files["PDF/PDF101_test.py"].replace("@rule_registration.register_rule_to(PDF)\n", "")}, "is not registered with category PDF"
    if case == "missing category documentation":
        return {path: content for path, content in valid_files.items() if path != "PDF/PDF.md"}, "missing adjacent documentation PDF.md"
    if case == "missing rule documentation":
        return {path: content for path, content in valid_files.items() if path != "PDF/PDF101_test.md"}, "missing adjacent documentation PDF101_test.md"
    if case == "orphan documentation":
        return {**valid_files, "PDF/PDF999_orphan.md": "# orphan\n"}, "contains orphan Markdown files"
    raise AssertionError(f"Unknown invalid rule package case: {case}")


def _import_synthetic_rule_package(files: dict[str, str]) -> None:
    """Import a synthetic rule package through the production loader."""
    package_name = "synthetic_rule_definitions"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        package_root = root / package_name
        for relative_path, content in files.items():
            _write(package_root / relative_path, content)

        previous_registry = rule_registration.DEFAULT_RULE_REGISTRY
        rule_registration.DEFAULT_RULE_REGISTRY = rule_registration.RuleRegistry()
        sys.path.insert(0, str(root))
        importlib.invalidate_caches()
        try:
            package = importlib.import_module(package_name)
            rule_collection.import_package_rule_categories(package=package)
        finally:
            rule_registration.DEFAULT_RULE_REGISTRY = previous_registry
            sys.path.remove(str(root))
            for module_name in tuple(sys.modules):
                if module_name == package_name or module_name.startswith(f"{package_name}.") or module_name == "synthetic_rule_support":
                    del sys.modules[module_name]
            importlib.invalidate_caches()


def test_default_rule_collection_is_collected_on_import() -> None:
    collection = rule_collection.RULE_COLLECTION
    definition_module_names = tuple(module.name for module in pkgutil.walk_packages(path=rule_definitions.__path__, prefix=f"{rule_definitions.__name__}.") if not module.ispkg)
    discovered_category_classes: list[type[RuleCategoryBase]] = []
    discovered_rule_classes: list[type[RuleBase]] = []

    for module_name in definition_module_names:
        module = importlib.import_module(module_name)
        module_category_classes = [
            category_class for _, category_class in inspect.getmembers(module, inspect.isclass) if category_class.__module__ == module.__name__ and issubclass(category_class, RuleCategoryBase)
        ]
        module_rule_classes = [rule_class for _, rule_class in inspect.getmembers(module, inspect.isclass) if rule_class.__module__ == module.__name__ and issubclass(rule_class, RuleBase)]
        assert len(module_category_classes) + len(module_rule_classes) == 1
        discovered_category_classes.extend(module_category_classes)
        discovered_rule_classes.extend(module_rule_classes)

    assert collection.categories == rule_collection.RuleCollection(discovered_category_classes).categories
    assert collection.rules == tuple(sorted(discovered_rule_classes, key=lambda rule_class: rule_class.meta.code))
    assert tuple(category.meta.prefix for category in collection.categories) == ("PCF", "PDF")
    assert rule_documentation.undocumented_rules(collection) == ()
    assert rule_documentation.undocumented_rule_categories(collection) == ()
    template_root = Path(__file__).parents[1] / "src" / "pydocformatter" / "rules" / "templates"
    assert (template_root / "rule_template.md").is_file()
    assert (template_root / "rule_category_template.md").is_file()
    for category_class in collection.categories:
        explanation = rule_documentation.load_rule_explanation(category_class)
        assert explanation.startswith(f"# {category_class.meta.name} ({category_class.meta.prefix})\n\n")
        assert markdown_level_two_headings(explanation) == EXPECTED_RULE_CATEGORY_DOCUMENTATION_SECTIONS
    for rule_class in collection.rules:
        explanation = rule_documentation.load_rule_explanation(rule_class)
        assert explanation.startswith(f"# {rule_class.meta.name} ({rule_class.meta.code})\n\n")
        assert f"\n\n{rule_documentation.rule_fix_text(rule_class.meta)}\n\n" in explanation
        assert markdown_level_two_headings(explanation) == EXPECTED_RULE_DOCUMENTATION_SECTIONS


def test_every_builtin_rule_intentionally_declares_file_local_cache_behavior() -> None:
    assert rule_collection.RULE_COLLECTION.rules
    for rule_class in rule_collection.RULE_COLLECTION.rules:
        assert isinstance(rule_class.meta.cache_behavior, rule_models.RuleCacheBehavior)
        assert rule_class.meta.cache_behavior is rule_models.RuleCacheBehavior.FILE_LOCAL


def test_cacheable_rule_sources_have_no_advisory_external_dependency_markers() -> None:
    forbidden_modules = {"datetime", "http", "os", "pathlib", "random", "socket", "subprocess", "time", "urllib"}
    forbidden_calls = {"eval", "exec", "getenv", "open", "popen", "system", "urlopen"}
    source_roots = (Path(rule_definitions.__file__).parent, Path(rule_definitions.__file__).parent.parent / "definition_helpers")
    findings: list[str] = []
    for source_root in source_roots:
        for path in sorted(source_root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    findings.extend(f"{path}: imports {alias.name}" for alias in node.names if alias.name.split(".", 1)[0] in forbidden_modules)
                elif isinstance(node, ast.ImportFrom) and node.module is not None and node.module.split(".", 1)[0] in forbidden_modules:
                    findings.append(f"{path}: imports from {node.module}")
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                    findings.append(f"{path}: calls {node.func.id}")

    assert findings == []


@pytest.mark.parametrize("rule_class", rule_collection.RULE_COLLECTION.rules, ids=lambda rule_class: str(rule_class.meta.code))
def test_builtin_rule_file_and_class_names_match_rule_content(rule_class: type[RuleBase]) -> None:
    rule = rule_class.meta
    source_file = inspect.getsourcefile(rule_class)
    assert source_file is not None
    source_path = Path(source_file)
    expected_python_stem = f"{rule.code}_{rule.name.replace('-', '_')}"
    assert source_path.stem == expected_python_stem
    assert rule_class.__name__ == f"{rule.code}{''.join(part.capitalize() for part in rule.name.split('-'))}"

    heading = rule_documentation.load_rule_explanation(rule_class).splitlines()[0]
    heading_name, separator, heading_code = heading.removeprefix("# ").rpartition(" (")
    assert separator == " ("
    assert heading_code.endswith(")")
    expected_markdown_stem = f"{heading_code.removesuffix(')')}_{heading_name.replace('-', '_')}"
    assert source_path.with_suffix(".md").stem == expected_markdown_stem


@pytest.mark.parametrize(
    "rule_class", tuple(rule_class for rule_class in rule_collection.RULE_COLLECTION.rules if rule_class.meta.check_kind == RuleCheckKind.STANDARD), ids=lambda rule_class: str(rule_class.meta.code)
)
def test_standard_rules_define_violations_api(rule_class: type[RuleBase]) -> None:
    """Check that standard built-in rules define the canonical violation API."""
    assert "violations" in rule_class.__dict__


def test_builtin_rule_modules_use_violation_helpers() -> None:
    """Built-in rules and reusable rule helpers should not construct violation records directly."""
    source_root = Path(__file__).parents[1] / "src" / "pydocformatter" / "rules"
    paths = tuple(sorted((source_root / "definitions").glob("*/*.py"))) + tuple(sorted((source_root / "definition_helpers").glob("*.py")))
    forbidden: list[str] = []
    forbidden_imports_by_module = {"pydocformatter.rules.models": {"RuleFinding"}, "pydocformatter.rules.violations": {"RuleSourceFix", "RuleViolation"}}
    forbidden_suffixes = ("RuleFinding", "RuleViolation", "RuleSourceFix", "RuleSourceFix.from_change", "_finding_for_planned_source_change")
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                forbidden_names = forbidden_imports_by_module.get(node.module or "", set())
                forbidden.extend(f"{path.relative_to(source_root.parent.parent)}:{node.lineno}: import {node.module}.{alias.name}" for alias in node.names if alias.name in forbidden_names)
            elif isinstance(node, ast.Call):
                call_name = _ast_call_name(node.func)
                if call_name.endswith(forbidden_suffixes):
                    forbidden.append(f"{path.relative_to(source_root.parent.parent)}:{node.lineno}: {call_name}")

    assert forbidden == []


def test_rule_modules_import_before_collection_without_changing_default_collection() -> None:
    source_root = Path(__file__).parents[1] / "src"
    environment = {**os.environ, "PYTHONPATH": str(source_root)}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pydocformatter.rules.definitions.PCF.PCF import PCF\n"
                "from pydocformatter.rules.definitions.PDF.PDF101_docstring_reflow import PDF101DocstringReflow\n"
                "from pydocformatter.rules.definitions.PDF.PDF import PDF\n"
                "import sys\n"
                "assert 'pydocformatter.rules.collection' not in sys.modules\n"
                "import pydocformatter.rules.collection as rule_collection\n"
                "codes = {str(rule.meta.code) for rule in rule_collection.RULE_COLLECTION.rules}\n"
                "assert {'PCF001', 'PCF002', 'PDF000', 'PDF101', 'PDF203'} <= codes\n"
                "print(PCF.meta.prefix, PDF.meta.prefix)\n"
            ),
        ],
        check=True,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.stdout == "PCF PDF\n"


def test_rule_registry_collects_categories_and_rules() -> None:
    registry = rule_registration.RuleRegistry()

    class PDFTestCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    @rule_registration.register_rule_to(PDFTestCategory)
    class PDF999TestRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("PDF999"),
            name="test-rule",
            message="Test rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
        violations = classmethod(_no_violations)

    registry.register(PDFTestCategory)

    assert registry.category_classes == {PDFTestCategory}
    assert rule_collection.RuleCollection.from_registry(registry).categories == (PDFTestCategory,)
    assert rule_collection.RuleCollection.from_registry(registry).category_class == {"PDF": PDFTestCategory}
    assert rule_collection.RuleCollection.from_registry(registry).rules == (PDF999TestRule,)
    assert rule_collection.RuleCollection.from_registry(registry).rule_class == {RuleCode("PDF999"): PDF999TestRule}


def test_register_rule_category_decorator_collects_category_in_default_registry() -> None:
    previous_registry = rule_registration.DEFAULT_RULE_REGISTRY
    rule_registration.DEFAULT_RULE_REGISTRY = rule_registration.RuleRegistry()
    try:

        @rule_registration.register_rule_category
        class PDFTestCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

        collection = rule_collection.RuleCollection.from_registry(rule_registration.DEFAULT_RULE_REGISTRY)
    finally:
        rule_registration.DEFAULT_RULE_REGISTRY = previous_registry

    assert collection.categories == (PDFTestCategory,)


def test_import_package_rule_categories_imports_package_modules() -> None:
    rule_collection.import_package_rule_categories(package=rule_definitions)


@pytest.mark.parametrize("case", INVALID_RULE_PACKAGE_CASES, ids=lambda case: case.replace(" ", "-"))
def test_import_package_rule_categories_validates_package_structure_and_registration(case: str) -> None:
    package_name = "synthetic_rule_definitions"
    valid_files = _valid_rule_package_files(package_name)
    _import_synthetic_rule_package(valid_files)
    files, message = _invalid_rule_package_files(valid_files, case)

    with pytest.raises(rule_registration.RuleError, match=message):
        _import_synthetic_rule_package(files)


def test_import_package_rule_categories_rejects_registered_rules_outside_category_package() -> None:
    package_name = "synthetic_rule_definitions"
    files = _valid_rule_package_files(package_name)
    files["../synthetic_rule_support.py"] = (
        "from pydocformatter.rules.definition import RuleBase\n"
        "from pydocformatter.rules.codes import RuleCode\n"
        "from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata\n\n"
        "class PDF100External(RuleBase):\n"
        "    meta = RuleMetadata(code=RuleCode('PDF100'), name='external', message='External', fix_availability=FixAvailability.ALWAYS, stable_since='1.0.0', setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)\n"
        "    @classmethod\n"
        "    def violations(cls, context):\n"
        "        del cls, context\n"
        "        return ()\n"
    )
    files["PDF/PDF.py"] += "\nfrom synthetic_rule_support import PDF100External\nrule_registration.register_rule_to(PDF)(PDF100External)\n"

    with pytest.raises(rule_registration.RuleError, match="contains rules from outside package"):
        _import_synthetic_rule_package(files)


def test_import_package_rule_categories_rejects_registered_rules_without_rule_modules() -> None:
    package_name = "synthetic_rule_definitions"
    files = _valid_rule_package_files(package_name)
    files["PDF/__init__.py"] = (
        "from pydocformatter.rules.definition import RuleBase\n"
        "from pydocformatter.rules.codes import RuleCode\n"
        "from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata\n\n"
        "class PDF100PackageRule(RuleBase):\n"
        "    meta = RuleMetadata(code=RuleCode('PDF100'), name='package-rule', message='Package rule', fix_availability=FixAvailability.ALWAYS, stable_since='1.0.0', setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)\n"
        "    @classmethod\n"
        "    def violations(cls, context):\n"
        "        del cls, context\n"
        "        return ()\n"
    )
    files["PDF/PDF.py"] += f"\nfrom {package_name}.PDF import PDF100PackageRule\nrule_registration.register_rule_to(PDF)(PDF100PackageRule)\n"

    with pytest.raises(rule_registration.RuleError, match="registered rules without matching rule modules"):
        _import_synthetic_rule_package(files)


def test_register_rule_category_to_collects_category_in_bound_registry() -> None:
    registry = rule_registration.RuleRegistry()

    @rule_registration.register_rule_category_to(registry)
    class PDFTestCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    assert rule_collection.RuleCollection.from_registry(registry).categories == (PDFTestCategory,)


def test_rule_category_rejects_duplicate_rule_codes_from_different_classes() -> None:
    class PDFTestCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    @rule_registration.register_rule_to(PDFTestCategory)
    class PDF999FirstRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("PDF999"),
            name="first-rule",
            message="First rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
        violations = classmethod(_no_violations)

    with pytest.raises(rule_registration.RuleError, match="Duplicate rule code in category PDF: PDF999"):

        @rule_registration.register_rule_to(PDFTestCategory)
        class PDF999SecondRule(RuleBase):
            meta = RuleMetadata(
                code=RuleCode("PDF999"),
                name="second-rule",
                message="Second rule",
                fix_availability=FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )
            violations = classmethod(_no_violations)


def test_rule_category_allows_registering_the_same_rule_class_twice() -> None:
    class PDFTestCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    class PDF999TestRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("PDF999"),
            name="test-rule",
            message="Test rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
        violations = classmethod(_no_violations)

    rule_registration.register_rule_to(PDFTestCategory)(PDF999TestRule)
    rule_registration.register_rule_to(PDFTestCategory)(PDF999TestRule)

    assert PDFTestCategory.ordered_rules() == (PDF999TestRule,)


def test_rule_collection_allows_the_same_category_class_twice() -> None:
    class PDFTestCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    collection = rule_collection.RuleCollection((PDFTestCategory, PDFTestCategory))

    assert collection.categories == (PDFTestCategory,)


def test_rule_registry_and_collection_reject_direct_rules() -> None:
    registry = rule_registration.RuleRegistry()

    with pytest.raises(rule_registration.RuleError, match="Registered rule category must inherit RuleCategoryBase"):
        registry.register(typing.cast("type[RuleCategoryBase]", PDF101SampleRule))
    with pytest.raises(rule_registration.RuleError, match="Collected rule category must inherit RuleCategoryBase"):
        rule_collection.RuleCollection((typing.cast("type[RuleCategoryBase]", PDF101SampleRule),))


def test_rule_registry_is_frozen_but_keeps_mutable_registration_state() -> None:
    registry = rule_registration.RuleRegistry()

    class PDFTestCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    registry.register(PDFTestCategory)

    with pytest.raises(dataclasses.FrozenInstanceError):
        registry.category_classes = set()  # ty: ignore[invalid-assignment]
    assert rule_collection.RuleCollection.from_registry(registry).categories == (PDFTestCategory,)


def test_rule_registries_are_isolated() -> None:
    default_registry = rule_registration.RuleRegistry()
    isolated_registry = rule_registration.RuleRegistry()

    @rule_registration.register_rule_category_to(default_registry)
    class PDFDefaultCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="default PDF", url=None)

    @rule_registration.register_rule_category_to(isolated_registry)
    class PDFIsolatedCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="isolated PDF", url=None)

    assert rule_collection.RuleCollection.from_registry(default_registry).categories == (PDFDefaultCategory,)
    assert rule_collection.RuleCollection.from_registry(isolated_registry).categories == (PDFIsolatedCategory,)


def test_rule_metadata_derives_prefix_and_number_from_code() -> None:
    rule = RuleMetadata(
        code=RuleCode("PDF001"),
        name="docstring-quote-style",
        message="Docstring should use triple double quotes",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    assert tuple(field.name for field in dataclasses.fields(RuleCode)) == ("tag", "prefix", "number_str", "number")
    assert str(rule.code) == "PDF001"
    assert rule.code.tag == "PDF001"
    assert rule.code.prefix == "PDF"
    assert rule.code.number_str == "001"
    assert rule.code.number == 1
    assert RuleCode.is_valid_tag("PDF001")
    assert not RuleCode.is_valid_tag("001")
    assert not RuleCode.is_valid_tag("ALL001")
    assert not hasattr(rule_models, "valid_rule_code_tag")
    assert not hasattr(rule_models, "split_rule_code")
    assert rule.stable_since == "1.0.0"
    assert tuple(field.name for field in dataclasses.fields(RuleMetadata)) == (
        "code",
        "name",
        "message",
        "fix_availability",
        "stable_since",
        "setting_effects",
        "incompatible_with",
        "check_kind",
        "cache_behavior",
    )
    assert rule.cache_behavior is rule_models.RuleCacheBehavior.UNCACHEABLE
    assert not hasattr(RuleMetadata, "file_local")
    assert all(field.default is dataclasses.MISSING for field in dataclasses.fields(RuleMetadata)[:-1])
    assert dataclasses.fields(RuleMetadata)[-1].default is rule_models.RuleCacheBehavior.UNCACHEABLE
    assert all(field.default_factory is dataclasses.MISSING for field in dataclasses.fields(RuleMetadata))
    assert rule.check_kind == RuleCheckKind.STANDARD
    assert rule.setting_effects == ()
    assert rule.incompatible_with == ()
    assert isinstance(hash(TST001IgnoredSampleRule.meta), int)
    assert rule_codes.RuleCode is RuleCode
    assert not hasattr(rule_models, "RuleSelector")
    assert rule_documentation.rule_fix_text(rule) == "Fix is always available."
    assert (
        rule_documentation.rule_fix_text(
            RuleMetadata(
                code=RuleCode("PDF999"),
                name="usually-rule",
                message="Usually rule",
                fix_availability=FixAvailability.USUALLY,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )
        )
        == "Fix is usually available."
    )
    assert (
        rule_documentation.rule_fix_text(
            RuleMetadata(
                code=RuleCode("PDF999"),
                name="sometimes-rule",
                message="Sometimes rule",
                fix_availability=FixAvailability.SOMETIMES,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )
        )
        == "Fix is sometimes available."
    )
    assert str(FixAvailability.USUALLY) == "Usually"
    assert str(FixAvailability.SOMETIMES) == "Sometimes"
    assert not hasattr(rule, "matches_selector")
    assert not hasattr(rule, "matches_selector_parts")


def test_rule_metadata_resolves_setting_effects_with_disabled_precedence() -> None:
    rule = dataclasses.replace(
        PDF101SampleRule.meta,
        setting_effects=(
            RuleSettingEffects(setting="sample_setting", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=("ignored", "both")),)),
            RuleSettingEffects(setting="sample_setting", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=("disabled", "both")),)),
        ),
    )

    assert rule.setting_effect("other_setting", "both") is None
    assert rule.setting_effect("sample_setting", "other") is None
    assert rule.setting_effect("sample_setting", "ignored") is RuleSettingEffect.IGNORED
    assert rule.setting_effect("sample_setting", "disabled") is RuleSettingEffect.DISABLED
    assert rule.setting_effect("sample_setting", "both") is RuleSettingEffect.DISABLED


def test_rule_selector_selects_code() -> None:
    code = RuleCode("PDF101")

    selector = RuleSelector("PDF10")

    assert tuple(field.name for field in dataclasses.fields(RuleSelector)) == ("tag", "prefix", "number_str")
    assert str(selector) == "PDF10"
    assert selector.tag == "PDF10"
    assert selector.prefix == "PDF"
    assert selector.number_str == "10"
    assert RuleSelector.is_valid_tag("ALL")
    assert RuleSelector.is_valid_tag("PDF10")
    assert not RuleSelector.is_valid_tag("bad")
    assert not RuleSelector.is_valid_tag("ALL1")
    assert not hasattr(rule_models, "rule_selector_is_valid")
    assert not hasattr(rule_models, "split_rule_selector")
    assert RuleSelector("ALL").selects_code(code)
    assert RuleSelector("PDF").selects_code(code)
    assert RuleSelector("PDF1").selects_code(code)
    assert selector.selects_code(code)
    assert not RuleSelector("PDF203").selects_code(code)
    assert not RuleSelector("P").selects_code(code)


def test_rule_metadata_validates_rule_code() -> None:
    with pytest.raises(ValueError, match="Invalid rule code: bad"):
        RuleCode("bad")
    with pytest.raises(ValueError, match="Invalid rule code: ALL001"):
        RuleCode("ALL001")
    with pytest.raises(TypeError, match="Expected RuleCode, got str"):
        RuleMetadata(
            code=typing.cast("typing.Any", "bad"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
    with pytest.raises(TypeError, match="Expected FixAvailability, got str"):
        RuleMetadata(
            code=RuleCode("PDF101"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=typing.cast("typing.Any", "Always"),
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
    with pytest.raises(TypeError, match="Expected RuleCheckKind, got str"):
        RuleMetadata(
            code=RuleCode("PDF101"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=typing.cast("typing.Any", "standard"),
        )
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'stable_since'"):
        RuleMetadata(code=RuleCode("PDF101"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)  # ty: ignore[missing-argument]
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'setting_effects'"):
        RuleMetadata(
            code=RuleCode("PDF101"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, stable_since="1.0.0", incompatible_with=(), check_kind=RuleCheckKind.STANDARD
        )  # ty: ignore[missing-argument]
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'incompatible_with'"):
        RuleMetadata(code=RuleCode("PDF101"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, stable_since="1.0.0", setting_effects=(), check_kind=RuleCheckKind.STANDARD)  # ty: ignore[missing-argument]
    with pytest.raises(ValueError, match="PDF101: Stable version must not be empty"):
        RuleMetadata(
            code=RuleCode("PDF101"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
    with pytest.raises(ValueError, match="Rule setting name must not be empty"):
        RuleSettingEffects(setting="", effects=())
    with pytest.raises(TypeError, match="Expected RuleSettingEffect, got str"):
        RuleSettingEffectValues(effect=typing.cast("typing.Any", "Ignored"), values=(True,))
    with pytest.raises(ValueError, match="triggering values must not be empty"):
        RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=())
    with pytest.raises(TypeError, match="triggering values must be a tuple"):
        RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=typing.cast("typing.Any", [True]))
    with pytest.raises(TypeError, match="triggering values must be hashable"):
        RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(typing.cast("typing.Any", []),))
    with pytest.raises(TypeError, match="must contain RuleSettingEffectValues instances"):
        RuleSettingEffects(setting="docstring_convention", effects=typing.cast("typing.Any", ("bad",)))
    with pytest.raises(TypeError, match="Rule setting effects must contain RuleSettingEffects instances"):
        RuleMetadata(
            code=RuleCode("PDF101"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=typing.cast("typing.Any", ("bad",)),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
    with pytest.raises(TypeError, match="Incompatible rule codes must be a tuple"):
        RuleMetadata(
            code=RuleCode("PDF101"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=typing.cast("typing.Any", [RuleCode("PDF100")]),
            check_kind=RuleCheckKind.STANDARD,
        )
    with pytest.raises(TypeError, match="Incompatible rule codes must contain RuleCode instances"):
        RuleMetadata(
            code=RuleCode("PDF101"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=typing.cast("typing.Any", ("PDF100",)),
            check_kind=RuleCheckKind.STANDARD,
        )
    with pytest.raises(ValueError, match="Incompatible rule codes must not contain duplicates"):
        RuleMetadata(
            code=RuleCode("PDF101"),
            name="bad-rule",
            message="Bad rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(RuleCode("PDF100"), RuleCode("PDF100")),
            check_kind=RuleCheckKind.STANDARD,
        )


def test_rule_selector_validates_tag() -> None:
    with pytest.raises(ValueError, match="Invalid rule selector: bad"):
        RuleSelector("bad")
    with pytest.raises(ValueError, match="Invalid rule selector: ALL1"):
        RuleSelector("ALL1")


def test_rule_base_requires_subclass_metadata() -> None:
    with pytest.raises(TypeError, match="MissingMetaRule must define RuleMetadata as 'meta'"):

        class MissingMetaRule(RuleBase):
            pass


def test_rule_base_rejects_non_metadata_subclass_metadata() -> None:
    with pytest.raises(TypeError, match=re.escape("InvalidMetaRule.meta must be a RuleMetadata instance")):

        class InvalidMetaRule(RuleBase):
            meta: typing.ClassVar[typing.Any] = None


def test_rule_base_rejects_standard_rule_without_violations() -> None:
    with pytest.raises(TypeError, match="MissingViolationsRule must define violations"):

        class MissingViolationsRule(RuleBase):
            meta = RuleMetadata(
                code=RuleCode("PDF999"),
                name="missing-violations",
                message="Missing violations",
                fix_availability=FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )


def test_rule_base_rejects_non_classmethod_violations_hook() -> None:
    def instance_violations(self: object, context: object) -> tuple[object, ...]:
        del self, context
        return ()

    with pytest.raises(TypeError, match="InstanceViolationsRule\\.violations must be a @classmethod"):
        _define_synthetic_standard_rule("InstanceViolationsRule", instance_violations)

    def static_violations(context: object) -> tuple[object, ...]:
        del context
        return ()

    with pytest.raises(TypeError, match="StaticViolationsRule\\.violations must be a @classmethod"):
        _define_synthetic_standard_rule("StaticViolationsRule", staticmethod(static_violations))


def test_rule_base_rejects_bad_violations_signature() -> None:
    def extra_argument_violations(cls: type[RuleBase], context: object, extra: object) -> tuple[object, ...]:
        del cls, context, extra
        return ()

    with pytest.raises(TypeError, match="ExtraArgumentRule\\.violations must accept exactly one required positional argument named context"):
        _define_synthetic_standard_rule("ExtraArgumentRule", classmethod(extra_argument_violations))

    def wrong_context_name_violations(cls: type[RuleBase], node: object) -> tuple[object, ...]:
        del cls, node
        return ()

    with pytest.raises(TypeError, match="WrongContextNameRule\\.violations must accept exactly one required positional argument named context"):
        _define_synthetic_standard_rule("WrongContextNameRule", classmethod(wrong_context_name_violations))

    def optional_argument_violations(cls: type[RuleBase], context: object, extra: object | None = None) -> tuple[object, ...]:
        del cls, context, extra
        return ()

    with pytest.raises(TypeError, match="OptionalArgumentRule\\.violations must accept exactly one required positional argument named context"):
        _define_synthetic_standard_rule("OptionalArgumentRule", classmethod(optional_argument_violations))


def test_rule_base_rejects_noncallable_classmethod_violations_hook() -> None:
    with pytest.raises(TypeError, match="NonCallableViolationsRule\\.violations must be callable"):
        _define_synthetic_standard_rule("NonCallableViolationsRule", classmethod(typing.cast("typing.Any", None)))


def test_rule_base_allows_suppression_audit_rule_without_violations() -> None:
    class SuppressionAuditRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("PDF999"),
            name="suppression-audit",
            message="Suppression audit",
            fix_availability=FixAvailability.NEVER,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.SUPPRESSION_AUDIT,
        )

    assert SuppressionAuditRule.violations(typing.cast("typing.Any", object())) == ()


def test_rule_category_metadata_and_base_validate_definitions() -> None:
    metadata = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    class PDFTestCategory(RuleCategoryBase):
        meta = metadata

    assert tuple(field.name for field in dataclasses.fields(RuleCategoryMetadata)) == ("prefix", "name", "url")
    assert all(field.default is dataclasses.MISSING for field in dataclasses.fields(RuleCategoryMetadata))
    assert (metadata.prefix, metadata.name, metadata.url) == ("PDF", "test PDF", None)
    assert (PDFTestCategory.prefix, PDFTestCategory.name, PDFTestCategory.url) == ("PDF", "test PDF", None)
    assert (PDFTestCategory().prefix, PDFTestCategory().name, PDFTestCategory().url) == ("PDF", "test PDF", None)
    with pytest.raises(ValueError, match="Invalid rule category prefix: bad"):
        RuleCategoryMetadata(prefix="bad", name="bad", url=None)
    with pytest.raises(ValueError, match="PDF: Rule category name must not be empty"):
        RuleCategoryMetadata(prefix="PDF", name="", url=None)
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'url'"):
        RuleCategoryMetadata(prefix="PDF", name="test PDF")  # ty: ignore[missing-argument]
    with pytest.raises(TypeError, match="MissingMetaCategory must define RuleCategoryMetadata as 'meta'"):

        class MissingMetaCategory(RuleCategoryBase):
            pass

    with pytest.raises(TypeError, match=re.escape("InvalidMetaCategory.meta must be a RuleCategoryMetadata instance")):

        class InvalidMetaCategory(RuleCategoryBase):
            meta: typing.ClassVar[typing.Any] = None


def test_rule_category_rejects_rule_with_different_prefix() -> None:
    class PDFTestCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

    with pytest.raises(rule_registration.RuleError, match="Rule category must inherit RuleCategoryBase"):
        rule_registration.register_rule_to(typing.cast("type[RuleCategoryBase]", object))
    with pytest.raises(rule_registration.RuleError, match="Registered rule must inherit RuleBase"):
        rule_registration.register_rule_to(PDFTestCategory)(typing.cast("type[RuleBase]", object))
    with pytest.raises(rule_registration.RuleError, match="Rule code prefix 'PCF' does not match rule category prefix 'PDF'"):
        rule_registration.register_rule_to(PDFTestCategory)(PCF001SampleRule)


def test_rule_collection_rejects_duplicate_category_prefixes() -> None:
    class PDFFirstCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="first PDF", url=None)

    class PDFSecondCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="second PDF", url=None)

    with pytest.raises(rule_registration.RuleError, match="Duplicate rule category prefix: PDF"):
        rule_collection.RuleCollection((PDFFirstCategory, PDFSecondCategory))


def test_rule_collection_validates_rule_incompatibilities() -> None:
    class TSTSelfCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="TST", name="self incompatible", url=None)

    @rule_registration.register_rule_to(TSTSelfCategory)
    class TST001SelfRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("TST001"),
            name="self-incompatible",
            message="Self incompatible",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(RuleCode("TST001"),),
            check_kind=RuleCheckKind.STANDARD,
        )
        violations = classmethod(_no_violations)

    with pytest.raises(rule_registration.RuleError, match="Rule TST001 cannot be incompatible with itself"):
        rule_collection.RuleCollection((TSTSelfCategory,))

    class TSTUnknownCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="TST", name="unknown incompatible", url=None)

    @rule_registration.register_rule_to(TSTUnknownCategory)
    class TST001UnknownRule(RuleBase):
        meta = dataclasses.replace(TST001SelfRule.meta, incompatible_with=(RuleCode("TST999"),))
        violations = classmethod(_no_violations)

    with pytest.raises(rule_registration.RuleError, match="Rule TST001 is incompatible with unknown rule code TST999"):
        rule_collection.RuleCollection((TSTUnknownCategory,))

    class TSTAsymmetricCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="TST", name="asymmetric incompatibility", url=None)

    @rule_registration.register_rule_to(TSTAsymmetricCategory)
    class TST001AsymmetricRule(RuleBase):
        meta = dataclasses.replace(TST001SelfRule.meta, incompatible_with=(RuleCode("TST002"),))
        violations = classmethod(_no_violations)

    @rule_registration.register_rule_to(TSTAsymmetricCategory)
    class TST002AsymmetricRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("TST002"),
            name="asymmetric-peer",
            message="Asymmetric peer",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
        violations = classmethod(_no_violations)

    with pytest.raises(rule_registration.RuleError, match="Rule incompatibility between TST001 and TST002 must be declared by both rules"):
        rule_collection.RuleCollection((TSTAsymmetricCategory,))


def test_rule_base_class_properties_redirect_to_metadata() -> None:
    class PDF999TestRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("PDF999"),
            name="test-rule",
            message="Test rule",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
        violations = classmethod(_no_violations)

    rule = PDF999TestRule()

    assert (
        PDF999TestRule.code,
        PDF999TestRule.prefix,
        PDF999TestRule.number_str,
        PDF999TestRule.number,
        PDF999TestRule.name,
        PDF999TestRule.message,
        PDF999TestRule.fix_availability,
        PDF999TestRule.setting_effects,
        PDF999TestRule.incompatible_with,
    ) == ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", FixAvailability.ALWAYS, (), ())
    assert PDF999TestRule.stable_since == "1.0.0"
    assert (rule.code, rule.prefix, rule.number_str, rule.number, rule.name, rule.message, rule.fix_availability, rule.stable_since, rule.setting_effects, rule.incompatible_with) == (
        "PDF999",
        "PDF",
        "999",
        999,
        "test-rule",
        "Test rule",
        FixAvailability.ALWAYS,
        "1.0.0",
        (),
        (),
    )


def test_selectors_must_use_complete_rule_prefixes() -> None:
    collection = sample_collection()

    assert collection.matching_rules_exist(RuleSelector("ALL"))
    assert collection.matching_rules_exist(RuleSelector("PDF"))
    assert collection.matching_rules_exist(RuleSelector("PDF1"))
    assert collection.matching_rules_exist(RuleSelector("PDF10"))
    assert not collection.matching_rules_exist(RuleSelector("PDF108"))
    assert not collection.matching_rules_exist(RuleSelector("R"))
    assert not collection.matching_rules_exist(RuleSelector("P"))
    assert not collection.matching_rules_exist(RuleSelector("RD"))


def test_rule_collection_orders_rules_and_rule_class_index_the_same_way() -> None:
    class PDFReverseRegistrationCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="PDF", name="reverse PDF", url=None)

    rule_registration.register_rule_to(PDFReverseRegistrationCategory)(PDF110SampleRule)
    rule_registration.register_rule_to(PDFReverseRegistrationCategory)(PDF101SampleRule)
    collection = sample_collection()

    assert collection.categories == (PCFSampleCategory, PDFSampleCategory)
    assert tuple(collection.category_class.values()) == collection.categories
    assert collection.rules == (PCF001SampleRule, PDF101SampleRule, PDF110SampleRule)
    assert tuple(collection.rule_class.values()) == collection.rules
    assert PCFSampleCategory.ordered_rules() == (PCF001SampleRule,)
    assert PDFSampleCategory.ordered_rules() == (PDF101SampleRule, PDF110SampleRule)
    assert tuple(PDFSampleCategory.ordered_code_class_map().values()) == PDFSampleCategory.ordered_rules()
    assert PDFReverseRegistrationCategory.ordered_rules() == (PDF101SampleRule, PDF110SampleRule)


def test_rule_collection_matching_rules_returns_rule_classes() -> None:
    collection = sample_collection()

    assert collection.matching_rules(RuleSelector("PDF")) == (PDF101SampleRule, PDF110SampleRule)


def test_builtin_rule_setting_effect_matrix() -> None:
    for rule_class in rule_collection.RULE_COLLECTION.rules:
        for setting_effects in rule_class.meta.setting_effects:
            if setting_effects.setting == "docstring_convention":
                for effect_values in setting_effects.effects:
                    assert effect_values.effect in {RuleSettingEffect.IGNORED, RuleSettingEffect.DISABLED}
                    for value in effect_values.values:
                        assert isinstance(value, DocstringConvention)

    assert any(_disabled_docstring_conventions(rule_class.meta) for rule_class in rule_collection.RULE_COLLECTION.rules)
    assert (
        tuple(
            rule_class.meta.code.tag
            for rule_class in rule_collection.RULE_COLLECTION.rules
            if rule_class.meta.code.prefix == "PCF" and any(setting_effects.setting == "docstring_convention" for setting_effects in rule_class.meta.setting_effects)
        )
        == ()
    )


def test_docstring_convention_setting_effect_helper_builds_expected_effects() -> None:
    disabled_only = docstring_conventions.convention_setting_effects(disabled=(DocstringConvention.NONE,))
    ignored_only = docstring_conventions.convention_setting_effects(ignored=(DocstringConvention.GOOGLE,))
    mixed = docstring_conventions.convention_setting_effects(disabled=(DocstringConvention.NONE,), ignored=(DocstringConvention.GOOGLE,))

    assert docstring_conventions.convention_setting_effects() == ()
    assert _setting_effect_values(disabled_only) == {RuleSettingEffect.DISABLED: (DocstringConvention.NONE,)}
    assert _setting_effect_values(ignored_only) == {RuleSettingEffect.IGNORED: (DocstringConvention.GOOGLE,)}
    assert _setting_effect_values(mixed) == {RuleSettingEffect.DISABLED: (DocstringConvention.NONE,), RuleSettingEffect.IGNORED: (DocstringConvention.GOOGLE,)}


def test_typed_entry_rule_metadata_uses_disabled_unparsed_conventions() -> None:
    supported = typed_entry_rules.metadata("PDF900", "sample-supported", "Sample", convention_opt_in=False)
    convention_opt_in = typed_entry_rules.metadata("PDF901", "sample-convention-opt-in", "Sample", convention_opt_in=True)

    assert _disabled_docstring_conventions(supported) == UNPARSED_CONVENTIONS
    assert _ignored_docstring_conventions(supported) == frozenset()
    assert _disabled_docstring_conventions(convention_opt_in) == UNPARSED_CONVENTIONS
    assert _ignored_docstring_conventions(convention_opt_in) == PARSED_CONVENTIONS


def test_builtin_rule_incompatibilities_are_declared() -> None:
    assert BUILTIN_RULE_INCOMPATIBILITY_PAIRS


@pytest.mark.parametrize("convention", DOCSTRING_CONVENTION_CASES)
def test_builtin_docstring_convention_broad_profiles_are_conflict_free(convention: DocstringConvention) -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("ALL",), docstring_convention=convention))
    selected_codes = frozenset(rule.rule.code for rule in selection.rules)

    assert selection.errors == ()
    for first_code, second_code in BUILTIN_RULE_INCOMPATIBILITY_PAIRS:
        assert not {first_code, second_code} <= selected_codes


@pytest.mark.parametrize(("first_code", "second_code"), BUILTIN_RULE_INCOMPATIBILITY_CASES)
def test_builtin_rule_incompatibilities_resolve_pairwise(first_code: RuleCode, second_code: RuleCode) -> None:
    selection = rules_selection.select_rules(CheckSettings(select=(first_code.tag, second_code.tag), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(rule.rule.code for rule in selection.rules) == (first_code,)
    assert selection.errors == (f"Selected rule {second_code} is incompatible with earlier selected rule {first_code}; {second_code} has been disabled",)


def test_builtin_docstring_convention_opt_in_rules_are_declared_and_separate_from_require_explicit() -> None:
    require_explicit_codes = frozenset(CheckSettings().require_explicit)

    assert CONVENTION_OPT_IN_RULE_CODES
    assert not require_explicit_codes.intersection(CONVENTION_OPT_IN_RULE_CODES)
    for rule_class in rule_collection.RULE_COLLECTION.rules:
        if rule_class.meta.code.tag in CONVENTION_OPT_IN_RULE_CODES:
            assert _ignored_docstring_conventions(rule_class.meta)


@pytest.mark.parametrize(("code", "convention"), IGNORED_DOCSTRING_CONVENTION_CASES)
def test_builtin_ignored_docstring_convention_rules_require_exact_selection(code: str, convention: DocstringConvention) -> None:
    broad_selection = rules_selection.select_rules(CheckSettings(select=("ALL",), docstring_convention=convention))
    exact_selection = rules_selection.select_rules(CheckSettings(select=(code,), docstring_convention=convention))
    exact_extension = rules_selection.select_rules(CheckSettings(select=("ALL",), extend_select=(code,), docstring_convention=convention))

    assert code not in tuple(rule.rule.code.tag for rule in broad_selection.rules)
    assert code in tuple(rule.rule.code.tag for rule in exact_selection.rules)
    assert code in tuple(rule.rule.code.tag for rule in exact_extension.rules)
    assert exact_extension.errors == ()


@pytest.mark.parametrize(("code", "convention"), DISABLED_DOCSTRING_CONVENTION_CASES)
def test_builtin_disabled_docstring_convention_rules_are_not_exactly_selectable(code: str, convention: DocstringConvention) -> None:
    exact_selection = rules_selection.select_rules(CheckSettings(select=(code,), docstring_convention=convention))

    assert code not in tuple(rule.rule.code.tag for rule in exact_selection.rules)


def test_builtin_none_and_pep257_broad_rule_profiles_are_distinct() -> None:
    none_selection = rules_selection.select_rules(CheckSettings(docstring_convention=DocstringConvention.NONE))
    pep257_selection = rules_selection.select_rules(CheckSettings(docstring_convention=DocstringConvention.PEP257))

    assert none_selection.errors == ()
    assert pep257_selection.errors == ()
    none_codes = frozenset(str(rule.rule.code) for rule in none_selection.rules)
    pep257_codes = frozenset(str(rule.rule.code) for rule in pep257_selection.rules)
    expected_none_only = frozenset(
        rule_class.meta.code.tag
        for rule_class in rule_collection.RULE_COLLECTION.rules
        if DocstringConvention.PEP257 in _ignored_docstring_conventions(rule_class.meta)
        and DocstringConvention.NONE not in _ignored_docstring_conventions(rule_class.meta)
        and rule_class.meta.code.tag not in CheckSettings().require_explicit
    )
    expected_pep257_only = frozenset(
        rule_class.meta.code.tag
        for rule_class in rule_collection.RULE_COLLECTION.rules
        if DocstringConvention.NONE in _ignored_docstring_conventions(rule_class.meta)
        and DocstringConvention.PEP257 not in _ignored_docstring_conventions(rule_class.meta)
        and rule_class.meta.code.tag not in CheckSettings().require_explicit
    )

    assert none_codes != pep257_codes
    assert none_codes - pep257_codes == expected_none_only
    assert pep257_codes - none_codes == expected_pep257_only


def test_rule_collection_does_not_expose_selector_convenience_indexes() -> None:
    collection = sample_collection()

    assert not hasattr(collection, "by_code")
    assert not hasattr(collection, "rule_codes")
    assert not hasattr(collection, "rule_prefixes")
    assert not hasattr(collection, "selector_matches_rule")
    assert not hasattr(collection, "selector_matches_some_rule")
    assert not hasattr(collection, "from_metadata")
    assert not hasattr(collection, "from_rule_classes")


def test_select_rules_resolves_selection_and_fixability() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF",), ignore=("PDF110",), fixable=("PDF",), unfixable=("PDF110",)), collection=sample_collection())

    assert selection.errors == ()
    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF101",)
    assert tuple(rule.fixable for rule in selection.rules) == (True,)


def test_select_rules_requires_exact_selection_for_require_explicit_rules() -> None:
    require_explicit_codes = CheckSettings().require_explicit
    defaults = rules_selection.select_rules(CheckSettings(select=("ALL",)))
    prefixed = rules_selection.select_rules(CheckSettings(select=("PDF",)))
    mixed_broad = rules_selection.select_rules(CheckSettings(select=("ALL", "PCF001")))

    assert defaults.errors == ()
    assert prefixed.errors == ()
    assert mixed_broad.errors == ()
    default_codes = tuple(rule.rule.code.tag for rule in defaults.rules)
    prefixed_codes = tuple(rule.rule.code.tag for rule in prefixed.rules)
    mixed_broad_codes = tuple(rule.rule.code.tag for rule in mixed_broad.rules)
    for code in require_explicit_codes:
        base_selector = "PCF" if code.startswith("PDF") else "PDF"
        assert code not in default_codes
        assert code not in prefixed_codes
        assert code not in mixed_broad_codes
        assert code in tuple(rule.rule.code.tag for rule in rules_selection.select_rules(CheckSettings(select=(code,), docstring_convention=DocstringConvention.GOOGLE)).rules)
        assert code in tuple(
            rule.rule.code.tag for rule in rules_selection.select_rules(CheckSettings(select=(base_selector,), extend_select=(code,), docstring_convention=DocstringConvention.GOOGLE)).rules
        )


def test_default_require_explicit_selectors_are_exact_known_rule_codes() -> None:
    default_selectors = CheckSettings().require_explicit
    known_rule_codes = frozenset(rule_class.meta.code.tag for rule_class in rule_collection.RULE_COLLECTION.rules)

    assert tuple(selector for selector in default_selectors if not RuleCode.is_valid_tag(selector)) == ()
    assert tuple(selector for selector in default_selectors if selector not in known_rule_codes) == ()


def test_default_require_explicit_rules_have_a_broad_selection_counterfactual() -> None:
    settings = CheckSettings(select=("ALL",))

    for code in settings.require_explicit:
        reduced_require_explicit = tuple(selector for selector in settings.require_explicit if selector != code)
        selections = tuple(
            rules_selection.select_rules(dataclasses.replace(settings, require_explicit=reduced_require_explicit, docstring_convention=convention)) for convention in DocstringConvention
        )
        assert any(not selection.errors and code in {rule.rule.code.tag for rule in selection.rules} for selection in selections), code


def test_select_rules_reports_require_explicit_selector_errors() -> None:
    selection = rules_selection.select_rules(CheckSettings(require_explicit=("bad", "PDF999")))

    assert "require-explicit rules contains invalid selector: bad" in selection.errors
    assert "require-explicit rules contains unknown selector: PDF999" in selection.errors


def test_select_rules_applies_ignored_setting_effect_after_normal_precedence() -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("TST",), docstring_convention=DocstringConvention.GOOGLE), collection=setting_effect_collection())
    exact = rules_selection.select_rules(CheckSettings(select=("TST001",), docstring_convention=DocstringConvention.GOOGLE), collection=setting_effect_collection())
    explicitly_ignored = rules_selection.select_rules(
        CheckSettings(select=("TST",), extend_select=("TST001",), ignore=("TST001",), docstring_convention=DocstringConvention.GOOGLE), collection=setting_effect_collection()
    )
    higher_priority_ignore = rules_selection.select_rules(
        CheckSettings(select=("TST001",), ignore=("TST",), docstring_convention=DocstringConvention.GOOGLE),
        collection=setting_effect_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "ignore": settings_core.ARGUMENT_SOURCE_PRIORITY},
    )

    assert tuple(rule.rule.code.tag for rule in broad.rules) == ()
    assert tuple(rule.rule.code.tag for rule in exact.rules) == ("TST001",)
    assert explicitly_ignored.rules == ()
    assert higher_priority_ignore.rules == ()


def test_select_rules_retains_exact_setting_effect_override_across_higher_priority_broad_extension() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST001",), extend_select=("TST",), docstring_convention=DocstringConvention.GOOGLE),
        collection=setting_effect_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY},
    )

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001",)
    assert tuple((rule.enabled_priority, rule.enabled_specificity) for rule in selection.rules) == ((settings_core.ARGUMENT_SOURCE_PRIORITY, len("TST")),)


def test_select_rules_retains_lower_priority_exact_setting_effect_override_when_broad_extension_outweighs_config_ignore() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST001",), extend_select=("TST",), ignore=("TST001",), docstring_convention=DocstringConvention.GOOGLE),
        collection=setting_effect_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY, "ignore": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001",)


def test_select_rules_does_not_retain_skipped_lower_priority_exact_setting_effect_override() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST",), extend_select=("TST001",), docstring_convention=DocstringConvention.GOOGLE),
        collection=setting_effect_collection(),
        field_priorities={"select": settings_core.ARGUMENT_SOURCE_PRIORITY, "extend_select": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )

    assert selection.rules == ()


def test_select_rules_applies_same_priority_broad_ignore_before_exact_setting_effect_override() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST001",), extend_select=("TST",), ignore=("TST",), docstring_convention=DocstringConvention.GOOGLE),
        collection=setting_effect_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY, "ignore": settings_core.ARGUMENT_SOURCE_PRIORITY},
    )

    assert selection.rules == ()


def test_select_rules_applies_per_file_ignore_after_cross_priority_exact_setting_effect_override() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST001",), extend_select=("TST",), docstring_convention=DocstringConvention.GOOGLE, per_file_ignores=(("tests/*.py", ("TST001",)),)),
        collection=setting_effect_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY},
    )

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001",)
    assert selection.for_path("tests/example.py") == ()


def test_select_rules_combines_multiple_setting_effects_with_disabled_precedence() -> None:
    ignored = rules_selection.select_rules(CheckSettings(select=("TST002",), docstring_parse_tables=False), collection=setting_effect_collection())
    disabled = rules_selection.select_rules(CheckSettings(select=("TST002",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_tables=False), collection=setting_effect_collection())

    assert tuple(rule.rule.code.tag for rule in ignored.rules) == ("TST002",)
    assert disabled.rules == ()


def test_select_rules_keeps_first_rules_when_incompatibilities_conflict() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("ALL",)), collection=incompatibility_collection())

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001", "TST003")
    assert selection.errors == (
        "Selected rule TST002 is incompatible with earlier selected rule TST001; TST002 has been disabled",
        "Selected rule TST004 is incompatible with earlier selected rules TST001, TST003; TST004 has been disabled",
    )


def test_select_rules_applies_setting_effects_before_incompatibilities() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("ALL",), docstring_convention=DocstringConvention.GOOGLE), collection=incompatibility_collection())

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST002", "TST004")
    assert selection.errors == ("Selected rule TST003 is incompatible with earlier selected rule TST002; TST003 has been disabled",)


def test_select_rules_uses_selector_strength_before_collection_order_for_incompatibilities() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST001",), extend_select=("TST004",)),
        collection=incompatibility_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY},
    )

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST004",)
    assert selection.errors == ()


def test_select_rules_uses_specificity_to_resolve_incompatibilities_without_errors() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("TST",), extend_select=("TST004",)), collection=incompatibility_collection())

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST002", "TST004")
    assert selection.errors == ()


def test_select_rules_reports_only_equal_strength_incompatibilities() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("TST", "TST001", "TST004")), collection=incompatibility_collection())

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001", "TST003")
    assert selection.errors == ("Selected rule TST004 is incompatible with earlier selected rule TST001; TST004 has been disabled",)


def test_select_rules_resolves_incompatibilities_globally_by_strength() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST", "TST002"), extend_select=("TST003",), ignore=("TST004",)),
        collection=incompatibility_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY, "ignore": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001", "TST003")
    assert selection.errors == ()


def test_select_rules_does_not_restore_incompatible_rules_after_per_file_ignores() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("TST001", "TST004"), per_file_ignores=(("tests/*.py", ("TST001",)),)), collection=incompatibility_collection())

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001",)
    assert selection.for_path("tests/example.py") == ()


def test_select_rules_applies_per_file_ignores_to_exactly_restored_ignored_rules() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("TST001",), docstring_convention=DocstringConvention.GOOGLE, per_file_ignores=(("tests/*.py", ("TST001",)),)), collection=setting_effect_collection()
    )

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("TST001",)
    assert selection.for_path("tests/example.py") == ()


def test_select_rules_rejects_unknown_setting_effect_fields() -> None:
    class TSTUnknownSettingEffectCategory(RuleCategoryBase):
        meta = RuleCategoryMetadata(prefix="TST", name="unknown setting effect", url=None)

    class TST999UnknownSettingEffectRule(RuleBase):
        meta = RuleMetadata(
            code=RuleCode("TST999"),
            name="unknown-setting",
            message="Unknown setting",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(RuleSettingEffects(setting="unknown_setting", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(True,)),)),),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )
        violations = classmethod(_no_violations)

    rule_registration.register_rule_to(TSTUnknownSettingEffectCategory)(TST999UnknownSettingEffectRule)

    with pytest.raises(ValueError, match="TST999: Unknown rule setting effect field: unknown_setting"):
        rules_selection.select_rules(CheckSettings(select=("TST999",)), collection=rule_collection.RuleCollection((TSTUnknownSettingEffectCategory,)))


def test_select_rules_prefers_more_specific_select_over_broader_ignore() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("ALL",), extend_select=("PDF14",), ignore=("PDF1",)), collection=specificity_collection())

    assert selection.errors == ()
    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF142",)


def test_select_rules_prefers_more_specific_ignore_over_broader_select() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF1",), ignore=("PDF14",)), collection=specificity_collection())

    assert selection.errors == ()
    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF150",)


def test_select_rules_ignore_wins_equal_specificity() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF14",), ignore=("PDF14",)), collection=specificity_collection())

    assert selection.errors == ()
    assert selection.rules == ()


def test_select_rules_all_is_less_specific_than_exact_extensions() -> None:
    selected_rule = rules_selection.select_rules(CheckSettings(select=("ALL",), extend_select=("PDF142",), ignore=("ALL",)), collection=specificity_collection())
    selected_fix = rules_selection.select_rules(CheckSettings(select=("PDF1",), fixable=("ALL",), extend_fixable=("PDF142",), unfixable=("ALL",)), collection=specificity_collection())

    assert tuple(rule.rule.code.tag for rule in selected_rule.rules) == ("PDF142",)
    assert tuple((rule.rule.code.tag, rule.fixable) for rule in selected_fix.rules) == (("PDF142", True), ("PDF150", False))


def test_select_rules_uses_source_priority_before_specificity() -> None:
    lower_priority_ignore = rules_selection.select_rules(
        CheckSettings(select=("PDF1",), ignore=("PDF142",)),
        collection=specificity_collection(),
        field_priorities={"select": settings_core.ARGUMENT_SOURCE_PRIORITY, "ignore": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )
    higher_priority_ignore = rules_selection.select_rules(
        CheckSettings(select=("PDF142",), ignore=("PDF1",)),
        collection=specificity_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "ignore": settings_core.ARGUMENT_SOURCE_PRIORITY},
    )
    higher_priority_extend_select = rules_selection.select_rules(
        CheckSettings(select=("PDF1",), extend_select=("PDF14",), ignore=("PDF142",)),
        collection=specificity_collection(),
        field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY, "ignore": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )
    lower_priority_extend_select = rules_selection.select_rules(
        CheckSettings(select=("PDF142",), extend_select=("PDF150",)),
        collection=specificity_collection(),
        field_priorities={"select": settings_core.ARGUMENT_SOURCE_PRIORITY, "extend_select": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )

    assert tuple(rule.rule.code.tag for rule in lower_priority_ignore.rules) == ("PDF142", "PDF150")
    assert higher_priority_ignore.rules == ()
    assert tuple(rule.rule.code.tag for rule in higher_priority_extend_select.rules) == ("PDF142", "PDF150")
    assert tuple(rule.rule.code.tag for rule in lower_priority_extend_select.rules) == ("PDF142",)


def test_select_rules_reports_errors_from_lower_priority_skipped_selectors() -> None:
    selection = rules_selection.select_rules(
        CheckSettings(select=("PDF142",), extend_select=("PDF999",), ignore=("bad",), fixable=("PDF142",), extend_fixable=("PDF999",), unfixable=("bad",)),
        collection=specificity_collection(),
        field_priorities={
            "select": settings_core.ARGUMENT_SOURCE_PRIORITY,
            "extend_select": settings_core.CONFIG_FILE_SOURCE_PRIORITY,
            "ignore": settings_core.CONFIG_FILE_SOURCE_PRIORITY,
            "fixable": settings_core.ARGUMENT_SOURCE_PRIORITY,
            "extend_fixable": settings_core.CONFIG_FILE_SOURCE_PRIORITY,
            "unfixable": settings_core.CONFIG_FILE_SOURCE_PRIORITY,
        },
    )

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF142",)
    assert "rule selection contains unknown selector: PDF999" in selection.errors
    assert "ignored rules contains invalid selector: bad" in selection.errors
    assert "fixable rules contains unknown selector: PDF999" in selection.errors
    assert "unfixable rules contains invalid selector: bad" in selection.errors


def test_select_rules_applies_per_file_ignores_without_enabled_selector_specificity() -> None:
    broader_ignore = rules_selection.select_rules(CheckSettings(select=("PDF14",), per_file_ignores=(("tests/*.py", ("PDF1",)),)), collection=specificity_collection())
    more_specific_ignore = rules_selection.select_rules(CheckSettings(select=("PDF1",), per_file_ignores=(("tests/*.py", ("PDF14",)),)), collection=specificity_collection())

    assert tuple(rule.rule.code.tag for rule in broader_ignore.for_path("tests/a.py")) == ()
    assert tuple(rule.rule.code.tag for rule in more_specific_ignore.for_path("tests/a.py")) == ("PDF150",)


def test_ruff_spec_repeated_cli_per_file_ignore_patterns_append_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "a.py"
        _write(target)
        with monkeypatch.context() as patch:
            patch.chdir(root)
            profile = SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(select=["PDF200,PDF110"], per_file_ignores=['{"a.py" = ["PDF200"]}', '{"a.py" = ["PDF110"]}']), path=str(target))

    selection = rules_selection.select_rules(profile.settings, profile=profile)

    assert profile.settings.per_file_ignores == (("a.py", ("PDF200", "PDF110")),)
    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF110", "PDF200")
    assert tuple(rule.rule.code.tag for rule in selection.for_path(str(target))) == ()


def test_select_rules_applies_fixability_specificity() -> None:
    specific_fixable = rules_selection.select_rules(CheckSettings(select=("PDF1",), fixable=("PDF14",), unfixable=("PDF1",)), collection=specificity_collection())
    specific_unfixable = rules_selection.select_rules(CheckSettings(select=("PDF1",), fixable=("PDF1",), unfixable=("PDF14",)), collection=specificity_collection())
    equal_unfixable = rules_selection.select_rules(CheckSettings(select=("PDF14",), fixable=("PDF14",), unfixable=("PDF14",)), collection=specificity_collection())

    assert tuple((rule.rule.code.tag, rule.fixable) for rule in specific_fixable.rules) == (("PDF142", True), ("PDF150", False))
    assert tuple((rule.rule.code.tag, rule.fixable) for rule in specific_unfixable.rules) == (("PDF142", False), ("PDF150", True))
    assert tuple((rule.rule.code.tag, rule.fixable) for rule in equal_unfixable.rules) == (("PDF142", False),)


def test_select_rules_uses_source_priority_for_fixability() -> None:
    lower_priority_unfixable = rules_selection.select_rules(
        CheckSettings(select=("PDF1",), fixable=("PDF1",), unfixable=("PDF142",)),
        collection=specificity_collection(),
        field_priorities={"fixable": settings_core.ARGUMENT_SOURCE_PRIORITY, "unfixable": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )
    higher_priority_unfixable = rules_selection.select_rules(
        CheckSettings(select=("PDF1",), fixable=("PDF1",), unfixable=("PDF142",)),
        collection=specificity_collection(),
        field_priorities={"fixable": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "unfixable": settings_core.ARGUMENT_SOURCE_PRIORITY},
    )
    lower_priority_extend_fixable = rules_selection.select_rules(
        CheckSettings(select=("PDF1",), fixable=("PDF142",), extend_fixable=("PDF150",)),
        collection=specificity_collection(),
        field_priorities={"fixable": settings_core.ARGUMENT_SOURCE_PRIORITY, "extend_fixable": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
    )

    assert tuple((rule.rule.code.tag, rule.fixable) for rule in lower_priority_unfixable.rules) == (("PDF142", True), ("PDF150", True))
    assert tuple((rule.rule.code.tag, rule.fixable) for rule in higher_priority_unfixable.rules) == (("PDF142", False), ("PDF150", True))
    assert tuple((rule.rule.code.tag, rule.fixable) for rule in lower_priority_extend_fixable.rules) == (("PDF142", True), ("PDF150", False))


def test_select_rules_treats_per_instance_fixable_rules_as_having_available_fixes() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF160", "PDF170"), fixable=("PDF160", "PDF170")), collection=fix_availability_collection())

    assert selection.errors == ()
    assert tuple((rule.rule.code.tag, rule.fixable) for rule in selection.rules) == (("PDF160", True), ("PDF170", True))


def test_select_rules_reports_selector_operational_errors() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("BAD", "bad"), fixable=("PDF110",)), collection=sample_collection())

    assert "rule selection contains unknown selector: BAD" in selection.errors
    assert "rule selection contains invalid selector: bad" in selection.errors
    assert "fixable rules selector 'PDF110' only matches rules with no available fixes" in selection.errors


def test_select_rules_applies_per_file_ignores() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("ALL",), per_file_ignores=(("tests/*.py", ("PDF101",)),)), collection=sample_collection())

    assert tuple(rule.rule.code.tag for rule in selection.for_path("src/a.py")) == ("PCF001", "PDF101", "PDF110")
    assert tuple(rule.rule.code.tag for rule in selection.for_path("tests/a.py")) == ("PCF001", "PDF110")


def test_ruff_spec_negated_per_file_ignore_patterns_ignore_everywhere_else() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF",), per_file_ignores=(("!src/*.py", ("PDF101",)), ("!tests/*.py", ("PDF110",)))), collection=sample_collection())

    assert tuple(rule.rule.code.tag for rule in selection.for_path("src/a.py")) == ("PDF101",)
    assert tuple(rule.rule.code.tag for rule in selection.for_path("tests/a.py")) == ("PDF110",)
    assert tuple(rule.rule.code.tag for rule in selection.for_path("a.py")) == ()


def test_ruff_spec_per_file_ignores_are_auto_config_directory_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "src" / "pkg" / "a.py"
        _write(target)
        with monkeypatch.context() as patch:
            patch.chdir(root / "src")
            _write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')
            matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            _write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"pkg/*.py" = ["PDF101"]}\n')
            non_matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            _write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"*.py" = ["PDF101"]}\n')
            bare_star_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            _write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"a.py" = ["PDF101"]}\n')
            bare_literal_profile = SETTINGS_SCHEMA.load_profile(path=str(target))

    assert _active_rule_tags_for_path(matching_profile, target) == ()
    assert _active_rule_tags_for_path(non_matching_profile, target) == ("PDF101",)
    assert _active_rule_tags_for_path(bare_star_profile, target) == ()
    assert _active_rule_tags_for_path(bare_literal_profile, target) == ()


def test_ruff_spec_per_file_ignores_do_not_use_git_root_as_base(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        target = root / "src" / "pkg" / "a.py"
        _write(target)
        with monkeypatch.context() as patch:
            patch.chdir(root / "src" / "pkg")
            _write(root / "src" / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"pkg/*.py" = ["PDF101"]}\n')
            matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            _write(root / "src" / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')
            non_matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))

    assert _active_rule_tags_for_path(matching_profile, target) == ()
    assert _active_rule_tags_for_path(non_matching_profile, target) == ("PDF101",)


def test_ruff_spec_explicit_config_per_file_ignores_are_current_directory_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        repo = root / "repo"
        config = root / "config" / "pydocfmt.toml"
        target = repo / "src" / "pkg" / "a.py"
        _write(target)
        _write(config, 'select = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')

        with monkeypatch.context() as patch:
            patch.chdir(repo)
            matching_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))

        with monkeypatch.context() as patch:
            patch.chdir(repo / "src")
            non_matching_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))
            _write(config, 'select = ["PDF101"]\nper-file-ignores = {"pkg/*.py" = ["PDF101"]}\n')
            changed_pattern_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))

    assert _active_rule_tags_for_path(matching_profile, target) == ()
    assert _active_rule_tags_for_path(non_matching_profile, target) == ("PDF101",)
    assert _active_rule_tags_for_path(changed_pattern_profile, target) == ()


def test_ruff_spec_cli_per_file_ignores_are_current_directory_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "src" / "pkg" / "a.py"
        _write(target)
        _write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\n')
        with monkeypatch.context() as patch:
            patch.chdir(root / "src")
            matching_profile = SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(per_file_ignores=['{"pkg/*.py" = ["PDF101"]}']), path=str(target))
            non_matching_profile = SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(per_file_ignores=['{"src/pkg/*.py" = ["PDF101"]}']), path=str(target))

    assert _active_rule_tags_for_path(matching_profile, target) == ()
    assert _active_rule_tags_for_path(non_matching_profile, target) == ("PDF101",)


def test_ruff_spec_per_file_ignores_apply_to_explicit_files(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "src" / "pkg" / "a.py"
        _write(target)
        _write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')
        with monkeypatch.context() as patch:
            patch.chdir(root / "src")
            selection = file_selection.select_files(["pkg/a.py"], SETTINGS_SCHEMA.resolver())

    assert selection.accepted_paths == (str(target),)
    assert _active_rule_tags_for_path(selection.profile_for_path(str(target)), target) == ()


def test_print_rules_prints_active_rules_with_effective_fixability() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("ALL",), unfixable=("PCF001",)), collection=sample_collection())
    output = StringIO()

    check.print_rules(selection, output=output)

    assert (
        output.getvalue()
        == "PCF001 comment-reflow-required (Comment chunk needs reflow)\nPDF101* docstring-reflow (Docstring chunk needs reflow)\nPDF110 summary-too-long (Docstring summary does not fit on one line)\n"
    )


def test_print_rules_reflects_setting_aware_selection() -> None:
    broad_output = StringIO()
    exact_output = StringIO()

    check.print_rules(rules_selection.select_rules(CheckSettings(docstring_convention=DocstringConvention.GOOGLE)), output=broad_output)
    check.print_rules(rules_selection.select_rules(CheckSettings(select=("PDF107",), docstring_convention=DocstringConvention.GOOGLE)), output=exact_output)

    assert "PDF106*" in broad_output.getvalue()
    assert "PDF107" not in broad_output.getvalue()
    assert "PDF108" not in broad_output.getvalue()
    assert "PDF107*" in exact_output.getvalue()


def test_print_rules_prints_operational_errors_before_rules() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("BAD",), fixable=("PDF110",)), collection=sample_collection())
    output = StringIO()

    check.print_rules(selection, output=output)

    assert output.getvalue() == "ERROR: rule selection contains unknown selector: BAD\nERROR: fixable rules selector 'PDF110' only matches rules with no available fixes\n\nNo active rules.\n"


def test_print_rules_prints_empty_message_without_active_rules() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF",), ignore=("PDF",)), collection=sample_collection())
    output = StringIO()

    check.print_rules(selection, output=output)

    assert output.getvalue() == "No active rules.\n"


def test_print_rules_ignores_per_file_rule_ignores() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("ALL",), per_file_ignores=(("tests/*.py", ("PDF101",)),)), collection=sample_collection())
    output = StringIO()

    check.print_rules(selection, output=output)

    assert "PDF101* docstring-reflow (Docstring chunk needs reflow)\n" in output.getvalue()
