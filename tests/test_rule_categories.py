import enum
import json
import unittest

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.collection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PCF.PCF import PCF, CommentKind, CommentPlacement, PCFCategoryData
from pydocformatter.rules.definitions.PDF.PDF import PDF, DefinitionKind, DocstringKind, PDFCategoryData


class TestCategoryEnums(unittest.TestCase):
    def test_internal_classification_enums_require_explicit_string_conversion(self) -> None:
        enum_types = (DefinitionKind, DocstringKind, CommentPlacement, CommentKind)

        for enum_type in enum_types:
            with self.subTest(enum_type=enum_type.__name__):
                member = next(iter(enum_type))
                self.assertTrue(issubclass(enum_type, enum.Enum))
                self.assertFalse(issubclass(enum_type, enum.StrEnum))
                self.assertNotEqual(member, member.value)
                with self.assertRaises(TypeError):
                    json.dumps(member)
                self.assertEqual(json.dumps(member.value), f'"{member.value}"')


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


class TestPCFCategory(unittest.TestCase):
    def test_prepare_classifies_comments_and_groups_only_eligible_standalone_blocks(self) -> None:
        source = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n# first\n# second\n#\n# third\ndef f():\n    # inner first\n    # inner second\n    value = 1  # trailing\n# type: ignore\n# noqa\n"

        data = PCF.prepare(category_context(source))

        self.assertEqual(
            tuple(comment.text for comment in data.comments),
            ("#!/usr/bin/env python", "# -*- coding: utf-8 -*-", "# first", "# second", "#", "# third", "# inner first", "# inner second", "# trailing", "# type: ignore", "# noqa"),
        )
        self.assertEqual(
            tuple(comment.kind for comment in data.comments),
            (
                CommentKind.SHEBANG,
                CommentKind.ENCODING_COOKIE,
                CommentKind.REGULAR,
                CommentKind.REGULAR,
                CommentKind.REGULAR,
                CommentKind.REGULAR,
                CommentKind.REGULAR,
                CommentKind.REGULAR,
                CommentKind.REGULAR,
                CommentKind.TYPE_DIRECTIVE,
                CommentKind.TOOL_DIRECTIVE,
            ),
        )
        self.assertEqual(
            tuple(comment.placement for comment in data.comments), (CommentPlacement.STANDALONE,) * 8 + (CommentPlacement.TRAILING, CommentPlacement.STANDALONE, CommentPlacement.STANDALONE)
        )
        self.assertEqual(tuple(comment.indent for comment in data.comments), ("", "", "", "", "", "", "    ", "    ", "    ", "", ""))
        self.assertEqual(tuple(tuple(comment.text for comment in block.comments) for block in data.standalone_blocks), (("# first", "# second"), ("# third",), ("# inner first", "# inner second")))
        self.assertEqual(tuple(block.indent for block in data.standalone_blocks), ("", "", "    "))

    def test_prepare_preserves_comment_order_with_crlf_source(self) -> None:
        data = PCF.prepare(category_context("# first\r\nvalue = 1  # second\r\n"))

        self.assertEqual(tuple((comment.text, comment.range.start.line) for comment in data.comments), (("# first", 1), ("# second", 2)))

    def test_second_line_encoding_text_after_code_is_regular_comment(self) -> None:
        data = PCF.prepare(category_context('value = """first second"""\n# coding: utf-8\n'))

        self.assertEqual(data.comments[0].kind, CommentKind.REGULAR)
        self.assertEqual(data.comments[0].range.start.line, 2)

    def test_require_data_validates_category_data_type(self) -> None:
        context = category_context("# comment\n")
        data = PCF.prepare(context)

        self.assertIs(PCF.require_data(rule_context(context, data)), data)
        with self.assertRaisesRegex(TypeError, "require PCFCategoryData"):
            PCF.require_data(rule_context(context, None))


