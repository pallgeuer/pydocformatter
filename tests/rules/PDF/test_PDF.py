import libcst as cst
import libcst.metadata as cst_metadata
import pytest

from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import (
    PDF,
    DefinitionKind,
    DocstringBlock,
    DocstringBlockKind,
    DocstringEntryKind,
    DocstringKind,
    DocstringStructure,
    ReflowRegionLine,
    escaped_closing_quote_body_source,
    simple_docstring_body_source_candidates,
)


def reflow_texts(lines: tuple[ReflowRegionLine, ...]) -> tuple[str, ...]:
    return tuple(line.text for line in lines)


def category_context(source: str, *, settings: CheckSettings | None = None) -> RuleCategoryContext:
    module = cst.parse_module(source)
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    return RuleCategoryContext(
        path="example.py",
        settings=CheckSettings() if settings is None else settings,
        module=module,
        metadata_wrapper=metadata_wrapper,
        positions=metadata_wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
    )


def rule_context(context: RuleCategoryContext, data: object | None) -> RuleContext:
    return RuleContext(
        path=context.path,
        settings=context.settings,
        module=context.module,
        metadata_wrapper=context.metadata_wrapper,
        positions=context.positions,
        line_ending=context.line_ending,
        category_data=data,
        effectively_fixable=True,
    )


def test_prepare_collects_definitions_docstrings_and_owner_metadata() -> None:
    source = '"""module doc"""\n@decorator\nclass Outer:\n    """class doc"""\n    async def method(self, value: int) -> str:\n        ("method doc")\n        return str(value)\n\n    def no_doc(self):\n        pass\n\ndef concatenated():\n    "first " "second"\n\ndef empty(): "" ; return None\ndef formatted():\n    f"not a docstring"\ndef binary():\n    b"not a docstring"\n'
    data = PDF.prepare(category_context(source))
    assert tuple((definition.kind, definition.qualified_name) for definition in data.definitions) == (
        (DefinitionKind.MODULE, "<module>"),
        (DefinitionKind.CLASS, "Outer"),
        (DefinitionKind.FUNCTION, "Outer.method"),
        (DefinitionKind.FUNCTION, "Outer.no_doc"),
        (DefinitionKind.FUNCTION, "concatenated"),
        (DefinitionKind.FUNCTION, "empty"),
        (DefinitionKind.FUNCTION, "formatted"),
        (DefinitionKind.FUNCTION, "binary"),
    )
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("<module>", "Outer", "Outer.method", "concatenated", "empty")
    assert tuple(docstring.kind for docstring in data.docstrings) == (DocstringKind.SIMPLE, DocstringKind.SIMPLE, DocstringKind.SIMPLE, DocstringKind.CONCATENATED, DocstringKind.SIMPLE)
    assert tuple(docstring.value for docstring in data.docstrings) == ("module doc", "class doc", "method doc", "first second", "")
    assert data.docstrings[2].source == '"method doc"'
    assert data.definitions[2].asynchronous
    assert len(data.definitions[1].decorators) == 1
    assert data.definitions[2].parameters is not None
    assert data.definitions[2].returns is not None
    assert data.definitions[2].parent is data.definitions[1]
    assert data.docstring_for(data.definitions[1]) is data.docstrings[1]
    assert data.docstring_for(data.definitions[3]) is None


def test_prepare_preserves_multiline_crlf_source_and_physical_lines() -> None:
    source = 'def function():\r\n    r"""first\r\n    second"""\r\n    pass\r\n'
    data = PDF.prepare(category_context(source))
    docstring = data.docstrings[0]
    assert docstring.source == 'r"""first\r\n    second"""'
    assert tuple((line.line_number, line.start_column, line.end_column, line.source) for line in docstring.physical_lines) == ((2, 4, 13, 'r"""first'), (3, 0, 13, '    second"""'))
    assert docstring.value_lines == ("first", "    second")


def test_prepare_accepts_only_string_valued_first_expressions_as_docstrings() -> None:
    source = 'def parenthesized():\n    (u"doc")\n\ndef later_string():\n    value = 1\n    "not a docstring"\n'
    data = PDF.prepare(category_context(source))
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("parenthesized",)
    assert data.docstrings[0].source == 'u"doc"'


def test_unicode_line_separator_inside_literal_is_not_a_physical_source_line() -> None:
    data = PDF.prepare(category_context('"""first\u2028second"""\n'))
    assert len(data.docstrings[0].physical_lines) == 1
    assert data.docstrings[0].physical_lines[0].source == '"""first\u2028second"""'


def test_require_data_validates_category_data_type() -> None:
    context = category_context('"""doc"""\n')
    data = PDF.prepare(context)
    assert PDF.require_data(rule_context(context, data)) is data
    with pytest.raises(TypeError, match="require PDFCategoryData"):
        PDF.require_data(rule_context(context, None))


def test_escaped_closing_quote_body_source_skips_single_character_delimiter() -> None:
    node = cst.ensure_type(cst.parse_expression("'Summary'"), cst.SimpleString)

    assert escaped_closing_quote_body_source(node, "Say '") is None


def test_simple_docstring_body_source_candidates_try_value_preserving_both_end_quote_escape_first() -> None:
    node = cst.ensure_type(cst.parse_expression('"""Summary"""'), cst.SimpleString)

    assert next(simple_docstring_body_source_candidates(node, '"quoted"', expected_value='"quoted"')) == ('\\"quoted\\"', '"quoted"')


def test_simple_docstring_body_source_candidates_include_separator_fallback_value_changes() -> None:
    node = cst.ensure_type(cst.parse_expression('r"""Summary"""'), cst.SimpleString)

    candidates = tuple(simple_docstring_body_source_candidates(node, "Path \\", expected_value="Path \\"))

    assert (" Path \\", " Path \\") in candidates
    assert ("Path \\ ", "Path \\ ") in candidates
    assert (" Path \\ ", " Path \\ ") in candidates


def block_kinds(blocks: tuple[DocstringBlock, ...]) -> tuple[DocstringBlockKind, ...]:
    """Return block kinds recursively in source order."""
    return tuple(kind for block in blocks for kind in (block.kind, *block_kinds(block.children)))


def structure_for(value: str, *, settings: CheckSettings | None = None) -> DocstringStructure:
    """Return prepared semantic structure for a module docstring value."""
    source = f'"""{value}"""\n'
    return PDF.prepare(category_context(source, settings=settings)).docstrings[0].structure


def top_level_blocks(value: str, *, settings: CheckSettings | None = None) -> tuple[tuple[DocstringBlockKind, int, int], ...]:
    """Return top-level block kinds and logical line ranges."""
    return tuple((block.kind, block.start_line, block.end_line) for block in structure_for(value, settings=settings).blocks)


def assert_block_partition(blocks: tuple[DocstringBlock, ...], start: int, end: int) -> None:
    """Assert that sibling blocks exactly partition a logical line range."""
    assert blocks
    assert blocks[0].start_line == start
    assert blocks[-1].end_line == end
    assert all(left.end_line == right.start_line for left, right in zip(blocks, blocks[1:]))
    for block in blocks:
        assert block.start_line < block.end_line
        if block.children:
            assert_block_partition(block.children, block.start_line, block.end_line)


