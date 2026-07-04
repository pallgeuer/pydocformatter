import argparse
import ast
import dataclasses
import importlib
import inspect
import os
import pkgutil
import subprocess
import sys
import tempfile
import typing
import unittest
from io import StringIO
from pathlib import Path

import pydocformatter.cli.check as check
import pydocformatter.file_selection as file_selection
import pydocformatter.rules.codes as rule_codes
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definitions as rule_definitions
import pydocformatter.rules.documentation as rule_documentation
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules_selection as rules_selection
import pydocformatter.settings as settings_core
from pydocformatter.cli.global_args import GlobalArgs
from pydocformatter.cli.settings_check import SETTINGS_SCHEMA, CheckSettings, DocstringConvention
from pydocformatter.rules.codes import RuleCode, RuleSelector
from pydocformatter.rules.definition import RuleBase, RuleCategoryBase
from pydocformatter.rules.models import FixAvailability, RuleCategoryMetadata, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues

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
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),),
            ),
        ),
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
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=(DocstringConvention.GOOGLE,)),),
            ),
            RuleSettingEffects(
                setting="docstring_parse_tables",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(False,)),),
            ),
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
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),),
            ),
        ),
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


def _exec_rule_definition(source: str) -> None:
    """Execute a synthetic rule definition for runtime contract tests."""
    namespace = {
        "FixAvailability": FixAvailability,
        "RuleBase": RuleBase,
        "RuleCheckKind": RuleCheckKind,
        "RuleCode": RuleCode,
        "RuleMetadata": RuleMetadata,
        "typing": typing,
    }
    exec(source, namespace)


