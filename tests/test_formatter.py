import collections
import contextlib
import dataclasses
import inspect
import os
import tempfile
import typing
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path

import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.cli.check as check_command
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.formatter as formatter
import pydocformatter.rules.codes as rule_codes
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definition as rule_base
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.runner as rule_runner
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation, LineEnding
from pydocformatter.formatter import FormatterResult
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleFinding, RuleMetadata

PDF101_RULE = RuleMetadata(
    code=RuleCode("PDF101"),
    name="docstring-reflow",
    message="Docstring chunk needs reflow",
    fix_availability=FixAvailability.ALWAYS,
    stable_since="1.0.0",
    setting_effects=(),
    incompatible_with=(),
    check_kind=RuleCheckKind.STANDARD,
)
PDF110_RULE = RuleMetadata(
    code=RuleCode("PDF110"),
    name="summary-too-long",
    message="Docstring summary does not fit on one line",
    fix_availability=FixAvailability.NEVER,
    stable_since="1.0.0",
    setting_effects=(),
    incompatible_with=(),
    check_kind=RuleCheckKind.STANDARD,
)
PCF100_RULE = RuleMetadata(
    code=RuleCode("PCF100"),
    name="comment-formatting-needed",
    message="Comment needs formatting",
    fix_availability=FixAvailability.ALWAYS,
    stable_since="1.0.0",
    setting_effects=(),
    incompatible_with=(),
    check_kind=RuleCheckKind.STANDARD,
)


def default_rule_selection() -> rules_selection.RuleSelection:
    return rules_selection.select_rules(CheckSettings())


def isolated_rule_selection(*categories: type[rule_base.RuleCategoryBase], fixable: bool = True, fixable_by_code: dict[RuleCode, bool] | None = None) -> rules_selection.RuleSelection:
    collection = rule_collection.RuleCollection(categories)
    return rules_selection.RuleSelection(
        rules=tuple(
            rules_selection.SelectedRule(
                rule=rule_class.meta, fixable=fixable_by_code.get(rule_class.meta.code, fixable) if fixable_by_code is not None else fixable, enabled_priority=0, enabled_specificity=0
            )
            for rule_class in collection.rules
        ),
        per_file_ignores=(),
        errors=(),
        collection=collection,
    )


def diagnostic_violation(rule: rule_models.RuleMetadata, line_numbers: tuple[int, ...] = (1,)) -> rule_violations.RuleViolation:
    return rule_violations.RuleViolation(finding=rule_models.RuleFinding(rule=rule, line_numbers=line_numbers, instance_fixable=None))


def source_replacement_change(context: rule_base.RuleContext, replacement: str, line_numbers: tuple[int, ...] = (1,)) -> rule_edits.PlannedSourceChange:
    source_lines = context.source_lines
    end_line = len(source_lines)
    end_column = len(source_lines[-1].rstrip("\r\n")) if source_lines else 0
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(end_line, end_column)), replacement),
        line_numbers=line_numbers,
        suppression_line_numbers=(),
    )


def source_replacement_violation(rule: rule_models.RuleMetadata, context: rule_base.RuleContext, replacement: str, line_numbers: tuple[int, ...] = (1,)) -> rule_violations.RuleViolation:
    change = source_replacement_change(context, replacement, line_numbers=line_numbers)
    return rule_violations.RuleViolation(finding=rule_models.RuleFinding(rule=rule, line_numbers=line_numbers, instance_fixable=None), fix=rule_violations.RuleSourceFix.from_change(change))


