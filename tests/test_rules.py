import unittest

import pydocformatter.rules as rules


class TestRules(unittest.TestCase):
    def test_selectors_must_use_complete_rule_prefixes(self) -> None:
        self.assertTrue(rules.selector_matches_known_rule("ALL", tool_name="pydocfmt"))
        self.assertTrue(rules.selector_matches_known_rule("RD", tool_name="pydocfmt"))
        self.assertTrue(rules.selector_matches_known_rule("RD2", tool_name="pydocfmt"))
        self.assertTrue(rules.selector_matches_known_rule("RD20", tool_name="pydocfmt"))
        self.assertTrue(rules.selector_matches_known_rule("RD205", tool_name="pydocfmt"))
        self.assertFalse(rules.selector_matches_known_rule("R", tool_name="pydocfmt"))
        self.assertFalse(rules.selector_matches_known_rule("P", tool_name=None))
        self.assertFalse(rules.selector_matches_known_rule("RD3", tool_name="pydocfmt"))

    def test_selectors_are_validated_against_tool_ownership(self) -> None:
        self.assertTrue(rules.selector_matches_known_rule("PDF000", tool_name="pydocfmt"))
        self.assertTrue(rules.selector_matches_known_rule("PCF", tool_name="pycommentfmt"))
        self.assertFalse(rules.selector_matches_known_rule("PCF", tool_name="pydocfmt"))
        self.assertFalse(rules.selector_matches_known_rule("PDF", tool_name="pycommentfmt"))


if __name__ == "__main__":
    unittest.main()
