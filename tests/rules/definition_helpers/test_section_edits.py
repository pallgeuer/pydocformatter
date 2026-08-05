"""Tests for docstring section edit helpers."""

# Standard library imports
import dataclasses

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF409_docstring_entry_spacing import PDF409DocstringEntrySpacing


contexts = pdf_helpers.contexts_for("PDF409")


def test_replacement_accumulator_keeps_request_state_private_and_structural() -> None:
    """Expose only one private collection for mutable request state."""
    field_names = tuple(field.name for field in dataclasses.fields(section_edits.ReplacementAccumulator))

    assert field_names == ("docstring", "context", "rule", "_requests")


def test_replacement_accumulator_groups_ordered_span_edits_and_uses_default_for_distinct_messages() -> None:
    """Build one fix and use rule metadata for multiple distinct messages."""
    source = 'def function(value, other):\n    """Summary.\n\n    Args:\n        value (int): Description.\n        other (bool): Other description.\n\n    Returns:\n        str: Result.\n    """\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)
    first_line = docstring.structure.lines[3]
    second_line = docstring.structure.lines[4]
    third_line = docstring.structure.lines[7]
    first_start = first_line.text.index("int")
    second_start = second_line.text.index("bool")
    third_start = third_line.text.index("str")

    accumulator.add(first_line, first_start, first_start + len("int"), "float", instance_message="Normalize type")
    accumulator.add(second_line, second_start, second_start + len("bool"), "bytes", instance_message="Normalize result")
    accumulator.add(third_line, third_start, third_start + len("str"), "complex", instance_message="Normalize result")
    (violation,) = accumulator.results()

    assert violation.finding.message == PDF409DocstringEntrySpacing.meta.message
    assert violation.fix is not None
    module = rule_edits.apply_context_source_changes(context, violation.fix.planned_changes())
    assert module.code == source.replace("value (int)", "value (float)").replace("other (bool)", "other (bytes)").replace("str: Result.", "complex: Result.")


def test_replacement_accumulator_deduplicates_identical_messages() -> None:
    """Keep one concrete message when every grouped request agrees."""
    source = 'def function(value, other):\n    """Summary.\n\n    Args:\n        value (int): Description.\n        other (bool): Other description.\n    """\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)
    for line, old, new in ((docstring.structure.lines[3], "int", "float"), (docstring.structure.lines[4], "bool", "bytes")):
        start = line.text.index(old)
        accumulator.add(line, start, start + len(old), new, instance_message="Normalize type")

    (violation,) = accumulator.results()

    assert violation.finding.message == "Normalize type"


def test_replacement_accumulator_returns_nothing_without_candidates() -> None:
    """Return no violations when no replacement was requested."""
    source = 'def function():\n    """Summary."""\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)

    assert accumulator.results() == ()


def test_replacement_accumulator_accepts_precomputed_replacements() -> None:
    """Record an existing mapped replacement through the shared lifecycle."""
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (integer): Description.\n    """\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    line = docstring.structure.lines[3]
    start = line.text.index("integer")
    replacement = section_edits.text_replacement(line, start, start + len("integer"), "int")
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)

    accumulator.add_replacement(line, replacement, "int", instance_message="Normalize type")
    (violation,) = accumulator.results()

    assert violation.fix is not None
    assert violation.finding.message == "Normalize type"
    module = rule_edits.apply_context_source_changes(context, violation.fix.planned_changes())
    assert module.code == source.replace("integer", "int")


def test_replacement_accumulator_keeps_fixable_and_unfixable_candidates_separate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return independent violations when only some requested spans map safely."""
    source = 'def function(value, other):\n    """Summary.\n\n    Args:\n        value (int): Description.\n        other (bool): Other description.\n    """\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    first_line = docstring.structure.lines[3]
    second_line = docstring.structure.lines[4]
    first_start = first_line.text.index("int")
    second_start = second_line.text.index("bool")
    original_text_replacement = section_edits.text_replacement

    def selective_text_replacement(line: PDF_definition.DocstringValueLine, start_column: int, end_column: int, text: str) -> rule_edits.PlannedTextReplacement | None:
        return None if line is second_line else original_text_replacement(line, start_column, end_column, text)

    monkeypatch.setattr(section_edits, "text_replacement", selective_text_replacement)
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)
    accumulator.add(first_line, first_start, first_start + len("int"), "float", instance_message="Fixable")
    accumulator.add(second_line, second_start, second_start + len("bool"), "bytes", instance_message="Unfixable")
    fixable, unfixable = accumulator.results()

    assert fixable.fix is not None
    assert fixable.finding.message == "Fixable"
    assert unfixable.fix is None
    assert unfixable.finding.message == "Unfixable"


def test_replacement_accumulator_reports_unsafe_concatenated_mapping_without_fix() -> None:
    """Retain a diagnostic when accumulated spans cannot produce safe source edits."""
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Args:\\n"\n     "    value (int): Description.")\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    line = docstring.structure.lines[3]
    start = line.text.index("int")
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)

    accumulator.add(line, start, start + len("int"), "float")
    (violation,) = accumulator.results()

    assert violation.fix is None
    assert violation.finding.line_numbers == (2, 3, 4)


@pytest.mark.parametrize("reverse_order", [False, True])
def test_replacement_accumulator_applies_same_line_fallback_edits_against_original_offsets(reverse_order: bool) -> None:
    """Apply length-changing fallback replacements right to left regardless of request order."""
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (dict[integ\\x65r, string]): Description.\n    """\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    line = docstring.structure.lines[3]
    requests = [(line.text.index("integer"), line.text.index("integer") + len("integer"), "int"), (line.text.index("string"), line.text.index("string") + len("string"), "bytes")]
    if reverse_order:
        requests.reverse()
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)
    for start, end, text in requests:
        accumulator.add(line, start, end, text)

    (violation,) = accumulator.results()

    assert violation.fix is not None
    module = rule_edits.apply_context_source_changes(context, violation.fix.planned_changes())
    assert module.code == source.replace("dict[integ\\x65r, string]", "dict[int, bytes]")


def test_replacement_accumulator_reports_overlapping_requests_without_fix() -> None:
    """Reject overlapping immutable replacement requests instead of corrupting fallback text."""
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (integer): Description.\n    """\n'
    _, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    line = docstring.structure.lines[3]
    start = line.text.index("integer")
    accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=PDF409DocstringEntrySpacing.meta)
    accumulator.add(line, start, start + len("integer"), "int")
    accumulator.add(line, start + 1, start + len("integer"), "number")

    (violation,) = accumulator.results()

    assert violation.fix is None


def test_planned_line_text_change_uses_owner_line_for_exact_escaped_logical_line() -> None:
    """Keep exact escaped-line edits operational when the logical line has no physical line number."""
    source = 'def function(value):\n    """Summary.\\n\\nArgs:\\nvalue: Description."""\n'
    category, context = contexts(source)
    docstring = PDF.require_data(context).docstrings[0]
    line = docstring.structure.lines[3]

    change = section_edits.planned_line_text_change(docstring, line, 0, 0, "    ", context=context)

    assert change is not None
    module = rule_edits.apply_context_source_changes(category, (change,))
    assert module.code == source.replace("\\nvalue:", "\\n    value:")
