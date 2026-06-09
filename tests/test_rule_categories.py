import enum
import json
import unittest

from pydocformatter.rules.definitions.PCF.PCF import CommentKind, CommentPlacement
from pydocformatter.rules.definitions.PDF.PDF import DefinitionKind, DocstringKind


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
