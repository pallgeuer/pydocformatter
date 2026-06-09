import libcst as cst
import libcst.metadata as cst_metadata
import pytest

from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF, DefinitionKind, DocstringKind


def category_context(source: str) -> RuleCategoryContext:
    module = cst.parse_module(source)
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    return RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(experimental=True),
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
