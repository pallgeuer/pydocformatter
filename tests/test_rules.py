import dataclasses
import typing
import unittest
from io import StringIO

import pydocformatter.cli.check as check
import pydocformatter.rules.base as rule_base
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definitions as rule_definitions
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata, RuleSelector


class PDF001SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fixable=True)


class PDF105SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fixable=False)


class PDF142SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF142"), name="specific-rule", message="Specific rule", fixable=True)


class PDF150SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF150"), name="sibling-rule", message="Sibling rule", fixable=True)


class PCF001SampleRule(RuleBase):
    meta = RuleMetadata(code=RuleCode("PCF001"), name="comment-reflow-required", message="Comment chunk needs reflow", fixable=True)


def sample_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for selector tests."""
    return rule_collection.RuleCollection((PDF001SampleRule, PDF105SampleRule, PCF001SampleRule))


def specificity_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for selector specificity tests."""
    return rule_collection.RuleCollection((PDF142SampleRule, PDF150SampleRule))


class TestRules(unittest.TestCase):
    def test_default_rule_collection_is_collected_on_import(self) -> None:
        collection = rule_collection.RULE_COLLECTION

        self.assertEqual(collection.rules, ())

    def test_rule_registry_collects_rule_metadata(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fixable=True)

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
                meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fixable=True)

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
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fixable=True)

        self.assertEqual(registry.collection().rules, (PDF999TestRule,))

    def test_rule_collection_rejects_duplicate_rule_codes_from_different_classes(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999FirstRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="first-rule", message="First rule", fixable=True)

        class PDF999SecondRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="second-rule", message="Second rule", fixable=True)

        registry.register(PDF999FirstRule)
        registry.register(PDF999SecondRule)

        with self.assertRaisesRegex(ValueError, "Duplicate rule code: PDF999"):
            registry.collection()

    def test_rule_registry_allows_registering_the_same_rule_class_twice(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fixable=True)

        registry.register(PDF999TestRule)
        registry.register(PDF999TestRule)

        self.assertEqual(registry.collection().rules, (PDF999TestRule,))

    def test_rule_collection_allows_the_same_rule_class_twice(self) -> None:
        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fixable=True)

        collection = rule_collection.RuleCollection((PDF999TestRule, PDF999TestRule))

        self.assertEqual(collection.rules, (PDF999TestRule,))

    def test_rule_registry_rejects_non_rule_base_classes(self) -> None:
        registry = rule_collection.RuleRegistry()

        with self.assertRaisesRegex(TypeError, "Registered rule must inherit RuleBase"):
            registry.register(typing.cast(type[RuleBase], object))

    def test_rule_registry_is_frozen_but_keeps_mutable_registration_state(self) -> None:
        registry = rule_collection.RuleRegistry()

        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fixable=True)

        registry.register(PDF999TestRule)

        with self.assertRaises(dataclasses.FrozenInstanceError):
            setattr(registry, "rule_classes", set())
        self.assertEqual(registry.collection().rules, (PDF999TestRule,))

    def test_rule_registries_are_isolated(self) -> None:
        default_registry = rule_collection.RuleRegistry()
        isolated_registry = rule_collection.RuleRegistry()

        @rule_collection.register_rule_to(default_registry)
        class PDF999DefaultRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF999"), name="default-rule", message="Default rule", fixable=True)

        @rule_collection.register_rule_to(isolated_registry)
        class PDF998IsolatedRule(RuleBase):
            meta = RuleMetadata(code=RuleCode("PDF998"), name="isolated-rule", message="Isolated rule", fixable=True)

        self.assertEqual(default_registry.collection().rules, (PDF999DefaultRule,))
        self.assertEqual(isolated_registry.collection().rules, (PDF998IsolatedRule,))

    def test_rule_metadata_derives_prefix_and_number_from_code(self) -> None:
        rule = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fixable=True)

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
        self.assertEqual(tuple(field.name for field in dataclasses.fields(RuleMetadata)), ("code", "name", "message", "fixable"))
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
            RuleMetadata(code=typing.cast(typing.Any, "bad"), name="bad-rule", message="Bad rule", fixable=True)

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
            meta = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test rule", fixable=True)

        rule = PDF999TestRule()

        self.assertEqual(
            (PDF999TestRule.code, PDF999TestRule.prefix, PDF999TestRule.number_str, PDF999TestRule.number, PDF999TestRule.name, PDF999TestRule.message, PDF999TestRule.fixable),
            ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", True),
        )
        self.assertEqual((rule.code, rule.prefix, rule.number_str, rule.number, rule.name, rule.message, rule.fixable), ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", True))

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

    def test_select_rules_applies_per_file_ignore_specificity(self) -> None:
        broader_ignore = rules_selection.select_rules(
            CheckSettings(select=("PDF14",), per_file_ignores=(("tests/*.py", ("PDF1",)),)),
            collection=specificity_collection(),
        )
        more_specific_ignore = rules_selection.select_rules(
            CheckSettings(select=("PDF1",), per_file_ignores=(("tests/*.py", ("PDF14",)),)),
            collection=specificity_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in broader_ignore.for_path("tests/a.py")), ("PDF142",))
        self.assertEqual(tuple(rule.rule.code.tag for rule in more_specific_ignore.for_path("tests/a.py")), ("PDF150",))

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

    def test_select_rules_reports_selector_operational_errors(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("BAD", "bad"), fixable=("PDF105",)),
            collection=sample_collection(),
        )

        self.assertIn("rule selection contains unknown selector: BAD", selection.errors)
        self.assertIn("rule selection contains invalid selector: bad", selection.errors)
        self.assertIn("fixable rules selector 'PDF105' only matches inherently unfixable rules", selection.errors)

    def test_select_rules_applies_per_file_ignores(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("ALL",), per_file_ignores=(("tests/*.py", ("PDF001",)),)),
            collection=sample_collection(),
        )

        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("src/a.py")), ("PCF001", "PDF001", "PDF105"))
        self.assertEqual(tuple(rule.rule.code.tag for rule in selection.for_path("tests/a.py")), ("PCF001", "PDF105"))

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
            "ERROR: rule selection contains unknown selector: BAD\n" "ERROR: fixable rules selector 'PDF105' only matches inherently unfixable rules\n" "\n" "No active rules.\n",
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