def test_prepare_collects_deeply_nested_definitions_in_lexical_order() -> None:
    source = 'class Outer:\n    class Inner:\n        """inner"""\n        def method(self):\n            """method"""\n            def local():\n                """local"""\n                pass\n            return local\n\ndef top():\n    class LocalClass:\n        """local class"""\n    return LocalClass\n'
    data = PDF.prepare(category_context(source))
    assert tuple(definition.qualified_name for definition in data.definitions) == ("<module>", "Outer", "Outer.Inner", "Outer.Inner.method", "Outer.Inner.method.local", "top", "top.LocalClass")
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("Outer.Inner", "Outer.Inner.method", "Outer.Inner.method.local", "top.LocalClass")
    assert data.definitions[4].parent is data.definitions[3]
    assert data.definitions[6].parent is data.definitions[5]


def test_prepare_handles_simple_statement_suites_and_non_expression_first_statements() -> None:
    source = 'class Documented: "class doc"; value = 1\nclass Undocumented: value = 1; "late"\ndef documented(): "function doc"; return 1\ndef assigned_first(): value = 1; "late"\n'
    data = PDF.prepare(category_context(source))
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("Documented", "documented")
    assert all(docstring.statement is docstring.owner.body for docstring in data.docstrings)


def test_comments_before_first_statements_do_not_prevent_docstring_collection() -> None:
    source = '#!/usr/bin/env python\n# module comment\n"""module doc"""\n\nclass Example:\n    # class comment\n    """class doc"""\n\n    def method(self):\n        # function comment\n        """method doc"""\n'
    data = PDF.prepare(category_context(source))
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("<module>", "Example", "Example.method")
    assert tuple(docstring.range.start.line for docstring in data.docstrings) == (3, 7, 11)
    assert tuple(docstring.structure.lines[0].source_line_number for docstring in data.docstrings) == (3, 7, 11)


def test_concatenations_containing_formatted_strings_are_not_docstrings() -> None:
    source = 'value = "dynamic"\ndef function():\n    "prefix " f"{value}"\n'
    data = PDF.prepare(category_context(source))
    assert tuple(definition.qualified_name for definition in data.definitions) == ("<module>", "function")
    assert data.docstrings == ()


def test_concatenated_docstring_preserves_exact_parenthesized_source_and_disables_source_mapping() -> None:
    source = 'def function():\n    (\n        "first\\n"\n        r"second"\n    )\n'
    docstring = PDF.prepare(category_context(source)).docstrings[0]
    assert docstring.source == '"first\\n"\n        r"second"'
    assert docstring.value == "first\nsecond"
    assert tuple(line.source_line_number for line in docstring.structure.lines) == (None, None)


def test_evaluated_escape_newline_disables_ambiguous_source_line_mapping() -> None:
    docstring = PDF.prepare(category_context(r'"""first\nsecond"""' + "\n")).docstrings[0]
    assert len(docstring.physical_lines) == 1
    assert tuple((line.raw_text, line.source_line_number) for line in docstring.structure.lines) == (("first", None), ("second", None))


def test_balanced_physical_and_evaluated_line_counts_do_not_imply_valid_source_mapping() -> None:
    source = 'def function():\n    """first\\nsecond\\\nthird"""\n'
    docstring = PDF.prepare(category_context(source)).docstrings[0]
    assert len(docstring.physical_lines) == len(docstring.structure.lines) == 2
    assert tuple(line.raw_text for line in docstring.structure.lines) == ("first", "secondthird")
    assert tuple(line.source_line_number for line in docstring.structure.lines) == (None, None)


def test_value_lines_track_offsets_dedentation_and_source_lines() -> None:
    source = 'def function():\n    """Summary.\n        over-indented\n    aligned\n    """\n'
    lines = PDF.prepare(category_context(source)).docstrings[0].structure.lines
    assert tuple((line.index, line.start_offset, line.end_offset, line.raw_text, line.text, line.source_line_number) for line in lines) == (
        (0, 0, 8, "Summary.", "Summary.", 2),
        (1, 9, 30, "        over-indented", "    over-indented", 3),
        (2, 31, 42, "    aligned", "aligned", 4),
        (3, 43, 47, "    ", "", 5),
    )


def test_nested_tab_indentation_uses_the_docstring_visual_column() -> None:
    source = 'class Outer:\n\tclass Inner:\n\t\tdef method(self):\n\t\t\t"""Summary.\n\t\t\tArgs:\n\t\t\t\tvalue: Description.\n\t\t\t"""\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary.", "Args:", "\tvalue: Description.", "")
    assert tuple(section.name for section in structure.sections) == ("Args",)
    assert tuple(entry.names for entry in structure.entries) == (("value",),)


def test_tab_crossing_docstring_margin_preserves_residual_indentation() -> None:
    source = 'def function():\n    """Summary::\n\tIndented literal.\n    """\n'
    structure = PDF.prepare(category_context(source)).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "    Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_simple_suite_docstring_uses_suite_indentation_instead_of_literal_column() -> None:
    source = 'def function(): """Summary::\n        Indented literal.\n    """\n'
    structure = PDF.prepare(category_context(source)).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "    Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_nested_simple_suite_docstring_includes_enclosing_indentation() -> None:
    source = 'class Outer:\n    def method(self): """Summary::\n            Indented literal.\n        """\n'
    structure = PDF.prepare(category_context(source)).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "    Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_simple_suite_docstring_uses_configured_indentation_width() -> None:
    source = 'def function(): """Summary::\n    Indented literal.\n  """\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(indent_width=2))).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "  Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_mixed_evaluated_newline_sequences_have_exact_offsets() -> None:
    docstring = PDF.prepare(category_context(r'"""first\r\nsecond\rthird\nfourth"""' + "\n")).docstrings[0]
    assert docstring.value_lines == ("first", "second", "third", "fourth")
    assert tuple((line.start_offset, line.end_offset, line.raw_text, line.source_line_number) for line in docstring.structure.lines) == (
        (0, 5, "first", None),
        (7, 13, "second", None),
        (14, 19, "third", None),
        (20, 26, "fourth", None),
    )
    assert reflow_texts(docstring.structure.reflow_regions[0].lines) == ("first", "second", "third", "fourth")


def test_reflow_region_lines_carry_description_offsets_when_text_matches_prefix() -> None:
    value = "Args:\n    x: x words around enough to wrap after a matching entry name."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    region = structure.reflow_regions[0]

    assert reflow_texts(region.lines) == ("x words around enough to wrap after a matching entry name.",)
    assert region.lines[0].start_offset == value.index("x words")
    assert region.lines[0].start_offset != value.index("x:")


def test_trailing_evaluated_newline_does_not_create_a_phantom_logical_line() -> None:
    docstring = PDF.prepare(category_context(r'"""Summary.\n"""' + "\n")).docstrings[0]
    assert docstring.value_lines == ("Summary.",)
    assert tuple(line.raw_text for line in docstring.structure.lines) == ("Summary.",)
    assert top_level_blocks("Summary.\n") == ((DocstringBlockKind.SUMMARY, 0, 1),)


