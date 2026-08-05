"""Tests for docstring source mapping and edit planning."""

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import docstring_source


def test_mapping_capability_is_separate_from_canonical_rewrite_policy() -> None:
    _, context = pdf_helpers.contexts_for("PDF100")('"""safe"""\n"""ignored additional"""\nvalue = 1\n"""hazard\u202e"""\n')
    safe, hazardous = PDF_definition.PDF.require_data(context).docstrings

    assert docstring_source.is_safely_mapped_simple_docstring(safe)
    assert docstring_source.can_canonically_rewrite_simple_docstring(safe)
    assert docstring_source.is_safely_mapped_simple_docstring(hazardous)
    assert not docstring_source.can_canonically_rewrite_simple_docstring(hazardous)
