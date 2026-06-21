import unittest
import unittest.mock

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.edits as rule_edits
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleCategoryContext
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


class TestSourceEdits(unittest.TestCase):
    def test_planned_source_changes_apply_edits_and_create_findings(self) -> None:
        module = cst.parse_module("value = 1\n")
        rule = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test message", fix_availability=FixAvailability.ALWAYS, stable_since="1.0.0", setting_effects=(), incompatible_with=())
        changes = (
            rule_edits.PlannedSourceChange(
                edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 8), end=cst_metadata.CodePosition(1, 9)), "2"),
                line_numbers=(1,),
            ),
        )

        result = rule_edits.apply_planned_source_changes(module, changes)
        findings = rule_edits.findings_for_planned_source_changes(rule, changes)
        explicitly_fixable_findings = rule_edits.findings_for_planned_source_changes(rule, changes, instance_fixable=True)

        self.assertEqual(result.code, "value = 2\n")
        self.assertEqual(findings, (RuleFinding(rule=rule, line_numbers=(1,)),))
        self.assertEqual(explicitly_fixable_findings, (RuleFinding(rule=rule, line_numbers=(1,), instance_fixable=True),))

    def test_sometimes_fixable_findings_require_explicit_instance_fixability(self) -> None:
        rule = RuleMetadata(
            code=RuleCode("PDF999"), name="test-rule", message="Test message", fix_availability=FixAvailability.SOMETIMES, stable_since="1.0.0", setting_effects=(), incompatible_with=()
        )
        changes = (
            rule_edits.PlannedSourceChange(
                edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""),
                line_numbers=(1,),
            ),
        )

        with self.assertRaisesRegex(ValueError, "must specify instance_fixable"):
            rule_edits.findings_for_planned_source_changes(rule, changes)

    def test_usually_fixable_findings_require_explicit_instance_fixability(self) -> None:
        rule = RuleMetadata(code=RuleCode("PDF999"), name="test-rule", message="Test message", fix_availability=FixAvailability.USUALLY, stable_since="1.0.0", setting_effects=(), incompatible_with=())
        changes = (
            rule_edits.PlannedSourceChange(
                edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 0)), ""),
                line_numbers=(1,),
            ),
        )

        with self.assertRaisesRegex(ValueError, "must specify instance_fixable"):
            rule_edits.findings_for_planned_source_changes(rule, changes)

    def test_empty_edits_return_original_module(self) -> None:
        module = cst.parse_module("x = 1\n")

        self.assertIs(rule_edits.apply_source_edits(module, ()), module)

    def test_multiple_unsorted_edits_support_unicode_and_adjacent_ranges(self) -> None:
        module = cst.parse_module("alpha = '\u03b1'\nbeta = 2\n")
        edits = (
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 9), end=cst_metadata.CodePosition(1, 10)), "\u03c9"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 5)), "name"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 4), end=cst_metadata.CodePosition(2, 5)), ""),
        )

        result = rule_edits.apply_source_edits(module, edits)

        self.assertEqual(result.code, "name = '\u03c9'\ngamma= 2\n")

    def test_cached_source_and_line_bounds_apply_without_reading_module_code(self) -> None:
        source = "alpha = 1\nbeta = 2\n"
        module = cst.parse_module(source)
        edits = (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),)
        lines = tuple(source_text.source_lines(source))

        def _unexpected_code_access(module: cst.Module) -> str:
            del module
            raise AssertionError("Module.code should not be read")

        with unittest.mock.patch.object(cst.Module, "code", new=property(_unexpected_code_access)):
            result = rule_edits.apply_source_edits(module, edits, source=source, line_bounds=source_text.line_bounds_from_lines(lines))

        self.assertEqual(result.code, "alpha = 1\ngamma = 2\n")

    def test_cached_source_and_line_bounds_must_be_provided_together(self) -> None:
        source = "alpha = 1\nbeta = 2\n"
        module = cst.parse_module(source)
        edits = (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),)
        line_bounds = source_text.line_bounds_from_lines(source_text.source_lines(source))

        with self.assertRaisesRegex(ValueError, "source and line_bounds must be provided together"):
            rule_edits.apply_source_edits(module, edits, source=source)
        with self.assertRaisesRegex(ValueError, "source and line_bounds must be provided together"):
            rule_edits.apply_source_edits(module, edits, line_bounds=line_bounds)

    def test_context_source_changes_apply_cached_context_source_without_reading_module_code(self) -> None:
        source = "alpha = 1\nbeta = 2\n"
        module = cst.parse_module(source)
        metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
        lines = tuple(source_text.source_lines(source))
        context = RuleCategoryContext(
            path="example.py",
            settings=CheckSettings(),
            module=module,
            metadata_wrapper=metadata_wrapper,
            positions=metadata_wrapper.resolve(cst_metadata.PositionProvider),
            line_ending="\n",
            source=source,
            source_lines=lines,
            line_bounds=source_text.line_bounds_from_lines(lines),
        )
        changes = (
            rule_edits.PlannedSourceChange(
                edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),
                line_numbers=(2,),
            ),
        )

        def _unexpected_code_access(module: cst.Module) -> str:
            del module
            raise AssertionError("Module.code should not be read")

        with unittest.mock.patch.object(cst.Module, "code", new=property(_unexpected_code_access)):
            result = rule_edits.apply_context_source_changes(context, changes)

        self.assertEqual(result.code, "alpha = 1\ngamma = 2\n")

    def test_cached_source_edits_support_no_final_newline(self) -> None:
        source = "alpha = 1\nbeta = 2"
        module = cst.parse_module(source)
        edits = (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 7), end=cst_metadata.CodePosition(2, 8)), "3"),)
        lines = tuple(source_text.source_lines(source))

        result = rule_edits.apply_source_edits(module, edits, source=source, line_bounds=source_text.line_bounds_from_lines(lines))

        self.assertEqual(result.code, "alpha = 1\nbeta = 3")

    def test_overlapping_edits_are_rejected(self) -> None:
        module = cst.parse_module("value = 1\n")
        edits = (
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 5)), "name"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 4), end=cst_metadata.CodePosition(1, 7)), "x"),
        )

        with self.assertRaisesRegex(ValueError, "must not overlap"):
            rule_edits.apply_source_edits(module, edits)

    def test_invalid_range_positions_are_rejected(self) -> None:
        module = cst.parse_module("x = 1\n")

        with self.assertRaisesRegex(ValueError, "line is outside"):
            rule_edits.apply_source_edits(module, (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(3, 0), end=cst_metadata.CodePosition(3, 0)), ""),))
        with self.assertRaisesRegex(ValueError, "column is outside"):
            rule_edits.apply_source_edits(module, (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 10), end=cst_metadata.CodePosition(1, 10)), ""),))

    def test_replacement_must_produce_valid_python(self) -> None:
        module = cst.parse_module("x = 1\n")
        edit = rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 4), end=cst_metadata.CodePosition(1, 5)), "(")

        with self.assertRaises(cst.ParserSyntaxError):
            rule_edits.apply_source_edits(module, (edit,))

    def test_edits_preserve_crlf_parser_configuration(self) -> None:
        module = cst.parse_module("first = 1\r\nsecond = 2\r\n")
        edit = rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 6)), "renamed")

        result = rule_edits.apply_source_edits(module, (edit,))

        self.assertEqual(result.code, "first = 1\r\nrenamed = 2\r\n")