def test_concatenated_docstring_uses_common_value_indentation_and_preserves_interstitial_comments() -> None:
    source = 'def function():\n    ("Summary.\\n"\n     "        deeper\\n"\n     # Interstitial source comment.\n     "    aligned")\n'
    docstring = PDF.prepare(category_context(source)).docstrings[0]
    assert docstring.source == '"Summary.\\n"\n     "        deeper\\n"\n     # Interstitial source comment.\n     "    aligned"'
    assert tuple((line.raw_text, line.text) for line in docstring.structure.lines) == (("Summary.", "Summary."), ("        deeper", "    deeper"), ("    aligned", "aligned"))
    assert tuple(line.source_line_number for line in docstring.structure.lines) == (None, None, None)
    assert tuple(line.line_number for line in docstring.physical_lines) == (2, 3, 4, 5)


def test_empty_and_whitespace_only_docstrings_have_only_blank_semantics() -> None:
    empty = structure_for("")
    whitespace = structure_for("  \n\t")
    assert top_level_blocks("") == ((DocstringBlockKind.BLANK, 0, 1),)
    assert top_level_blocks("  \n\t") == ((DocstringBlockKind.BLANK, 0, 2),)
    assert empty.reflow_regions == ()
    assert whitespace.reflow_regions == ()


def test_summary_paragraph_blank_and_verbatim_blocks_preserve_ranges() -> None:
    value = "Summary first\nsummary second\n\nParagraph first\nparagraph second\n\n    indented\n    verbatim"
    structure = structure_for(value)
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 2),
        (DocstringBlockKind.BLANK, 2, 3),
        (DocstringBlockKind.PARAGRAPH, 3, 5),
        (DocstringBlockKind.BLANK, 5, 6),
        (DocstringBlockKind.VERBATIM, 6, 8),
    )
    assert tuple((region.kind, reflow_texts(region.lines), region.start_offset, region.end_offset) for region in structure.reflow_regions) == (
        (DocstringBlockKind.SUMMARY, ("Summary first", "summary second"), 0, 28),
        (DocstringBlockKind.PARAGRAPH, ("Paragraph first", "paragraph second"), 30, 62),
    )


def test_verbatim_blocks_exclude_trailing_blank_lines() -> None:
    structure = structure_for("Summary.\n\n    indented\n    verbatim\n\n\nBody.")

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 1),
        (DocstringBlockKind.BLANK, 1, 2),
        (DocstringBlockKind.VERBATIM, 2, 4),
        (DocstringBlockKind.BLANK, 4, 6),
        (DocstringBlockKind.PARAGRAPH, 6, 7),
    )


def test_a_leading_protected_block_prevents_a_later_paragraph_becoming_summary() -> None:
    assert top_level_blocks("```\ncode\n```\nLater prose.") == ((DocstringBlockKind.CODE_FENCE, 0, 3), (DocstringBlockKind.PARAGRAPH, 3, 4))


@pytest.mark.parametrize("header", ("Args:", "ARGS:", "Arguments", "Keyword Arguments:", "Other Args:"))
def test_google_section_header_spellings_are_case_insensitive_and_preserved(header: str) -> None:
    structure = structure_for(f"Summary.\n\n{header}\n    value: Description.", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple(section.name for section in structure.sections) == (header.removesuffix(":"),)
    assert structure.sections[0].header_line == 2
    assert structure.sections[0].start_line == 2
    assert structure.sections[0].end_line == 4


def test_adjacent_empty_google_sections_have_nonoverlapping_header_only_blocks() -> None:
    structure = structure_for("Args:\nReturns:", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((section.name, section.start_line, section.end_line, section.entries) for section in structure.sections) == (("Args", 0, 1, ()), ("Returns", 1, 2, ()))
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.SECTION, 0, 1), (DocstringBlockKind.SECTION, 1, 2))
    assert all(tuple(child.kind for child in block.children) == (DocstringBlockKind.SECTION_HEADER,) for block in structure.blocks)


@pytest.mark.parametrize(
    "name",
    (
        "Args",
        "Arguments",
        "Attention",
        "Attributes",
        "Caution",
        "Danger",
        "Error",
        "Example",
        "Examples",
        "Hint",
        "Important",
        "Keyword Args",
        "Keyword Arguments",
        "Methods",
        "Note",
        "Notes",
        "Other Args",
        "Other Arguments",
        "Raises",
        "References",
        "Return",
        "Returns",
        "See Also",
        "Tip",
        "Todo",
        "Warning",
        "Warnings",
        "Warns",
        "Yield",
        "Yields",
    ),
)
def test_all_google_section_names_are_recognized(name: str) -> None:
    structure = structure_for(f"{name}:\n    Content.", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple(section.name for section in structure.sections) == (name,)


def test_google_parameter_entries_support_stars_dotted_names_types_and_empty_descriptions() -> None:
    value = "Args:\n    *args (tuple[str, ...]): Positional values.\n    **kwargs (dict[str, object]):\n        Keyword values.\n    model.value: Untyped dotted name."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.names, entry.type_text, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("*args",), "tuple[str, ...]", "Positional values.", 1, 2),
        (("**kwargs",), "dict[str, object]", "Keyword values.", 2, 4),
        (("model.value",), None, "Untyped dotted name.", 4, 5),
    )


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    (
        ("Returns", "str: Result.", DocstringEntryKind.RETURN, (), "str"),
        ("Yields", "tuple[int, int]: Pair.", DocstringEntryKind.YIELD, (), "tuple[int, int]"),
        ("Raises", "ValueError: Invalid value.", DocstringEntryKind.EXCEPTION, ("ValueError",), None),
        ("Warns", "RuntimeWarning: Possibly unstable.", DocstringEntryKind.EXCEPTION, ("RuntimeWarning",), None),
        ("Warnings", "RuntimeWarning: Possibly unstable.", DocstringEntryKind.FIELD, ("RuntimeWarning",), None),
        ("Attributes", "name (str): Public name.", DocstringEntryKind.ATTRIBUTE, ("name",), "str"),
        ("Methods", "run: Execute it.", DocstringEntryKind.METHOD, ("run",), None),
        ("Notes", "topic: General note.", DocstringEntryKind.FIELD, ("topic",), None),
    ),
)
def test_google_section_names_determine_entry_semantics(section: str, entry_text: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...], expected_type: str | None) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry.type_text) == (expected_kind, expected_names, expected_type)


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind"),
    (("Returns", "None", DocstringEntryKind.RETURN), ("Returns", "None.", DocstringEntryKind.RETURN), ("Yields", "None", DocstringEntryKind.YIELD), ("Yields", "None.", DocstringEntryKind.YIELD)),
)
def test_google_return_and_yield_sections_parse_bare_none_as_empty_typed_entry(section: str, entry_text: str, expected_kind: DocstringEntryKind) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.kind, entry.names, entry.type_text, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((expected_kind, (), "None", "", 1, 2),)
    assert structure.reflow_regions == ()


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    (
        ("Returns", "Mapping[ str, Sequence[int  ]]: Result.", DocstringEntryKind.RETURN, (), "Mapping[ str, Sequence[int  ]]"),
        ("Yields", "Iterator[tuple[str, int | None]]: Item.", DocstringEntryKind.YIELD, (), "Iterator[tuple[str, int | None]]"),
        ("Raises", "mypkg.errors.CustomError: Bad value.", DocstringEntryKind.EXCEPTION, ("mypkg.errors.CustomError",), None),
        ("Raises", "ValueError | TypeError: Bad value.", DocstringEntryKind.EXCEPTION, ("ValueError | TypeError",), None),
    ),
)
def test_google_return_yield_and_raise_entries_preserve_generic_looking_type_text(
    section: str,
    entry_text: str,
    expected_kind: DocstringEntryKind,
    expected_names: tuple[str, ...],
    expected_type: str | None,
) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    entry = structure.entries[0]

    assert (entry.kind, entry.names, entry.type_text, entry.description) == (expected_kind, expected_names, expected_type, entry_text.rpartition(":")[2].strip())