class TestPDFCategory(unittest.TestCase):
    def test_prepare_collects_definitions_docstrings_and_owner_metadata(self) -> None:
        source = '"""module doc"""\n@decorator\nclass Outer:\n    """class doc"""\n    async def method(self, value: int) -> str:\n        ("method doc")\n        return str(value)\n\n    def no_doc(self):\n        pass\n\ndef concatenated():\n    "first " "second"\n\ndef empty(): "" ; return None\ndef formatted():\n    f"not a docstring"\ndef binary():\n    b"not a docstring"\n'

        data = PDF.prepare(category_context(source))

        self.assertEqual(
            tuple((definition.kind, definition.qualified_name) for definition in data.definitions),
            (
                (DefinitionKind.MODULE, "<module>"),
                (DefinitionKind.CLASS, "Outer"),
                (DefinitionKind.FUNCTION, "Outer.method"),
                (DefinitionKind.FUNCTION, "Outer.no_doc"),
                (DefinitionKind.FUNCTION, "concatenated"),
                (DefinitionKind.FUNCTION, "empty"),
                (DefinitionKind.FUNCTION, "formatted"),
                (DefinitionKind.FUNCTION, "binary"),
            ),
        )
        self.assertEqual(tuple(docstring.owner.qualified_name for docstring in data.docstrings), ("<module>", "Outer", "Outer.method", "concatenated", "empty"))
        self.assertEqual(tuple(docstring.kind for docstring in data.docstrings), (DocstringKind.SIMPLE, DocstringKind.SIMPLE, DocstringKind.SIMPLE, DocstringKind.CONCATENATED, DocstringKind.SIMPLE))
        self.assertEqual(tuple(docstring.value for docstring in data.docstrings), ("module doc", "class doc", "method doc", "first second", ""))
        self.assertEqual(data.docstrings[2].source, '"method doc"')
        self.assertTrue(data.definitions[2].asynchronous)
        self.assertEqual(len(data.definitions[1].decorators), 1)
        self.assertIsNotNone(data.definitions[2].parameters)
        self.assertIsNotNone(data.definitions[2].returns)
        self.assertIs(data.definitions[2].parent, data.definitions[1])
        self.assertIs(data.docstring_for(data.definitions[1]), data.docstrings[1])
        self.assertIsNone(data.docstring_for(data.definitions[3]))

    def test_prepare_preserves_multiline_crlf_source_and_physical_lines(self) -> None:
        source = 'def function():\r\n    r"""first\r\n    second"""\r\n    pass\r\n'

        data = PDF.prepare(category_context(source))
        docstring = data.docstrings[0]

        self.assertEqual(docstring.source, 'r"""first\r\n    second"""')
        self.assertEqual(tuple((line.line_number, line.start_column, line.end_column, line.source) for line in docstring.physical_lines), ((2, 4, 13, 'r"""first'), (3, 0, 13, '    second"""')))
        self.assertEqual(docstring.value_lines, ("first", "    second"))

    def test_prepare_accepts_only_string_valued_first_expressions_as_docstrings(self) -> None:
        source = 'def parenthesized():\n    (u"doc")\n\ndef later_string():\n    value = 1\n    "not a docstring"\n'

        data = PDF.prepare(category_context(source))

        self.assertEqual(tuple(docstring.owner.qualified_name for docstring in data.docstrings), ("parenthesized",))
        self.assertEqual(data.docstrings[0].source, 'u"doc"')

    def test_unicode_line_separator_inside_literal_is_not_a_physical_source_line(self) -> None:
        data = PDF.prepare(category_context('"""first second"""\n'))

        self.assertEqual(len(data.docstrings[0].physical_lines), 1)
        self.assertEqual(data.docstrings[0].physical_lines[0].source, '"""first second"""')

    def test_require_data_validates_category_data_type(self) -> None:
        context = category_context('"""doc"""\n')
        data = PDF.prepare(context)

        self.assertIs(PDF.require_data(rule_context(context, data)), data)
        with self.assertRaisesRegex(TypeError, "require PDFCategoryData"):
            PDF.require_data(rule_context(context, None))