def no_violations(cls: type[rule_base.RuleBase], context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    del cls, context
    return ()


def single_diagnostic_violations(cls: type[rule_base.RuleBase], context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    del context
    return (diagnostic_violation(cls.meta),)


def insert_leading_line_violations(cls: type[rule_base.RuleBase], context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    if context.module.header:
        return ()
    return (source_replacement_violation(cls.meta, context, f"\n{context.source}"),)


def invalid_violation(finding: rule_models.RuleFinding, fix: rule_violations.RuleSourceFix | None) -> rule_violations.RuleViolation:
    violation = object.__new__(rule_violations.RuleViolation)
    object.__setattr__(violation, "finding", finding)
    object.__setattr__(violation, "fix", fix)
    return violation


class TestFormatterResults(unittest.TestCase):
    def test_formatter_result_field_order_has_no_defaults(self) -> None:
        fields = dataclasses.fields(FormatterResult)

        self.assertEqual(tuple(field.name for field in fields), ("path", "old_source", "new_source", "modified", "fixed_findings", "unfixed_findings", "errors"))
        self.assertTrue(all(field.default is dataclasses.MISSING for field in fields))
        self.assertTrue(all(field.default_factory is dataclasses.MISSING for field in fields))

    def test_rule_file_formatter_write_has_no_default(self) -> None:
        signature = inspect.signature(formatter.format_file)

        self.assertIs(signature.parameters["write"].default, inspect.Parameter.empty)

    def test_rule_source_formatter_requires_precomputed_rule_selection(self) -> None:
        signature = inspect.signature(formatter.format_source)

        self.assertIs(signature.parameters["rule_selection"].default, inspect.Parameter.empty)

    def test_max_fix_iterations_is_twenty(self) -> None:
        self.assertEqual(rule_runner.MAX_FIX_ITERATIONS, 20)

    def test_formatter_result_tracks_modified_and_findings_explicitly(self) -> None:
        clean = FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
        modified = FormatterResult(path="a.py", old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())
        finding = RuleFinding(
            rule=RuleMetadata(
                code=RuleCode("PDF110"),
                name="summary-too-long",
                message="Docstring summary does not fit on one line",
                fix_availability=FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            ),
            line_numbers=(3,),
            instance_fixable=None,
        )
        with_findings = FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(finding,), errors=())

        self.assertFalse(clean.modified)
        self.assertEqual(clean.unfixed_findings, ())
        self.assertEqual(clean.old_source, "")
        self.assertEqual(clean.new_source, "")
        self.assertEqual(clean.fixed_findings, collections.Counter())
        self.assertTrue(modified.modified)
        self.assertEqual(modified.fixed_findings, collections.Counter({PDF101_RULE: 1}))
        self.assertEqual(with_findings.unfixed_findings, (finding,))

    def test_rule_finding_uses_rule_defaults_with_per_finding_overrides(self) -> None:
        rule = RuleMetadata(
            code=RuleCode("PDF101"),
            name="docstring-reflow",
            message="Docstring chunk needs reflow",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )

        default_finding = RuleFinding(rule=rule, line_numbers=(2,), instance_fixable=None)
        overridden_finding = RuleFinding(
            rule=rule,
            line_numbers=(3,),
            instance_message="Custom message",
            instance_fixable=False,
        )

        self.assertEqual(default_finding.message, "Docstring chunk needs reflow")
        self.assertTrue(default_finding.fixable)
        self.assertEqual(overridden_finding.message, "Custom message")
        self.assertFalse(overridden_finding.fixable)

    def test_rule_metadata_and_finding_keys_are_sortable(self) -> None:
        later_rule = RuleMetadata(
            code=RuleCode("PDF999"),
            name="later",
            message="Later",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )

        self.assertEqual(sorted((later_rule, PDF101_RULE)), [PDF101_RULE, later_rule])
        self.assertTrue(dataclasses.is_dataclass(RuleFinding.Key))
        self.assertEqual(
            sorted((RuleFinding.Key(rule=later_rule, message="Later", fixable=True), RuleFinding.Key(rule=PDF101_RULE, message="Docstring chunk needs reflow", fixable=True))),
            [RuleFinding.Key(rule=PDF101_RULE, message="Docstring chunk needs reflow", fixable=True), RuleFinding.Key(rule=later_rule, message="Later", fixable=True)],
        )

    def test_rule_finding_requires_instance_fixability_for_sometimes_fixable_rules(self) -> None:
        rule = RuleMetadata(
            code=RuleCode("PDF999"),
            name="sometimes-rule",
            message="Sometimes rule",
            fix_availability=FixAvailability.SOMETIMES,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )

        self.assertTrue(RuleFinding(rule=rule, line_numbers=(2,), instance_fixable=True).fixable)
        self.assertFalse(RuleFinding(rule=rule, line_numbers=(3,), instance_fixable=False).fixable)
        with self.assertRaisesRegex(ValueError, "Findings for sometimes-fixable rules must specify instance_fixable"):
            _ = RuleFinding(rule=rule, line_numbers=(4,), instance_fixable=None).fixable

    def test_rule_finding_requires_instance_fixability_for_usually_fixable_rules(self) -> None:
        rule = RuleMetadata(
            code=RuleCode("PDF999"),
            name="usually-rule",
            message="Usually rule",
            fix_availability=FixAvailability.USUALLY,
            stable_since="1.0.0",
            setting_effects=(),
            incompatible_with=(),
            check_kind=RuleCheckKind.STANDARD,
        )

        self.assertTrue(RuleFinding(rule=rule, line_numbers=(2,), instance_fixable=True).fixable)
        self.assertFalse(RuleFinding(rule=rule, line_numbers=(3,), instance_fixable=False).fixable)
        with self.assertRaisesRegex(ValueError, "Findings for usually-fixable rules must specify instance_fixable"):
            _ = RuleFinding(rule=rule, line_numbers=(4,), instance_fixable=None).fixable

    def test_grouped_output_merges_matching_findings_and_prints_summary(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(
                RuleFinding(rule=PDF101_RULE, line_numbers=(2, 2, 3), instance_fixable=None),
                RuleFinding(rule=PDF110_RULE, line_numbers=(5,), instance_fixable=None),
                RuleFinding(rule=PDF101_RULE, line_numbers=(8,), instance_fixable=None),
            ),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PDF101* Docstring chunk needs reflow. Lines 2-3, 8",
                "  PDF110 Docstring summary does not fit on one line. Line 5",
                "",
                "Found 3 rule check errors (2 fixable).",
            ],
        )

    def test_grouped_output_keeps_different_instance_messages_separate(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(
                RuleFinding(rule=PDF101_RULE, line_numbers=(2,), instance_message="First issue", instance_fixable=None),
                RuleFinding(rule=PDF101_RULE, line_numbers=(2,), instance_message="Second issue", instance_fixable=None),
                RuleFinding(rule=PDF101_RULE, line_numbers=(3,), instance_message="First issue", instance_fixable=None),
            ),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PDF101* First issue. Lines 2-3",
                "  PDF101* Second issue. Line 2",
                "",
                "Found 3 rule check errors (3 fixable).",
            ],
        )

    def test_grouped_output_prints_fixed_findings_before_unfixed_findings(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=True,
            fixed_findings=collections.Counter({PDF101_RULE: 50, PCF100_RULE: 1}),
            unfixed_findings=(RuleFinding(rule=PDF110_RULE, line_numbers=(5,), instance_fixable=None),),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PCF100* Comment needs formatting. Fixed 1 time.",
                "  PDF101* Docstring chunk needs reflow. Fixed 50 times.",
                "  PDF110 Docstring summary does not fit on one line. Line 5",
                "",
                "Fixed 51 rule check errors and left 1 more unfixed (0 fixable).",
            ],
        )

    def test_grouped_output_reports_fixed_findings_for_clean_results(self) -> None:
        result = FormatterResult(path="a.py", old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PDF101* Docstring chunk needs reflow. Fixed 1 time.",
                "",
                "Fixed 1 rule check error.",
            ],
        )

    def test_grouped_output_prints_success_message_for_clean_results(self) -> None:
        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped(
                [], [FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())], output=None
            )

        self.assertEqual(output.getvalue(), "All checks passed!\n")

    def test_grouped_output_prints_errors_without_success_message(self) -> None:
        result = FormatterResult(path="a.py", old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=("Failed to read file a.py",))

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped(["Using standard input instead of input path: b.py"], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "ERROR: Using standard input instead of input path: b.py",
                "ERROR: Failed to read file a.py",
                "",
                "Found 2 operational errors.",
            ],
        )

    def test_grouped_output_summary_counts_findings_and_operational_errors(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source=None,
            new_source=None,
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(RuleFinding(rule=PDF101_RULE, line_numbers=(2,), instance_fixable=None),),
            errors=("Failed to read file a.py",),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped(["Using standard input instead of input path: b.py"], [result], output=None)

        self.assertEqual(output.getvalue().splitlines()[-3:], ["", "Found 2 operational errors.", "Found 1 rule check error (1 fixable)."])

    def test_diff_summary_reports_fixed_and_remaining_findings(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=True,
            fixed_findings=collections.Counter({PDF101_RULE: 2}),
            unfixed_findings=(RuleFinding(rule=PDF110_RULE, line_numbers=(1,), instance_fixable=None),),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_diff_summary([], [result], output=None)

        self.assertEqual(output.getvalue(), "Would fix 2 rule check errors and leave 1 more unfixed (0 fixable).\n")

    def test_diff_summary_reports_remaining_findings_without_fixes(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(RuleFinding(rule=PDF101_RULE, line_numbers=(1,), instance_fixable=None), RuleFinding(rule=PDF110_RULE, line_numbers=(2,), instance_fixable=None)),
            errors=(),
        )

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_diff_summary([], [result], output=None)

        self.assertEqual(output.getvalue(), "Would leave 2 rule check errors unfixed (1 fixable).\n")

    def test_diff_summary_reports_operational_errors_separately(self) -> None:
        result = FormatterResult(path="a.py", old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=("Failed to read file a.py",))

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_diff_summary(["Using standard input instead of input path: b.py"], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "ERROR: Using standard input instead of input path: b.py",
                "ERROR: Failed to read file a.py",
                "",
                "Found 2 operational errors.",
            ],
        )

    def test_output_stream_does_not_convert_body_os_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_file = str(Path(td) / "errors.txt")

            with self.assertRaisesRegex(OSError, "Body failed"):
                with check_command.output_stream(output_file):
                    raise OSError("Body failed")

    def test_rule_formatter_interface_is_noop_and_preserves_display_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                result = formatter.format_file("a.py", settings=CheckSettings(), rule_selection=default_rule_selection(), fix=True, write=True)
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(result.path, "a.py")
            self.assertEqual(result.old_source, "x = 1\n")
            self.assertEqual(result.new_source, "x = 1\n")
            self.assertFalse(result.modified)
            self.assertEqual(result.unfixed_findings, ())
            self.assertEqual(target.read_text(encoding="utf-8"), "x = 1\n")

    def test_rule_source_formatter_seeds_initial_check_context_without_module_code(self) -> None:
        observed_contexts: list[tuple[str, tuple[str, ...], source_text.LineBounds | None]] = []

        def _raise_code_access(module: cst.Module) -> str:
            del module
            raise AssertionError("Module.code should not be read for seeded initial check contexts")

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                observed_contexts.append((context.source, context.source_lines, context.line_bounds))
                return None

        @rule_registration.register_rule_to(TST)
        class TST001ObserveSource(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="observe-source",
                message="Observe source",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                self.assertEqual(context.source, expected_context_source)
                return ()

        source = "\ufeffx = 1\r\ny = 2\r\n"
        expected_context_source = source.removeprefix("\ufeff")
        expected_lines = tuple(source_text.source_lines(expected_context_source))

        with unittest.mock.patch.object(cst.Module, "code", new=property(_raise_code_access)):
            result = formatter.format_source(source, "a.py", settings=CheckSettings(), rule_selection=isolated_rule_selection(TST), fix=False)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.errors, ())
        self.assertEqual(observed_contexts, [(expected_context_source, expected_lines, source_text.line_bounds_from_lines(expected_lines))])

    def test_rule_source_formatter_aligns_bom_seed_with_libcst_positions(self) -> None:
        source = "\ufeffx = 1  #bad\n"

        result = formatter.format_source(source, "a.py", settings=CheckSettings(), rule_selection=default_rule_selection(), fix=True)

        self.assertEqual(result.new_source, "\ufeffx = 1  # bad\n")
        self.assertTrue(result.modified)
        self.assertEqual(result.errors, ())

    def test_rule_source_formatter_aligns_trailing_cr_seed_with_libcst_positions(self) -> None:
        observed_contexts: list[tuple[str, tuple[str, ...], source_text.LineBounds | None]] = []

        def _raise_code_access(module: cst.Module) -> str:
            del module
            raise AssertionError("Module.code should not be read for seeded initial check contexts")

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                observed_contexts.append((context.source, context.source_lines, context.line_bounds))
                return None

        @rule_registration.register_rule_to(TST)
        class TST001ObserveSource(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="observe-source",
                message="Observe source",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        source = "x = 1\ry = 2\r"
        expected_context_source = "x = 1\ry = 2"
        expected_lines = tuple(source_text.source_lines(expected_context_source))

        with unittest.mock.patch.object(cst.Module, "code", new=property(_raise_code_access)):
            result = formatter.format_source(source, "a.py", settings=CheckSettings(), rule_selection=isolated_rule_selection(TST), fix=False)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.errors, ())
        self.assertEqual(observed_contexts, [(expected_context_source, expected_lines, source_text.line_bounds_from_lines(expected_lines))])

    def test_rule_runner_recomputes_source_after_seeded_fix_replaces_module(self) -> None:
        original_code_property = inspect.getattr_static(cst.Module, "code")
        if not isinstance(original_code_property, property) or original_code_property.fget is None:
            raise AssertionError("Expected LibCST Module.code to be a property")
        original_code_getter = typing.cast("typing.Callable[[cst.Module], str]", original_code_property.fget)
        code_accesses: list[cst.Module] = []
        observed_sources: list[str] = []

        def _count_code_access(module: cst.Module) -> str:
            code_accesses.append(module)
            return original_code_getter(module)

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="insert-leading-line",
                message="Insert leading line",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(insert_leading_line_violations)

        class TSW(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TSW", name="test two", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                observed_sources.append(context.source)
                return None

        @rule_registration.register_rule_to(TSW)
        class TSW001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TSW001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        module = cst.parse_module("x = 1\n")
        selection = isolated_rule_selection(TST, TSW)

        with unittest.mock.patch.object(cst.Module, "code", new=property(_count_code_access)):
            result = rule_runner.run_rules(module, path="a.py", settings=CheckSettings(), line_ending="\n", rule_selection=selection, fix=True, source="x = 1\n")

        self.assertTrue(result.source_changed)
        self.assertEqual(result.fixed_findings, (RuleFinding(rule=TST001InsertLeadingLine.meta, line_numbers=(1,), instance_fixable=None),))
        self.assertEqual(result.errors, ())
        self.assertTrue(observed_sources)
        self.assertEqual(set(observed_sources), {"x = 1\n", "\nx = 1\n"})
        self.assertTrue(any(accessed_module is result.module for accessed_module in code_accesses))

    def test_rule_runner_skips_fix_hooks_when_precheck_has_no_fixable_findings(self) -> None:
        fix_calls: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001Manual(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="manual",
                message="Manual",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(single_diagnostic_violations)

        @rule_registration.register_rule_to(TST)
        class TST002UnexpectedFix(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST002"),
                name="unexpected-fix",
                message="Unexpected fix",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(no_violations)

        settings = CheckSettings()
        selection = isolated_rule_selection(TST, fixable_by_code={TST001Manual.meta.code: False, TST002UnexpectedFix.meta.code: True})
        module = cst.parse_module("x = 1\n")

        check_result = rule_runner.run_rules(module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, fix=False)
        fix_result = rule_runner.run_rules(module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, fix=True)

        self.assertIs(fix_result.module, module)
        self.assertFalse(fix_result.source_changed)
        self.assertEqual(fix_result.fixed_findings, ())
        self.assertEqual(fix_result.unfixed_findings, check_result.unfixed_findings)
        self.assertEqual(fix_result.errors, ())
        self.assertEqual(fix_calls, [])

    def test_rule_source_formatter_precheck_uses_effective_fixability(self) -> None:
        fix_calls: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001ConfiguredUnfixable(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="configured-unfixable",
                message="Configured unfixable",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                return (source_replacement_violation(cls.meta, context, f"\n{context.source}"),)

        settings = CheckSettings()
        selection = isolated_rule_selection(TST, fixable_by_code={TST001ConfiguredUnfixable.meta.code: False})

        result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=selection, fix=True)

        self.assertEqual(result.new_source, "x = 1\n")
        self.assertFalse(result.modified)
        self.assertEqual(result.fixed_findings, collections.Counter())
        self.assertEqual(result.unfixed_findings, (RuleFinding(rule=TST001ConfiguredUnfixable.meta, line_numbers=(1,), instance_fixable=False),))
        self.assertFalse(result.unfixed_findings[0].fixable)
        self.assertEqual(result.errors, ())
        self.assertEqual(fix_calls, [])

    def test_rule_source_formatter_runs_fix_pass_when_precheck_finds_fixable_finding(self) -> None:
        fix_calls: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="insert-leading-line",
                message="Insert leading line",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(insert_leading_line_violations)

        settings = CheckSettings()
        result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\nx = 1\n")
        self.assertTrue(result.modified)
        self.assertEqual(result.fixed_findings, collections.Counter({TST001InsertLeadingLine.meta: 1}))
        self.assertEqual(result.unfixed_findings, ())
        self.assertEqual(result.errors, ())
        self.assertEqual(fix_calls, [])

    def test_rule_source_formatter_discards_precheck_errors_when_falling_back(self) -> None:
        fix_calls: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001BrokenCheck(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="broken-check",
                message="Broken check",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                del cls, context
                raise RuntimeError("broken check")

        settings = CheckSettings()
        result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "x = 1\n")
        self.assertFalse(result.modified)
        self.assertEqual(result.fixed_findings, collections.Counter())
        self.assertEqual(result.unfixed_findings, ())
        self.assertEqual(result.errors, ("a.py: TST001 automatic fix failed: broken check", "a.py: TST001 check failed: broken check"))
        self.assertEqual(fix_calls, [])

    def test_rule_fix_pass_same_module_noop_skips_source_comparison(self) -> None:
        code_accesses: list[cst.Module] = []

        def _raise_code_access(module: cst.Module) -> str:
            code_accesses.append(module)
            raise AssertionError("Module.code should not be read for same-module no-op fixes")

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                del cls, context
                patcher = unittest.mock.patch.object(cst.Module, "code", new=property(_raise_code_access))
                patcher.start()
                self.addCleanup(patcher.stop)
                return ()

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        result_module, findings, changed = rule_runner._run_fix_pass(
            module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
        )

        self.assertIs(result_module, module)
        self.assertEqual(findings, ())
        self.assertFalse(changed)
        self.assertEqual(errors, [])
        self.assertEqual(code_accesses, [])

    def test_rule_fix_pass_rejects_same_source_reported_fix(self) -> None:
        original_code_property = inspect.getattr_static(cst.Module, "code")
        if not isinstance(original_code_property, property) or original_code_property.fget is None:
            raise AssertionError("Expected LibCST Module.code to be a property")
        original_code_getter = typing.cast("typing.Callable[[cst.Module], str]", original_code_property.fget)
        code_accesses: list[cst.Module] = []

        def _count_code_access(module: cst.Module) -> str:
            code_accesses.append(module)
            return original_code_getter(module)

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001ReturnEquivalentSource(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="return-equivalent-source",
                message="Return equivalent source",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                patcher = unittest.mock.patch.object(cst.Module, "code", new=property(_count_code_access))
                patcher.start()
                self.addCleanup(patcher.stop)
                return (source_replacement_violation(cls.meta, context, context.source),)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        result_module, findings, changed = rule_runner._run_fix_pass(
            module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
        )

        self.assertIs(result_module, module)
        self.assertEqual(findings, ())
        self.assertFalse(changed)
        self.assertEqual(errors, ["a.py: TST001 automatic fix must change source if and only if it reports fixed findings"])
        self.assertGreaterEqual(len(code_accesses), 1)

    def test_rule_fix_pass_does_not_apply_suppressed_violations(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001SuppressedFix(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="suppressed-fix",
                message="Suppressed fix",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                return (source_replacement_violation(cls.meta, context, "y = 2  # pydocfmt: ignore[TST001]\n"),)

        module = cst.parse_module("x = 1  # pydocfmt: ignore[TST001]\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        result_module, findings, changed = rule_runner._run_fix_pass(
            module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
        )

        self.assertIs(result_module, module)
        self.assertEqual(findings, ())
        self.assertFalse(changed)
        self.assertEqual(errors, [])

    def test_rule_check_pass_rejects_finding_outside_source(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001OutsideSource(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="outside-source",
                message="Outside source",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                del context
                return (diagnostic_violation(cls.meta, line_numbers=(99,)),)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        findings = rule_runner._run_check_pass(module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors)

        self.assertEqual(findings, ())
        self.assertEqual(errors, ["a.py: TST001 check returned a finding outside the source line range"])

    def test_rule_fix_pass_rejects_violation_fixability_mismatch(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001MissingFix(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="missing-fix",
                message="Missing fix",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                del context
                return (invalid_violation(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,), instance_fixable=None), None),)

        @rule_registration.register_rule_to(TST)
        class TST002UnexpectedFix(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST002"),
                name="unexpected-fix",
                message="Unexpected fix",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                fix = rule_violations.RuleSourceFix.from_change(source_replacement_change(context, "\nx = 1\n"))
                return (invalid_violation(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,), instance_fixable=None), fix),)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        result_module, findings, changed = rule_runner._run_fix_pass(
            module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
        )

        self.assertIs(result_module, module)
        self.assertEqual(findings, ())
        self.assertFalse(changed)
        self.assertEqual(
            errors,
            [
                "a.py: TST001 automatic fix returned a violation whose fix does not match finding fixability",
                "a.py: TST002 automatic fix returned a violation whose fix does not match finding fixability",
            ],
        )

    def test_rule_fix_pass_rejects_mismatched_source_change_targets(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001MismatchedFix(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="mismatched-fix",
                message="Mismatched fix",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                finding = rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,), instance_fixable=None)
                change = source_replacement_change(context, "x = 1\nz = 3\n", line_numbers=(2,))
                return (rule_violations.RuleViolation(finding=finding, fix=rule_violations.RuleSourceFix.from_change(change)),)

        module = cst.parse_module("x = 1\ny = 2\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        result_module, findings, changed = rule_runner._run_fix_pass(
            module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
        )

        self.assertIs(result_module, module)
        self.assertEqual(findings, ())
        self.assertFalse(changed)
        self.assertEqual(errors, ["a.py: TST001 automatic fix returned source changes whose line targets do not match the finding"])

    def test_rule_check_pass_reuses_position_metadata_across_categories(self) -> None:
        observed_contexts: list[tuple[cst.Module, cst_metadata.MetadataWrapper, object, str, tuple[str, ...]]] = []
        resolved_modules: list[cst.Module] = []
        original_resolve = cst_metadata.MetadataWrapper.resolve

        def _count_position_resolve(wrapper: cst_metadata.MetadataWrapper, provider: object) -> object:
            if provider is cst_metadata.PositionProvider:
                resolved_modules.append(wrapper.module)
            return typing.cast("typing.Any", original_resolve)(wrapper, provider)

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                observed_contexts.append((context.module, context.metadata_wrapper, context.positions, context.source, context.source_lines))
                return None

        @rule_registration.register_rule_to(TST)
        class TST001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        class TSW(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TSW", name="test two", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                observed_contexts.append((context.module, context.metadata_wrapper, context.positions, context.source, context.source_lines))
                return None

        @rule_registration.register_rule_to(TSW)
        class TSW001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TSW001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST, TSW)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        with unittest.mock.patch.object(cst_metadata.MetadataWrapper, "resolve", autospec=True, side_effect=_count_position_resolve):
            findings = rule_runner._run_check_pass(module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors)

        self.assertEqual(findings, ())
        self.assertEqual(errors, [])
        self.assertEqual(resolved_modules, [module])
        self.assertEqual(len(observed_contexts), 2)
        self.assertIs(observed_contexts[0][0], module)
        self.assertIs(observed_contexts[1][0], module)
        self.assertIs(observed_contexts[0][1], observed_contexts[1][1])
        self.assertIs(observed_contexts[0][2], observed_contexts[1][2])
        self.assertEqual(observed_contexts[0][3], "x = 1\n")
        self.assertIs(observed_contexts[0][4], observed_contexts[1][4])

    def test_rule_check_pass_reports_position_metadata_errors_as_category_preparation(self) -> None:
        def _raise_position_resolve(wrapper: cst_metadata.MetadataWrapper, provider: object) -> object:
            del wrapper
            if provider is cst_metadata.PositionProvider:
                raise RuntimeError("position metadata failed")
            return {}

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        with unittest.mock.patch.object(cst_metadata.MetadataWrapper, "resolve", autospec=True, side_effect=_raise_position_resolve):
            findings = rule_runner._run_check_pass(module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors)

        self.assertEqual(findings, ())
        self.assertEqual(errors, ["a.py: TST category preparation failed: position metadata failed"])

    def test_rule_fix_pass_reuses_position_metadata_across_unchanged_categories(self) -> None:
        observed_contexts: list[tuple[cst_metadata.MetadataWrapper, object]] = []
        resolved_modules: list[cst.Module] = []
        original_resolve = cst_metadata.MetadataWrapper.resolve

        def _count_position_resolve(wrapper: cst_metadata.MetadataWrapper, provider: object) -> object:
            if provider is cst_metadata.PositionProvider:
                resolved_modules.append(wrapper.module)
            return typing.cast("typing.Any", original_resolve)(wrapper, provider)

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                observed_contexts.append((context.metadata_wrapper, context.positions))
                return None

        @rule_registration.register_rule_to(TST)
        class TST001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        class TSW(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TSW", name="test two", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                observed_contexts.append((context.metadata_wrapper, context.positions))
                return None

        @rule_registration.register_rule_to(TSW)
        class TSW001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TSW001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST, TSW)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        with unittest.mock.patch.object(cst_metadata.MetadataWrapper, "resolve", autospec=True, side_effect=_count_position_resolve):
            result_module, findings, changed = rule_runner._run_fix_pass(
                module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
            )

        self.assertIs(result_module, module)
        self.assertEqual(findings, ())
        self.assertFalse(changed)
        self.assertEqual(errors, [])
        self.assertEqual(resolved_modules, [module])
        self.assertEqual(len(observed_contexts), 2)
        self.assertIs(observed_contexts[0][0], observed_contexts[1][0])
        self.assertIs(observed_contexts[0][1], observed_contexts[1][1])

    def test_rule_fix_pass_reports_position_metadata_errors_as_category_preparation(self) -> None:
        def _raise_position_resolve(wrapper: cst_metadata.MetadataWrapper, provider: object) -> object:
            del wrapper
            if provider is cst_metadata.PositionProvider:
                raise RuntimeError("position metadata failed")
            return {}

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        with unittest.mock.patch.object(cst_metadata.MetadataWrapper, "resolve", autospec=True, side_effect=_raise_position_resolve):
            result_module, findings, changed = rule_runner._run_fix_pass(
                module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
            )

        self.assertIs(result_module, module)
        self.assertEqual(findings, ())
        self.assertFalse(changed)
        self.assertEqual(errors, ["a.py: TST category preparation failed: position metadata failed"])

    def test_rule_fix_pass_refreshes_position_metadata_after_changed_module(self) -> None:
        observed_sources: list[str] = []
        observed_line_numbers: list[tuple[int, ...]] = []
        resolved_modules: list[cst.Module] = []
        original_resolve = cst_metadata.MetadataWrapper.resolve

        def _count_position_resolve(wrapper: cst_metadata.MetadataWrapper, provider: object) -> object:
            if provider is cst_metadata.PositionProvider:
                resolved_modules.append(wrapper.module)
            return typing.cast("typing.Any", original_resolve)(wrapper, provider)

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="insert-leading-line",
                message="Insert leading line",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(insert_leading_line_violations)

        class TSW(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TSW", name="test two", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                collector = _NameCollector("x")
                context.module.visit(collector)
                observed_sources.append(context.source)
                observed_line_numbers.append(tuple(context.positions[node].start.line for node in collector.nodes))
                return None

        @rule_registration.register_rule_to(TSW)
        class TSW001Noop(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TSW001"),
                name="noop",
                message="Noop",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )
            violations = classmethod(no_violations)

        class _NameCollector(cst.CSTVisitor):
            def __init__(self, name: str) -> None:
                super().__init__()
                self.name = name
                self.nodes: list[cst.Name] = []

            def visit_Name(self, node: cst.Name) -> None:
                if node.value == self.name:
                    self.nodes.append(node)

        module = cst.parse_module("x = 1\n")
        settings = CheckSettings()
        selection = isolated_rule_selection(TST, TSW)
        selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in selection.for_path("a.py")}
        errors: list[str] = []

        with unittest.mock.patch.object(cst_metadata.MetadataWrapper, "resolve", autospec=True, side_effect=_count_position_resolve):
            result_module, findings, changed = rule_runner._run_fix_pass(
                module, path="a.py", settings=settings, line_ending="\n", rule_selection=selection, selected_rule_by_code=selected_rule_by_code, errors=errors
            )

        self.assertEqual(result_module.code, "\nx = 1\n")
        self.assertEqual(findings, (RuleFinding(rule=TST001InsertLeadingLine.meta, line_numbers=(1,), instance_fixable=None),))
        self.assertTrue(changed)
        self.assertEqual(errors, [])
        self.assertEqual(len(resolved_modules), 2)
        self.assertIs(resolved_modules[0], module)
        self.assertIs(resolved_modules[1], result_module)
        self.assertEqual(observed_sources, ["\nx = 1\n"])
        self.assertEqual(observed_line_numbers, [(2,)])

    def test_rule_source_formatter_runs_fixes_to_convergence_and_checks_latest_positions(self) -> None:
        prepare_sources: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                prepare_sources.append(context.source)
                return context.source

        @rule_registration.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="insert-leading-line",
                message="Insert leading line",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(insert_leading_line_violations)

        @rule_registration.register_rule_to(TST)
        class TST002FindName(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST002"),
                name="find-name",
                message="Found name",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                collector = _NameCollector("x")
                context.module.visit(collector)
                line_numbers = tuple(context.positions[node].start.line for node in collector.nodes)
                return (diagnostic_violation(cls.meta, line_numbers=line_numbers),)

        class _NameCollector(cst.CSTVisitor):
            def __init__(self, name: str) -> None:
                super().__init__()
                self.name = name
                self.nodes: list[cst.Name] = []

            def visit_Name(self, node: cst.Name) -> None:
                if node.value == self.name:
                    self.nodes.append(node)

        settings = CheckSettings()
        result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\nx = 1\n")
        self.assertEqual(result.fixed_findings, collections.Counter({TST001InsertLeadingLine.meta: 1}))
        self.assertEqual(result.unfixed_findings, (RuleFinding(rule=TST002FindName.meta, line_numbers=(2,), instance_fixable=None),))
        self.assertEqual(prepare_sources, ["x = 1\n", "x = 1\n", "\nx = 1\n", "\nx = 1\n", "\nx = 1\n"])
        self.assertEqual(result.errors, ())

    def test_rule_source_formatter_refreshes_and_reuses_category_data_after_a_fix(self) -> None:
        prepared_data: list[object] = []
        observed_data: list[object | None] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                collector = _NameCollector("x")
                context.module.visit(collector)
                data = (context.source, tuple(context.positions[node].start.line for node in collector.nodes))
                prepared_data.append(data)
                return data

        @rule_registration.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="insert-leading-line",
                message="Insert leading line",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(insert_leading_line_violations)

        @rule_registration.register_rule_to(TST)
        class TST002ObserveCategoryData(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST002"),
                name="observe-category-data",
                message="Observe category data",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                del cls
                observed_data.append(context.category_data)
                return ()

        @rule_registration.register_rule_to(TST)
        class TST003ObserveCategoryDataAgain(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST003"),
                name="observe-category-data-again",
                message="Observe category data again",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                del cls
                observed_data.append(context.category_data)
                return ()

        class _NameCollector(cst.CSTVisitor):
            def __init__(self, name: str) -> None:
                super().__init__()
                self.name = name
                self.nodes: list[cst.Name] = []

            def visit_Name(self, node: cst.Name) -> None:
                if node.value == self.name:
                    self.nodes.append(node)

        settings = CheckSettings()
        result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\nx = 1\n")
        self.assertEqual(result.fixed_findings, collections.Counter({TST001InsertLeadingLine.meta: 1}))
        self.assertEqual(observed_data[:2], [("x = 1\n", (1,))] * 2)
        self.assertEqual(observed_data[2:], [("\nx = 1\n", (2,))] * len(observed_data[2:]))
        self.assertIs(observed_data[0], observed_data[1])
        self.assertIs(observed_data[2], observed_data[3])
        self.assertIsNot(observed_data[0], observed_data[2])
        self.assertEqual(prepared_data[:2], [("x = 1\n", (1,))] * 2)
        self.assertEqual(prepared_data[2:], [("\nx = 1\n", (2,))] * len(prepared_data[2:]))
        self.assertEqual(result.errors, ())

    def test_rule_source_formatter_does_not_normalize_line_endings_without_a_fix(self) -> None:
        settings = CheckSettings(line_ending=LineEnding.CR_LF)
        source = "x = 1\ny = 2\n"

        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=isolated_rule_selection(), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)

    def test_rule_source_formatter_preserves_untouched_line_endings_after_a_fix(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="insert-leading-line",
                message="Insert leading line",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(insert_leading_line_violations)

        settings = CheckSettings(line_ending=LineEnding.CR_LF)
        result = formatter.format_source("x = 1\ny = 2\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\nx = 1\ny = 2\n")

    def test_rule_source_formatter_preserves_utf8_bom_after_a_fix(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="insert-leading-line",
                message="Insert leading line",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            violations = classmethod(insert_leading_line_violations)

        settings = CheckSettings()
        result = formatter.format_source("\ufeffx = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\ufeff\nx = 1\n")

    def test_rule_source_formatter_applies_per_file_ignores(self) -> None:
        checks: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        @rule_registration.register_rule_to(TST)
        class TST001Check(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="check",
                message="Check",
                fix_availability=rule_models.FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                checks.append(context.path)
                return (diagnostic_violation(cls.meta),)

        settings = CheckSettings(select=("TST",), per_file_ignores=(("skip.py", ("TST",)),))
        selection = rules_selection.select_rules(settings, collection=rule_collection.RuleCollection((TST,)))
        result = formatter.format_source("x = 1\n", "skip.py", settings=settings, rule_selection=selection, fix=False)

        self.assertEqual(checks, [])
        self.assertEqual(result.unfixed_findings, ())

    def test_rule_source_formatter_reports_non_converging_fixes_and_keeps_latest_source(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        class ToggleInteger(cst.CSTTransformer):
            def leave_Integer(self, original_node: cst.Integer, updated_node: cst.Integer) -> cst.Integer:
                del original_node
                return updated_node.with_changes(value="2" if updated_node.value == "1" else "1")

        @rule_registration.register_rule_to(TST)
        class TST001Toggle(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="toggle",
                message="Toggle",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                toggled = context.module.visit(ToggleInteger()).code
                return (source_replacement_violation(cls.meta, context, toggled),)

        settings = CheckSettings()
        with unittest.mock.patch.object(rule_runner, "MAX_FIX_ITERATIONS", 3):
            result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "x = 2\n")
        self.assertEqual(result.fixed_findings, collections.Counter({TST001Toggle.meta: 3}))
        self.assertEqual(result.unfixed_findings, (RuleFinding(rule=TST001Toggle.meta, line_numbers=(1,), instance_fixable=None),))
        self.assertEqual(len(result.errors), 1)
        self.assertIn("did not converge after 3 iterations", result.errors[0])
        self.assertIn("TST001 lines 1", result.errors[0])

    def test_rule_source_formatter_accepts_convergence_on_final_fix_iteration(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test", url=None)

        class IncrementInteger(cst.CSTTransformer):
            def leave_Integer(self, original_node: cst.Integer, updated_node: cst.Integer) -> cst.Integer:
                del original_node
                return updated_node.with_changes(value=str(int(updated_node.value) + 1))

        @rule_registration.register_rule_to(TST)
        class TST001IncrementToFour(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_codes.RuleCode("TST001"),
                name="increment-to-four",
                message="Increment to four",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=rule_models.RuleCheckKind.STANDARD,
            )

            @classmethod
            def violations(cls, context: rule_base.RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
                if context.source == "x = 4\n":
                    return ()
                incremented = context.module.visit(IncrementInteger()).code
                return (source_replacement_violation(cls.meta, context, incremented),)

        settings = CheckSettings()
        with unittest.mock.patch.object(rule_runner, "MAX_FIX_ITERATIONS", 3):
            result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "x = 4\n")
        self.assertEqual(result.fixed_findings, collections.Counter({TST001IncrementToFour.meta: 3}))
        self.assertEqual(result.unfixed_findings, ())
        self.assertEqual(result.errors, ())

    def test_rule_source_formatter_reports_libcst_parse_errors(self) -> None:
        settings = CheckSettings()

        result = formatter.format_source("def broken(:\n", "broken.py", settings=settings, rule_selection=isolated_rule_selection(), fix=True)

        self.assertEqual(result.old_source, "def broken(:\n")
        self.assertEqual(result.new_source, "def broken(:\n")
        self.assertFalse(result.modified)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Failed to parse broken.py with LibCST", result.errors[0])

    def test_rule_file_formatter_delegates_to_source_formatter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_args: list[tuple[str, str, bool]] = []

            def fake_format_source(source: str, path: str, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool) -> FormatterResult:
                del settings, rule_selection
                called_args.append((source, path, fix))
                return FormatterResult(path=path, old_source=source, new_source=source, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            with unittest.mock.patch("pydocformatter.formatter.format_source", side_effect=fake_format_source):
                result = formatter.format_file(str(target), settings=CheckSettings(), rule_selection=default_rule_selection(), fix=False, write=True)

        self.assertEqual(called_args, [("x = 1\n", str(target), False)])
        self.assertEqual(result.path, str(target))
        self.assertEqual(result.new_source, "x = 1\n")
        self.assertFalse(result.modified)

    def test_rule_file_formatter_writes_modified_fix_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_source(source: str, path: str, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool) -> FormatterResult:
                del source, settings, rule_selection, fix
                return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

            with unittest.mock.patch("pydocformatter.formatter.format_source", side_effect=fake_format_source):
                result = formatter.format_file(str(target), settings=CheckSettings(), rule_selection=default_rule_selection(), fix=True, write=True)

            self.assertEqual(result.new_source, "x = 2\n")
            self.assertEqual(result.old_source, "x = 1\n")
            self.assertTrue(result.modified)
            self.assertEqual(target.read_text(encoding="utf-8"), "x = 2\n")

    def test_rule_file_formatter_can_skip_modified_fix_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_source(source: str, path: str, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool) -> FormatterResult:
                del source, settings, rule_selection, fix
                return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

            with unittest.mock.patch("pydocformatter.formatter.format_source", side_effect=fake_format_source):
                result = formatter.format_file(str(target), settings=CheckSettings(), rule_selection=default_rule_selection(), fix=True, write=False)

            self.assertEqual(result.new_source, "x = 2\n")
            self.assertEqual(result.old_source, "x = 1\n")
            self.assertTrue(result.modified)
            self.assertEqual(target.read_text(encoding="utf-8"), "x = 1\n")

    def test_rule_file_formatter_reports_file_io_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = str(Path(td) / "missing.py")
            result = formatter.format_file(missing, settings=CheckSettings(), rule_selection=default_rule_selection(), fix=False, write=True)

        self.assertIsNone(result.new_source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())
        self.assertEqual(len(result.errors), 1)
        self.assertIn(f"Failed to read file {missing}", result.errors[0])

    def test_format_files_formats_each_received_path_without_deduplicating(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            called_paths: list[str] = []

            def fake_format_source(source: str, path: str, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool) -> FormatterResult:
                del source, settings, rule_selection, fix
                called_paths.append(path)
                return FormatterResult(path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())

            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with unittest.mock.patch("pydocformatter.formatter.format_source", side_effect=fake_format_source):
                    results = [formatter.format_file(path, settings=CheckSettings(), rule_selection=default_rule_selection(), fix=True, write=True) for path in ("a.py", str(target))]
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(called_paths, ["a.py", str(target)])
        self.assertEqual([result.path for result in results], ["a.py", str(target)])

    @pytest.mark.isolated_cwd
    def test_check_exit_status_depends_on_remaining_findings_not_modified_results(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(path=path, old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

            argv = ["pydocfmt", "check", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format_file),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)

    @pytest.mark.isolated_cwd
    def test_exit_zero_suppresses_remaining_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            rule = RuleMetadata(
                code=RuleCode("PDF110"),
                name="summary-too-long",
                message="Docstring summary does not fit on one line",
                fix_availability=FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(
                    path=path,
                    old_source="",
                    new_source="",
                    modified=False,
                    fixed_findings=collections.Counter(),
                    unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,), instance_fixable=None),),
                    errors=(),
                )

            argv = ["pydocfmt", "check", "--exit-zero", str(target)]
            stdout = StringIO()
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format_file),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)

    @pytest.mark.isolated_cwd
    def test_errors_affect_exit_status_without_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=("Failed to read file",))

            for extra_args, expected_exit_code in (([], 1), (["--exit-zero"], 0)):
                argv = ["pydocfmt", "check", *extra_args, str(target)]
                stdout = StringIO()
                with (
                    unittest.mock.patch("sys.argv", argv),
                    unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format_file),
                    contextlib.redirect_stdout(stdout),
                ):
                    exit_code = pydocfmt_cli.main()

                self.assertEqual(exit_code, expected_exit_code)
                self.assertNotIn("All checks passed!", stdout.getvalue())

    @pytest.mark.isolated_cwd
    def test_fix_mode_exits_nonzero_for_remaining_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            rule = RuleMetadata(
                code=RuleCode("PDF110"),
                name="summary-too-long",
                message="Docstring summary does not fit on one line",
                fix_availability=FixAvailability.NEVER,
                stable_since="1.0.0",
                setting_effects=(),
                incompatible_with=(),
                check_kind=RuleCheckKind.STANDARD,
            )

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(
                    path=path,
                    old_source="",
                    new_source="",
                    modified=False,
                    fixed_findings=collections.Counter(),
                    unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,), instance_fixable=None),),
                    errors=(),
                )

            argv = ["pydocfmt", "check", "--fix", str(target)]
            stdout = StringIO()
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format_file),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 1)

    @pytest.mark.isolated_cwd
    def test_exit_non_zero_on_fix_reports_modified_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(path=path, old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF101_RULE: 1}), unfixed_findings=(), errors=())

            for extra_args, expected_exit_code in ((["--fix"], 0), (["--fix", "--exit-non-zero-on-fix"], 1)):
                argv = ["pydocfmt", "check", *extra_args, str(target)]
                with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format_file):
                    exit_code = pydocfmt_cli.main()

                self.assertEqual(exit_code, expected_exit_code)

    def test_docstring_closing_quote_directive_suppresses_whole_docstring_check_and_fix(self) -> None:
        source = 'def function():\n    """This is a long summary that needs wrapping into more than one physical line."""  # pydocfmt: ignore[PDF101]\n'
        settings = CheckSettings(select=("PDF101",), line_length=48)
        selection = rules_selection.select_rules(settings)

        without_directive = formatter.format_source(source.replace("  # pydocfmt: ignore[PDF101]", ""), "a.py", settings=settings, rule_selection=selection, fix=False)
        check_result = formatter.format_source(source, "a.py", settings=settings, rule_selection=selection, fix=False)
        fix_result = formatter.format_source(source, "a.py", settings=settings, rule_selection=selection, fix=True)

        self.assertEqual(tuple(finding.rule.code.tag for finding in without_directive.unfixed_findings), ("PDF101",))
        self.assertEqual(check_result.unfixed_findings, ())
        self.assertEqual(fix_result.new_source, source)
        self.assertFalse(fix_result.modified)
        self.assertEqual(fix_result.fixed_findings, collections.Counter())

    def test_docstring_closing_quote_directive_suppresses_multiline_docstring_interior_findings(self) -> None:
        source = 'def function():\n    """This is a long summary that should be joined with the following line\n    because the paragraph is one reflowable docstring chunk.\n    """  # pydocfmt: ignore[PDF101]\n'
        settings = CheckSettings(select=("PDF101",), line_length=88)
        selection = rules_selection.select_rules(settings)

        without_directive = formatter.format_source(source.replace("  # pydocfmt: ignore[PDF101]", ""), "a.py", settings=settings, rule_selection=selection, fix=False)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=selection, fix=True)

        self.assertEqual(tuple(finding.rule.code.tag for finding in without_directive.unfixed_findings), ("PDF101",))
        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())

    def test_preceding_pydocfmt_directive_suppresses_immediately_following_docstring(self) -> None:
        source = 'def function():\n    # pydocfmt: ignore[PDF101]\n    """This is a long summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PDF101",), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_preceding_pydocfmt_directive_does_not_skip_blank_lines(self) -> None:
        source = 'def function():\n    # pydocfmt: ignore[PDF101]\n\n    """This is a long summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PDF101",), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(tuple(finding.rule.code.tag for finding in result.unfixed_findings), ("PDF101",))

    def test_preceding_pydocfmt_directive_suppresses_following_standalone_comment_run_check_and_fix(self) -> None:
        source = "# pydocfmt: ignore[PCF001]\n# This is a long comment that needs wrapping into more than one physical line.\n# This line belongs to the same comment run.\n"
        settings = CheckSettings(select=("PCF001",), line_length=42)
        selection = rules_selection.select_rules(settings)

        without_directive = formatter.format_source(source.replace("# pydocfmt: ignore[PCF001]\n", ""), "a.py", settings=settings, rule_selection=selection, fix=False)
        check_result = formatter.format_source(source, "a.py", settings=settings, rule_selection=selection, fix=False)
        fix_result = formatter.format_source(source, "a.py", settings=settings, rule_selection=selection, fix=True)

        self.assertTrue(all(finding.rule.code.tag == "PCF001" for finding in without_directive.unfixed_findings))
        self.assertTrue(without_directive.unfixed_findings)
        self.assertEqual(check_result.unfixed_findings, ())
        self.assertEqual(fix_result.new_source, source)
        self.assertFalse(fix_result.modified)

    def test_preceding_pydocfmt_directive_suppresses_following_trailing_comment(self) -> None:
        source = "# pydocfmt: ignore[PCF002]\nvalue = 1 # trailing\n"
        settings = CheckSettings(select=("PCF002",))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())

    def test_local_all_selector_suppresses_following_docstring_or_comment_target(self) -> None:
        settings = CheckSettings(select=("PDF101", "PCF002", "PCF006"), line_length=48)
        selection = rules_selection.select_rules(settings)
        docstring_source = '# pydocfmt: ignore[ALL]\n"""This is a long module summary that needs wrapping into more than one physical line."""\n'
        comment_source = "# pydocfmt: ignore[ALL]\nvalue = 1 # trailing\n"

        docstring = formatter.format_source(docstring_source, "a.py", settings=settings, rule_selection=selection, fix=False)
        comment = formatter.format_source(comment_source, "a.py", settings=settings, rule_selection=selection, fix=True)

        self.assertEqual(docstring.unfixed_findings, ())
        self.assertEqual(comment.new_source, comment_source)
        self.assertFalse(comment.modified)
        self.assertEqual(comment.unfixed_findings, ())

    def test_bare_noqa_is_line_only_except_closing_docstring_line(self) -> None:
        line_only_source = '# noqa: PDF101\n"""This is a long module summary that needs wrapping into more than one physical line."""\n'
        closing_source = '"""This is a long module summary that needs wrapping into more than one physical line."""  # noqa: PDF101\n'
        settings = CheckSettings(select=("PDF101",), line_length=48)
        selection = rules_selection.select_rules(settings)

        line_only_result = formatter.format_source(line_only_source, "a.py", settings=settings, rule_selection=selection, fix=False)
        closing_result = formatter.format_source(closing_source, "a.py", settings=settings, rule_selection=selection, fix=False)

        self.assertEqual(tuple(finding.rule.code.tag for finding in line_only_result.unfixed_findings), ("PDF101",))
        self.assertEqual(closing_result.unfixed_findings, ())

    def test_bare_noqa_without_payload_suppresses_closing_docstring_line(self) -> None:
        source = '"""This is a long module summary that needs wrapping into more than one physical line."""  # noqa\n'
        settings = CheckSettings(select=("PDF101",), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())

    def test_bare_noqa_suppresses_pcf_findings_without_blanket_pcf006_audit(self) -> None:
        source = "value = 1 # noqa\n"
        settings = CheckSettings(select=("PCF002", "PCF006"))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())

    def test_bare_noqa_pydocformatter_selectors_suppress_and_are_audited(self) -> None:
        used_source = "value = 1 # noqa: PCF002\n"
        unused_source = "value = 1  # noqa: PCF002\n"
        foreign_source = "value = 1  # noqa: F401\n"
        settings = CheckSettings(select=("PCF002", "PCF006"))
        selection = rules_selection.select_rules(settings)

        used = formatter.format_source(used_source, "a.py", settings=settings, rule_selection=selection, fix=False)
        unused = formatter.format_source(unused_source, "a.py", settings=settings, rule_selection=selection, fix=False)
        foreign = formatter.format_source(foreign_source, "a.py", settings=settings, rule_selection=selection, fix=False)

        self.assertEqual(used.unfixed_findings, ())
        self.assertEqual(tuple((finding.rule.code.tag, finding.message) for finding in unused.unfixed_findings), (("PCF006", "Suppression selector 'PCF002' did not suppress any findings"),))
        self.assertEqual(foreign.unfixed_findings, ())

    def test_unused_suppression_reports_unused_and_invalid_pydocfmt_selectors(self) -> None:
        settings = CheckSettings(select=("PCF001", "PCF006"))
        selection = rules_selection.select_rules(settings)

        unused = formatter.format_source("# pydocfmt: ignore[PCF001]\n# Short comment.\n", "a.py", settings=settings, rule_selection=selection, fix=False)
        invalid = formatter.format_source("# pydocfmt: ignore[not-a-rule]\n# Short comment.\n", "a.py", settings=settings, rule_selection=selection, fix=False)

        self.assertEqual(tuple(finding.message for finding in unused.unfixed_findings), ("Suppression selector 'PCF001' did not suppress any findings",))
        self.assertEqual(tuple(finding.message for finding in invalid.unfixed_findings), ("Invalid pydocfmt suppression selector 'NOT-A-RULE'",))

    def test_unused_suppression_reports_partially_unused_selector_lists(self) -> None:
        source = "# pydocfmt: ignore[PCF001, PCF002]\n# This is a long comment that needs wrapping into more than one physical line.\n"
        settings = CheckSettings(select=("PCF001", "PCF002", "PCF006"), line_length=42)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(tuple((finding.rule.code.tag, finding.message) for finding in result.unfixed_findings), (("PCF006", "Suppression selector 'PCF002' did not suppress any findings"),))

    def test_unused_suppression_does_not_report_selectors_for_disabled_rules(self) -> None:
        source = '# pydocfmt: ignore[PDF101]\n"""This is a long module summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PCF006",), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_pydocfmt_directive_can_suppress_pcf006(self) -> None:
        settings = CheckSettings(select=("PCF006",))
        selection = rules_selection.select_rules(settings)
        sources = (
            "# pydocfmt: file-ignore[PCF006]\n# pydocfmt: ignore[]\n# Short comment.\n",
            "# pydocfmt: noqa: PCF006\n# pydocfmt: ignore[]\n# Short comment.\n",
            "# pydocfmt: ignore[PCF006]\n# pydocfmt: noqa: not-a-rule\n# Short comment.\n",
        )

        for source in sources:
            result = formatter.format_source(source, "a.py", settings=settings, rule_selection=selection, fix=False)
            self.assertEqual(result.unfixed_findings, ())

    def test_file_level_pydocfmt_directive_suppresses_findings_anywhere_in_file(self) -> None:
        source = 'def first():\n    """This is a long summary that needs wrapping into more than one physical line."""\n\n# pydocfmt: noqa: PDF101\n\ndef second():\n    """This is another long summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PDF101", "PCF006"), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_file_ignore_prefix_selector_suppresses_multiple_pdf_rules(self) -> None:
        source = '# pydocfmt: file-ignore[PDF]\ndef function():\n    """   This is a long summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PDF101", "PDF104", "PCF006"), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_file_level_blanket_pydocfmt_noqa_suppresses_mixed_pcf_and_pdf_findings(self) -> None:
        source = '# pydocfmt: noqa\ndef function():\n    """This is a long summary that needs wrapping into more than one physical line."""\n\nvalue = 1 # trailing\n'
        settings = CheckSettings(select=("PDF101", "PCF002", "PCF006"), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())

    def test_adjacent_local_directives_stack_for_one_following_docstring(self) -> None:
        source = 'def function():\n    # pydocfmt: ignore[PDF101]\n    # pydocfmt: ignore[PDF104]\n    """   This is a long summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PDF101", "PDF104", "PCF006"), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_local_directive_wrong_target_type_is_unused_and_does_not_suppress_other_findings(self) -> None:
        source = '# pydocfmt: ignore[PCF001]\n"""This is a long module summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PCF001", "PDF101", "PCF006"), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertCountEqual(
            tuple((finding.rule.code.tag, finding.message) for finding in result.unfixed_findings),
            (
                ("PCF006", "Suppression selector 'PCF001' did not suppress any findings"),
                ("PDF101", "Docstring chunk needs reflow"),
            ),
        )

    def test_local_comment_directive_suppresses_only_first_contiguous_comment_run(self) -> None:
        source = "# pydocfmt: ignore[PCF001]\n# This is a long comment that needs wrapping into more than one physical line.\n\n# This is another long comment that needs wrapping into more than one physical line.\n"
        settings = CheckSettings(select=("PCF001", "PCF006"), line_length=42)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(tuple((finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings), (("PCF001", (4,)),))

    def test_local_comment_directive_does_not_cross_indent_or_protected_boundaries(self) -> None:
        indented_source = "# pydocfmt: ignore[PCF001]\n# This is a long comment that needs wrapping into more than one physical line.\n    # This is another long comment that needs wrapping into more than one physical line.\n"
        protected_source = "# pydocfmt: ignore[PCF001]\n# This is a long comment that needs wrapping into more than one physical line.\n# noqa\n# This is another long comment that needs wrapping into more than one physical line.\n"
        settings = CheckSettings(select=("PCF001", "PCF006"), line_length=42)
        selection = rules_selection.select_rules(settings)

        indented = formatter.format_source(indented_source, "a.py", settings=settings, rule_selection=selection, fix=False)
        protected = formatter.format_source(protected_source, "a.py", settings=settings, rule_selection=selection, fix=False)

        self.assertEqual(tuple((finding.rule.code.tag, finding.line_numbers) for finding in indented.unfixed_findings), (("PCF001", (3,)),))
        self.assertEqual(tuple((finding.rule.code.tag, finding.line_numbers) for finding in protected.unfixed_findings), (("PCF001", (4,)),))

    def test_trailing_pydocfmt_ignore_suppresses_pcf_findings(self) -> None:
        source = "value = 1 # pydocfmt: ignore[PCF002]\n"
        settings = CheckSettings(select=("PCF002", "PCF006"))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())

    def test_pydocfmt_directive_with_trailing_reason_still_suppresses(self) -> None:
        source = '# pydocfmt: ignore[PDF101] because generated\n"""This is a long module summary that needs wrapping into more than one physical line."""\n'
        settings = CheckSettings(select=("PDF101", "PCF006"), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_local_docstring_directive_suppresses_owner_diagnostics_reported_outside_docstring(self) -> None:
        cases = (
            (
                "PDF500",
                'def function(first, second):\n    # pydocfmt: ignore[PDF500]\n    """Summary.\n\n    Args:\n        first: First.\n    """\n',
            ),
            (
                "PDF502",
                'def function():\n    # pydocfmt: ignore[PDF502]\n    """Return a value."""\n    return 1\n',
            ),
            (
                "PDF504",
                'def function():\n    # pydocfmt: ignore[PDF504]\n    """Generate values."""\n    yield 1\n',
            ),
            (
                "PDF506",
                'def function():\n    # pydocfmt: ignore[PDF506]\n    """Validate a value."""\n    raise ValueError("bad")\n',
            ),
        )

        for rule_code, source in cases:
            settings = CheckSettings(select=(rule_code, "PCF006"), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
            result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
            with self.subTest(rule_code=rule_code):
                self.assertEqual(result.unfixed_findings, ())

    def test_owner_docstring_suppression_preserves_report_lines_without_directive(self) -> None:
        cases = (
            (
                "PDF500",
                'def function(first, second):\n    """Summary.\n\n    Args:\n        first: First.\n    """\n',
                (1,),
            ),
            (
                "PDF502",
                'def function():\n    """Return a value."""\n    return 1\n',
                (3,),
            ),
            (
                "PDF504",
                'def function():\n    """Generate values."""\n    yield 1\n',
                (3,),
            ),
            (
                "PDF506",
                'def function():\n    """Validate a value."""\n    raise ValueError("bad")\n',
                (3,),
            ),
        )

        for rule_code, source, expected_lines in cases:
            settings = CheckSettings(select=(rule_code,), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
            result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
            with self.subTest(rule_code=rule_code):
                self.assertEqual(tuple((finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings), ((rule_code, expected_lines),))

    def test_report_line_directive_still_suppresses_owner_docstring_diagnostic(self) -> None:
        source = 'def function():\n    """Return a value."""\n    return 1  # pydocfmt: ignore[PDF502]\n'
        settings = CheckSettings(select=("PDF502", "PCF006"), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_suppressed_and_unsuppressed_fixes_for_same_rule_are_filtered_independently(self) -> None:
        source = "# pydocfmt: ignore[PCF002]\nfirst = 1 # first\nsecond = 2 # second\n"
        settings = CheckSettings(select=("PCF002", "PCF006"))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, "# pydocfmt: ignore[PCF002]\nfirst = 1 # first\nsecond = 2  # second\n")
        self.assertEqual(result.fixed_findings, collections.Counter({next(rule.rule for rule in rules_selection.select_rules(settings).rules if rule.rule.code.tag == "PCF002"): 1}))
        self.assertEqual(result.unfixed_findings, ())

    def test_bare_noqa_with_foreign_codes_does_not_suppress_pydocfmt_findings(self) -> None:
        source = '"""This is a long module summary that needs wrapping into more than one physical line."""  # noqa: F401\n'
        settings = CheckSettings(select=("PDF101",))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(tuple(finding.rule.code.tag for finding in result.unfixed_findings), ("PDF101",))

    def test_bare_noqa_with_mixed_foreign_and_pydocfmt_codes_suppresses_pydocfmt_finding(self) -> None:
        source = '"""This is a long module summary that needs wrapping into more than one physical line."""  # noqa: F401, PDF101\n'
        settings = CheckSettings(select=("PDF101",), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)
        self.assertEqual(result.unfixed_findings, ())

    def test_unsupported_pydocfmt_disable_enable_directives_do_not_suppress_findings(self) -> None:
        source = '# pydocfmt: disable[PDF101]\n"""This is a long module summary that needs wrapping into more than one physical line."""\n# pydocfmt: enable[PDF101]\n'
        settings = CheckSettings(select=("PDF101",), line_length=48)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(tuple(finding.rule.code.tag for finding in result.unfixed_findings), ("PDF101",))

    def test_unused_suppression_reports_unknown_valid_selector_and_empty_payload(self) -> None:
        settings = CheckSettings(select=("PCF006",))
        selection = rules_selection.select_rules(settings)

        unknown = formatter.format_source("# pydocfmt: ignore[PDF999]\n# Short comment.\n", "a.py", settings=settings, rule_selection=selection, fix=False)
        empty = formatter.format_source("# pydocfmt: ignore[]\n# Short comment.\n", "a.py", settings=settings, rule_selection=selection, fix=False)

        self.assertEqual(tuple(finding.message for finding in unknown.unfixed_findings), ("Unknown pydocfmt suppression selector 'PDF999'",))
        self.assertEqual(tuple(finding.message for finding in empty.unfixed_findings), ("Invalid pydocfmt suppression selector ''",))

    def test_file_level_blanket_directive_suppresses_pcf006_unused_report(self) -> None:
        source = "# pydocfmt: noqa\nvalue = 1\n"
        settings = CheckSettings(select=("PCF001", "PCF006"))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

        self.assertEqual(result.unfixed_findings, ())

    def test_suppressed_and_unsuppressed_summary_fixes_are_filtered_independently(self) -> None:
        source = 'def first():\n    # pydocfmt: ignore[PDF300]\n    """return value"""\n\ndef second():\n    """return value"""\n'
        expected = 'def first():\n    # pydocfmt: ignore[PDF300]\n    """return value"""\n\ndef second():\n    """return value."""\n'
        settings = CheckSettings(select=("PDF300", "PCF006"))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, expected)
        self.assertEqual({rule.code.tag: count for rule, count in result.fixed_findings.items()}, {"PDF300": 1})
        self.assertEqual(result.unfixed_findings, ())

    def test_normalized_suppression_directive_still_suppresses_later_pdf_fix(self) -> None:
        source = 'def first():\n    # PYDOCFMT : ignore [ pdf300, ]  # reason\n    """return value"""\n\ndef second():\n    """return value"""\n'
        expected = 'def first():\n    # pydocfmt: ignore[PDF300]  # reason\n    """return value"""\n\ndef second():\n    """return value."""\n'
        settings = CheckSettings(select=("PCF003", "PDF300", "PCF006"))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, expected)
        self.assertEqual({rule.code.tag: count for rule, count in result.fixed_findings.items()}, {"PCF003": 1, "PDF300": 1})
        self.assertEqual(result.unfixed_findings, ())

    def test_suppressed_and_unsuppressed_section_fixes_are_filtered_independently(self) -> None:
        source = 'def first(value):\n    # pydocfmt: ignore[PDF404]\n    """Summary.\n\n    Args\n        value: Description.\n    """\n\ndef second(value):\n    """Summary.\n\n    Args\n        value: Description.\n    """\n'
        expected = 'def first(value):\n    # pydocfmt: ignore[PDF404]\n    """Summary.\n\n    Args\n        value: Description.\n    """\n\ndef second(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
        settings = CheckSettings(select=("PDF404", "PCF006"), docstring_convention=DocstringConvention.GOOGLE)
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, expected)
        self.assertEqual({rule.code.tag: count for rule, count in result.fixed_findings.items()}, {"PDF404": 1})
        self.assertEqual(result.unfixed_findings, ())

    def test_suppressed_and_unsuppressed_pcf003_fixes_are_filtered_independently(self) -> None:
        source = "# pydocfmt: ignore[PCF003]\n#NOQA\n\n#RUFF : ignore [ F401 ]\n"
        expected = "# pydocfmt: ignore[PCF003]\n#NOQA\n\n# ruff: ignore[F401]\n"
        settings = CheckSettings(select=("PCF003", "PCF006"))
        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

        self.assertEqual(result.new_source, expected)
        self.assertEqual({rule.code.tag: count for rule, count in result.fixed_findings.items()}, {"PCF003": 1})
        self.assertEqual(result.unfixed_findings, ())