@pytest.mark.parametrize(("section", "entry_text"), (("Returns", "str."), ("Yields", "Iterator[int]."), ("Raises", "None.")))
def test_google_bare_none_entry_special_case_does_not_apply_to_other_content(section: str, entry_text: str) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert structure.entries == ()


def test_google_section_boundaries_and_non_entry_content_are_nested_correctly() -> None:
    value = "Args:\n    Introductory prose without a field.\n\n    value: Description.\n\nExamples:\n    >>> call(value)\n    result\n\nTrailing prose."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((section.name, section.start_line, section.end_line, len(section.entries)) for section in structure.sections) == (("Args", 0, 5, 1), ("Examples", 5, 10, 0))
    assert tuple(block.kind for block in structure.blocks) == (DocstringBlockKind.SECTION, DocstringBlockKind.SECTION)
    assert DocstringBlockKind.VERBATIM in block_kinds(structure.blocks)
    assert DocstringBlockKind.DOCTEST in block_kinds(structure.blocks)


def test_google_section_headers_and_entries_inside_code_fences_are_opaque() -> None:
    value = "Args:\n    value: Description.\n\n```text\nReturns:\n    fake: Not an entry.\n```\n\nReturns:\n    str: Real result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((section.name, section.start_line, section.end_line) for section in structure.sections) == (("Args", 0, 8), ("Returns", 8, 10))
    assert tuple((entry.kind, entry.names, entry.type_text, entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), None, "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Real result."),
    )
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.SECTION_ENTRY, 1, 2),
        (DocstringBlockKind.BLANK, 2, 3),
        (DocstringBlockKind.CODE_FENCE, 3, 7),
        (DocstringBlockKind.BLANK, 7, 8),
    )


def test_indented_google_section_name_is_entry_description_text() -> None:
    value = "Args:\n    value: First line.\n        Returns:\n        Still the value description.\nReturns:\n    str: Actual result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.kind, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, "First line. Returns: Still the value description.", 1, 4),
        (DocstringEntryKind.RETURN, "Actual result.", 5, 6),
    )


def test_indented_google_section_headers_are_recognized_as_malformed_sections() -> None:
    value = "Summary.\n\n  Args:\n      value: Description.\n\n  Returns:\n      str: Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.kind, entry.names, entry.type_text, entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), None, "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Result."),
    )
    assert tuple((region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions if region.kind == DocstringBlockKind.SECTION_ENTRY) == (
        ("    value: ", "        "),
        ("    str: ", "        "),
    )


def test_nested_protected_blocks_are_not_folded_into_google_entry_descriptions() -> None:
    value = "Args:\n    value: Description.\n        - First choice.\n        - Second choice.\n        ```text\n        value: code, not prose\n        ```\n    other: Other description."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("value",), "Description.", 1, 2),
        (("other",), "Other description.", 7, 8),
    )
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.SECTION_ENTRY, 1, 2),
        (DocstringBlockKind.LIST_ITEM, 2, 3),
        (DocstringBlockKind.LIST_ITEM, 3, 4),
        (DocstringBlockKind.CODE_FENCE, 4, 7),
        (DocstringBlockKind.SECTION_ENTRY, 7, 8),
    )


def test_rest_fields_and_generic_reflow_regions_stay_in_source_order() -> None:
    value = ":param first: First description.\n- Interposed list item.\n:param second: Second description.\n> Quoted text.\n:param third: Third description."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    assert tuple((entry.names, entry.start_line) for entry in structure.entries) == ((("first",), 0), (("second",), 2), (("third",), 4))
    assert tuple((region.kind, region.start_line) for region in structure.reflow_regions) == (
        (DocstringBlockKind.REST_FIELD, 0),
        (DocstringBlockKind.LIST_ITEM, 1),
        (DocstringBlockKind.REST_FIELD, 2),
        (DocstringBlockKind.BLOCK_QUOTE, 3),
        (DocstringBlockKind.REST_FIELD, 4),
    )


@pytest.mark.parametrize("convention", (DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.NUMPY))
def test_google_sections_are_only_parsed_for_google_convention(convention: DocstringConvention) -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (int): A value.\n    """\n'
    data = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=convention)))
    assert data.docstrings[0].structure.sections == ()


def test_google_sections_parse_entries_and_reflow_descriptions() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (int): A value described on\n            two physical lines.\n\n    Returns:\n        str: The result.\n    """\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.kind, entry.names, entry.type_text, entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), "int", "A value described on two physical lines."),
        (DocstringEntryKind.RETURN, (), "str", "The result."),
    )
    assert tuple(reflow_texts(region.lines) for region in structure.reflow_regions) == (("Summary.",), ("A value described on", "two physical lines."), ("The result.",))


