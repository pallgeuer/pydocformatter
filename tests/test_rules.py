import argparse
import dataclasses
import importlib
import inspect
import os
import pkgutil
import tempfile
import typing
import unittest
from io import StringIO
from pathlib import Path

import pydocformatter.cli.check as check
import pydocformatter.file_selection as file_selection
import pydocformatter.rules.base as rule_base
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definitions as rule_definitions
import pydocformatter.rules.documentation as rule_documentation
import pydocformatter.rules_selection as rules_selection
import pydocformatter.settings as settings_core
from pydocformatter.cli.global_args import GlobalArgs
from pydocformatter.cli.settings_check import SETTINGS_SCHEMA, CheckSettings
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata, RuleSelector


class PDF001SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")


class PDF105SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fix_availability=FixAvailability.NEVER, stable_since="0.3.0")


class PDF142SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF142"), name="specific-rule", message="Specific rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")


class PDF150SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF150"), name="sibling-rule", message="Sibling rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")


class PDF160SometimesFixableSampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF160"), name="sometimes-fixable-rule", message="Sometimes fixable rule", fix_availability=FixAvailability.SOMETIMES, stable_since="0.3.0")


class PCF001SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PCF001"), name="comment-reflow-required", message="Comment chunk needs reflow", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")


def sample_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for selector tests."""
    return rule_collection.RuleCollection((PDF001SampleRule, PDF105SampleRule, PCF001SampleRule))


def specificity_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for selector specificity tests."""
    return rule_collection.RuleCollection((PDF142SampleRule, PDF150SampleRule))


