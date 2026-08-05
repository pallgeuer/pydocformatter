"""Assertion rewriting configuration for shared test helpers.

Attributes:
    ASSERT_REWRITE_MODULES (tuple[str, ...]): Shared helper modules whose plain assertions require pytest introspection.
"""

ASSERT_REWRITE_MODULES = ("tests.git_helpers", "tests.markdown_example_helpers", "tests.markdown_table_helpers", "tests.rules.PDF.helpers")