def test_numpy_sections_are_only_parsed_for_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        A value.\n    """\n'
    numpy = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))).docstrings[0].structure
    google = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    assert tuple(section.name for section in numpy.sections) == ("Parameters",)
    assert tuple((entry.kind, entry.names, entry.type_text, entry.description) for entry in numpy.entries) == ((DocstringEntryKind.PARAMETER, ("value",), "int", "A value."),)
    assert google.sections == ()


def test_indented_numpy_section_headers_are_recognized_as_malformed_sections() -> None:
    value = "Summary.\n\n  Parameters\n  ----------\n  value : int\n      Description.\n\n  Returns\n  -------\n  str\n      Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))

    assert tuple(section.name for section in structure.sections) == ("Parameters", "Returns")
    assert tuple((entry.kind, entry.names, entry.type_text, entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), "int", "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Result."),
    )
    assert tuple((region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions if region.kind == DocstringBlockKind.SECTION_ENTRY) == (("    ", "    "), ("    ", "    "))


@pytest.mark.parametrize("header", ("Parameters\n----------", "PARAMETERS\n==========", "Other Parameters", "Returns"))
def test_numpy_section_header_variants_are_recognized(header: str) -> None:
    structure = structure_for(f"{header}\nvalue : int\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert len(structure.sections) == 1
    section = structure.sections[0]
    assert section.name == header.splitlines()[0]
    assert section.header_line == 0
    assert section.entries[0].type_text == "int"


@pytest.mark.parametrize(
    "name",
    (
        "Attributes",
        "Examples",
        "Extended Summary",
        "Methods",
        "Notes",
        "Other Parameters",
        "Other Params",
        "Parameters",
        "Raises",
        "Receives",
        "References",
        "Returns",
        "See Also",
        "Short Summary",
        "Warnings",
        "Warns",
        "Yields",
    ),
)
def test_all_numpy_section_names_are_recognized(name: str) -> None:
    structure = structure_for(f"{name}\n{'-' * len(name)}\nContent.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple(section.name for section in structure.sections) == (name,)


def test_numpy_parameter_entries_support_multiple_names_stars_and_multiline_descriptions() -> None:
    value = "Parameters\n----------\nx, y : int | None\n    First description line.\n    Second description line.\n*args : tuple[str, ...]\n    Positional values.\n**kwargs : dict[str, object]"
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple((entry.names, entry.type_text, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("x", "y"), "int | None", "First description line. Second description line.", 2, 5),
        (("*args",), "tuple[str, ...]", "Positional values.", 5, 7),
        (("**kwargs",), "dict[str, object]", "", 7, 8),
    )
    assert tuple((region.start_line, region.end_line, reflow_texts(region.lines), region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions) == (
        (3, 5, ("First description line.", "Second description line."), "    ", "    "),
        (6, 7, ("Positional values.",), "    ", "    "),
    )


def test_numpy_section_headers_and_entries_inside_code_fences_are_opaque() -> None:
    value = "Parameters\n----------\nx : int\n    Description.\n\n```text\nReturns\n-------\nfake : entry\n```\n\nReturns\n-------\nstr\n    Real result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple((section.name, section.start_line, section.end_line) for section in structure.sections) == (("Parameters", 0, 11), ("Returns", 11, 15))
    assert tuple((entry.kind, entry.names, entry.type_text, entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("x",), "int", "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Real result."),
    )
    assert DocstringBlockKind.CODE_FENCE in block_kinds(structure.blocks[0].children)


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    (
        ("Returns", "str", DocstringEntryKind.RETURN, (), "str"),
        ("Yields", "Iterator[int]", DocstringEntryKind.YIELD, (), "Iterator[int]"),
        ("Raises", "ValueError", DocstringEntryKind.EXCEPTION, ("ValueError",), None),
        ("Warnings", "RuntimeWarning", DocstringEntryKind.EXCEPTION, ("RuntimeWarning",), None),
        ("Attributes", "name : str", DocstringEntryKind.ATTRIBUTE, ("name",), "str"),
        ("Methods", "run : Callable[[], None]", DocstringEntryKind.METHOD, ("run",), "Callable[[], None]"),
        ("Receives", "value : int", DocstringEntryKind.PARAMETER, ("value",), "int"),
    ),
)
def test_numpy_section_names_determine_entry_semantics(section: str, entry_text: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...], expected_type: str | None) -> None:
    structure = structure_for(f"{section}\n{'-' * len(section)}\n{entry_text}\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry.type_text, entry.description) == (expected_kind, expected_names, expected_type, "Description.")


def test_numpy_colon_header_is_not_misclassified_as_a_section() -> None:
    structure = structure_for("Parameters:\nvalue : int\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert structure.sections == ()


def test_numpy_bare_return_without_description_does_not_create_reflow_region() -> None:
    structure = structure_for("Returns\n-------\nstr", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple((entry.names, entry.type_text, entry.description) for entry in structure.entries) == (((), "str", ""),)
    assert structure.reflow_regions == ()


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    (
        ("Returns", "Mapping[str, Sequence[int]]", DocstringEntryKind.RETURN, (), "Mapping[str, Sequence[int]]"),
        ("Yields", "Iterator[tuple[str, int | None]]", DocstringEntryKind.YIELD, (), "Iterator[tuple[str, int | None]]"),
        ("Raises", "mypkg.errors.CustomError", DocstringEntryKind.EXCEPTION, ("mypkg.errors.CustomError",), None),
    ),
)
def test_numpy_return_yield_and_raise_entries_preserve_generic_looking_type_text(
    section: str,
    entry_text: str,
    expected_kind: DocstringEntryKind,
    expected_names: tuple[str, ...],
    expected_type: str | None,
) -> None:
    structure = structure_for(f"{section}\n{'-' * len(section)}\n{entry_text}\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    entry = structure.entries[0]

    assert (entry.kind, entry.names, entry.type_text, entry.description) == (expected_kind, expected_names, expected_type, "Description.")


def test_section_block_contains_header_entries_blanks_and_generic_children() -> None:
    structure = structure_for("Args:\n\n    value: Description.\n\n    - nested item\n      continuation", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    section_block = structure.blocks[0]
    assert section_block.kind == DocstringBlockKind.SECTION
    assert tuple((child.kind, child.start_line, child.end_line) for child in section_block.children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.BLANK, 1, 2),
        (DocstringBlockKind.SECTION_ENTRY, 2, 3),
        (DocstringBlockKind.BLANK, 3, 4),
        (DocstringBlockKind.LIST_ITEM, 4, 6),
    )
    assert section_block.children[2].entry is structure.entries[0]


@pytest.mark.parametrize(
    ("field", "expected_kind", "expected_names"),
    (
        (":param value: Description.", DocstringEntryKind.PARAMETER, ("value",)),
        (":kwarg option: Description.", DocstringEntryKind.PARAMETER, ("option",)),
        (":type value: int", DocstringEntryKind.PARAMETER, ("value",)),
        (":returns: Description.", DocstringEntryKind.RETURN, ()),
        (":rtype: str", DocstringEntryKind.RETURN, ()),
        (":yield item: Description.", DocstringEntryKind.YIELD, ("item",)),
        (":raises ValueError: Description.", DocstringEntryKind.EXCEPTION, ("ValueError",)),
        (":meta private: Description.", DocstringEntryKind.FIELD, ("private",)),
    ),
)
def test_rest_field_aliases_map_to_semantic_entry_kinds(field: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...]) -> None:
    structure = structure_for(field, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry.description) == (expected_kind, expected_names, field.rpartition(":")[2].strip())
    assert structure.blocks[0].entry is entry


@pytest.mark.parametrize(
    ("field", "expected_names", "expected_type"),
    (
        (":param int first: Description.", ("first",), "int"),
        (":param int\tfirst: Description.", ("first",), "int"),
        (":param dict[str, int] options: Description.", ("options",), "dict[str, int]"),
        (":param tuple[str, ...] *args: Description.", ("*args",), "tuple[str, ...]"),
        (":kwarg Mapping[str, object] **kwargs: Description.", ("**kwargs",), "Mapping[str, object]"),
    ),
)
def test_typed_rest_parameter_fields_split_type_from_name(field: str, expected_names: tuple[str, ...], expected_type: str) -> None:
    structure = structure_for(field, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry.type_text, entry.description) == (DocstringEntryKind.PARAMETER, expected_names, expected_type, "Description.")


@pytest.mark.parametrize(
    ("field", "expected_kind", "expected_names", "expected_description"),
    (
        (":rtype: Mapping[str, Sequence[int]]", DocstringEntryKind.RETURN, (), "Mapping[str, Sequence[int]]"),
        (":ytype: Iterator[tuple[str, int | None]]", DocstringEntryKind.YIELD, (), "Iterator[tuple[str, int | None]]"),
        (":raises mypkg.errors.CustomError: Bad value.", DocstringEntryKind.EXCEPTION, ("mypkg.errors.CustomError",), "Bad value."),
    ),
)
def test_rest_return_yield_and_raise_fields_preserve_generic_looking_type_text(
    field: str,
    expected_kind: DocstringEntryKind,
    expected_names: tuple[str, ...],
    expected_description: str,
) -> None:
    structure = structure_for(field, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    entry = structure.entries[0]

    assert (entry.kind, entry.names, entry.type_text, entry.description) == (expected_kind, expected_names, None, expected_description)


@pytest.mark.parametrize(
    ("field", "expected_kind"),
    (
        ("param", DocstringEntryKind.PARAMETER),
        ("parameter", DocstringEntryKind.PARAMETER),
        ("arg", DocstringEntryKind.PARAMETER),
        ("argument", DocstringEntryKind.PARAMETER),
        ("keyword", DocstringEntryKind.PARAMETER),
        ("kwarg", DocstringEntryKind.PARAMETER),
        ("return", DocstringEntryKind.RETURN),
        ("returns", DocstringEntryKind.RETURN),
        ("rtype", DocstringEntryKind.RETURN),
        ("yield", DocstringEntryKind.YIELD),
        ("yields", DocstringEntryKind.YIELD),
        ("ytype", DocstringEntryKind.YIELD),
        ("raise", DocstringEntryKind.EXCEPTION),
        ("raises", DocstringEntryKind.EXCEPTION),
        ("except", DocstringEntryKind.EXCEPTION),
        ("exception", DocstringEntryKind.EXCEPTION),
        ("custom", DocstringEntryKind.FIELD),
    ),
)
def test_all_rest_field_aliases_are_classified(field: str, expected_kind: DocstringEntryKind) -> None:
    entry = structure_for(f":{field}: Description.", settings=CheckSettings(docstring_convention=DocstringConvention.REST)).entries[0]
    assert entry.kind == expected_kind


def test_rest_field_continuation_and_tabbed_prefix_have_exact_reflow_indentation() -> None:
    structure = structure_for("\n\t:param value: First line.\n\t\tSecond line.", settings=CheckSettings(docstring_convention=DocstringConvention.REST, indent_width=2))
    entry = structure.entries[0]
    region = structure.reflow_regions[0]
    assert entry.description == "First line. Second line."
    assert reflow_texts(region.lines) == ("First line.", "Second line.")
    assert region.initial_indent == "\t:param value: "
    assert region.subsequent_indent == " " * 16


def test_rest_field_stops_before_a_peer_list_item() -> None:
    value = ":param value: Description.\n- Peer list item."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    assert tuple((entry.names, entry.start_line, entry.end_line) for entry in structure.entries) == ((("value",), 0, 1),)
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.REST_FIELD, 0, 1),
        (DocstringBlockKind.LIST_ITEM, 1, 2),
    )


def test_rest_field_includes_indented_protected_body_without_reflowing_it() -> None:
    value = ":param value:\n    - First choice.\n      Continued choice.\n    - Second choice.\n:returns: Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("value",), "", 0, 4),
        ((), "Result.", 4, 5),
    )
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.REST_FIELD, 0, 4),
        (DocstringBlockKind.REST_FIELD, 4, 5),
    )
    assert tuple((region.kind, region.start_line, region.end_line, reflow_texts(region.lines)) for region in structure.reflow_regions) == ((DocstringBlockKind.REST_FIELD, 4, 5, ("Result.",)),)


def test_rest_field_inline_description_reflow_stops_before_protected_body() -> None:
    value = ":param value: Intro text.\n    - First choice.\n      Continued choice.\n    - Second choice.\n:returns: Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("value",), "Intro text.", 0, 4),
        ((), "Result.", 4, 5),
    )
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.REST_FIELD, 0, 4),
        (DocstringBlockKind.REST_FIELD, 4, 5),
    )
    assert tuple((region.kind, region.start_line, region.end_line, reflow_texts(region.lines)) for region in structure.reflow_regions) == (
        (DocstringBlockKind.REST_FIELD, 0, 1, ("Intro text.",)),
        (DocstringBlockKind.REST_FIELD, 4, 5, ("Result.",)),
    )


def test_rest_fields_are_not_semantic_inside_google_sections() -> None:
    value = "Examples:\n    :param value: Description.\n    - Peer list item."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert structure.entries == ()
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.VERBATIM, 1, 3),
    )


@pytest.mark.parametrize("convention", tuple(DocstringConvention))
def test_structure_records_the_explicit_docstring_convention(convention: DocstringConvention) -> None:
    assert structure_for("Summary.", settings=CheckSettings(docstring_convention=convention)).convention is convention


@pytest.mark.parametrize(
    ("value", "expected_ranges", "expected_regions"),
    (
        ("- first\n  continuation\n+ second\n* third", ((0, 2), (2, 3), (3, 4)), (("- ", "  "), ("+ ", "  "), ("* ", "  "))),
        ("1. first\n   continuation\n2) second", ((0, 2), (2, 3)), (("1. ", "   "), ("2) ", "   "))),
        ("\n\t- tabbed\n\t\tcontinuation", ((1, 3),), (("\t- ", " " * 6),)),
    ),
)
def test_list_markers_boundaries_and_reflow_prefixes(value: str, expected_ranges: tuple[tuple[int, int], ...], expected_regions: tuple[tuple[str, str], ...]) -> None:
    structure = structure_for(value)
    blocks = tuple(block for block in structure.blocks if block.kind == DocstringBlockKind.LIST_ITEM)
    regions = tuple(region for region in structure.reflow_regions if region.kind == DocstringBlockKind.LIST_ITEM)
    assert tuple((block.start_line, block.end_line) for block in blocks) == expected_ranges
    assert tuple((region.initial_indent, region.subsequent_indent) for region in regions) == expected_regions


def test_empty_list_item_is_classified_without_an_empty_reflow_region() -> None:
    structure = structure_for("- ")
    assert tuple(block.kind for block in structure.blocks) == (DocstringBlockKind.LIST_ITEM,)
    assert structure.reflow_regions == ()


def test_block_quote_depth_and_spacing_split_distinct_reflow_regions() -> None:
    structure = structure_for("> first\n> second\n>> nested\n>  differently spaced")
    assert tuple((block.start_line, block.end_line) for block in structure.blocks) == ((0, 2), (2, 3), (3, 4))
    assert tuple((reflow_texts(region.lines), region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions) == (
        (("first", "second"), "> ", "> "),
        (("nested",), ">> ", ">> "),
        (("differently spaced",), ">  ", ">  "),
    )


@pytest.mark.parametrize(
    ("value", "expected_end"),
    (
        ("```python\ncode\n```\nafter", 3),
        ("````\n```\nstill code\n`````\nafter", 4),
        ("~~~text\ncode\n```\nstill code\n~~~\nafter", 5),
        ("```\nunclosed", 2),
    ),
)
def test_code_fences_require_compatible_closing_delimiters(value: str, expected_end: int) -> None:
    block = structure_for(value).blocks[0]
    assert (block.kind, block.start_line, block.end_line) == (DocstringBlockKind.CODE_FENCE, 0, expected_end)


def test_doctest_consumes_nonblank_transcript_but_stops_at_blank_line() -> None:
    structure = structure_for(">>> value = 1\n>>> value + 1\n2\n\nFollowing paragraph.")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.DOCTEST, 0, 3),
        (DocstringBlockKind.BLANK, 3, 4),
        (DocstringBlockKind.PARAGRAPH, 4, 5),
    )


@pytest.mark.parametrize("prompt", (">>>> quoted", ">>>>>>> branch"))
def test_doctest_prompt_requires_trailing_whitespace(prompt: str) -> None:
    structure = structure_for(f"{prompt}\nfollowing prose")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.BLOCK_QUOTE, 0, 1),
        (DocstringBlockKind.PARAGRAPH, 1, 2),
    )
    assert DocstringBlockKind.DOCTEST not in block_kinds(structure.blocks)


def test_directives_and_literal_blocks_include_blank_lines_and_indented_bodies() -> None:
    directive = structure_for(".. warning:: title\n\n    First body line.\n        Nested.\nAfter.")
    literal = structure_for("Example::\n\n    value = 1\n    print(value)\nAfter.")
    assert tuple((block.kind, block.start_line, block.end_line) for block in directive.blocks) == ((DocstringBlockKind.DIRECTIVE, 0, 4), (DocstringBlockKind.PARAGRAPH, 4, 5))
    assert tuple((block.kind, block.start_line, block.end_line) for block in literal.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 4), (DocstringBlockKind.PARAGRAPH, 4, 5))


def test_literal_block_detection_compares_visual_indentation_with_tabs() -> None:
    shallower_spaces = structure_for("\n\tExample::\n    Not nested.")
    deeper_tab = structure_for("\n    Example::\n\tNested.")
    assert DocstringBlockKind.LITERAL_BLOCK not in block_kinds(shallower_spaces.blocks)
    assert tuple((block.kind, block.start_line, block.end_line) for block in deeper_tab.blocks) == ((DocstringBlockKind.BLANK, 0, 1), (DocstringBlockKind.LITERAL_BLOCK, 1, 3))


@pytest.mark.parametrize(
    ("value", "expected_end"),
    (
        ("| A | B |\n| :--- | ---: |\n| 1 | 2 |\nAfter", 3),
        ("+---+---+\n| A | B |\n+===+===+\n| 1 | 2 |\n+---+---+\nAfter", 5),
        ("=== ===\nA   B\n--- ---\n1   2\n\nAfter", 4),
    ),
)
def test_markdown_and_rest_table_variants_are_protected(value: str, expected_end: int) -> None:
    block = structure_for(value).blocks[0]
    assert (block.kind, block.start_line, block.end_line) == (DocstringBlockKind.TABLE, 0, expected_end)


@pytest.mark.parametrize(
    ("value", "expected_end"),
    (
        ("# ATX heading\nAfter", 1),
        ("### Deeper heading ###\nAfter", 1),
        ("Setext heading\n===============\nAfter", 2),
        ("reST heading\n~~~~~~~~~~~~\nAfter", 2),
    ),
)
def test_markdown_and_rest_heading_variants_are_protected(value: str, expected_end: int) -> None:
    block = structure_for(value).blocks[0]
    assert (block.kind, block.start_line, block.end_line) == (DocstringBlockKind.HEADING, 0, expected_end)


@pytest.mark.parametrize(
    ("value", "unexpected_kind"),
    (
        ("#Not a heading", DocstringBlockKind.HEADING),
        ("| A | B |\n| -- | --- |", DocstringBlockKind.TABLE),
        (".. note: not a directive", DocstringBlockKind.DIRECTIVE),
        ("Example::\nnot indented", DocstringBlockKind.LITERAL_BLOCK),
        ("Example::", DocstringBlockKind.LITERAL_BLOCK),
        (":param missing terminator", DocstringBlockKind.REST_FIELD),
        ("-missing marker space", DocstringBlockKind.LIST_ITEM),
        ("ordinary > embedded quote", DocstringBlockKind.BLOCK_QUOTE),
    ),
)
def test_malformed_structures_are_not_overclassified(value: str, unexpected_kind: DocstringBlockKind) -> None:
    assert unexpected_kind not in block_kinds(structure_for(value).blocks)


def test_generic_structures_are_classified_and_protected_inside_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Examples:\n        ```python\n        print(value)\n        ```\n\n    - A list item continued on\n      another line.\n    > A quoted line\n    > continued.\n    :param value: A Sphinx description\n        continued.\n    """\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    kinds = block_kinds(structure.blocks)
    assert DocstringBlockKind.CODE_FENCE in kinds
    assert DocstringBlockKind.LIST_ITEM in kinds
    assert DocstringBlockKind.BLOCK_QUOTE in kinds
    assert DocstringBlockKind.REST_FIELD not in kinds
    assert tuple(region.kind for region in structure.reflow_regions) == (DocstringBlockKind.SUMMARY, DocstringBlockKind.LIST_ITEM, DocstringBlockKind.BLOCK_QUOTE, DocstringBlockKind.PARAGRAPH)