class TestRules(unittest.TestCase):
    @staticmethod
    def _write(path: Path, text: str = "x = 1\n") -> None:
        """Write a UTF-8 test fixture file, creating parents as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def _active_rule_tags_for_path(profile: typing.Any, path: Path) -> tuple[str, ...]:
        """Return active sample rule tags for a path after per-file ignores."""
        selection = rules_selection.select_rules(profile.settings, collection=sample_collection(), profile=profile)
        return tuple(rule.rule.code.tag for rule in selection.for_path(str(path)))

    @staticmethod
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

    @classmethod
    def _import_synthetic_rule_package(cls, files: dict[str, str]) -> None:
        """Import a synthetic rule package through the production loader."""
        package_name = "synthetic_rule_definitions"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package_root = root / package_name
            for relative_path, content in files.items():
                cls._write(package_root / relative_path, content)

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

    def test_default_rule_collection_is_collected_on_import(self) -> None:
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
            self.assertEqual(len(module_category_classes) + len(module_rule_classes), 1)
            discovered_category_classes.extend(module_category_classes)
            discovered_rule_classes.extend(module_rule_classes)

        self.assertEqual(collection.categories, rule_collection.RuleCollection(discovered_category_classes).categories)
        self.assertEqual(collection.rules, tuple(sorted(discovered_rule_classes, key=lambda rule_class: rule_class.meta.code)))
        self.assertEqual(tuple(category.meta.prefix for category in collection.categories), ("PCF", "PDF"))
        self.assertEqual(rule_documentation.undocumented_rules(collection), ())
        self.assertEqual(rule_documentation.undocumented_rule_categories(collection), ())
        self.assertTrue(rule_documentation.TEMPLATE_PATH.is_file())
        self.assertTrue(rule_documentation.CATEGORY_TEMPLATE_PATH.is_file())
        for category_class in collection.categories:
            explanation = rule_documentation.load_rule_explanation(category_class)
            self.assertTrue(explanation.startswith(f"# {category_class.meta.name} ({category_class.meta.prefix})\n\n"))
            self.assertEqual(markdown_level_two_headings(explanation), EXPECTED_RULE_CATEGORY_DOCUMENTATION_SECTIONS)
        for rule_class in collection.rules:
            explanation = rule_documentation.load_rule_explanation(rule_class)
            self.assertTrue(explanation.startswith(f"# {rule_class.meta.name} ({rule_class.meta.code})\n\n"))
            self.assertIn(f"\n\n{rule_documentation.rule_fix_text(rule_class.meta)}\n\n", explanation)
            self.assertEqual(markdown_level_two_headings(explanation), EXPECTED_RULE_DOCUMENTATION_SECTIONS)

    def test_builtin_rule_file_and_class_names_match_rule_content(self) -> None:
        for rule_class in rule_collection.RULE_COLLECTION.rules:
            rule = rule_class.meta
            with self.subTest(code=str(rule.code)):
                source_file = inspect.getsourcefile(rule_class)
                self.assertIsNotNone(source_file)
                source_path = Path(typing.cast(str, source_file))
                expected_python_stem = f"{rule.code}_{rule.name.replace('-', '_')}"
                self.assertEqual(source_path.stem, expected_python_stem)
                self.assertEqual(rule_class.__name__, f"{rule.code}{''.join(part.capitalize() for part in rule.name.split('-'))}")

                heading = rule_documentation.load_rule_explanation(rule_class).splitlines()[0]
                heading_name, separator, heading_code = heading.removeprefix("# ").rpartition(" (")
                self.assertEqual(separator, " (")
                self.assertTrue(heading_code.endswith(")"))
                expected_markdown_stem = f"{heading_code.removesuffix(')')}_{heading_name.replace('-', '_')}"
                self.assertEqual(source_path.with_suffix(".md").stem, expected_markdown_stem)

    def test_standard_rules_define_violations_api(self) -> None:
        """Check that standard built-in rules define the canonical violation API."""
        for rule_class in rule_collection.RULE_COLLECTION.rules:
            with self.subTest(code=str(rule_class.meta.code)):
                if rule_class.meta.check_kind == RuleCheckKind.STANDARD:
                    self.assertIn("violations", rule_class.__dict__)

    def test_builtin_rule_modules_use_violation_helpers(self) -> None:
        """Built-in rules and reusable rule helpers should not construct violation records directly."""
        source_root = Path(__file__).parents[1] / "src" / "pydocformatter" / "rules"
        paths = tuple(sorted((source_root / "definitions").glob("*/*.py"))) + tuple(sorted((source_root / "definition_helpers").glob("*.py")))
        forbidden: list[str] = []
        forbidden_imports_by_module = {
            "pydocformatter.rules.models": {"RuleFinding"},
            "pydocformatter.rules.violations": {"RuleSourceFix", "RuleViolation"},
        }
        forbidden_suffixes = (
            "RuleFinding",
            "RuleViolation",
            "RuleSourceFix",
            "RuleSourceFix.from_change",
            "_finding_for_planned_source_change",
        )
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    forbidden_names = forbidden_imports_by_module.get(node.module or "", set())
                    for alias in node.names:
                        if alias.name in forbidden_names:
                            forbidden.append(f"{path.relative_to(source_root.parent.parent)}:{node.lineno}: import {node.module}.{alias.name}")
                elif isinstance(node, ast.Call):
                    call_name = _ast_call_name(node.func)
                    if call_name.endswith(forbidden_suffixes):
                        forbidden.append(f"{path.relative_to(source_root.parent.parent)}:{node.lineno}: {call_name}")

        self.assertEqual(forbidden, [])

    def test_rule_modules_import_before_collection_without_changing_default_collection(self) -> None:
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(result.stdout, "PCF PDF\n")

    def test_rule_registry_collects_categories_and_rules(self) -> None:
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

        self.assertEqual(registry.category_classes, {PDFTestCategory})
        self.assertEqual(rule_collection.RuleCollection.from_registry(registry).categories, (PDFTestCategory,))
        self.assertEqual(rule_collection.RuleCollection.from_registry(registry).category_class, {"PDF": PDFTestCategory})
        self.assertEqual(rule_collection.RuleCollection.from_registry(registry).rules, (PDF999TestRule,))
        self.assertEqual(rule_collection.RuleCollection.from_registry(registry).rule_class, {RuleCode("PDF999"): PDF999TestRule})

    def test_register_rule_category_decorator_collects_category_in_default_registry(self) -> None:
        previous_registry = rule_registration.DEFAULT_RULE_REGISTRY
        rule_registration.DEFAULT_RULE_REGISTRY = rule_registration.RuleRegistry()
        try:

            @rule_registration.register_rule_category
            class PDFTestCategory(RuleCategoryBase):
                meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

            collection = rule_collection.RuleCollection.from_registry(rule_registration.DEFAULT_RULE_REGISTRY)
        finally:
            rule_registration.DEFAULT_RULE_REGISTRY = previous_registry

        self.assertEqual(collection.categories, (PDFTestCategory,))

    def test_import_package_rule_categories_imports_package_modules(self) -> None:
        rule_collection.import_package_rule_categories(package=rule_definitions)

    def test_import_package_rule_categories_validates_package_structure_and_registration(self) -> None:
        package_name = "synthetic_rule_definitions"
        valid_files = self._valid_rule_package_files(package_name)
        self._import_synthetic_rule_package(valid_files)

        cases: tuple[tuple[str, dict[str, str], str], ...] = (
            (
                "stray definitions module",
                {**valid_files, "stray.py": ""},
                "must contain only category packages",
            ),
            (
                "nested category package",
                {**valid_files, "PDF/nested/__init__.py": ""},
                "must not contain nested packages",
            ),
            (
                "missing category module",
                {path: content for path, content in valid_files.items() if path != "PDF/PDF.py"},
                "must contain category module",
            ),
            (
                "wrong category class name",
                {**valid_files, "PDF/PDF.py": valid_files["PDF/PDF.py"].replace("class PDF", "class WrongPDF")},
                "exactly one RuleCategoryBase subclass named PDF",
            ),
            (
                "category metadata prefix mismatch",
                {**valid_files, "PDF/PDF.py": valid_files["PDF/PDF.py"].replace("prefix='PDF'", "prefix='PCF'")},
                "does not match package and module name",
            ),
            (
                "unregistered category",
                {**valid_files, "PDF/PDF.py": valid_files["PDF/PDF.py"].replace("@rule_registration.register_rule_category\n", "")},
                "is not registered with the rule registry",
            ),
            (
                "unexpected category module",
                {**valid_files, "PDF/helper.py": "value = 1\n"},
                "Unexpected module in rule category package",
            ),
            (
                "rule module without name suffix",
                {**valid_files, "PDF/PDF100.py": ""},
                "Unexpected module in rule category package",
            ),
            (
                "reserved rule module code",
                {**valid_files, "PDF/ALL001_test.py": ""},
                "Unexpected module in rule category package",
            ),
            (
                "multiple rule classes",
                {
                    **valid_files,
                    "PDF/PDF101_test.py": valid_files["PDF/PDF101_test.py"]
                    + "\nclass PDF100Test(RuleBase):\n    meta = RuleMetadata(code=RuleCode('PDF100'), name='test-two', message='Test two', fix_availability=FixAvailability.ALWAYS, stable_since='1.0.0', setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)\n    @classmethod\n    def violations(cls, context):\n        del cls, context\n        return ()\n",
                },
                "must define exactly one RuleBase subclass",
            ),
            (
                "rule module code mismatch",
                {**valid_files, "PDF/PDF101_test.py": valid_files["PDF/PDF101_test.py"].replace("RuleCode('PDF101')", "RuleCode('PDF100')")},
                "does not match rule code",
            ),
            (
                "unregistered rule",
                {**valid_files, "PDF/PDF101_test.py": valid_files["PDF/PDF101_test.py"].replace("@rule_registration.register_rule_to(PDF)\n", "")},
                "is not registered with category PDF",
            ),
            (
                "missing category documentation",
                {path: content for path, content in valid_files.items() if path != "PDF/PDF.md"},
                "missing adjacent documentation PDF.md",
            ),
            (
                "missing rule documentation",
                {path: content for path, content in valid_files.items() if path != "PDF/PDF101_test.md"},
                "missing adjacent documentation PDF101_test.md",
            ),
            (
                "orphan documentation",
                {**valid_files, "PDF/PDF999_orphan.md": "# orphan\n"},
                "contains orphan Markdown files",
            ),
        )
        for name, files, message in cases:
            with self.subTest(name=name), self.assertRaisesRegex(rule_registration.RuleError, message):
                self._import_synthetic_rule_package(files)

    def test_import_package_rule_categories_rejects_registered_rules_outside_category_package(self) -> None:
        package_name = "synthetic_rule_definitions"
        files = self._valid_rule_package_files(package_name)
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

        with self.assertRaisesRegex(rule_registration.RuleError, "contains rules from outside package"):
            self._import_synthetic_rule_package(files)

    def test_import_package_rule_categories_rejects_registered_rules_without_rule_modules(self) -> None:
        package_name = "synthetic_rule_definitions"
        files = self._valid_rule_package_files(package_name)
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

        with self.assertRaisesRegex(rule_registration.RuleError, "registered rules without matching rule modules"):
            self._import_synthetic_rule_package(files)

    def test_register_rule_category_to_collects_category_in_bound_registry(self) -> None:
        registry = rule_registration.RuleRegistry()

        @rule_registration.register_rule_category_to(registry)
        class PDFTestCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

        self.assertEqual(rule_collection.RuleCollection.from_registry(registry).categories, (PDFTestCategory,))

    def test_rule_category_rejects_duplicate_rule_codes_from_different_classes(self) -> None:
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

        with self.assertRaisesRegex(rule_registration.RuleError, "Duplicate rule code in category PDF: PDF999"):

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

    def test_rule_category_allows_registering_the_same_rule_class_twice(self) -> None:
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

        self.assertEqual(PDFTestCategory.ordered_rules(), (PDF999TestRule,))

    def test_rule_collection_allows_the_same_category_class_twice(self) -> None:
        class PDFTestCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

        collection = rule_collection.RuleCollection((PDFTestCategory, PDFTestCategory))

        self.assertEqual(collection.categories, (PDFTestCategory,))

    def test_rule_registry_and_collection_reject_direct_rules(self) -> None:
        registry = rule_registration.RuleRegistry()

        with self.assertRaisesRegex(rule_registration.RuleError, "Registered rule category must inherit RuleCategoryBase"):
            registry.register(typing.cast(type[RuleCategoryBase], PDF101SampleRule))
        with self.assertRaisesRegex(rule_registration.RuleError, "Collected rule category must inherit RuleCategoryBase"):
            rule_collection.RuleCollection((typing.cast(type[RuleCategoryBase], PDF101SampleRule),))

    def test_rule_registry_is_frozen_but_keeps_mutable_registration_state(self) -> None:
        registry = rule_registration.RuleRegistry()

        class PDFTestCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

        registry.register(PDFTestCategory)

        with self.assertRaises(dataclasses.FrozenInstanceError):
            setattr(registry, "category_classes", set())
        self.assertEqual(rule_collection.RuleCollection.from_registry(registry).categories, (PDFTestCategory,))

    def test_rule_registries_are_isolated(self) -> None:
        default_registry = rule_registration.RuleRegistry()
        isolated_registry = rule_registration.RuleRegistry()

        @rule_registration.register_rule_category_to(default_registry)
        class PDFDefaultCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="default PDF", url=None)

        @rule_registration.register_rule_category_to(isolated_registry)
        class PDFIsolatedCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="isolated PDF", url=None)

        self.assertEqual(rule_collection.RuleCollection.from_registry(default_registry).categories, (PDFDefaultCategory,))
        self.assertEqual(rule_collection.RuleCollection.from_registry(isolated_registry).categories, (PDFIsolatedCategory,))

    def test_rule_metadata_derives_prefix_and_number_from_code(self) -> None:
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

        self.assertEqual(tuple(field.name for field in dataclasses.fields(RuleCode)), ("tag", "prefix", "number_str", "number"))
        self.assertEqual(str(rule.code), "PDF001")
        self.assertEqual(rule.code.tag, "PDF001")
        self.assertEqual(rule.code.prefix, "PDF")
        self.assertEqual(rule.code.number_str, "001")
        self.assertEqual(rule.code.number, 1)
        self.assertTrue(RuleCode.is_valid_tag("PDF001"))
        self.assertFalse(RuleCode.is_valid_tag("001"))
        self.assertFalse(RuleCode.is_valid_tag("ALL001"))
        self.assertFalse(hasattr(rule_models, "valid_rule_code_tag"))
        self.assertFalse(hasattr(rule_models, "split_rule_code"))
        self.assertEqual(rule.stable_since, "1.0.0")
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(RuleMetadata)), ("code", "name", "message", "fix_availability", "stable_since", "setting_effects", "incompatible_with", "check_kind")
        )
        self.assertTrue(all(field.default is dataclasses.MISSING for field in dataclasses.fields(RuleMetadata)))
        self.assertTrue(all(field.default_factory is dataclasses.MISSING for field in dataclasses.fields(RuleMetadata)))
        self.assertEqual(rule.check_kind, RuleCheckKind.STANDARD)
        self.assertEqual(rule.setting_effects, ())
        self.assertEqual(rule.incompatible_with, ())
        self.assertIsInstance(hash(TST001IgnoredSampleRule.meta), int)
        self.assertIs(rule_codes.RuleCode, RuleCode)
        self.assertFalse(hasattr(rule_models, "RuleSelector"))
        self.assertEqual(rule_documentation.rule_fix_text(rule), "Fix is always available.")
        self.assertEqual(
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
            ),
            "Fix is usually available.",
        )
        self.assertEqual(
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
            ),
            "Fix is sometimes available.",
        )
        self.assertEqual(str(FixAvailability.USUALLY), "Usually")
        self.assertEqual(str(FixAvailability.SOMETIMES), "Sometimes")
        self.assertFalse(hasattr(rule, "matches_selector"))
        self.assertFalse(hasattr(rule, "matches_selector_parts"))

    def test_rule_selector_selects_code(self) -> None:
        code = RuleCode("PDF101")

        selector = RuleSelector("PDF10")

        self.assertEqual(tuple(field.name for field in dataclasses.fields(RuleSelector)), ("tag", "prefix", "number_str"))
        self.assertEqual(str(selector), "PDF10")
        self.assertEqual(selector.tag, "PDF10")
        self.assertEqual(selector.prefix, "PDF")
        self.assertEqual(selector.number_str, "10")
        self.assertTrue(RuleSelector.is_valid_tag("ALL"))
        self.assertTrue(RuleSelector.is_valid_tag("PDF10"))
        self.assertFalse(RuleSelector.is_valid_tag("bad"))
        self.assertFalse(RuleSelector.is_valid_tag("ALL1"))
        self.assertFalse(hasattr(rule_models, "rule_selector_is_valid"))
        self.assertFalse(hasattr(rule_models, "split_rule_selector"))
        self.assertTrue(RuleSelector("ALL").selects_code(code))
        self.assertTrue(RuleSelector("PDF").selects_code(code))
        self.assertTrue(RuleSelector("PDF1").selects_code(code))
        self.assertTrue(selector.selects_code(code))
        self.assertFalse(RuleSelector("PDF203").selects_code(code))
        self.assertFalse(RuleSelector("P").selects_code(code))

    def test_rule_metadata_validates_rule_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid rule code: bad"):
            RuleCode("bad")
        with self.assertRaisesRegex(ValueError, "Invalid rule code: ALL001"):
            RuleCode("ALL001")
        with self.assertRaisesRegex(TypeError, "Expected RuleCode, got str"):
            RuleMetadata(
                code=typing.cast(typing.Any, "bad"),
                name="bad-rule",
                message="Bad rule",
                fix_availability=FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )
        with self.assertRaisesRegex(TypeError, "Expected FixAvailability, got str"):
            RuleMetadata(
                code=RuleCode("PDF101"),
                name="bad-rule",
                message="Bad rule",
                fix_availability=typing.cast(typing.Any, "Always"),
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )
        with self.assertRaisesRegex(TypeError, "Expected RuleCheckKind, got str"):
            RuleMetadata(
                code=RuleCode("PDF101"),
                name="bad-rule",
                message="Bad rule",
                fix_availability=FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=typing.cast(typing.Any, "standard"),
            )
        with self.assertRaisesRegex(TypeError, "missing 1 required positional argument: 'stable_since'"):
            RuleMetadata(code=RuleCode("PDF101"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)  # type: ignore[call-arg]
        with self.assertRaisesRegex(TypeError, "missing 1 required positional argument: 'setting_effects'"):
            RuleMetadata(code=RuleCode("PDF101"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, stable_since="1.0.0", incompatible_with=(), check_kind=RuleCheckKind.STANDARD)  # type: ignore[call-arg]
        with self.assertRaisesRegex(TypeError, "missing 1 required positional argument: 'incompatible_with'"):
            RuleMetadata(code=RuleCode("PDF101"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, stable_since="1.0.0", setting_effects=(), check_kind=RuleCheckKind.STANDARD)  # type: ignore[call-arg]
        with self.assertRaisesRegex(ValueError, "PDF101: Stable version must not be empty"):
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
        with self.assertRaisesRegex(ValueError, "Rule setting name must not be empty"):
            RuleSettingEffects(setting="", effects=())
        with self.assertRaisesRegex(TypeError, "Expected RuleSettingEffect, got str"):
            RuleSettingEffectValues(effect=typing.cast(typing.Any, "Ignored"), values=(True,))
        with self.assertRaisesRegex(ValueError, "triggering values must not be empty"):
            RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=())
        with self.assertRaisesRegex(TypeError, "triggering values must be a tuple"):
            RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=typing.cast(typing.Any, [True]))
        with self.assertRaisesRegex(TypeError, "triggering values must be hashable"):
            RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(typing.cast(typing.Any, []),))
        with self.assertRaisesRegex(TypeError, "must contain RuleSettingEffectValues instances"):
            RuleSettingEffects(setting="docstring_convention", effects=typing.cast(typing.Any, ("bad",)))
        with self.assertRaisesRegex(TypeError, "Rule setting effects must contain RuleSettingEffects instances"):
            RuleMetadata(
                code=RuleCode("PDF101"),
                name="bad-rule",
                message="Bad rule",
                fix_availability=FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=typing.cast(typing.Any, ("bad",)),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )
        with self.assertRaisesRegex(TypeError, "Incompatible rule codes must be a tuple"):
            RuleMetadata(
                code=RuleCode("PDF101"),
                name="bad-rule",
                message="Bad rule",
                fix_availability=FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=typing.cast(typing.Any, [RuleCode("PDF100")]),
                check_kind=RuleCheckKind.STANDARD,
            )
        with self.assertRaisesRegex(TypeError, "Incompatible rule codes must contain RuleCode instances"):
            RuleMetadata(
                code=RuleCode("PDF101"),
                name="bad-rule",
                message="Bad rule",
                fix_availability=FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=typing.cast(typing.Any, ("PDF100",)),
                check_kind=RuleCheckKind.STANDARD,
            )
        with self.assertRaisesRegex(ValueError, "Incompatible rule codes must not contain duplicates"):
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

    def test_rule_selector_validates_tag(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid rule selector: bad"):
            RuleSelector("bad")
        with self.assertRaisesRegex(ValueError, "Invalid rule selector: ALL1"):
            RuleSelector("ALL1")

    def test_rule_base_requires_subclass_metadata(self) -> None:
        with self.assertRaisesRegex(TypeError, "MissingMetaRule must define RuleMetadata as 'meta'"):

            class MissingMetaRule(RuleBase):
                pass

    def test_rule_base_rejects_non_metadata_subclass_metadata(self) -> None:
        with self.assertRaisesRegex(TypeError, "InvalidMetaRule.meta must be a RuleMetadata instance"):

            class InvalidMetaRule(RuleBase):
                meta: typing.ClassVar[typing.Any] = None

    def test_rule_base_rejects_standard_rule_without_violations(self) -> None:
        with self.assertRaisesRegex(TypeError, "MissingViolationsRule must define violations"):

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

    def test_rule_base_rejects_non_classmethod_violations_hook(self) -> None:
        with self.assertRaisesRegex(TypeError, "InstanceViolationsRule\\.violations must be a @classmethod"):
            _exec_rule_definition("""
class InstanceViolationsRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF999"), name="instance-violations", message="Instance violations", fix_availability=FixAvailability.NEVER, stable_since="1.0.0", setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)

    def violations(self, context):
        del self, context
        return ()
""")

        with self.assertRaisesRegex(TypeError, "StaticViolationsRule\\.violations must be a @classmethod"):
            _exec_rule_definition("""
class StaticViolationsRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF999"), name="static-violations", message="Static violations", fix_availability=FixAvailability.NEVER, stable_since="1.0.0", setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)

    @staticmethod
    def violations(context):
        del context
        return ()
""")

    def test_rule_base_rejects_bad_violations_signature(self) -> None:
        with self.assertRaisesRegex(TypeError, "ExtraArgumentRule\\.violations must accept exactly one required positional argument named context"):
            _exec_rule_definition("""
class ExtraArgumentRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF999"), name="extra-argument", message="Extra argument", fix_availability=FixAvailability.NEVER, stable_since="1.0.0", setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)

    @classmethod
    def violations(cls, context, extra):
        del cls, context, extra
        return ()
""")

        with self.assertRaisesRegex(TypeError, "WrongContextNameRule\\.violations must accept exactly one required positional argument named context"):
            _exec_rule_definition("""
class WrongContextNameRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF999"), name="wrong-context-name", message="Wrong context name", fix_availability=FixAvailability.NEVER, stable_since="1.0.0", setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)

    @classmethod
    def violations(cls, node):
        del cls, node
        return ()