def fix_availability_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for rule-level fix availability tests."""
    return rule_collection.RuleCollection((PDF105SampleRule, PDF160SometimesFixableSampleRule))


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

    def test_default_rule_collection_is_collected_on_import(self) -> None:
        collection = rule_collection.RULE_COLLECTION
        rule_module_names = tuple(module.name for module in pkgutil.walk_packages(path=rule_definitions.__path__, prefix=f"{rule_definitions.__name__}.") if not module.ispkg)
        discovered_rule_classes: list[type[RuleBase]] = []
        modules_without_rules: list[str] = []

        for module_name in rule_module_names:
            module = importlib.import_module(module_name)
            module_rule_classes = [rule_class for _, rule_class in inspect.getmembers(module, inspect.isclass) if rule_class.__module__ == module.__name__ and issubclass(rule_class, RuleBase)]
            if not module_rule_classes:
                modules_without_rules.append(module_name)
            discovered_rule_classes.extend(module_rule_classes)

        self.assertEqual(modules_without_rules, [])
        self.assertEqual(collection.rules, rule_collection.RuleCollection(discovered_rule_classes).rules)
        self.assertEqual(rule_documentation.undocumented_rules(collection), ())
        self.assertTrue(rule_documentation.TEMPLATE_PATH.is_file())
        for rule_class in collection.rules:
            explanation = rule_documentation.load_rule_explanation(rule_class)
            self.assertTrue(explanation.startswith(f"# {rule_class.meta.name} ({rule_class.meta.code})\n\n"))
            self.assertIn(f"\n\n{rule_base.rule_fix_text(rule_class.meta)}\n\n", explanation)

    def test_rule_registry_collects_rule_metadata(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        registry.register(PDF999TestRule)

        self.assertEqual(registry.rule_classes, {PDF999TestRule})
        self.assertEqual(registry.collection().rules, (PDF999TestRule,))
        self.assertEqual(registry.collection().rule_class, {RuleCode("PDF999"): PDF999TestRule})

    def test_register_rule_decorator_collects_rule_metadata_in_default_registry(self) -> None:
        previous_registry = rule_collection.DEFAULT_RULE_REGISTRY
        rule_collection.DEFAULT_RULE_REGISTRY = rule_collection.RuleRegistry()
        try:

            @rule_collection.register_rule
            class PDF999TestRule(RuleBase):
                meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

            collection = rule_collection.DEFAULT_RULE_REGISTRY.collection()
        finally:
            rule_collection.DEFAULT_RULE_REGISTRY = previous_registry

        self.assertEqual(collection.rules, (PDF999TestRule,))

    def test_import_package_rules_imports_package_modules(self) -> None:
        rule_collection.import_package_rules(package=rule_definitions)

    def test_register_rule_to_collects_rule_metadata_in_bound_registry(self) -> None:
        registry = rule_collection.RuleRegistry()

        @rule_collection.register_rule_to(registry)
        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        self.assertEqual(registry.collection().rules, (PDF999TestRule,))

    def test_rule_collection_rejects_duplicate_rule_codes_from_different_classes(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999FirstRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="first-rule", message="First rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        class PDF999SecondRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="second-rule", message="Second rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        registry.register(PDF999FirstRule)
        registry.register(PDF999SecondRule)

        with self.assertRaisesRegex(ValueError, "Duplicate rule code: PDF999"):
            registry.collection()

    def test_rule_registry_allows_registering_the_same_rule_class_twice(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        registry.register(PDF999TestRule)
        registry.register(PDF999TestRule)

        self.assertEqual(registry.collection().rules, (PDF999TestRule,))

    def test_rule_collection_allows_the_same_rule_class_twice(self) -> None:
        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        collection = rule_collection.RuleCollection((PDF999TestRule, PDF999TestRule))

        self.assertEqual(collection.rules, (PDF999TestRule,))

    def test_rule_registry_rejects_non_rule_base_classes(self) -> None:
        registry = rule_collection.RuleRegistry()

        with self.assertRaisesRegex(TypeError, "Registered rule must inherit RuleBase"):
            registry.register(typing.cast(type[RuleBase], object))

    def test_rule_registry_is_frozen_but_keeps_mutable_registration_state(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        registry.register(PDF999TestRule)

        with self.assertRaises(dataclasses.FrozenInstanceError):
            setattr(registry, "rule_classes", set())
        self.assertEqual(registry.collection().rules, (PDF999TestRule,))

    def test_rule_registries_are_isolated(self) -> None:
        default_registry = rule_collection.RuleRegistry()
        isolated_registry = rule_collection.RuleRegistry()

        @rule_collection.register_rule_to(default_registry)
        class PDF999DefaultRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="default-rule", message="Default rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        @rule_collection.register_rule_to(isolated_registry)
        class PDF998IsolatedRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF998"), name="isolated-rule", message="Isolated rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        self.assertEqual(default_registry.collection().rules, (PDF999DefaultRule,))
        self.assertEqual(isolated_registry.collection().rules, (PDF998IsolatedRule,))

    def test_rule_metadata_derives_prefix_and_number_from_code(self) -> None:
        rule = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        self.assertEqual(tuple(field.name for field in dataclasses.fields(RuleCode)), ("tag", "prefix", "number_str", "number"))
        self.assertEqual(str(rule.code), "PDF001")
        self.assertEqual(rule.code.tag, "PDF001")
        self.assertEqual(rule.code.prefix, "PDF")
        self.assertEqual(rule.code.number_str, "001")
        self.assertEqual(rule.code.number, 1)
        self.assertTrue(RuleCode.is_valid_tag("PDF001"))
        self.assertFalse(RuleCode.is_valid_tag("001"))
        self.assertFalse(RuleCode.is_valid_tag("ALL001"))
        self.assertFalse(hasattr(rule_base, "valid_rule_code_tag"))
        self.assertFalse(hasattr(rule_base, "split_rule_code"))
        self.assertEqual(rule.stable_since, "0.3.0")
        self.assertEqual(tuple(field.name for field in dataclasses.fields(RuleMetadata)), ("code", "name", "message", "fix_availability", "stable_since"))
        self.assertTrue(all(field.default is dataclasses.MISSING for field in dataclasses.fields(RuleMetadata)))
        self.assertEqual(rule_base.rule_fix_text(rule), "Fix is always available.")
        self.assertEqual(
            rule_base.rule_fix_text(RuleMetadata(code=RuleCode("PDF999"), name="sometimes-rule", message="Sometimes rule", fix_availability=FixAvailability.SOMETIMES, stable_since="0.3.0")),
            "Fix is sometimes available.",
        )
        self.assertEqual(str(FixAvailability.SOMETIMES), "Sometimes")
        self.assertFalse(hasattr(rule, "matches_selector"))
        self.assertFalse(hasattr(rule, "matches_selector_parts"))

    def test_rule_selector_selects_code(self) -> None:
        code = RuleCode("PDF105")

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
        self.assertFalse(hasattr(rule_base, "rule_selector_is_valid"))
        self.assertFalse(hasattr(rule_base, "split_rule_selector"))
        self.assertTrue(RuleSelector("ALL").selects_code(code))
        self.assertTrue(RuleSelector("PDF").selects_code(code))
        self.assertTrue(RuleSelector("PDF1").selects_code(code))
        self.assertTrue(selector.selects_code(code))
        self.assertFalse(RuleSelector("PDF106").selects_code(code))
        self.assertFalse(RuleSelector("P").selects_code(code))

    def test_rule_metadata_validates_rule_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid rule code: bad"):
            RuleCode("bad")
        with self.assertRaisesRegex(ValueError, "Invalid rule code: ALL001"):
            RuleCode("ALL001")
        with self.assertRaisesRegex(TypeError, "Expected RuleCode, got str"):
            RuleMetadata(code=typing.cast(typing.Any, "bad"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")
        with self.assertRaisesRegex(TypeError, "Expected FixAvailability, got str"):
            RuleMetadata(code=RuleCode("PDF001"), name="bad-rule", message="Bad rule", fix_availability=typing.cast(typing.Any, "Always"), stable_since="0.3.0")
        with self.assertRaisesRegex(TypeError, "missing 1 required positional argument: 'stable_since'"):
            RuleMetadata(code=RuleCode("PDF001"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS)  # type: ignore[call-arg]
        with self.assertRaisesRegex(ValueError, "PDF001: Stable version must not be empty"):
            RuleMetadata(code=RuleCode("PDF001"), name="bad-rule", message="Bad rule", fix_availability=FixAvailability.ALWAYS, stable_since="")

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

    def test_rule_base_class_properties_redirect_to_metadata(self) -> None:
        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        rule = PDF999TestRule()

        self.assertEqual(
            (PDF999TestRule.code, PDF999TestRule.prefix, PDF999TestRule.number_str, PDF999TestRule.number, PDF999TestRule.name, PDF999TestRule.message, PDF999TestRule.fix_availability),
            ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", FixAvailability.ALWAYS),
        )
        self.assertEqual(PDF999TestRule.stable_since, "0.3.0")
        self.assertEqual(
            (rule.code, rule.prefix, rule.number_str, rule.number, rule.name, rule.message, rule.fix_availability, rule.stable_since),
            ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", FixAvailability.ALWAYS, "0.3.0"),
        )

    def test_selectors_must_use_complete_rule_prefixes(self) -> None:
        collection = sample_collection()

        self.assertTrue(collection.matching_rules_exist(RuleSelector("ALL")))
        self.assertTrue(collection.matching_rules_exist(RuleSelector("PDF")))
        self.assertTrue(collection.matching_rules_exist(RuleSelector("PDF1")))
        self.assertTrue(collection.matching_rules_exist(RuleSelector("PDF10")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("PDF107")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("R")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("P")))
        self.assertFalse(collection.matching_rules_exist(RuleSelector("RD")))

    def test_rule_collection_orders_rules_and_rule_class_index_the_same_way(self) -> None:
        collection = sample_collection()

        self.assertEqual(collection.rules, (PCF001SampleRule, PDF001SampleRule, PDF105SampleRule))
        self.assertEqual(tuple(collection.rule_class.values()), collection.rules)

    def test_rule_collection_matching_rules_returns_rule_classes(self) -> None:
        collection = sample_collection()

        self.assertEqual(collection.matching_rules(RuleSelector("PDF")), (PDF001SampleRule, PDF105SampleRule))

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
            CheckSettings(select=("PDF",), ignore=("PDF105",), fixable=("PDF",), unfixable=("PDF105",)),
            collection=sample_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("PDF001",))
        self.assertEqual(tuple(rule.fixable for rule in selection.rules), (True,))

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
                        select=["PDF100,PDF105"],
                        per_file_ignores=[
                            '{"a.py" = ["PDF100"]}',
                            '{"a.py" = ["PDF105"]}',
                        ],
                    ),
                    path=str(target),
                )
            finally:
                os.chdir(previous_cwd)

        selection = rules_selection.select_rules(profile.settings, profile=profile)

        self.assertEqual(profile.settings.per_file_ignores, (("a.py", ("PDF100", "PDF105")),))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.rules), ("PDF100", "PDF105"))
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

    def test_select_rules_treats_sometimes_fixable_rules_as_having_available_fixes(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF160",), fixable=("PDF160",)),
            collection=fix_availability_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(tuple((rule.rule.code.tag, rule.fixable) for rule in selection.rules), (("PDF160", True),))

    def test_select_rules_reports_selector_operational_errors(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("BAD", "bad"), fixable=("PDF105",)),
            collection=sample_collection(),
        )

        self.assertIn("rule selection contains unknown selector: BAD", selection.errors)
        self.assertIn("rule selection contains invalid selector: bad", selection.errors)
        self.assertIn("fixable rules selector 'PDF105' only matches rules with no available fixes", selection.errors)

    def test_select_rules_applies_per_file_ignores(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), per_file_ignores=(("tests/*.py", ("PDF001",)),)),
            collection=sample_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("src/a.py")), ("PCF001", "PDF001", "PDF105"))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("tests/a.py")), ("PCF001", "PDF105"))

    def test_ruff_spec_negated_per_file_ignore_patterns_ignore_everywhere_else(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF",), per_file_ignores=(("!src/*.py", ("PDF001",)), ("!tests/*.py", ("PDF105",)))),
            collection=sample_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("src/a.py")), ("PDF001",))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("tests/a.py")), ("PDF105",))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("a.py")), ())

    def test_ruff_spec_per_file_ignores_are_auto_config_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "src" / "pkg" / "a.py"
            self._write(target)
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF001"]}\n')
                matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\nper-file-ignores = {"pkg/*.py" = ["PDF001"]}\n')
                non_matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\nper-file-ignores = {"*.py" = ["PDF001"]}\n')
                bare_star_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\nper-file-ignores = {"a.py" = ["PDF001"]}\n')
                bare_literal_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF001",))
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
                self._write(root / "src" / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\nper-file-ignores = {"pkg/*.py" = ["PDF001"]}\n')
                matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
                self._write(root / "src" / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF001"]}\n')
                non_matching_profile = SETTINGS_SCHEMA.load_profile(path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF001",))

    def test_ruff_spec_explicit_config_per_file_ignores_are_current_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            config = root / "config" / "pydocfmt.toml"
            target = repo / "src" / "pkg" / "a.py"
            self._write(target)
            self._write(config, 'select = ["PDF001"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF001"]}\n')

            previous_cwd = os.getcwd()
            os.chdir(repo)
            try:
                matching_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))
            finally:
                os.chdir(previous_cwd)

            os.chdir(repo / "src")
            try:
                non_matching_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))
                self._write(config, 'select = ["PDF001"]\nper-file-ignores = {"pkg/*.py" = ["PDF001"]}\n')
                changed_pattern_profile = SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(config_options=(str(config),)), path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF001",))
        self.assertEqual(self._active_rule_tags_for_path(changed_pattern_profile, target), ())

    def test_ruff_spec_cli_per_file_ignores_are_current_directory_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "src" / "pkg" / "a.py"
            self._write(target)
            self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\n')
            previous_cwd = os.getcwd()
            os.chdir(root / "src")
            try:
                matching_profile = SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(per_file_ignores=['{"pkg/*.py" = ["PDF001"]}']), path=str(target))
                non_matching_profile = SETTINGS_SCHEMA.load_profile(args=argparse.Namespace(per_file_ignores=['{"src/pkg/*.py" = ["PDF001"]}']), path=str(target))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(self._active_rule_tags_for_path(matching_profile, target), ())
        self.assertEqual(self._active_rule_tags_for_path(non_matching_profile, target), ("PDF001",))

    def test_ruff_spec_per_file_ignores_apply_to_explicit_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "src" / "pkg" / "a.py"
            self._write(target)
            self._write(root / "pyproject.toml", '[tool.pydocfmt]\nselect = ["PDF001"]\nper-file-ignores = {"src/pkg/*.py" = ["PDF001"]}\n')
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
            "PDF001* reflow-required (Docstring chunk needs reflow)\n"
            "PDF105 summary-too-long (Docstring summary does not fit on one line)\n",
        )

    def test_print_rules_prints_operational_errors_before_rules(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("BAD",), fixable=("PDF105",)),
            collection=sample_collection(),
        )
        output = StringIO()

        check.print_rules(selection, output=output)

        self.assertEqual(
            output.getvalue(),
            "ERROR: rule selection contains unknown selector: BAD\n" "ERROR: fixable rules selector 'PDF105' only matches rules with no available fixes\n" "\n" "No active rules.\n",
        )

    def test_print_rules_prints_empty_message_without_active_rules(self) -> None:
        selection = rules_selection.select_rules(CheckSettings(select=("PDF",), ignore=("PDF",)), collection=sample_collection())
        output = StringIO()

        check.print_rules(selection, output=output)

        self.assertEqual(output.getvalue(), "No active rules.\n")

    def test_print_rules_ignores_per_file_rule_ignores(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), per_file_ignores=(("tests/*.py", ("PDF001",)),)),
            collection=sample_collection(),
        )
        output = StringIO()

        check.print_rules(selection, output=output)

        self.assertIn("PDF001* reflow-required (Docstring chunk needs reflow)\n", output.getvalue())


if __name__ == "__main__":
    unittest.main()