def test_directives_literal_blocks_and_tables_are_opaque_to_section_entry_parsing() -> None:
    value = "Examples:\n    .. note::\n        field: Directive body.\n\n    Literal::\n\n        field: Literal body.\n\n    | Name | Value |\n    | --- | --- |\n    | field | Table body |"
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert structure.entries == ()
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.DIRECTIVE, 1, 3),
        (DocstringBlockKind.BLANK, 3, 4),
        (DocstringBlockKind.LITERAL_BLOCK, 4, 7),
        (DocstringBlockKind.BLANK, 7, 8),
        (DocstringBlockKind.TABLE, 8, 11),
    )


@pytest.mark.parametrize(
    ("settings", "source", "kind"),
    (
        (CheckSettings(docstring_parse_list_items=False), "- item", DocstringBlockKind.LIST_ITEM),
        (CheckSettings(docstring_parse_headings=False), "# Heading", DocstringBlockKind.HEADING),
        (CheckSettings(docstring_parse_doctests=False), ">>> call()", DocstringBlockKind.DOCTEST),
        (CheckSettings(docstring_parse_code_fences=False), "```python\nvalue = 1\n```", DocstringBlockKind.CODE_FENCE),
        (CheckSettings(docstring_parse_block_quotes=False), "> quote", DocstringBlockKind.BLOCK_QUOTE),
        (CheckSettings(docstring_parse_tables=False), "| A | B |\n| --- | --- |\n| 1 | 2 |", DocstringBlockKind.TABLE),
        (CheckSettings(docstring_parse_directives=False), ".. note::\n    body", DocstringBlockKind.DIRECTIVE),
        (CheckSettings(docstring_parse_literal_blocks=False), "Example::\n\n    value = 1", DocstringBlockKind.LITERAL_BLOCK),
    ),
)
def test_structure_recognizers_can_be_disabled(settings: CheckSettings, source: str, kind: DocstringBlockKind) -> None:
    enabled = PDF.prepare(category_context(f'"""{source}"""\n')).docstrings[0].structure
    disabled = PDF.prepare(category_context(f'"""{source}"""\n', settings=settings)).docstrings[0].structure
    assert kind in block_kinds(enabled.blocks)
    assert kind not in block_kinds(disabled.blocks)


