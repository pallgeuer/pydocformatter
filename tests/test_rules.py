import dataclasses
import unittest
from io import StringIO

import pydocformatter.cli.check as check
import pydocformatter.rules.base as rule_base
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.base import RuleBase, RuleMetadata


def sample_collection() -> rule_collection.RuleCollection:
    """Return a synthetic rule collection for selector tests."""
    return rule_collection.RuleCollection.from_metadata(
        (
            RuleMetadata(code="PDF001", name="reflow-required", message="Docstring chunk needs reflow", fixable=True),
            RuleMetadata(code="PDF105", name="summary-too-long", message="Docstring summary does not fit on one line", fixable=False),
            RuleMetadata(code="PCF001", name="comment-reflow-required", message="Comment chunk needs reflow", fixable=True),
        )
    )


class TestRules(unittest.TestCase):
    def test_empty_definitions_collect_empty_rule_catalog(self) -> None:
        collection = rule_collection.collect_rules()

        self.assertEqual(collection.rules, ())

    def test_register_rule_decorator_collects_rule_metadata(self) -> None:
        previous_rules = dict(rule_collection._REGISTERED_RULES)
        rule_collection._REGISTERED_RULES.clear()
        try:

            @rule_collection.register_rule
            class PDF999TestRule(RuleBase):
                meta = RuleMetadata(code="PDF999", name="test-rule", message="Test rule", fixable=True)

            collection = rule_collection.collect_rules()
        finally:
            rule_collection._REGISTERED_RULES.clear()
            rule_collection._REGISTERED_RULES.update(previous_rules)

        self.assertEqual(collection.rules, (RuleMetadata(code="PDF999", name="test-rule", message="Test rule", fixable=True),))

    def test_rule_metadata_derives_prefix_and_number_from_code(self) -> None:
        rule = RuleMetadata(code="PDF001", name="reflow-required", message="Docstring chunk needs reflow", fixable=True)

        self.assertTrue(rule_base.rule_code_is_valid("PDF001"))
        self.assertFalse(rule_base.rule_code_is_valid("001"))
        self.assertEqual(rule_base.split_rule_code("PDF001"), ("PDF", "001"))
        with self.assertRaises(ValueError):
            rule_base.split_rule_code("001")
        self.assertEqual(tuple(field.name for field in dataclasses.fields(RuleMetadata)), ("code", "prefix", "number_str", "number", "name", "message", "fixable"))
        self.assertEqual(rule.prefix, "PDF")
        self.assertEqual(rule.number_str, "001")
        self.assertEqual(rule.number, 1)

    def test_rule_metadata_matches_selector_parts(self) -> None:
        rule = RuleMetadata(code="PDF105", name="summary-too-long", message="Docstring summary does not fit on one line", fixable=False)

        self.assertTrue(rule_base.rule_selector_is_valid("PDF10"))
        self.assertFalse(rule_base.rule_selector_is_valid("bad"))
        self.assertEqual(rule_base.split_rule_selector("PDF10"), ("PDF", "10"))
        with self.assertRaises(ValueError):
            rule_base.split_rule_selector("bad")
        self.assertTrue(rule.matches_selector("ALL"))
        self.assertTrue(rule.matches_selector("PDF"))
        self.assertTrue(rule.matches_selector("PDF1"))
        self.assertTrue(rule.matches_selector_parts("PDF", "10"))
        self.assertFalse(rule.matches_selector("PDF106"))
        self.assertFalse(rule.matches_selector("P"))
        self.assertFalse(rule.matches_selector("bad"))

    def test_rule_collection_validates_rule_code_with_metadata_error(self) -> None:
        rule = object.__new__(RuleMetadata)
        object.__setattr__(rule, "code", "bad")
        object.__setattr__(rule, "name", "bad-rule")
        object.__setattr__(rule, "message", "Bad rule")
        object.__setattr__(rule, "fixable", True)

        with self.assertRaisesRegex(ValueError, r"bad: Rule code must match"):
            rule_collection.RuleCollection.from_metadata((rule,))

    def test_rule_base_class_properties_redirect_to_metadata(self) -> None:
        class PDF999TestRule(RuleBase):
            meta = RuleMetadata(code="PDF999", name="test-rule", message="Test rule", fixable=True)

        rule = PDF999TestRule()

        self.assertEqual(
            (PDF999TestRule.code, PDF999TestRule.prefix, PDF999TestRule.number_str, PDF999TestRule.number, PDF999TestRule.name, PDF999TestRule.message, PDF999TestRule.fixable),
            ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", True),
        )
        self.assertEqual((rule.code, rule.prefix, rule.number_str, rule.number, rule.name, rule.message, rule.fixable), ("PDF999", "PDF", "999", 999, "test-rule", "Test rule", True))

    def test_selectors_must_use_complete_rule_prefixes(self) -> None:
        collection = sample_collection()

        self.assertTrue(collection.selector_matches_some_rule("ALL"))
        self.assertTrue(collection.selector_matches_some_rule("PDF"))
        self.assertTrue(collection.selector_matches_some_rule("PDF1"))
        self.assertTrue(collection.selector_matches_some_rule("PDF10"))
        self.assertFalse(collection.selector_matches_some_rule("PDF107"))
        self.assertFalse(collection.selector_matches_some_rule("R"))
        self.assertFalse(collection.selector_matches_some_rule("P"))
        self.assertFalse(collection.selector_matches_some_rule("RD"))

    def test_rule_collection_does_not_expose_selector_convenience_indexes(self) -> None:
        collection = sample_collection()

        self.assertFalse(hasattr(collection, "by_code"))
        self.assertFalse(hasattr(collection, "rule_codes"))
        self.assertFalse(hasattr(collection, "rule_prefixes"))
        self.assertFalse(hasattr(collection, "selector_matches_rule"))

    def test_select_rules_resolves_selection_and_fixability(self) -> None:
        selection = rules_selection.select_rules(
            CheckSettings(select=("PDF",), ignore=("PDF105",), fixable=("PDF",), unfixable=("PDF105",)),
            collection=sample_collection(),
        )

        self.assertEqual(selection.errors, ())
        self.assertEqual(tuple(rule.rule.code for rule in selection.rules), ("PDF001",))
        self.assertEqual(tuple(rule.fixable for rule in selection.rules), (True,))

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

        self.assertEqual(tuple(rule.rule.code for rule in selection.for_path("src/a.py")), ("PCF001", "PDF001", "PDF105"))
        self.assertEqual(tuple(rule.rule.code for rule in selection.for_path("tests/a.py")), ("PCF001", "PDF105"))

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
