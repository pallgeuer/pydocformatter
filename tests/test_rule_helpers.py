# Third-party imports
import libcst as cst
import pytest
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.definitions.PDF.PDF import PDF
from tests import rule_helpers


@pytest.mark.parametrize(("configured", "expected"), [(LineEnding.AUTO, "\r\n"), (LineEnding.LF, "\n")])
def test_direct_rule_category_context_resolves_configured_line_ending(configured: LineEnding, expected: str) -> None:
    context = rule_helpers.direct_rule_category_context("x = 1\r\n", settings=CheckSettings(line_ending=configured))

    assert context.line_ending == expected


def test_prepared_direct_rule_contexts_remap_positions_and_cache_exact_source_bounds() -> None:
    source = '\f"""D."""\r\n\r\n \t# C.\r\n'
    category_context, rule_context = rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=CheckSettings(), path="package/example.py")
    string_node = next(node for node in category_context.positions if isinstance(node, cst.SimpleString))

    assert category_context.path == "package/example.py"
    assert category_context.source == source
    assert category_context.source_lines == tuple(source_text.source_lines(source))
    assert category_context.line_bounds == source_text.line_bounds_from_lines(category_context.source_lines)
    assert category_context.positions[string_node] == cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 1), end=cst_metadata.CodePosition(1, 9))
    assert rule_context.module is category_context.module
    assert rule_context.positions is category_context.positions
    assert PDF.require_data(rule_context).docstrings[0].value == "D."