def test_rest_field_recognition_is_controlled_by_docstring_convention() -> None:
    source = '""":param value: description"""\n'
    rest = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.REST))).docstrings[0].structure
    google = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure

    assert DocstringBlockKind.REST_FIELD in block_kinds(rest.blocks)
    assert rest.entries[0].names == ("value",)
    assert DocstringBlockKind.REST_FIELD not in block_kinds(google.blocks)
    assert google.entries == ()


def test_rest_field_metadata_preserves_field_names_and_arguments_for_rule_helpers() -> None:
    value = ":PARAM int value: Description.\n:type value: int\n:meta private: yes\n:raises errors.ValueError: Bad value."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert tuple((entry.field_name, entry.field_argument, entry.names, entry.type_text, entry.description) for entry in structure.entries) == (
        ("param", "int value", ("value",), "int", "Description."),
        ("type", "value", ("value",), None, "int"),
        ("meta", "private", ("private",), None, "yes"),
        ("raises", "errors.ValueError", ("errors.ValueError",), None, "Bad value."),
    )


def test_disabling_directives_falls_back_to_literal_blocks_before_plain_text() -> None:
    value = ".. note::\n\n    Body."
    directive = structure_for(value)
    literal = structure_for(value, settings=CheckSettings(docstring_parse_directives=False))
    plain = structure_for(value, settings=CheckSettings(docstring_parse_directives=False, docstring_parse_literal_blocks=False))
    assert tuple(block.kind for block in directive.blocks) == (DocstringBlockKind.DIRECTIVE,)
    assert tuple(block.kind for block in literal.blocks) == (DocstringBlockKind.LITERAL_BLOCK,)
    assert tuple(block.kind for block in plain.blocks) == (DocstringBlockKind.SUMMARY, DocstringBlockKind.BLANK, DocstringBlockKind.VERBATIM)


