"""Repository Markdown table and semantic-adapter tests."""

# Standard library imports
import pathlib

# Third-party imports
import pytest
from la_dev_codex_plugins import markdown_tables

# First-party imports
from tests import markdown_table_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX_COMMAND = "uv run la-dev-markdown-tables"


def test_tracked_markdown_tables_use_canonical_style() -> None:
    """Check every tracked Markdown table with the shared formatter."""
    failures: list[str] = []
    for path in markdown_tables.select_markdown_paths(root=ROOT):
        result = markdown_tables.format_markdown_tables_file(path, check=True)
        failures.extend(f"{change.path}:{change.line_number}: {change.message}" for change in result.changes)
        failures.extend(f"{issue.path}:{issue.line_number}: {issue.message}" for issue in result.issues)

    assert not failures, f"Markdown table failures. Run: {FIX_COMMAND}\n" + "\n".join(failures)


def test_semantic_table_adapter_handles_escaped_pipes() -> None:
    """Check that upstream-parsed escaped pipes remain in their semantic cell."""
    text = "# Example\n\n| Name | Value  |\n|------|--------|\n| one  | x\\|y |\n"
    table = markdown_table_helpers.table_after_heading(text, "# Example", label="example")

    assert markdown_table_helpers.table_rows(table, label="example") == ({"Name": "one", "Value": "x\\|y"},)


def test_semantic_table_adapter_handles_escaped_pipes_inside_code_spans() -> None:
    """Honor GFM escapes inside inline spans before recognizing cell boundaries."""
    text = "# Example\n\n| Name | Value     |\n|------|-----------|\n| one  | `x \\| y` |\n"
    table = markdown_table_helpers.table_after_heading(text, "# Example", label="example")

    assert markdown_table_helpers.table_rows(table, label="example") == ({"Name": "one", "Value": "`x \\| y`"},)


def test_shared_parser_treats_unescaped_code_span_pipes_as_cell_boundaries() -> None:
    """Keep table parsing aligned with GitHub Flavored Markdown block structure."""
    text = "| Name | Value   |\n|------|---------|\n| one  | `x | y` |\n"

    with pytest.raises(markdown_tables.MarkdownTableError, match="Malformed Markdown table"):
        markdown_tables.parse_markdown_tables(text)


def test_semantic_table_adapter_accepts_declared_structural_wrapper() -> None:
    """Check that heading lookup accepts only an explicitly declared wrapper."""
    wrapper = '<div class="table-wrapper" markdown="1">'
    text = f"# Example\n\n{wrapper}\n\n| Name |\n|------|\n| one  |\n"

    table = markdown_table_helpers.table_after_heading(text, "# Example", label="example", expected_leading_lines=(wrapper,))

    assert markdown_table_helpers.table_rows(table, label="example") == ({"Name": "one"},)


def test_semantic_table_adapter_allows_unconstrained_section_prose() -> None:
    """Keep heading ownership while allowing prose that is not part of the table contract."""
    text = "# Example\n\nArbitrary introductory prose.\n\n| Name |\n|------|\n| one  |\n"

    table = markdown_table_helpers.table_after_heading(text, "# Example", label="example", expected_leading_lines=None)

    assert markdown_table_helpers.table_rows(table, label="example") == ({"Name": "one"},)


@pytest.mark.parametrize("indentation", [" ", "  ", "   "])
def test_semantic_table_adapter_recognizes_indented_heading_boundaries(indentation: str) -> None:
    """Treat ATX headings with up to three leading spaces as section boundaries."""
    text = f"# Example\n\n{indentation}# Other\n\n| Name |\n|------|\n| one  |\n"

    with pytest.raises(AssertionError, match="section following"):
        markdown_table_helpers.table_after_heading(text, "# Example", label="example", expected_leading_lines=None)


def test_semantic_table_adapter_keeps_four_space_heading_like_lines_as_code() -> None:
    """Do not treat a four-space-indented heading-like line as an ATX heading."""
    text = "# Example\n\n    # Not a heading\n\n| Name |\n|------|\n| one  |\n"

    table = markdown_table_helpers.table_after_heading(text, "# Example", label="example", expected_leading_lines=None)

    assert markdown_table_helpers.table_rows(table, label="example") == ({"Name": "one"},)


def test_semantic_table_adapter_rejects_mismatched_structural_wrapper() -> None:
    """Check that heading lookup rejects a wrapper other than the declared one."""
    text = '# Example\n\n<div class="actual">\n\n| Name |\n|------|\n| one  |\n'

    with pytest.raises(AssertionError, match="expected leading lines"):
        markdown_table_helpers.table_after_heading(text, "# Example", label="example", expected_leading_lines=('<div class="expected">',))


def test_semantic_table_adapter_ignores_fenced_headings() -> None:
    """Check that fenced headings are neither matches nor section boundaries."""
    leading_lines = ("```markdown", "# Other", "```")
    text = "```markdown\n# Example\n```\n\n# Example\n\n```markdown\n# Other\n```\n\n| Name |\n|------|\n| one  |\n"

    table = markdown_table_helpers.table_after_heading(text, "# Example", label="example", expected_leading_lines=leading_lines)

    assert markdown_table_helpers.table_rows(table, label="example") == ({"Name": "one"},)


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("# Example\n\n| Name | Name |\n|------|------|\n| one  | two  |\n", "duplicate headers"),
        ("# Example\n\n| Name |  |\n|------|--|\n| one  |  |\n", "empty header"),
        ("# Example\n\n| Name |\n|------|\n", "no body rows"),
        ("# Example\n\nUnexpected prose.\n\n| Name |\n|------|\n| one  |\n", "expected leading lines"),
        ('# Example\n\n<div class="wrong">\n\n| Name |\n|------|\n| one  |\n', "expected leading lines"),
        ("# Example\n\n# Other\n\n| Name |\n|------|\n| one  |\n", "section following"),
        ("# Example\n\n# Example\n\n| Name |\n|------|\n| one  |\n", "found 2"),
        ("```markdown\n# Example\n```\n\n| Name |\n|------|\n| one  |\n", "found 0"),
    ],
)
def test_semantic_table_adapter_rejects_weak_table_contracts(text: str, match: str) -> None:
    """Check that semantic table lookup rejects ambiguous or incomplete tables."""
    with pytest.raises(AssertionError, match=match):
        markdown_table_helpers.table_after_heading(text, "# Example", label="example")
