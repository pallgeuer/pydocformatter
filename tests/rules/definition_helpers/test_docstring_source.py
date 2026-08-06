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


def test_opening_delimiter_suffix_requires_a_mapped_physical_separator() -> None:
    sources = ('def separate():\n    """  \n    Body."""\n', 'def compact():\n    """Body.\n    More."""\n', 'def escaped():\n    """\\nBody."""\n')
    docstrings = tuple(PDF_definition.PDF.require_data(pdf_helpers.contexts_for("PDF200")(source)[1]).docstrings[0] for source in sources)
    separate, compact, escaped = docstrings

    assert docstring_source.is_same_line_opening_delimiter_suffix(separate, separate.structure.lines[0])
    assert not docstring_source.is_same_line_opening_delimiter_suffix(compact, compact.structure.lines[0])
    assert not docstring_source.is_same_line_opening_delimiter_suffix(escaped, escaped.structure.lines[0])


def test_canonical_margin_distinguishes_attached_docstring_statement_shapes() -> None:
    sources_and_margins = (('value = 1\n("""Summary.\nBody.\n""")\n', ""), ('value = 1; ("""Summary.\nBody.\n""")\n', " " * 12), ('def function(): """Summary.\nBody.\n"""\n', " " * 4))

    for source, expected_margin in sources_and_margins:
        _, context = pdf_helpers.contexts_for("PDF100")(source)
        docstring = PDF_definition.PDF.require_data(context).docstrings[0]
        assert docstring_source.docstring_canonical_margin(docstring, context=context) == expected_margin


def test_canonical_margin_excludes_indentation_form_feeds() -> None:
    sources_and_margins = (
        ('\f"""Summary.\nBody.\n"""\n', ""),
        ('def function():\n\f    """Summary.\nBody.\n    """\n', " " * 4),
        ('def function():\n \f    """Summary.\nBody.\n    """\n', " " * 4),
        ('\fdef function(): """Summary.\nBody.\n"""\n', " " * 4),
        ('\fvalue = 1; ("""Summary.\nBody.\n""")\n', " " * 12),
        ('\f("""Summary.\nBody.\n""")\n', ""),
    )

    for source, expected_margin in sources_and_margins:
        _, context = pdf_helpers.contexts_for("PDF100")(source)
        docstring = PDF_definition.PDF.require_data(context).docstrings[0]
        margin = docstring_source.docstring_canonical_margin(docstring, context=context)

        assert margin == expected_margin
        assert "\f" not in margin