def test_disabling_all_generic_recognizers_produces_one_plain_reflow_region() -> None:
    settings = CheckSettings(
        docstring_parse_list_items=False,
        docstring_parse_headings=False,
        docstring_parse_doctests=False,
        docstring_parse_code_fences=False,
        docstring_parse_block_quotes=False,
        docstring_parse_tables=False,
        docstring_parse_directives=False,
        docstring_parse_literal_blocks=False,
    )
    value = "# Heading\n>>> call()\n- item\n> quote\n:param value: description"
    structure = structure_for(value, settings=settings)
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.SUMMARY, 0, 5),)
    assert structure.entries == ()
    assert tuple((region.kind, reflow_texts(region.lines)) for region in structure.reflow_regions) == ((DocstringBlockKind.SUMMARY, tuple(value.splitlines())),)


def test_convention_sections_remain_enabled_when_all_generic_recognizers_are_disabled() -> None:
    settings = CheckSettings(
        docstring_convention=DocstringConvention.GOOGLE,
        docstring_parse_list_items=False,
        docstring_parse_headings=False,
        docstring_parse_doctests=False,
        docstring_parse_code_fences=False,
        docstring_parse_block_quotes=False,
        docstring_parse_tables=False,
        docstring_parse_directives=False,
        docstring_parse_literal_blocks=False,
    )
    structure = structure_for("Args:\n    value: Description.", settings=settings)
    assert tuple(section.name for section in structure.sections) == ("Args",)
    assert tuple((entry.kind, entry.names, entry.description) for entry in structure.entries) == ((DocstringEntryKind.PARAMETER, ("value",), "Description."),)


def test_code_fence_setting_controls_whether_fenced_section_syntax_is_opaque() -> None:
    value = "Args:\n```text\nReturns:\n    fake: Fake result.\n```\nReturns:\n    str: Real result."
    enabled = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    disabled = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE, docstring_parse_code_fences=False))
    assert tuple(section.name for section in enabled.sections) == ("Args", "Returns")
    assert tuple(section.name for section in disabled.sections) == ("Args", "Returns", "Returns")


def test_indent_width_changes_generated_tab_prefix_width_without_changing_semantics() -> None:
    value = "\n\t- First line.\n\t\tContinuation."
    narrow = structure_for(value, settings=CheckSettings(indent_width=2))
    wide = structure_for(value, settings=CheckSettings(indent_width=8))
    assert narrow.blocks == wide.blocks
    assert narrow.entries == wide.entries
    assert narrow.reflow_regions[0].initial_indent == wide.reflow_regions[0].initial_indent == "\t- "
    assert narrow.reflow_regions[0].subsequent_indent == " " * 4
    assert wide.reflow_regions[0].subsequent_indent == " " * 10


def test_complex_mixed_structure_partitions_lines_and_orders_semantic_regions() -> None:
    value = "Summary first line.\nsummary second line.\n\nArgs:\n    value: Description.\n        - Choice one.\n        - Choice two.\n    other: Other description.\n    :param legacy: Legacy description.\n\n    ```text\n    Returns:\n        fake: code\n    ```\n\nReturns:\n    tuple[str, int]: Result.\n\nTrailing section prose."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert_block_partition(structure.blocks, 0, len(structure.lines))
    assert tuple(section.start_line for section in structure.sections) == tuple(sorted(section.start_line for section in structure.sections))
    assert tuple(entry.start_line for entry in structure.entries) == tuple(sorted(entry.start_line for entry in structure.entries))
    assert tuple(region.start_line for region in structure.reflow_regions) == tuple(sorted(region.start_line for region in structure.reflow_regions))
    assert all(0 <= region.start_offset <= region.end_offset <= len(value) for region in structure.reflow_regions)
    assert all(structure.lines[region.start_line].start_offset == region.start_offset for region in structure.reflow_regions)
    assert all(structure.lines[region.end_line - 1].end_offset == region.end_offset for region in structure.reflow_regions)
    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.names, entry.type_text) for entry in structure.entries) == ((("value",), None), (("other",), None), ((), "tuple[str, int]"))
