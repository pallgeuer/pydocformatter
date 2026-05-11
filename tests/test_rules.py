import unittest

import pydocformatter.rules as rules


class TestRules(unittest.TestCase):
    def test_selectors_must_use_complete_rule_prefixes(self) -> None:
        self.assertTrue(rules.selector_matches_known_rule("ALL"))
        self.assertTrue(rules.selector_matches_known_rule("PDF"))
        self.assertTrue(rules.selector_matches_known_rule("PDF1"))
        self.assertTrue(rules.selector_matches_known_rule("PDF10"))
        self.assertFalse(rules.selector_matches_known_rule("PDF107"))
        self.assertFalse(rules.selector_matches_known_rule("R"))
        self.assertFalse(rules.selector_matches_known_rule("P"))
        self.assertFalse(rules.selector_matches_known_rule("RD"))

    def test_unified_formatter_accepts_docstring_and_comment_rule_prefixes(self) -> None:
        self.assertFalse(rules.selector_matches_known_rule("PDF000"))
        self.assertTrue(rules.selector_matches_known_rule("PDF"))
        self.assertTrue(rules.selector_matches_known_rule("PDF001"))
        self.assertTrue(rules.selector_matches_known_rule("PDF006"))
        self.assertTrue(rules.selector_matches_known_rule("PDF100"))
        self.assertTrue(rules.selector_matches_known_rule("PDF104"))
        self.assertTrue(rules.selector_matches_known_rule("PDF106"))
        self.assertTrue(rules.selector_matches_known_rule("PCF"))
        self.assertTrue(rules.selector_matches_known_rule("PCF001"))
        self.assertTrue(rules.selector_matches_known_rule("PCF002"))
        self.assertFalse(rules.selector_matches_known_rule("XYZ"))


if __name__ == "__main__":
    unittest.main()