""")

        with self.assertRaisesRegex(TypeError, "OptionalArgumentRule\\.violations must accept exactly one required positional argument named context"):
            _exec_rule_definition("""
class OptionalArgumentRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF999"), name="optional-argument", message="Optional argument", fix_availability=FixAvailability.NEVER, stable_since="1.0.0", setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)

    @classmethod
    def violations(cls, context, extra=None):
        del cls, context, extra
        return ()
""")

    def test_rule_base_rejects_noncallable_classmethod_violations_hook(self) -> None:
        with self.assertRaisesRegex(TypeError, "NonCallableViolationsRule\\.violations must be callable"):
            _exec_rule_definition("""
class NonCallableViolationsRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF999"), name="noncallable-violations", message="Noncallable violations", fix_availability=FixAvailability.NEVER, stable_since="1.0.0", setting_effects=(), incompatible_with=(), check_kind=RuleCheckKind.STANDARD)
    violations = classmethod(typing.cast(typing.Any, None))
""")

    def test_rule_base_allows_suppression_audit_rule_without_violations(self) -> None:
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

        self.assertEqual(SuppressionAuditRule.violations(typing.cast(typing.Any, object())), ())

    def test_rule_category_metadata_and_base_validate_definitions(self) -> None:
        metadata = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

        class PDFTestCategory(RuleCategoryBase):
            meta = metadata

        self.assertEqual(tuple(field.name for field in dataclasses.fields(RuleCategoryMetadata)), ("prefix", "name", "url"))
        self.assertTrue(all(field.default is dataclasses.MISSING for field in dataclasses.fields(RuleCategoryMetadata)))
        self.assertEqual((metadata.prefix, metadata.name, metadata.url), ("PDF", "test PDF", None))
        self.assertEqual((PDFTestCategory.prefix, PDFTestCategory.name, PDFTestCategory.url), ("PDF", "test PDF", None))
        self.assertEqual((PDFTestCategory().prefix, PDFTestCategory().name, PDFTestCategory().url), ("PDF", "test PDF", None))
        with self.assertRaisesRegex(ValueError, "Invalid rule category prefix: bad"):
            RuleCategoryMetadata(prefix="bad", name="bad", url=None)
        with self.assertRaisesRegex(ValueError, "PDF: Rule category name must not be empty"):
            RuleCategoryMetadata(prefix="PDF", name="", url=None)
        with self.assertRaisesRegex(TypeError, "missing 1 required positional argument: 'url'"):
            RuleCategoryMetadata(prefix="PDF", name="test PDF")  # type: ignore[call-arg]
        with self.assertRaisesRegex(TypeError, "MissingMetaCategory must define RuleCategoryMetadata as 'meta'"):

            class MissingMetaCategory(RuleCategoryBase):
                pass

        with self.assertRaisesRegex(TypeError, "InvalidMetaCategory.meta must be a RuleCategoryMetadata instance"):

            class InvalidMetaCategory(RuleCategoryBase):
                meta: typing.ClassVar[typing.Any] = None

    def test_rule_category_rejects_rule_with_different_prefix(self) -> None:
        class PDFTestCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="test PDF", url=None)

        with self.assertRaisesRegex(rule_registration.RuleError, "Rule category must inherit RuleCategoryBase"):
            rule_registration.register_rule_to(typing.cast(type[RuleCategoryBase], object))
        with self.assertRaisesRegex(rule_registration.RuleError, "Registered rule must inherit RuleBase"):
            rule_registration.register_rule_to(PDFTestCategory)(typing.cast(type[RuleBase], object))
        with self.assertRaisesRegex(rule_registration.RuleError, "Rule code prefix 'PCF' does not match rule category prefix 'PDF'"):
            rule_registration.register_rule_to(PDFTestCategory)(PCF001SampleRule)

    def test_rule_collection_rejects_duplicate_category_prefixes(self) -> None:
        class PDFFirstCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="first PDF", url=None)

        class PDFSecondCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="second PDF", url=None)

        with self.assertRaisesRegex(rule_registration.RuleError, "Duplicate rule category prefix: PDF"):
            rule_collection.RuleCollection((PDFFirstCategory, PDFSecondCategory))

    def test_rule_collection_validates_rule_incompatibilities(self) -> None:
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

        with self.assertRaisesRegex(rule_registration.RuleError, "Rule TST001 cannot be incompatible with itself"):
            rule_collection.RuleCollection((TSTSelfCategory,))

        class TSTUnknownCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="TST", name="unknown incompatible", url=None)

        @rule_registration.register_rule_to(TSTUnknownCategory)
        class TST001UnknownRule(RuleBase):
            meta = dataclasses.replace(TST001SelfRule.meta, incompatible_with=(RuleCode("TST999"),))
            violations = classmethod(_no_violations)

        with self.assertRaisesRegex(rule_registration.RuleError, "Rule TST001 is incompatible with unknown rule code TST999"):
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

        with self.assertRaisesRegex(rule_registration.RuleError, "Rule incompatibility between TST001 and TST002 must be declared by both rules"):
            rule_collection.RuleCollection((TSTAsymmetricCategory,))

    def test_rule_base_class_properties_redirect_to_metadata(self) -> None:
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

        self.assertEqual(
            (
                PDF999TestRule.code,
                PDF999TestRule.prefix,
                PDF999TestRule.number_str,
                PDF999TestRule.number,
                PDF999TestRule.name,
                PDF999TestRule.message,
                PDF999TestRule.fix_availability,
                PDF999TestRule.setting_effects,
                PDF999TestRule.incompatible_with,
            ),
            ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", FixAvailability.ALWAYS, (), ()),
        )
        self.assertEqual(PDF999TestRule.stable_since, "1.0.0")
        self.assertEqual(
            (rule.code, rule.prefix, rule.number_str, rule.number, rule.name, rule.message, rule.fix_availability, rule.stable_since, rule.setting_effects, rule.incompatible_with),
            ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", FixAvailability.ALWAYS, "1.0.0", (), ()),
        )

    def test_selectors_must_use_complete_rule_prefixes(self) -> None:
        collection = sample_collection()

        self.assertTrue(collection.matching_rules_exist(RuleSelector("ALL")))
        self.assertTrue(collection.matching_rules_exist(RuleSelector("PDF")))
        self.assertTrue(collection.matching_rules_exist(RuleSelector("PDF1")))
        self.assertTrue(collection.matching_rules_exist(RuleSelector("PDF10")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("PDF108")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("R")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("P")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("RD")))

    def test_rule_collection_orders_rules_and_rule_class_index_the_same_way(self) -> None:
        class PDFReverseRegistrationCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="PDF", name="reverse PDF", url=None)

        rule_registration.register_rule_to(PDFReverseRegistrationCategory)(PDF110SampleRule)
        rule_registration.register_rule_to(PDFReverseRegistrationCategory)(PDF101SampleRule)
        collection = sample_collection()

        self.assertEqual(collection.categories, (PCFSampleCategory, PDFSampleCategory))
        self.assertEqual(tuple(collection.category_class.values()), collection.categories)
        self.assertEqual(collection.rules, (PCF001SampleRule, PDF101SampleRule, PDF110SampleRule))
        self.assertEqual(tuple(collection.rule_class.values()), collection.rules)
        self.assertEqual(PCFSampleCategory.ordered_rules(), (PCF001SampleRule,))
        self.assertEqual(PDFSampleCategory.ordered_rules(), (PDF101SampleRule, PDF110SampleRule))
        self.assertEqual(tuple(PDFSampleCategory.ordered_code_class_map().values()), PDFSampleCategory.ordered_rules())
        self.assertEqual(PDFReverseRegistrationCategory.ordered_rules(), (PDF101SampleRule, PDF110SampleRule))

    def test_rule_collection_matching_rules_returns_rule_classes(self) -> None:
        collection = sample_collection()

        self.assertEqual(collection.matching_rules(RuleSelector("PDF")), (PDF101SampleRule, PDF110SampleRule))

    def test_builtin_rule_setting_effect_matrix(self) -> None:
        convention_effects: dict[str, dict[DocstringConvention, RuleSettingEffect]] = {}
        incompatibilities: dict[str, tuple[str, ...]] = {}
        for rule_class in rule_collection.RULE_COLLECTION.rules:
            rule_effects: dict[DocstringConvention, RuleSettingEffect] = {}
            for setting_effects in rule_class.meta.setting_effects:
                if setting_effects.setting == "docstring_convention":
                    for effect_values in setting_effects.effects:
                        for value in effect_values.values:
                            rule_effects[typing.cast(DocstringConvention, value)] = effect_values.effect
            convention_effects[rule_class.meta.code.tag] = rule_effects
            incompatibilities[rule_class.meta.code.tag] = tuple(rule_code.tag for rule_code in rule_class.meta.incompatible_with)

        self.assertTrue(all(not effects for code, effects in convention_effects.items() if code.startswith("PCF")))
        self.assertEqual(
            {code: effects for code, effects in convention_effects.items() if effects},
            {
                "PDF106": {DocstringConvention.PEP257: RuleSettingEffect.IGNORED, DocstringConvention.NUMPY: RuleSettingEffect.IGNORED},
                "PDF107": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF108": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF205": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF206": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF207": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF209": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF210": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF300": {DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED},
                "PDF301": {DocstringConvention.PEP257: RuleSettingEffect.IGNORED, DocstringConvention.NUMPY: RuleSettingEffect.IGNORED},
                "PDF302": {DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED},
                "PDF303": {DocstringConvention.NUMPY: RuleSettingEffect.IGNORED},
                "PDF305": {DocstringConvention.PEP257: RuleSettingEffect.IGNORED, DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED},
                "PDF306": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF307": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF308": {DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED},
                "PDF309": {DocstringConvention.PEP257: RuleSettingEffect.IGNORED, DocstringConvention.NUMPY: RuleSettingEffect.IGNORED},
                "PDF400": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF401": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                },
                "PDF402": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF403": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF404": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF405": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF406": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF407": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF408": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF409": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF410": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF411": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF412": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF500": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                },
                "PDF501": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF502": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF503": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF504": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF505": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF506": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF507": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF508": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF509": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF510": {
                    DocstringConvention.NONE: RuleSettingEffect.IGNORED,
                    DocstringConvention.PEP257: RuleSettingEffect.IGNORED,
                    DocstringConvention.GOOGLE: RuleSettingEffect.IGNORED,
                    DocstringConvention.NUMPY: RuleSettingEffect.IGNORED,
                    DocstringConvention.REST: RuleSettingEffect.IGNORED,
                },
                "PDF511": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF512": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
                "PDF513": {DocstringConvention.NONE: RuleSettingEffect.IGNORED, DocstringConvention.PEP257: RuleSettingEffect.IGNORED},
            },
        )
        self.assertEqual(
            {code: incompatible for code, incompatible in incompatibilities.items() if incompatible},
            {
                "PDF106": ("PDF107",),
                "PDF107": ("PDF106",),
                "PDF108": ("PDF109",),
                "PDF109": ("PDF108",),
                "PDF204": ("PDF205",),
                "PDF205": ("PDF204",),
                "PDF206": ("PDF207",),
                "PDF207": ("PDF206",),
                "PDF208": ("PDF209",),
                "PDF209": ("PDF208",),
                "PDF210": ("PDF211",),
                "PDF211": ("PDF210",),
            },
        )

    def test_builtin_opt_in_style_variant_rules_ignore_every_docstring_convention(self) -> None:
        rule_classes = {rule_class.meta.code.tag: rule_class for rule_class in rule_collection.RULE_COLLECTION.rules}

        for code in ("PDF107", "PDF108", "PDF205", "PDF206", "PDF207", "PDF209", "PDF210"):
            ignored_conventions: set[DocstringConvention] = set()
            for setting_effects in rule_classes[code].meta.setting_effects:
                if setting_effects.setting == "docstring_convention":
                    for effect_values in setting_effects.effects:
                        if effect_values.effect == RuleSettingEffect.IGNORED:
                            ignored_conventions.update(typing.cast(DocstringConvention, value) for value in effect_values.values)

            self.assertEqual(ignored_conventions, set(DocstringConvention))

    def test_builtin_none_and_pep257_broad_rule_profiles_are_distinct(self) -> None:
        none_selection = rules_selection.select_rules(CheckSettings(docstring_convention=DocstringConvention.NONE))
        pep257_selection = rules_selection.select_rules(CheckSettings(docstring_convention=DocstringConvention.PEP257))

        self.assertEqual(none_selection.errors, ())
        self.assertEqual(pep257_selection.errors, ())
        self.assertEqual(
            tuple(str(rule.rule.code) for rule in none_selection.rules),
            (
                "PCF001",
                "PCF002",
                "PCF003",
                "PCF004",
                "PCF006",
                "PDF000",
                "PDF001",
                "PDF002",
                "PDF100",
                "PDF101",
                "PDF102",
                "PDF103",
                "PDF104",
                "PDF105",
                "PDF106",
                "PDF109",
                "PDF110",
                "PDF200",
                "PDF201",
                "PDF202",
                "PDF203",
                "PDF204",
                "PDF208",
                "PDF211",
                "PDF300",
                "PDF301",
                "PDF302",
                "PDF303",
                "PDF304",
                "PDF305",
                "PDF308",
                "PDF309",
                "PDF310",
            ),
        )
        self.assertEqual(
            tuple(str(rule.rule.code) for rule in pep257_selection.rules),
            (
                "PCF001",
                "PCF002",
                "PCF003",
                "PCF004",
                "PCF006",
                "PDF000",
                "PDF001",
                "PDF002",
                "PDF100",
                "PDF101",
                "PDF102",
                "PDF103",
                "PDF104",
                "PDF105",
                "PDF109",
                "PDF110",
                "PDF200",
                "PDF201",
                "PDF202",
                "PDF203",
                "PDF204",
                "PDF208",
                "PDF211",
                "PDF300",
                "PDF302",
                "PDF303",
                "PDF304",
                "PDF308",
                "PDF310",
            ),
        )
        self.assertEqual(
            tuple(sorted(set(str(rule.rule.code) for rule in none_selection.rules) - set(str(rule.rule.code) for rule in pep257_selection.rules))),
            ("PDF106", "PDF301", "PDF305", "PDF309"),
        )

    def test_rule_collection_does_not_expose_selector_convenience_indexes(self) -> None:
        collection = sample_collection()

        self.assertFalse(hasattr(collection, "by_code"))
        self.assertFalse(hasattr(collection, "rule_codes"))
        self.assertFalse(hasattr(collection, "rule_prefixes"))
        self.assertFalse(hasattr(collection, "selector_matches_rule"))
        self.assertFalse(hasattr(collection, "selector_matches_some_rule"))
        self.assertFalse(hasattr(collection, "from_metadata"))
        self.assertFalse(hasattr(collection, "from_rule_classes"))

    def test_select_rules_resolves_selection_and_fixability(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF",), ignore=("PDF110",), fixable=("PDF",), unfixable=("PDF110",)),
            collection=sample_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("PDF101",))
        self.assertEqual(tuple(rule.fixable for rule in selection.rules), (True,))

    def test_select_rules_requires_exact_selection_for_require_explicit_rules(self) -> None:
        defaults = rules_selection.select_rules(CheckSettings(select=("ALL",)))
        prefixed = rules_selection.select_rules(CheckSettings(select=("PDF",)))
        mixed_broad = rules_selection.select_rules(CheckSettings(select=("ALL", "PCF001")))
        exact = rules_selection.select_rules(CheckSettings(select=("PDF", "PDF003")))
        extended_exact = rules_selection.select_rules(CheckSettings(extend_select=("PCF005", "PDF003")))
        disabled_requirement = rules_selection.select_rules(CheckSettings(require_explicit=()))

        self.assertEqual(defaults.errors, ())
        self.assertEqual(prefixed.errors, ())
        self.assertEqual(mixed_broad.errors, ())
        self.assertNotIn("PCF005", tuple(rule.rule.code.tag for rule in defaults.rules))
        self.assertNotIn("PDF003", tuple(rule.rule.code.tag for rule in defaults.rules))
        self.assertNotIn("PDF003", tuple(rule.rule.code.tag for rule in prefixed.rules))
        self.assertNotIn("PCF005", tuple(rule.rule.code.tag for rule in mixed_broad.rules))
        self.assertNotIn("PDF003", tuple(rule.rule.code.tag for rule in mixed_broad.rules))
        self.assertIn("PDF003", tuple(rule.rule.code.tag for rule in exact.rules))
        self.assertIn("PCF005", tuple(rule.rule.code.tag for rule in extended_exact.rules))
        self.assertIn("PDF003", tuple(rule.rule.code.tag for rule in extended_exact.rules))
        self.assertIn("PCF005", tuple(rule.rule.code.tag for rule in disabled_requirement.rules))
        self.assertIn("PDF003", tuple(rule.rule.code.tag for rule in disabled_requirement.rules))

    def test_select_rules_reports_require_explicit_selector_errors(self) -> None:
        selection = rules_selection.select_rules(CheckSettings(require_explicit=("bad", "PDF999")))

        self.assertIn("require-explicit rules contains invalid selector: bad", selection.errors)
        self.assertIn("require-explicit rules contains unknown selector: PDF999", selection.errors)

    def test_select_rules_applies_ignored_setting_effect_after_normal_precedence(self) -> None:
        broad = rules_selection.select_rules(CheckSettings(select=("TST",), docstring_convention=DocstringConvention.GOOGLE), collection=setting_effect_collection())
        exact = rules_selection.select_rules(CheckSettings(select=("TST001",), docstring_convention=DocstringConvention.GOOGLE), collection=setting_effect_collection())
        explicitly_ignored = rules_selection.select_rules(
            CheckSettings(select=("TST",), extend_select=("TST001",), ignore=("TST001",), docstring_convention=DocstringConvention.GOOGLE),
            collection=setting_effect_collection(),
        )
        higher_priority_ignore = rules_selection.select_rules(
            CheckSettings(select=("TST001",), ignore=("TST",), docstring_convention=DocstringConvention.GOOGLE),
            collection=setting_effect_collection(),
            field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "ignore": settings_core.ARGUMENT_SOURCE_PRIORITY},
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in broad.rules), ())
        self.assertEqual(tuple(rule.rule.code.tag for rule in exact.rules), ("TST001",))
        self.assertEqual(explicitly_ignored.rules, ())
        self.assertEqual(higher_priority_ignore.rules, ())

    def test_select_rules_retains_exact_setting_effect_override_across_higher_priority_broad_extension(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("TST001",), extend_select=("TST",), docstring_convention=DocstringConvention.GOOGLE),
            collection=setting_effect_collection(),
            field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY},
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST001",))
        self.assertEqual(tuple((rule.enabled_priority, rule.enabled_specificity) for rule in selection.rules), ((settings_core.ARGUMENT_SOURCE_PRIORITY, len("TST")),))

    def test_select_rules_retains_lower_priority_exact_setting_effect_override_when_broad_extension_outweighs_config_ignore(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("TST001",), extend_select=("TST",), ignore=("TST001",), docstring_convention=DocstringConvention.GOOGLE),
            collection=setting_effect_collection(),
            field_priorities={
                "select": settings_core.CONFIG_FILE_SOURCE_PRIORITY,
                "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY,
                "ignore": settings_core.CONFIG_FILE_SOURCE_PRIORITY,
            },
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST001",))

    def test_select_rules_does_not_retain_skipped_lower_priority_exact_setting_effect_override(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("TST",), extend_select=("TST001",), docstring_convention=DocstringConvention.GOOGLE),
            collection=setting_effect_collection(),
            field_priorities={"select": settings_core.ARGUMENT_SOURCE_PRIORITY, "extend_select": settings_core.CONFIG_FILE_SOURCE_PRIORITY},
        )

        self.assertEqual(selection.rules, ())

    def test_select_rules_applies_same_priority_broad_ignore_before_exact_setting_effect_override(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("TST001",), extend_select=("TST",), ignore=("TST",), docstring_convention=DocstringConvention.GOOGLE),
            collection=setting_effect_collection(),
            field_priorities={
                "select": settings_core.CONFIG_FILE_SOURCE_PRIORITY,
                "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY,
                "ignore": settings_core.ARGUMENT_SOURCE_PRIORITY,
            },
        )

        self.assertEqual(selection.rules, ())

    def test_select_rules_applies_per_file_ignore_after_cross_priority_exact_setting_effect_override(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(
                select=("TST001",),
                extend_select=("TST",),
                docstring_convention=DocstringConvention.GOOGLE,
                per_file_ignores=(("tests/*.py", ("TST001",)),),
            ),
            collection=setting_effect_collection(),
            field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY},
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST001",))
        self.assertEqual(selection.for_path("tests/example.py"), ())

    def test_select_rules_combines_multiple_setting_effects_with_disabled_precedence(self) -> None:
        ignored = rules_selection.select_rules(CheckSettings(select=("TST002",), docstring_parse_tables=False), collection=setting_effect_collection())
        disabled = rules_selection.select_rules(
            CheckSettings(select=("TST002",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_tables=False),
            collection=setting_effect_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in ignored.rules), ("TST002",))
        self.assertEqual(disabled.rules, ())

    def test_select_rules_keeps_first_rules_when_incompatibilities_conflict(self) -> None:
        selection = rules_selection.select_rules(CheckSettings(select=("ALL",)), collection=incompatibility_collection())

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST001", "TST003"))
        self.assertEqual(
            selection.errors,
            (
                "Selected rule TST002 is incompatible with earlier selected rule TST001; TST002 has been disabled",
                "Selected rule TST004 is incompatible with earlier selected rules TST001, TST003; TST004 has been disabled",
            ),
        )

    def test_select_rules_applies_setting_effects_before_incompatibilities(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), docstring_convention=DocstringConvention.GOOGLE),
            collection=incompatibility_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST002", "TST004"))
        self.assertEqual(selection.errors, ("Selected rule TST003 is incompatible with earlier selected rule TST002; TST003 has been disabled",))

    def test_select_rules_uses_collection_order_before_selector_strength_for_incompatibilities(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("TST001",), extend_select=("TST004",)),
            collection=incompatibility_collection(),
            field_priorities={"select": settings_core.CONFIG_FILE_SOURCE_PRIORITY, "extend_select": settings_core.ARGUMENT_SOURCE_PRIORITY},
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST001",))
        self.assertEqual(selection.errors, ("Selected rule TST004 is incompatible with earlier selected rule TST001; TST004 has been disabled",))

    def test_select_rules_does_not_restore_incompatible_rules_after_per_file_ignores(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("TST001", "TST004"), per_file_ignores=(("tests/*.py", ("TST001",)),)),
            collection=incompatibility_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST001",))
        self.assertEqual(selection.for_path("tests/example.py"), ())

    def test_select_rules_applies_per_file_ignores_to_exactly_restored_ignored_rules(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("TST001",), docstring_convention=DocstringConvention.GOOGLE, per_file_ignores=(("tests/*.py", ("TST001",)),)),
            collection=setting_effect_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("TST001",))
        self.assertEqual(selection.for_path("tests/example.py"), ())

    def test_select_rules_rejects_unknown_setting_effect_fields(self) -> None:
        class TSTUnknownSettingEffectCategory(RuleCategoryBase):
            meta = RuleCategoryMetadata(prefix="TST", name="unknown setting effect", url=None)

        class TST999UnknownSettingEffectRule(RuleBase):
            meta = RuleMetadata(
                code=RuleCode("TST999"),
                name="unknown-setting",
                message="Unknown setting",
                fix_availability=FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(
                    RuleSettingEffects(
                        setting="unknown_setting",
                        effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(True,)),),
                    ),
                ),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )
            violations = classmethod(_no_violations)

        rule_registration.register_rule_to(TSTUnknownSettingEffectCategory)(TST999UnknownSettingEffectRule)

        with self.assertRaisesRegex(ValueError, "TST999: Unknown rule setting effect field: unknown_setting"):
            rules_selection.select_rules(CheckSettings(select=("TST999",)), collection=rule_collection.RuleCollection((TSTUnknownSettingEffectCategory,)))

    def test_select_rules_prefers_more_specific_select_over_broader_ignore(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), extend_select=("PDF14",), ignore=("PDF1",)),
            collection=specificity_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("PDF142",))

    def test_select_rules_prefers_more_specific_ignore_over_broader_select(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF1",), ignore=("PDF14",)),
            collection=specificity_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("PDF150",))

    def test_select_rules_ignore_wins_equal_specificity(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF14",), ignore=("PDF14",)),
            collection=specificity_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(selection.rules, ())

    def test_select_rules_all_is_less_specific_than_exact_extensions(self) -> None:
        selected_rule = rules_selection.select_rules(
            CheckSettings(select=("ALL",), extend_select=("PDF142",), ignore=("ALL",)),
            collection=specificity_collection(),
        )
        selected_fix = rules_selection.select_rules(
            CheckSettings(select=("PDF1",), fixable=("ALL",), extend_fixable=("PDF142",), unfixable=("ALL",)),
            collection=specificity_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selected_rule.rules), ("PDF142",))
        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in selected_fix.rules), (("PDF142", True), ("PDF150", False)))

    def test_select_rules_uses_source_priority_before_specificity(self) -> None:
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

        self.assertEqual(tuple(rule.rule.code.tag for rule in lower_priority_ignore.rules), ("PDF142", "PDF150"))
        self.assertEqual(higher_priority_ignore.rules, ())
        self.assertEqual(tuple(rule.rule.code.tag for rule in higher_priority_extend_select.rules), ("PDF142", "PDF150"))
        self.assertEqual(tuple(rule.rule.code.tag for rule in lower_priority_extend_select.rules), ("PDF142",))

    def test_select_rules_reports_errors_from_lower_priority_skipped_selectors(self) -> None:
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

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("PDF142",))
        self.assertIn("rule selection contains unknown selector: PDF999", selection.errors)
        self.assertIn("ignored rules contains invalid selector: bad", selection.errors)
        self.assertIn("fixable rules contains unknown selector: PDF999", selection.errors)
        self.assertIn("unfixable rules contains invalid selector: bad", selection.errors)

    def test_select_rules_applies_per_file_ignores_without_enabled_selector_specificity(self) -> None:
        broader_ignore = rules_selection.select_rules(
            CheckSettings(select=("PDF14",), per_file_ignores=(("tests/*.py", ("PDF1",)),)),
            collection=specificity_collection(),
        )
        more_specific_ignore = rules_selection.select_rules(
            CheckSettings(select=("PDF1",), per_file_ignores=(("tests/*.py", ("PDF14",)),)),
            collection=specificity_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in broader_ignore.for_path("tests/a.py")), ())
        self.assertEqual(tuple(rule.rule.code.tag for rule in more_specific_ignore.for_path("tests/a.py")), ("PDF150",))

    def test_ruff_spec_repeated_cli_per_file_ignore_patterns_append_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            self._write(target)
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                profile = SETTINGS_SCHEMA.load_profile(
                    args=argparse.Namespace(
                        select=["PDF200,PDF110"],
                        per_file_ignores=[
                            '{"a.py" = ["PDF200"]}',
                            '{"a.py" = ["PDF110"]}',
                        ],
                    ),
                    path=str(target),
                )
            finally:
                os.chdir(previous_cwd)

        selection = rules_selection.select_rules(profile.settings, profile=profile)

        self.assertEqual(profile.settings.per_file_ignores, (("a.py", ("PDF200", "PDF110")),))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("PDF110", "PDF200"))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path(str(target))), ())

    def test_select_rules_applies_fixability_specificity(self) -> None:
        specific_fixable = rules_selection.select_rules(
            CheckSettings(select=("PDF1",), fixable=("PDF14",), unfixable=("PDF1",)),
            collection=specificity_collection(),
        )
        specific_unfixable = rules_selection.select_rules(
            CheckSettings(select=("PDF1",), fixable=("PDF1",), unfixable=("PDF14",)),
            collection=specificity_collection(),
        )
        equal_unfixable = rules_selection.select_rules(
            CheckSettings(select=("PDF14",), fixable=("PDF14",), unfixable=("PDF14",)),
            collection=specificity_collection(),
        )

        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in specific_fixable.rules), (("PDF142", True), ("PDF150", False)))
        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in specific_unfixable.rules), (("PDF142", False), ("PDF150", True)))
        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in equal_unfixable.rules), (("PDF142", False),))

    def test_select_rules_uses_source_priority_for_fixability(self) -> None:
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

        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in lower_priority_unfixable.rules), (("PDF142", True), ("PDF150", True)))
        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in higher_priority_unfixable.rules), (("PDF142", False), ("PDF150", True)))
        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in lower_priority_extend_fixable.rules), (("PDF142", True), ("PDF150", False)))

    def test_select_rules_treats_per_instance_fixable_rules_as_having_available_fixes(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF160", "PDF170"), fixable=("PDF160", "PDF170")),
            collection=fix_availability_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in selection.rules), (("PDF160", True), ("PDF170", True)))

    def test_select_rules_reports_selector_operational_errors(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("BAD", "bad"), fixable=("PDF110",)),
            collection=sample_collection(),
        )

        self.assertIn("rule selection contains unknown selector: BAD", selection.errors)
        self.assertIn("rule selection contains invalid selector: bad", selection.errors)
        self.assertIn("fixable rules selector 'PDF110' only matches rules with no available fixes", selection.errors)

    def test_select_rules_applies_per_file_ignores(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), per_file_ignores=(("tests/*.py", ("PDF101",)),)),
            collection=sample_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("src/a.py")), ("PCF001", "PDF101", "PDF110"))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("tests/a.py")), ("PCF001", "PDF110"))

    def test_ruff_spec_negated_per_file_ignore_patterns_ignore_everywhere_else(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF",), per_file_ignores=(("!src/*.py", ("PDF101",)), ("!tests/*.py", ("PDF110",)))),
            collection=sample_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("src/a.py")), ("PDF101",))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("tests/a.py")), ("PDF110",))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("a.py")), ())

    def test_ruff_spec_per_file_ignores_are_auto_config_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "src" / "pkg" / "a.py"
            self._write(target)
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')
                matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"pkg/*.py" = ["PDF101"]}\n')
                non_matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"*.py" = ["PDF101"]}\n')
                bare_star_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"a.py" = ["PDF101"]}\n')
                bare_literal_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF101",))
        self.assertEqual(self._active_rule_tags_for_path(bare_star_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(bare_literal_profile, target), ())

    def test_ruff_spec_per_file_ignores_do_not_use_git_root_as_base(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            target = root / "src" / "pkg" / "a.py"
            self._write(target)
            previous_cwd = os.getcwd()
            os.chdir(root / "src" / "pkg")
            try:
                self._write(root / "src" / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"pkg/*.py" = ["PDF101"]}\n')
                matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "src" / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')
                non_matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF101",))

    def test_ruff_spec_explicit_config_per_file_ignores_are_current_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            config = root / "config" / "pydocfmt.toml"
            target = repo / "src" / "pkg" / "a.py"
            self._write(target)
            self._write(config, 'select = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')

            previous_cwd = os.getcwd()
            os.chdir(repo)
            try:
                matching_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))
            finally:
                os.chdir(previous_cwd)

            os.chdir(repo / "src")
            try:
                non_matching_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))
                self._write(config, 'select = ["PDF101"]\nper-file-ignores = {"pkg/*.py" = ["PDF101"]}\n')
                changed_pattern_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF101",))
        self.assertEqual(self._active_rule_tags_for_path(changed_pattern_profile, target), ())

    def test_ruff_spec_cli_per_file_ignores_are_current_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "src" / "pkg" / "a.py"
            self._write(target)
            self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\n')
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                matching_profile = SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(per_file_ignores=['{"pkg/*.py" = ["PDF101"]}']), path=str(target))
                non_matching_profile = SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(per_file_ignores=['{"src/pkg/*.py" = ["PDF101"]}']), path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF101",))

    def test_ruff_spec_per_file_ignores_apply_to_explicit_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "src" / "pkg" / "a.py"
            self._write(target)
            self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF101"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF101"]}\n')
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                selection = file_selection.select_files(["pkg/a.py"], SETTINGS_SCHEMA.resolver())
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(selection.accepted_paths, (str(target),))
        self.assertEqual(self._active_rule_tags_for_path(selection.profile_for_path(str(target)), target), ())

    def test_print_rules_prints_active_rules_with_effective_fixability(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), unfixable=("PCF001",)),
            collection=sample_collection(),
        )
        output = StringIO()

        check.print_rules(selection, output=output)

        self.assertEqual(
            output.getvalue(),
            "PCF001 comment-reflow-required (Comment chunk needs reflow)\n"
            "PDF101* docstring-reflow (Docstring chunk needs reflow)\n"
            "PDF110 summary-too-long (Docstring summary does not fit on one line)\n",
        )

    def test_print_rules_reflects_setting_aware_selection(self) -> None:
        broad_output = StringIO()
        exact_output = StringIO()

        check.print_rules(rules_selection.select_rules(CheckSettings(docstring_convention=DocstringConvention.GOOGLE)), output=broad_output)
        check.print_rules(rules_selection.select_rules(CheckSettings(select=("PDF107",), docstring_convention=DocstringConvention.GOOGLE)), output=exact_output)

        self.assertIn("PDF106*", broad_output.getvalue())
        self.assertNotIn("PDF107", broad_output.getvalue())
        self.assertNotIn("PDF108", broad_output.getvalue())
        self.assertIn("PDF107*", exact_output.getvalue())

    def test_print_rules_prints_operational_errors_before_rules(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("BAD",), fixable=("PDF110",)),
            collection=sample_collection(),
        )
        output = StringIO()

        check.print_rules(selection, output=output)

        self.assertEqual(
            output.getvalue(),
            "ERROR: rule selection contains unknown selector: BAD\n" "ERROR: fixable rules selector 'PDF110' only matches rules with no available fixes\n" "\n" "No active rules.\n",
        )

    def test_print_rules_prints_empty_message_without_active_rules(self) -> None:
        selection = rules_selection.select_rules(CheckSettings(select=("PDF",), ignore=("PDF",)), collection=sample_collection())
        output = StringIO()

        check.print_rules(selection, output=output)

        self.assertEqual(output.getvalue(), "No active rules.\n")

    def test_print_rules_ignores_per_file_rule_ignores(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), per_file_ignores=(("tests/*.py", ("PDF101",)),)),
            collection=sample_collection(),
        )
        output = StringIO()

        check.print_rules(selection, output=output)

        self.assertIn("PDF101* docstring-reflow (Docstring chunk needs reflow)\n", output.getvalue())


if __name__ == "__main__":
    unittest.main()
