import collections
import contextlib
import dataclasses
import inspect
import os
import tempfile
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path

import libcst as cst

import pydocformatter.cli.check as check_command
import pydocformatter.cli.main as pydocfmt_cli
import pydocformatter.formatter as formatter
import pydocformatter.legacy.pydocfmt as pydocfmt
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definition as rule_base
import pydocformatter.rules.models as rule_models
import pydocformatter.rules.runner as rule_runner
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.formatter import FormatterResult
from pydocformatter.rules.models import FixAvailability, RuleCode, RuleFinding, RuleMetadata

PDF001_RULE = RuleMetadata(code=RuleCode("PDF001"), name="reflow-required", message="Docstring chunk needs reflow", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")
PDF105_RULE = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fix_availability=FixAvailability.NEVER, stable_since="0.3.0")
PCF100_RULE = RuleMetadata(code=RuleCode("PCF100"), name="comment-formatting-needed", message="Comment needs formatting", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")


def default_rule_selection() -> rules_selection.RuleSelection:
    return rules_selection.select_rules(CheckSettings())


def isolated_rule_selection(*categories: type[rule_base.RuleCategoryBase], fixable: bool = True) -> rules_selection.RuleSelection:
    collection = rule_collection.RuleCollection(categories)
    return rules_selection.RuleSelection(
        rules=tuple(rules_selection.SelectedRule(rule=rule_class.meta, fixable=fixable, enabled_priority=0, enabled_specificity=0) for rule_class in collection.rules),
        per_file_ignores=(),
        errors=(),
        collection=collection,
    )


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

    def test_max_fix_iterations_is_one_hundred(self) -> None:
        self.assertEqual(rule_runner.MAX_FIX_ITERATIONS, 100)

    def test_formatter_result_tracks_modified_and_findings_explicitly(self) -> None:
        clean = FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=())
        modified = FormatterResult(path="a.py", old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())
        finding = RuleFinding(
            rule=RuleMetadata(
                code=RuleCode("PDF105"),
                name="summary-too-long",
                message="Docstring summary does not fit on one line",
                fix_availability=FixAvailability.NEVER,
                stable_since="0.3.0",
            ),
            line_numbers=(3,),
        )
        with_findings = FormatterResult(path="a.py", old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(finding,), errors=())

        self.assertFalse(clean.modified)
        self.assertEqual(clean.unfixed_findings, ())
        self.assertEqual(clean.old_source, "")
        self.assertEqual(clean.new_source, "")
        self.assertEqual(clean.fixed_findings, collections.Counter())
        self.assertTrue(modified.modified)
        self.assertEqual(modified.fixed_findings, collections.Counter({PDF001_RULE: 1}))
        self.assertEqual(with_findings.unfixed_findings, (finding,))

    def test_rule_finding_uses_rule_defaults_with_per_finding_overrides(self) -> None:
        rule = RuleMetadata(
            code=RuleCode("PDF001"),
            name="reflow-required",
            message="Docstring chunk needs reflow",
            fix_availability=FixAvailability.ALWAYS,
            stable_since="0.3.0",
        )

        default_finding = RuleFinding(rule=rule, line_numbers=(2,))
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
        later_rule = RuleMetadata(code=RuleCode("PDF999"), name="later", message="Later", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")

        self.assertEqual(sorted((later_rule, PDF001_RULE)), [PDF001_RULE, later_rule])
        self.assertTrue(dataclasses.is_dataclass(RuleFinding.Key))
        self.assertEqual(
            sorted((RuleFinding.Key(rule=later_rule, message="Later", fixable=True), RuleFinding.Key(rule=PDF001_RULE, message="Docstring chunk needs reflow", fixable=True))),
            [RuleFinding.Key(rule=PDF001_RULE, message="Docstring chunk needs reflow", fixable=True), RuleFinding.Key(rule=later_rule, message="Later", fixable=True)],
        )

    def test_rule_finding_requires_instance_fixability_for_sometimes_fixable_rules(self) -> None:
        rule = RuleMetadata(code=RuleCode("PDF999"), name="sometimes-rule", message="Sometimes rule", fix_availability=FixAvailability.SOMETIMES, stable_since="0.3.0")

        self.assertTrue(RuleFinding(rule=rule, line_numbers=(2,), instance_fixable=True).fixable)
        self.assertFalse(RuleFinding(rule=rule, line_numbers=(3,), instance_fixable=False).fixable)
        with self.assertRaisesRegex(ValueError, "Findings for sometimes-fixable rules must specify instance_fixable"):
            _ = RuleFinding(rule=rule, line_numbers=(4,)).fixable

    def test_grouped_output_merges_matching_findings_and_prints_summary(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=False,
            fixed_findings=collections.Counter(),
            unfixed_findings=(
                RuleFinding(rule=PDF001_RULE, line_numbers=(2, 2, 3)),
                RuleFinding(rule=PDF105_RULE, line_numbers=(5,)),
                RuleFinding(rule=PDF001_RULE, line_numbers=(8,)),
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
                "  PDF001* Docstring chunk needs reflow. Lines 2-3, 8",
                "  PDF105 Docstring summary does not fit on one line. Line 5",
                "",
                "Found 3 rule check errors (2 fixable).",
            ],
        )

    def test_grouped_output_prints_fixed_findings_before_unfixed_findings(self) -> None:
        result = FormatterResult(
            path="a.py",
            old_source="",
            new_source="",
            modified=True,
            fixed_findings=collections.Counter({PDF001_RULE: 50, PCF100_RULE: 1}),
            unfixed_findings=(RuleFinding(rule=PDF105_RULE, line_numbers=(5,)),),
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
                "  PDF001* Docstring chunk needs reflow. Fixed 50 times.",
                "  PDF105 Docstring summary does not fit on one line. Line 5",
                "",
                "Fixed 51 rule check errors and left 1 more unfixed (0 fixable).",
            ],
        )

    def test_grouped_output_reports_fixed_findings_for_clean_results(self) -> None:
        result = FormatterResult(path="a.py", old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

        output = StringIO()
        with contextlib.redirect_stdout(output):
            check_command.print_results_grouped([], [result], output=None)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "a.py:",
                "  PDF001* Docstring chunk needs reflow. Fixed 1 time.",
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
            unfixed_findings=(RuleFinding(rule=PDF001_RULE, line_numbers=(2,)),),
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
            fixed_findings=collections.Counter({PDF001_RULE: 2}),
            unfixed_findings=(RuleFinding(rule=PDF105_RULE, line_numbers=(1,)),),
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
            unfixed_findings=(RuleFinding(rule=PDF001_RULE, line_numbers=(1,)), RuleFinding(rule=PDF105_RULE, line_numbers=(2,))),
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

    def test_rule_source_formatter_runs_fixes_to_convergence_and_checks_latest_positions(self) -> None:
        prepare_sources: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test")

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                prepare_sources.append(context.module.code)
                return context.module.code

        @rule_collection.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_models.RuleCode("TST001"), name="insert-leading-line", message="Insert leading line", fix_availability=rule_models.FixAvailability.ALWAYS, stable_since="0.3.0"
            )

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                if context.module.header:
                    return rule_base.RuleFixResult(module=context.module)
                return rule_base.RuleFixResult(module=context.module.with_changes(header=(cst.EmptyLine(),)), fixed_findings=(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),))

        @rule_collection.register_rule_to(TST)
        class TST002FindName(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(code=rule_models.RuleCode("TST002"), name="find-name", message="Found name", fix_availability=rule_models.FixAvailability.NEVER, stable_since="0.3.0")

            @classmethod
            def check(cls, context: rule_base.RuleContext) -> tuple[rule_models.RuleFinding, ...]:
                collector = _NameCollector("x")
                context.module.visit(collector)
                line_numbers = tuple(context.positions[node].start.line for node in collector.nodes)
                return (rule_models.RuleFinding(rule=cls.meta, line_numbers=line_numbers),)

        class _NameCollector(cst.CSTVisitor):
            def __init__(self, name: str) -> None:
                self.name = name
                self.nodes: list[cst.Name] = []

            def visit_Name(self, node: cst.Name) -> None:
                if node.value == self.name:
                    self.nodes.append(node)

        settings = CheckSettings()
        result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\nx = 1\n")
        self.assertEqual(result.fixed_findings, collections.Counter({TST001InsertLeadingLine.meta: 1}))
        self.assertEqual(result.unfixed_findings, (RuleFinding(rule=TST002FindName.meta, line_numbers=(2,)),))
        self.assertEqual(prepare_sources, ["x = 1\n", "\nx = 1\n", "\nx = 1\n", "\nx = 1\n"])
        self.assertEqual(result.errors, ())

    def test_rule_source_formatter_refreshes_and_reuses_category_data_after_a_fix(self) -> None:
        prepared_data: list[object] = []
        observed_data: list[object | None] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test")

            @classmethod
            def prepare(cls, context: rule_base.RuleCategoryContext) -> object:
                del cls
                collector = _NameCollector("x")
                context.module.visit(collector)
                data = (context.module.code, tuple(context.positions[node].start.line for node in collector.nodes))
                prepared_data.append(data)
                return data

        @rule_collection.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_models.RuleCode("TST001"), name="insert-leading-line", message="Insert leading line", fix_availability=rule_models.FixAvailability.ALWAYS, stable_since="0.3.0"
            )

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                if context.module.header:
                    return rule_base.RuleFixResult(module=context.module)
                return rule_base.RuleFixResult(module=context.module.with_changes(header=(cst.EmptyLine(),)), fixed_findings=(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),))

        @rule_collection.register_rule_to(TST)
        class TST002ObserveCategoryData(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_models.RuleCode("TST002"), name="observe-category-data", message="Observe category data", fix_availability=rule_models.FixAvailability.ALWAYS, stable_since="0.3.0"
            )

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                del cls
                observed_data.append(context.category_data)
                return rule_base.RuleFixResult(module=context.module)

        @rule_collection.register_rule_to(TST)
        class TST003ObserveCategoryDataAgain(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_models.RuleCode("TST003"),
                name="observe-category-data-again",
                message="Observe category data again",
                fix_availability=rule_models.FixAvailability.ALWAYS,
                stable_since="0.3.0",
            )

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                del cls
                observed_data.append(context.category_data)
                return rule_base.RuleFixResult(module=context.module)

        class _NameCollector(cst.CSTVisitor):
            def __init__(self, name: str) -> None:
                self.name = name
                self.nodes: list[cst.Name] = []

            def visit_Name(self, node: cst.Name) -> None:
                if node.value == self.name:
                    self.nodes.append(node)

        settings = CheckSettings()
        result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\nx = 1\n")
        self.assertEqual(result.fixed_findings, collections.Counter({TST001InsertLeadingLine.meta: 1}))
        self.assertEqual(observed_data, [("\nx = 1\n", (2,))] * 4)
        self.assertIs(observed_data[0], observed_data[1])
        self.assertIs(observed_data[2], observed_data[3])
        self.assertIsNot(observed_data[0], observed_data[2])
        self.assertEqual(prepared_data, [("x = 1\n", (1,)), ("\nx = 1\n", (2,)), ("\nx = 1\n", (2,)), ("\nx = 1\n", (2,))])
        self.assertEqual(result.errors, ())

    def test_rule_source_formatter_does_not_normalize_line_endings_without_a_fix(self) -> None:
        settings = CheckSettings(line_ending=LineEnding.CR_LF)
        source = "x = 1\ny = 2\n"

        result = formatter.format_source(source, "a.py", settings=settings, rule_selection=isolated_rule_selection(), fix=True)

        self.assertEqual(result.new_source, source)
        self.assertFalse(result.modified)

    def test_rule_source_formatter_preserves_untouched_line_endings_after_a_fix(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test")

        @rule_collection.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_models.RuleCode("TST001"), name="insert-leading-line", message="Insert leading line", fix_availability=rule_models.FixAvailability.ALWAYS, stable_since="0.3.0"
            )

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                if context.module.header:
                    return rule_base.RuleFixResult(module=context.module)
                return rule_base.RuleFixResult(module=context.module.with_changes(header=(cst.EmptyLine(),)), fixed_findings=(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),))

        settings = CheckSettings(line_ending=LineEnding.CR_LF)
        result = formatter.format_source("x = 1\ny = 2\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\nx = 1\ny = 2\n")

    def test_rule_source_formatter_preserves_utf8_bom_after_a_fix(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test")

        @rule_collection.register_rule_to(TST)
        class TST001InsertLeadingLine(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_models.RuleCode("TST001"), name="insert-leading-line", message="Insert leading line", fix_availability=rule_models.FixAvailability.ALWAYS, stable_since="0.3.0"
            )

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                if context.module.header:
                    return rule_base.RuleFixResult(module=context.module)
                return rule_base.RuleFixResult(module=context.module.with_changes(header=(cst.EmptyLine(),)), fixed_findings=(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),))

        settings = CheckSettings()
        result = formatter.format_source("\ufeffx = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "\ufeff\nx = 1\n")

    def test_rule_source_formatter_applies_per_file_ignores(self) -> None:
        checks: list[str] = []

        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test")

        @rule_collection.register_rule_to(TST)
        class TST001Check(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(code=rule_models.RuleCode("TST001"), name="check", message="Check", fix_availability=rule_models.FixAvailability.NEVER, stable_since="0.3.0")

            @classmethod
            def check(cls, context: rule_base.RuleContext) -> tuple[rule_models.RuleFinding, ...]:
                checks.append(context.path)
                return (rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),)

        settings = CheckSettings(select=("TST",), per_file_ignores=(("skip.py", ("TST",)),))
        selection = rules_selection.select_rules(settings, collection=rule_collection.RuleCollection((TST,)))
        result = formatter.format_source("x = 1\n", "skip.py", settings=settings, rule_selection=selection, fix=False)

        self.assertEqual(checks, [])
        self.assertEqual(result.unfixed_findings, ())

    def test_rule_source_formatter_reports_non_converging_fixes_and_keeps_latest_source(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test")

        class ToggleInteger(cst.CSTTransformer):
            def leave_Integer(self, original_node: cst.Integer, updated_node: cst.Integer) -> cst.Integer:
                del original_node
                return updated_node.with_changes(value="2" if updated_node.value == "1" else "1")

        @rule_collection.register_rule_to(TST)
        class TST001Toggle(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(code=rule_models.RuleCode("TST001"), name="toggle", message="Toggle", fix_availability=rule_models.FixAvailability.ALWAYS, stable_since="0.3.0")

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                return rule_base.RuleFixResult(module=context.module.visit(ToggleInteger()), fixed_findings=(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),))

            @classmethod
            def check(cls, context: rule_base.RuleContext) -> tuple[rule_models.RuleFinding, ...]:
                del context
                return (rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),)

        settings = CheckSettings()
        with unittest.mock.patch.object(rule_runner, "MAX_FIX_ITERATIONS", 3):
            result = formatter.format_source("x = 1\n", "a.py", settings=settings, rule_selection=isolated_rule_selection(TST), fix=True)

        self.assertEqual(result.new_source, "x = 2\n")
        self.assertEqual(result.fixed_findings, collections.Counter({TST001Toggle.meta: 3}))
        self.assertEqual(result.unfixed_findings, (RuleFinding(rule=TST001Toggle.meta, line_numbers=(1,)),))
        self.assertEqual(len(result.errors), 1)
        self.assertIn("did not converge after 3 iterations", result.errors[0])
        self.assertIn("TST001 lines 1", result.errors[0])

    def test_rule_source_formatter_accepts_convergence_on_final_fix_iteration(self) -> None:
        class TST(rule_base.RuleCategoryBase):
            meta = rule_models.RuleCategoryMetadata(prefix="TST", name="test")

        class IncrementInteger(cst.CSTTransformer):
            def leave_Integer(self, original_node: cst.Integer, updated_node: cst.Integer) -> cst.Integer:
                del original_node
                return updated_node.with_changes(value=str(int(updated_node.value) + 1))

        @rule_collection.register_rule_to(TST)
        class TST001IncrementToFour(rule_base.RuleBase):
            meta = rule_models.RuleMetadata(
                code=rule_models.RuleCode("TST001"), name="increment-to-four", message="Increment to four", fix_availability=rule_models.FixAvailability.ALWAYS, stable_since="0.3.0"
            )

            @classmethod
            def fix(cls, context: rule_base.RuleContext) -> rule_base.RuleFixResult:
                if context.module.code == "x = 4\n":
                    return rule_base.RuleFixResult(module=context.module)
                return rule_base.RuleFixResult(module=context.module.visit(IncrementInteger()), fixed_findings=(rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),))

            @classmethod
            def check(cls, context: rule_base.RuleContext) -> tuple[rule_models.RuleFinding, ...]:
                if context.module.code == "x = 4\n":
                    return ()
                return (rule_models.RuleFinding(rule=cls.meta, line_numbers=(1,)),)

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
                return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

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
                return FormatterResult(path=path, old_source="x = 1\n", new_source="x = 2\n", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

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

    def test_check_exit_status_depends_on_remaining_findings_not_modified_results(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(path=path, old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

            argv = ["pydocfmt", "check", str(target)]
            with (
                unittest.mock.patch("sys.argv", argv),
                unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format_file),
            ):
                exit_code = pydocfmt_cli.main()

        self.assertEqual(exit_code, 0)

    def test_exit_zero_suppresses_remaining_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            rule = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fix_availability=FixAvailability.NEVER, stable_since="0.3.0")

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(
                    path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,)),), errors=()
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

    def test_fix_mode_exits_nonzero_for_remaining_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")
            rule = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fix_availability=FixAvailability.NEVER, stable_since="0.3.0")

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(
                    path=path, old_source="", new_source="", modified=False, fixed_findings=collections.Counter(), unfixed_findings=(RuleFinding(rule=rule, line_numbers=(1,)),), errors=()
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

    def test_exit_non_zero_on_fix_reports_modified_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            def fake_format_file(path: str, *, file: object = None, settings: CheckSettings, rule_selection: rules_selection.RuleSelection, fix: bool, write: bool) -> FormatterResult:
                del file, settings, rule_selection, fix, write
                return FormatterResult(path=path, old_source="", new_source="", modified=True, fixed_findings=collections.Counter({PDF001_RULE: 1}), unfixed_findings=(), errors=())

            for extra_args, expected_exit_code in ((["--fix"], 0), (["--fix", "--exit-non-zero-on-fix"], 1)):
                argv = ["pydocfmt", "check", *extra_args, str(target)]
                with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("pydocformatter.formatter.format_file", side_effect=fake_format_file):
                    exit_code = pydocfmt_cli.main()

                self.assertEqual(exit_code, expected_exit_code)

    def test_legacy_check_result_uses_synthetic_finding_for_needed_formatting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            source_result = pydocfmt.SourceFormatResult(source="x = 1\n", docstring_changed_lines=(3, 1), comment_changed_lines=(5, 3))
            with unittest.mock.patch("pydocformatter.cli.check.legacy_formatter.format_file_source", return_value=source_result):
                results = check_command.format_legacy_files((str(target),), settings=CheckSettings(), fix=False, write=True)

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].modified)
        self.assertEqual(len(results[0].unfixed_findings), 1)
        self.assertEqual(results[0].unfixed_findings[0].rule.code.tag, "PDF000")
        self.assertEqual(results[0].unfixed_findings[0].line_numbers, (1, 3, 5))

    def test_legacy_check_result_uses_zero_line_fallback_for_missing_changed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            source_result = pydocfmt.SourceFormatResult(source="x = 1\n", docstring_changed_lines=(), comment_changed_lines=())
            with unittest.mock.patch.object(type(source_result), "modified", new_callable=unittest.mock.PropertyMock, return_value=True):
                with unittest.mock.patch("pydocformatter.cli.check.legacy_formatter.format_file_source", return_value=source_result):
                    results = check_command.format_legacy_files((str(target),), settings=CheckSettings(), fix=False, write=True)

        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0].unfixed_findings), 1)
        self.assertEqual(results[0].unfixed_findings[0].line_numbers, (0,))

    def test_legacy_format_result_uses_modified_for_actual_writes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.py"
            target.write_text("x = 1\n", encoding="utf-8")

            source_result = pydocfmt.SourceFormatResult(source="x = 1\n", docstring_changed_lines=(1,), comment_changed_lines=())
            with unittest.mock.patch("pydocformatter.cli.check.legacy_formatter.format_file_source", return_value=source_result):
                results = check_command.format_legacy_files((str(target),), settings=CheckSettings(), fix=True, write=True)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].modified)
        self.assertEqual(results[0].fixed_findings, collections.Counter({check_command.LEGACY_FORMAT_RULE_META: 1}))
        self.assertEqual(results[0].unfixed_findings, ())
