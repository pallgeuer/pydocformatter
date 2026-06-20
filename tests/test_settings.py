import argparse
import dataclasses
import enum
import os
import tempfile
import typing
import unittest
import unittest.mock
from pathlib import Path

import pydocformatter.cli.global_args as pydocformatter_global_args
import pydocformatter.cli.settings_check as pydocformatter_settings
import pydocformatter.settings as pydocformatter_settings_core
from pydocformatter.cli.settings_check import (
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    CheckSettings,
    CheckSettingsOverrides,
    IndentStyle,
    LineEnding,
    OutputFormat,
    SettingsGroup,
)
from pydocformatter.settings import (
    MultiStringMap,
    SettingCLIDefinition,
    SettingCLIOptions,
    SettingCLIValueKind,
    SettingDefinition,
    SettingsError,
    SettingsSchema,
    StringList,
)


class TestSettings(unittest.TestCase):
    @staticmethod
    def _write_git_marker(root: Path) -> None:
        """Write a minimal git worktree marker in a temporary root."""
        (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")

    def test_check_settings_schema_uses_generic_settings_definitions(self) -> None:
        self.assertIs(pydocformatter_settings.SETTINGS_SCHEMA.settings_type, CheckSettings)
        self.assertIs(pydocformatter_settings.SETTINGS_SCHEMA.overrides_type, CheckSettingsOverrides)
        self.assertTrue(all(isinstance(definition, SettingDefinition) for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions))
        self.assertNotIn("tags", tuple(field.name for field in dataclasses.fields(SettingDefinition)))
        self.assertNotIn("render", tuple(field.name for field in dataclasses.fields(SettingDefinition)))
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(SettingDefinition)),
            ("field", "value_type", "group", "help", "key", "available_in_cli", "available_in_toml", "validator", "cli", "documentation", "example"),
        )
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(SettingsSchema)),
            ("settings_type", "overrides_type", "group_type", "definitions", "table_path", "table_name", "post_validate"),
        )
        self.assertFalse(next(field for field in dataclasses.fields(SettingsSchema) if field.name == "table_name").init)
        self.assertEqual(pydocformatter_settings.SETTINGS_SCHEMA.table_name, "tool.pydocfmt")
        self.assertIs(pydocformatter_settings.SETTINGS_SCHEMA.group_type, SettingsGroup)
        self.assertIs(SettingsError, SettingsError)
        self.assertTrue(hasattr(pydocformatter_settings_core, "SettingCLIDefinition"))
        self.assertTrue(hasattr(pydocformatter_settings_core, "SettingCLIOptions"))
        self.assertFalse(hasattr(pydocformatter_settings_core, "SettingCliDefinition"))
        self.assertTrue(hasattr(pydocformatter_settings_core, "StringList"))
        self.assertTrue(hasattr(pydocformatter_settings_core, "MultiStringMap"))
        self.assertFalse(hasattr(pydocformatter_settings, "RuleSelectorMap"))

    def test_cli_options_and_resolved_definition_fields_match(self) -> None:
        options_hints = typing.get_type_hints(SettingCLIOptions)
        definition_hints = typing.get_type_hints(SettingCLIDefinition)

        self.assertFalse(SettingCLIOptions.__total__)
        self.assertEqual(options_hints, definition_hints)
        self.assertEqual(tuple(options_hints), tuple(field.name for field in dataclasses.fields(SettingCLIDefinition)))

    def test_cli_definition_stores_resolved_show_default(self) -> None:
        self.assertTrue(SettingCLIDefinition().show_default)
        self.assertTrue(SettingCLIDefinition(value_kind=SettingCLIValueKind.COMMA_LIST).show_default)
        self.assertFalse(SettingCLIDefinition(show_default=False).show_default)
        self.assertTrue(SettingCLIDefinition(value_kind=SettingCLIValueKind.COMMA_LIST, show_default=True).show_default)

    def test_setting_definition_resolves_default_key_and_cli_flags(self) -> None:
        definition = SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Maximum line length.",
            validator=pydocformatter_settings_core.validate_int(),
        )
        empty_documentation_definition = SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Maximum line length.",
            documentation="",
        )
        none_documentation_definition = SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Maximum line length.",
            documentation=None,
        )
        example_definition = SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Maximum line length.",
            example="line-length = 120",
        )

        self.assertEqual(definition.key, "line-length")
        self.assertEqual(definition.documentation, definition.help)
        self.assertEqual(definition.example, "")
        self.assertEqual(empty_documentation_definition.documentation, empty_documentation_definition.help)
        self.assertEqual(none_documentation_definition.documentation, none_documentation_definition.help)
        self.assertEqual(example_definition.example, "line-length = 120")
        self.assertIsNotNone(definition.cli)
        cli = definition.cli
        assert cli is not None
        self.assertEqual(cli.flags, ("--line-length",))

    def test_setting_definition_respects_explicit_key_and_cli_flags(self) -> None:
        definition = SettingDefinition(
            field="config_options",
            value_type=StringList,
            group=SettingsGroup.FORMATTING,
            help="Configuration options.",
            key="config",
            validator=pydocformatter_settings_core.validate_string_list,
            cli={"flags": ("-c", "--config")},
        )

        self.assertEqual(definition.key, "config")
        self.assertIsNotNone(definition.cli)
        cli = definition.cli
        assert cli is not None
        self.assertEqual(cli.flags, ("-c", "--config"))

    def test_setting_definition_uses_explicit_key_for_default_cli_flags(self) -> None:
        definition = SettingDefinition(
            field="config_options",
            value_type=StringList,
            group=SettingsGroup.FORMATTING,
            help="Configuration options.",
            key="config",
            validator=pydocformatter_settings_core.validate_string_list,
        )

        self.assertEqual(definition.key, "config")
        self.assertIsNotNone(definition.cli)
        cli = definition.cli
        assert cli is not None
        self.assertEqual(cli.flags, ("--config",))

    def test_setting_definition_respects_explicit_no_cli(self) -> None:
        definition = SettingDefinition(
            field="legacy",
            value_type=bool,
            group=SettingsGroup.FORMATTING,
            help="Legacy.",
            available_in_cli=False,
        )

        self.assertFalse(definition.available_in_cli)
        self.assertIsNone(definition.cli)

    def test_setting_definition_derives_defaults_from_type(self) -> None:
        enum_definition = SettingDefinition(
            field="line_ending",
            value_type=LineEnding,
            group=SettingsGroup.FORMATTING,
            help="Line ending.",
        )
        bool_definition = SettingDefinition(
            field="legacy",
            value_type=bool,
            group=SettingsGroup.FORMATTING,
            help="Legacy.",
        )
        int_definition = SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Line length.",
        )
        string_list_definition = SettingDefinition(
            field="include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Include.",
        )
        string_map_definition = SettingDefinition(
            field="per_file_ignores",
            value_type=MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            help="Per-file ignores.",
        )

        assert enum_definition.cli is not None
        assert bool_definition.cli is not None
        assert int_definition.cli is not None
        assert string_list_definition.cli is not None
        assert string_map_definition.cli is not None
        self.assertEqual(enum_definition.cli.choices, tuple(member.value for member in LineEnding))
        self.assertIs(bool_definition.cli.action, argparse.BooleanOptionalAction)
        self.assertIs(int_definition.cli.type, int)
        self.assertEqual(string_list_definition.cli.action, "append")
        self.assertEqual(string_list_definition.cli.value_kind, SettingCLIValueKind.COMMA_LIST)
        self.assertFalse(string_list_definition.cli.show_default)
        self.assertEqual(string_map_definition.cli.action, "append")
        self.assertEqual(string_map_definition.cli.value_kind, SettingCLIValueKind.TOML_MAP)
        self.assertFalse(string_map_definition.cli.show_default)
        self.assertEqual(enum_definition.validator("lf", "line-ending"), LineEnding.LF)
        self.assertTrue(bool_definition.validator(True, "legacy"))
        self.assertEqual(int_definition.validator(1, "line-length"), 1)
        self.assertEqual(string_list_definition.validator(["*.py"], "include"), ("*.py",))
        self.assertEqual(string_map_definition.validator({"tests/*.py": ["PCF001"]}, "per-file-ignores"), (("tests/*.py", ("PCF001",)),))

    def test_setting_definition_respects_explicit_cli_options_during_defaulting(self) -> None:
        default_int_definition = SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Line length.",
        )
        raw_list_definition = SettingDefinition(
            field="include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Include.",
            cli={"value_kind": SettingCLIValueKind.RAW},
        )
        show_default_list_definition = SettingDefinition(
            field="include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Include.",
            cli={"show_default": True},
        )

        assert default_int_definition.cli is not None
        assert raw_list_definition.cli is not None
        assert show_default_list_definition.cli is not None
        self.assertEqual(default_int_definition.cli.value_kind, SettingCLIValueKind.RAW)
        self.assertTrue(default_int_definition.cli.show_default)
        self.assertEqual(raw_list_definition.cli.value_kind, SettingCLIValueKind.RAW)
        self.assertTrue(raw_list_definition.cli.show_default)
        self.assertEqual(show_default_list_definition.cli.value_kind, SettingCLIValueKind.COMMA_LIST)
        self.assertTrue(show_default_list_definition.cli.show_default)

    def test_global_args_defaults_without_parser_values(self) -> None:
        args = argparse.Namespace()

        self.assertEqual(pydocformatter_global_args.global_values_from_arguments(args, dest_prefixes=("global", "command")), pydocformatter_global_args.GlobalArgs())

    def test_global_args_parse_all_parser_levels(self) -> None:
        parser = argparse.ArgumentParser()
        pydocformatter_global_args.add_global_arguments(parser, dest_prefix="global")
        subparsers = parser.add_subparsers(dest="command")
        command = subparsers.add_parser("check")
        pydocformatter_global_args.add_global_arguments(command, dest_prefix="command")

        args = parser.parse_args(["--config", "line-length = 90", "check", "--config", "line-length = 91", "--isolated"])

        global_values = pydocformatter_global_args.global_values_from_arguments(args, dest_prefixes=("global", "command"))

        self.assertEqual(global_values.config_options, ("line-length = 90", "line-length = 91"))
        self.assertTrue(global_values.isolated)

    def test_setting_definitions_match_formatter_settings_fields(self) -> None:
        setting_fields = tuple(field.name for field in dataclasses.fields(CheckSettings))
        setting_annotations = typing.get_type_hints(CheckSettings)
        override_annotations = typing.get_type_hints(CheckSettingsOverrides)
        definition_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions)

        self.assertEqual(definition_fields, setting_fields)
        self.assertEqual(tuple(definition.value_type for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions), tuple(setting_annotations[field] for field in setting_fields))
        self.assertEqual(set(override_annotations), set(setting_fields))
        self.assertEqual(override_annotations, {field: setting_annotations[field] for field in setting_fields})
        self.assertEqual(
            tuple(getattr(CheckSettings(), definition.field) for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions),
            tuple(getattr(CheckSettings(), field) for field in setting_fields),
        )

    def test_setting_definitions_are_iterable_by_group(self) -> None:
        formatting_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.FORMATTING)
        docstring_formatting_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.DOCSTRING_FORMATTING)
        comment_formatting_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.COMMENT_FORMATTING)
        rule_selection_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.RULE_SELECTION)
        file_selection_fields = tuple(definition.field for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.group == SettingsGroup.FILE_SELECTION)

        self.assertEqual(
            formatting_fields,
            (
                "output_format",
                "legacy",
                "line_length",
                "url_aware_wrapping",
                "line_ending",
                "indent_style",
                "indent_width",
            ),
        )
        self.assertEqual(
            docstring_formatting_fields,
            (
                "docstring_convention",
                "docstring_blank_line_style",
                "docstring_blank_line_after_last_section",
                "docstring_missing_documentation",
                "docstring_missing_documentation_public_only",
                "docstring_parse_list_items",
                "docstring_parse_headings",
                "docstring_parse_doctests",
                "docstring_parse_code_fences",
                "docstring_parse_block_quotes",
                "docstring_parse_tables",
                "docstring_parse_directives",
                "docstring_parse_literal_blocks",
            ),
        )
        self.assertEqual(
            comment_formatting_fields,
            (
                "comment_join_standalone_lines",
                "comment_format_list_items",
                "comment_preserve_headings",
                "comment_preserve_doctests",
                "comment_preserve_code_fences",
                "comment_format_block_quotes",
                "comment_preserve_tables",
                "comment_preserve_directives",
                "comment_detect_code",
                "comment_detect_statements",
                "comment_detect_expressions",
            ),
        )
        self.assertEqual(
            rule_selection_fields,
            (
                "select",
                "ignore",
                "extend_select",
                "per_file_ignores",
                "extend_per_file_ignores",
                "fixable",
                "unfixable",
                "extend_fixable",
            ),
        )
        self.assertEqual(
            file_selection_fields,
            (
                "include",
                "extend_include",
                "exclude",
                "extend_exclude",
                "respect_gitignore",
                "force_exclude",
            ),
        )

    def test_settings_schema_add_arguments_adds_groups_in_order(self) -> None:
        parser = argparse.ArgumentParser()

        pydocformatter_settings.SETTINGS_SCHEMA.add_arguments(parser, CheckSettings())

        group_titles = tuple(group.title for group in parser._action_groups)
        self.assertLess(group_titles.index(SettingsGroup.FORMATTING.value), group_titles.index(SettingsGroup.COMMENT_FORMATTING.value))
        self.assertLess(group_titles.index(SettingsGroup.FORMATTING.value), group_titles.index(SettingsGroup.DOCSTRING_FORMATTING.value))
        self.assertLess(group_titles.index(SettingsGroup.DOCSTRING_FORMATTING.value), group_titles.index(SettingsGroup.COMMENT_FORMATTING.value))
        self.assertLess(group_titles.index(SettingsGroup.COMMENT_FORMATTING.value), group_titles.index(SettingsGroup.RULE_SELECTION.value))
        self.assertLess(group_titles.index(SettingsGroup.RULE_SELECTION.value), group_titles.index(SettingsGroup.FILE_SELECTION.value))
        option_strings = {option for action in parser._actions for option in action.option_strings}
        schema_option_strings = {
            flag for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions if definition.available_in_cli for flag in typing.cast(SettingCLIDefinition, definition.cli).flags
        }
        self.assertLessEqual(schema_option_strings, option_strings)

    def test_settings_schema_rejects_invalid_definition_group(self) -> None:
        class OtherGroup(enum.StrEnum):
            OTHER = "Other"

        with self.assertRaisesRegex(TypeError, "must belong to SettingsGroup.*line_length"):
            SettingsSchema(
                settings_type=CheckSettings,
                overrides_type=CheckSettingsOverrides,
                group_type=SettingsGroup,
                definitions=(
                    SettingDefinition(
                        field="line_length",
                        value_type=int,
                        group=OtherGroup.OTHER,
                        help="Maximum line length.",
                    ),
                ),
                table_path=("tool", "custom"),
            )

    def test_settings_schema_rejects_empty_table_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "table_path.*non-empty"):
            SettingsSchema(
                settings_type=CheckSettings,
                overrides_type=CheckSettingsOverrides,
                group_type=SettingsGroup,
                definitions=pydocformatter_settings.SETTINGS_SCHEMA.definitions,
                table_path=(),
            )

    def test_settings_schema_rejects_empty_table_path_segment(self) -> None:
        with self.assertRaisesRegex(ValueError, "table_path.*non-empty"):
            SettingsSchema(
                settings_type=CheckSettings,
                overrides_type=CheckSettingsOverrides,
                group_type=SettingsGroup,
                definitions=pydocformatter_settings.SETTINGS_SCHEMA.definitions,
                table_path=("tool", ""),
            )

    def test_validation_context_uses_explicit_key(self) -> None:
        @dataclasses.dataclass(frozen=True)
        class CustomSettings:
            config_options: StringList = ()

        schema = SettingsSchema(
            settings_type=CustomSettings,
            overrides_type=dict[str, object],
            group_type=SettingsGroup,
            definitions=(
                SettingDefinition(
                    field="config_options",
                    value_type=StringList,
                    group=SettingsGroup.FORMATTING,
                    help="Configuration options.",
                    key="config",
                ),
            ),
            table_path=("tool", "custom"),
        )

        with self.assertRaises(SettingsError) as context:
            schema.load(field_overrides={"config_options": "not-a-list"}, global_values=pydocformatter_global_args.GlobalArgs(isolated=True))

        self.assertIn("<overrides>.config", str(context.exception))
        self.assertNotIn("config-options", str(context.exception))

    def test_load_toml_file_does_not_check_exists_before_open(self) -> None:
        with unittest.mock.patch("pydocformatter.settings.os.path.exists", side_effect=AssertionError("exists should not be called")):
            self.assertIsNone(pydocformatter_settings_core._load_toml_file("missing.toml", required=False))

    def test_settings_overrides_are_dict_like_and_omit_unspecified_values(self) -> None:
        overrides = CheckSettingsOverrides(line_length=103)

        self.assertEqual(overrides, {"line_length": 103})
        self.assertNotIn("line_ending", overrides)

    def test_readme_configuration_options_document_all_settings(self) -> None:
        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")

        for definition in pydocformatter_settings.SETTINGS_SCHEMA.definitions:
            self.assertIn(f"- `{definition.key}`:", readme)

    def test_load_settings_defaults_in_isolated_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)
        self.assertTrue(config.url_aware_wrapping)
        self.assertIs(config.line_ending, LineEnding.AUTO)
        self.assertIs(config.indent_style, IndentStyle.SPACE)
        self.assertEqual(config.indent_width, 4)
        self.assertFalse(config.comment_join_standalone_lines)
        self.assertTrue(config.comment_format_list_items)
        self.assertTrue(config.comment_preserve_headings)
        self.assertTrue(config.comment_preserve_doctests)
        self.assertTrue(config.comment_preserve_code_fences)
        self.assertTrue(config.comment_format_block_quotes)
        self.assertTrue(config.comment_preserve_tables)
        self.assertTrue(config.comment_preserve_directives)
        self.assertFalse(config.comment_detect_code)
        self.assertTrue(config.comment_detect_statements)
        self.assertFalse(config.comment_detect_expressions)
        self.assertEqual(config.include, DEFAULT_INCLUDE)
        self.assertEqual(config.extend_include, ())
        self.assertEqual(config.exclude, DEFAULT_EXCLUDE)
        self.assertEqual(config.extend_exclude, ())
        self.assertTrue(config.respect_gitignore)
        self.assertFalse(config.force_exclude)
        self.assertFalse(config.legacy)
        self.assertIs(config.output_format, OutputFormat.GROUPED)
        self.assertEqual(config.select, ("ALL",))
        self.assertEqual(config.extend_select, ())
        self.assertEqual(config.ignore, ())
        self.assertEqual(config.fixable, ("ALL",))
        self.assertEqual(config.extend_fixable, ())
        self.assertEqual(config.unfixable, ())
        self.assertEqual(config.per_file_ignores, ())
        self.assertEqual(config.extend_per_file_ignores, ())

    def test_load_profile_tracks_field_source_priorities(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\nselect = ["PDF"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                profile = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(
                    global_values=pydocformatter_global_args.GlobalArgs(config_options=('ignore = ["PDF101"]',)),
                    args=argparse.Namespace(extend_select=["PCF"]),
                    field_overrides=CheckSettingsOverrides(fixable=("PDF101",)),
                )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(profile.priority_for_field("select"), pydocformatter_settings_core.CONFIG_FILE_SOURCE_PRIORITY)
        self.assertEqual(profile.priority_for_field("ignore"), pydocformatter_settings_core.INLINE_CONFIG_SOURCE_PRIORITY)
        self.assertEqual(profile.priority_for_field("extend_select"), pydocformatter_settings_core.ARGUMENT_SOURCE_PRIORITY)
        self.assertEqual(profile.priority_for_field("fixable"), pydocformatter_settings_core.FIELD_OVERRIDE_SOURCE_PRIORITY)
        self.assertEqual(profile.priority_for_field("unfixable"), pydocformatter_settings_core.DEFAULT_SOURCE_PRIORITY)

    def test_settings_profile_key_is_hashable_and_mapping_order_independent(self) -> None:
        settings = CheckSettings()
        first = pydocformatter_settings_core.SettingsProfile(settings=settings, field_bases={"select": "/a", "ignore": "/b"}, field_priorities={"select": 1, "ignore": 2})
        second = pydocformatter_settings_core.SettingsProfile(settings=settings, field_bases={"ignore": "/b", "select": "/a"}, field_priorities={"ignore": 2, "select": 1})

        self.assertIsInstance(first.key(), pydocformatter_settings_core.SettingsProfile.Key)
        self.assertEqual(first.key(), second.key())
        self.assertEqual({first.key(): "value"}[second.key()], "value")

    def test_git_root_pyproject_is_loaded_from_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subdir = root / "src"
            subdir.mkdir()
            self._write_git_marker(root)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 73\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(subdir)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 73)

    def test_current_directory_pyproject_overrides_git_root_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subdir = root / "src"
            subdir.mkdir()
            self._write_git_marker(root)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 73\nindent-width = 2\n",
                encoding="utf-8",
            )
            (subdir / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 74\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(subdir)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 74)
        self.assertEqual(config.indent_width, 4)

    def test_config_options_override_auto_discovered_git_root_and_current_pyprojects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subdir = root / "src"
            subdir.mkdir()
            self._write_git_marker(root)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 73\nindent-width = 2\n",
                encoding="utf-8",
            )
            (subdir / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 74\n",
                encoding="utf-8",
            )
            config_path = root / "pydocfmt.toml"
            config_path.write_text(
                "line-length = 75\nindent-width = 3\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(subdir)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path), "line-length = 76")))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 76)
        self.assertEqual(config.indent_width, 3)

    def test_explicit_config_file_ignores_auto_discovered_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nindent-width = 2\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "line-length = 75\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 75)
        self.assertEqual(config.indent_width, 4)

    def test_isolated_ignores_git_root_and_current_directory_pyprojects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subdir = root / "src"
            subdir.mkdir()
            self._write_git_marker(root)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 73\n",
                encoding="utf-8",
            )
            (subdir / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 74\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(subdir)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)

    def test_auto_discovered_pyproject_path_skips_files_without_pydocfmt_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_git_marker(root)
            candidate = root / "pyproject.toml"
            candidate.write_text("[tool.other]\nvalue = true\n", encoding="utf-8")
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                path = pydocformatter_settings_core._auto_discovered_pyproject_path_for_path(None, table_path=("tool", "pydocfmt"))
            finally:
                os.chdir(previous_cwd)

        self.assertIsNotNone(path)
        self.assertNotEqual(path, str(candidate))

    def test_suite_temporary_directories_stay_below_configuration_boundary(self) -> None:
        boundary = Path(tempfile.gettempdir())
        boundary_config = boundary / "pyproject.toml"

        self.assertEqual(boundary_config.read_text(encoding="utf-8"), "[tool.pydocfmt]\n")
        with tempfile.TemporaryDirectory() as td:
            nested = Path(td) / "nested"
            nested.mkdir()
            discovered = pydocformatter_settings_core._auto_discovered_pyproject_path_for_path(str(nested), table_path=("tool", "pydocfmt"))
            settings = pydocformatter_settings.SETTINGS_SCHEMA.load_profile(path=str(nested)).settings

        self.assertTrue(nested.is_relative_to(boundary))
        self.assertEqual(discovered, str(boundary_config))
        self.assertEqual(settings, CheckSettings())

    def test_rule_settings_accept_all_rule_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\n" 'select = ["PDF", "PCF"]\n' 'ignore = ["PDF101"]\n' 'fixable = ["ALL"]\n' "[tool.pydocfmt.per-file-ignores]\n" '"tests/*.py" = ["PCF001"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.select, ("PDF", "PCF"))
        self.assertEqual(config.ignore, ("PDF101",))
        self.assertEqual(config.fixable, ("ALL",))
        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))

    def test_nested_docstring_table_settings_are_loaded_from_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt.docstring]\nconvention = "google"\nblank-line-style = "aligned"\nblank-line-after-last-section = true\nparse-tables = false\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.docstring_convention, pydocformatter_settings.DocstringConvention.GOOGLE)
        self.assertEqual(config.docstring_blank_line_style, pydocformatter_settings.DocstringBlankLineStyle.ALIGNED)
        self.assertTrue(config.docstring_blank_line_after_last_section)
        self.assertFalse(config.docstring_parse_tables)

    def test_nested_comment_table_settings_are_loaded_from_dedicated_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            config_path.write_text(
                "[comment]\njoin-standalone-lines = true\npreserve-tables = false\ndetect-expressions = true\n",
                encoding="utf-8",
            )

            config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

        self.assertTrue(config.comment_join_standalone_lines)
        self.assertFalse(config.comment_preserve_tables)
        self.assertTrue(config.comment_detect_expressions)

    def test_nested_setting_tables_are_loaded_from_inline_config_options(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(
                config_options=('docstring.convention = "numpy"\ncomment.detect-code = true',),
                isolated=True,
            )
        )

        self.assertEqual(config.docstring_convention, pydocformatter_settings.DocstringConvention.NUMPY)
        self.assertTrue(config.comment_detect_code)

    def test_nested_setting_table_rejects_duplicate_flat_key(self) -> None:
        with self.assertRaisesRegex(SettingsError, "sets docstring-convention more than once"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(
                global_values=pydocformatter_global_args.GlobalArgs(
                    config_options=('docstring-convention = "google"\n[docstring]\nconvention = "numpy"',),
                    isolated=True,
                )
            )

    def test_nested_setting_table_rejects_unknown_flattened_key(self) -> None:
        with self.assertRaisesRegex(SettingsError, "docstring-unknown"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(
                global_values=pydocformatter_global_args.GlobalArgs(
                    config_options=("[docstring]\nunknown = true",),
                    isolated=True,
                )
            )

    def test_nested_setting_table_rejects_deeper_tables(self) -> None:
        with self.assertRaisesRegex(SettingsError, "docstring-parse must not be a table"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(
                global_values=pydocformatter_global_args.GlobalArgs(
                    config_options=("[docstring.parse]\ntables = false",),
                    isolated=True,
                )
            )

    def test_unrelated_nested_setting_table_is_rejected(self) -> None:
        with self.assertRaisesRegex(SettingsError, "formatting"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(
                global_values=pydocformatter_global_args.GlobalArgs(
                    config_options=("[formatting]\nline-length = 99",),
                    isolated=True,
                )
            )

    def test_inline_per_file_rule_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\n" 'per-file-ignores = {"tests/*.py" = ["PCF001"]}\n' 'extend-per-file-ignores = {"generated/*.py" = ["PCF002"]}\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))
        self.assertEqual(config.extend_per_file_ignores, (("generated/*.py", ("PCF002",)),))

    def test_cli_rule_overrides_are_applied(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides=CheckSettingsOverrides(
                select=("PCF",),
                ignore=("PCF002",),
                per_file_ignores=(("tests/*.py", ("PCF001",)),),
            ),
        )

        self.assertEqual(config.select, ("PCF",))
        self.assertEqual(config.ignore, ("PCF002",))
        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))

    def test_format_settings_returns_stable_toml_output(self) -> None:
        settings = CheckSettings(
            line_ending=LineEnding.LF,
            select=("PDF", "PCF"),
            per_file_ignores=(('tests/"quoted"/*.py', ("PCF001",)),),
        )

        output = pydocformatter_settings.SETTINGS_SCHEMA.format(settings)

        self.assertIn("[tool.pydocfmt]\n", output)
        self.assertLess(output.index("output-format"), output.index("legacy"))
        self.assertLess(output.index("legacy"), output.index("line-length"))
        self.assertIn('line-ending = "lf"\n', output)
        self.assertIn('select = ["PDF", "PCF"]\n', output)
        self.assertIn('per-file-ignores = {"tests/\\"quoted\\"/*.py" = ["PCF001"]}\n', output)

    def test_legacy_setting_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nlegacy = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertTrue(config.legacy)

    def test_legacy_cli_override_is_applied(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides=CheckSettingsOverrides(legacy=True),
        )

        self.assertTrue(config.legacy)

    def test_legacy_setting_must_be_boolean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\nlegacy = "yes"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "legacy"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_url_aware_wrapping_setting_is_loaded_from_toml_and_cli(self) -> None:
        configured = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=("url-aware-wrapping = true",)))
        overridden = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(isolated=True),
            args=argparse.Namespace(url_aware_wrapping=True),
        )
        disabled = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(isolated=True, config_options=("url-aware-wrapping = true",)),
            args=argparse.Namespace(url_aware_wrapping=False),
        )

        self.assertTrue(configured.url_aware_wrapping)
        self.assertTrue(overridden.url_aware_wrapping)
        self.assertFalse(disabled.url_aware_wrapping)

    def test_comment_formatting_boolean_settings_are_loaded_from_toml_and_cli(self) -> None:
        configured = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(
                isolated=True,
                config_options=("comment-join-standalone-lines = true\ncomment-format-list-items = true\ncomment-detect-code = false",),
            )
        )
        overridden = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(isolated=True),
            args=argparse.Namespace(comment_preserve_tables=True, comment_detect_code=False),
        )

        self.assertTrue(configured.comment_join_standalone_lines)
        self.assertTrue(configured.comment_format_list_items)
        self.assertFalse(configured.comment_detect_code)
        self.assertTrue(overridden.comment_preserve_tables)
        self.assertFalse(overridden.comment_detect_code)

    def test_docstring_parsing_settings_are_loaded_and_validated(self) -> None:
        for convention in pydocformatter_settings.DocstringConvention:
            config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_convention": convention.value})
            self.assertEqual(config.docstring_convention, convention)
        for blank_line_style in pydocformatter_settings.DocstringBlankLineStyle:
            config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_blank_line_style": blank_line_style.value})
            self.assertEqual(config.docstring_blank_line_style, blank_line_style)
        for missing_documentation in pydocformatter_settings.DocstringMissingDocumentation:
            config = pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_missing_documentation": missing_documentation.value})
            self.assertEqual(config.docstring_missing_documentation, missing_documentation)

        configured = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(
                isolated=True,
                config_options=(
                    'docstring-convention = "google"\ndocstring-blank-line-style = "aligned"\ndocstring-blank-line-after-last-section = true\ndocstring-missing-documentation = "all-docstrings"\ndocstring-missing-documentation-public-only = false\ndocstring-parse-tables = false',
                ),
            )
        )
        overridden = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(isolated=True),
            args=argparse.Namespace(
                docstring_convention="numpy",
                docstring_blank_line_style="blank",
                docstring_blank_line_after_last_section=False,
                docstring_missing_documentation="non-summary-docstrings",
                docstring_missing_documentation_public_only=True,
                docstring_parse_tables=False,
            ),
        )
        self.assertEqual(configured.docstring_convention, pydocformatter_settings.DocstringConvention.GOOGLE)
        self.assertEqual(configured.docstring_blank_line_style, pydocformatter_settings.DocstringBlankLineStyle.ALIGNED)
        self.assertTrue(configured.docstring_blank_line_after_last_section)
        self.assertEqual(configured.docstring_missing_documentation, pydocformatter_settings.DocstringMissingDocumentation.ALL_DOCSTRINGS)
        self.assertFalse(configured.docstring_missing_documentation_public_only)
        self.assertFalse(configured.docstring_parse_tables)
        self.assertEqual(overridden.docstring_convention, pydocformatter_settings.DocstringConvention.NUMPY)
        self.assertEqual(overridden.docstring_blank_line_style, pydocformatter_settings.DocstringBlankLineStyle.BLANK)
        self.assertFalse(overridden.docstring_blank_line_after_last_section)
        self.assertEqual(overridden.docstring_missing_documentation, pydocformatter_settings.DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS)
        self.assertTrue(overridden.docstring_missing_documentation_public_only)
        self.assertFalse(overridden.docstring_parse_tables)

        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides={
                "docstring_parse_list_items": False,
                "docstring_parse_headings": False,
                "docstring_parse_doctests": False,
                "docstring_parse_code_fences": False,
                "docstring_parse_block_quotes": False,
                "docstring_parse_tables": False,
                "docstring_parse_directives": False,
                "docstring_parse_literal_blocks": False,
            }
        )
        self.assertFalse(config.docstring_parse_list_items)
        self.assertFalse(config.docstring_parse_headings)
        self.assertFalse(config.docstring_parse_doctests)
        self.assertFalse(config.docstring_parse_code_fences)
        self.assertFalse(config.docstring_parse_block_quotes)
        self.assertFalse(config.docstring_parse_tables)
        self.assertFalse(config.docstring_parse_directives)
        self.assertFalse(config.docstring_parse_literal_blocks)

        with self.assertRaisesRegex(SettingsError, "docstring_convention must be one of"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_convention": "automatic"})

        with self.assertRaisesRegex(SettingsError, "Unknown setting: docstring_parse_sphinx_fields"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(field_overrides={"docstring_parse_sphinx_fields": False})

    def test_output_format_setting_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\noutput-format = "grouped"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertIs(config.output_format, OutputFormat.GROUPED)

    def test_output_format_cli_override_is_applied(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides=CheckSettingsOverrides(output_format=OutputFormat.GROUPED),
        )

        self.assertIs(config.output_format, OutputFormat.GROUPED)

    def test_output_format_setting_must_be_grouped(self) -> None:
        unsupported_output_formats = ("json",)
        unsupported_output_format = unsupported_output_formats[0]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                f'[tool.pydocfmt]\noutput-format = "{unsupported_output_format}"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "output-format"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_settings_overrides_replace_independent_list_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\n"
                "line-length = 77\n"
                'line-ending = "cr-lf"\n'
                'indent-style = "space"\n'
                "indent-width = 3\n"
                'include = ["*.pyi"]\n'
                'extend-include = ["*.pyw"]\n'
                'exclude = ["build"]\n'
                'extend-exclude = ["dist"]\n'
                "force-exclude = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 77)
        self.assertIs(config.line_ending, LineEnding.CR_LF)
        self.assertIs(config.indent_style, IndentStyle.SPACE)
        self.assertEqual(config.indent_width, 3)
        self.assertEqual(config.include, ("*.pyi",))
        self.assertEqual(config.extend_include, ("*.pyw",))
        self.assertEqual(config.exclude, ("build",))
        self.assertEqual(config.extend_exclude, ("dist",))
        self.assertTrue(config.force_exclude)

    def test_overrides_replace_extend_lists(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides=CheckSettingsOverrides(
                include=("*.py",),
                extend_include=("*.pyw",),
                exclude=(),
                extend_exclude=("generated.py",),
            ),
        )

        self.assertEqual(config.include, ("*.py",))
        self.assertEqual(config.extend_include, ("*.pyw",))
        self.assertEqual(config.exclude, ())
        self.assertEqual(config.extend_exclude, ("generated.py",))

    def test_overrides_replace_indent_settings(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides=CheckSettingsOverrides(indent_style=IndentStyle.TAB, indent_width=2),
        )

        self.assertIs(config.indent_style, IndentStyle.TAB)
        self.assertEqual(config.indent_width, 2)

    def test_overrides_replace_line_ending(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides=CheckSettingsOverrides(line_ending=LineEnding.NATIVE),
        )

        self.assertIs(config.line_ending, LineEnding.NATIVE)

    def test_unknown_hyphenated_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nunknown-key = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "unknown-key"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_underscore_alias_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline_length = 100\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "line_length"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_bool_line_length_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "line-length"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_line_length_accepts_inclusive_bounds(self) -> None:
        lower = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 1",), isolated=True))
        upper = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 320",), isolated=True))

        self.assertEqual(lower.line_length, 1)
        self.assertEqual(upper.line_length, 320)

    def test_line_length_rejects_values_outside_bounds(self) -> None:
        with self.assertRaisesRegex(SettingsError, "line-length.*greater than or equal to 1"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 0",), isolated=True))
        with self.assertRaisesRegex(SettingsError, "line-length.*less than or equal to 320"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 321",), isolated=True))

    def test_indent_width_accepts_inclusive_bounds(self) -> None:
        lower = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 1",), isolated=True))
        upper = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 255",), isolated=True))

        self.assertEqual(lower.indent_width, 1)
        self.assertEqual(upper.indent_width, 255)

    def test_indent_width_rejects_values_outside_bounds(self) -> None:
        with self.assertRaisesRegex(SettingsError, "indent-width.*greater than or equal to 1"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 0",), isolated=True))
        with self.assertRaisesRegex(SettingsError, "indent-width.*less than or equal to 255"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=("indent-width = 256",), isolated=True))

    def test_invalid_indent_style_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\nindent-style = "spaces"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "indent-style"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_invalid_line_ending_lists_enum_options(self) -> None:
        with self.assertRaisesRegex(SettingsError, r"line-ending.*\{'auto', 'lf', 'cr-lf', 'native'\}"):
            pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=('line-ending = "crlf"',), isolated=True))

    def test_invalid_line_ending_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\nline-ending = "crlf"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "line-ending"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_invalid_indent_width_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nindent-width = 0\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "indent-width"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_formatter_config_must_be_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool]\npydocfmt = false\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, r"\[tool\.pydocfmt\] section must be a table"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_nested_tool_table_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt.pydocfmt]\nline-length = 72\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "pydocfmt"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_invalid_list_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = "*.py"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "include"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_settings_include_pattern_shape_is_not_file_selection_validated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.include, ("src/",))

    def test_empty_config_exclude_string_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\nexclude = [""]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(SettingsError, "exclude.*empty strings"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load()
            finally:
                os.chdir(previous_cwd)

    def test_empty_cli_include_string_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                with self.assertRaisesRegex(SettingsError, "include.*empty strings"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load(
                        field_overrides=CheckSettingsOverrides(include=("",)),
                    )
            finally:
                os.chdir(previous_cwd)

    def test_empty_cli_exclude_string_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                with self.assertRaisesRegex(SettingsError, "exclude.*empty strings"):
                    pydocformatter_settings.SETTINGS_SCHEMA.load(
                        field_overrides=CheckSettingsOverrides(exclude=("",)),
                    )
            finally:
                os.chdir(previous_cwd)

    def test_explicit_pyproject_config_file_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pyproject.toml"
            config_path.write_text(
                "[tool.pydocfmt]\nline-length = 99\nrespect-gitignore = false\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 99)
        self.assertFalse(config.respect_gitignore)

    def test_explicit_dedicated_config_file_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            config_path.write_text(
                'line-ending = "lf"\nselect = ["PCF"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))
            finally:
                os.chdir(previous_cwd)

        self.assertIs(config.line_ending, LineEnding.LF)
        self.assertEqual(config.select, ("PCF",))

    def test_explicit_non_pyproject_file_rejects_pyproject_style_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "config.toml"
            config_path.write_text(
                "[tool.pydocfmt]\nline-length = 99\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SettingsError, "unknown setting.*tool"):
                pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),)))

    def test_inline_config_option_is_applied(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(config_options=('line-length = 101\nignore = ["PCF001"]',)),
        )

        self.assertEqual(config.line_length, 101)
        self.assertEqual(config.ignore, ("PCF001",))

    def test_inline_config_options_override_config_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            config_path.write_text(
                "line-length = 90\n",
                encoding="utf-8",
            )
            config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path), "line-length = 91")))

        self.assertEqual(config.line_length, 91)

    def test_command_line_overrides_override_inline_config_options(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            field_overrides=CheckSettingsOverrides(line_length=103),
            global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 102",)),
        )

        self.assertEqual(config.line_length, 103)

    def test_load_accepts_argparse_namespace_overrides(self) -> None:
        args = argparse.Namespace(line_length=103, select=["PDF,PCF"], per_file_ignores=['{"tests/*.py" = ["PCF001"]}'])

        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 102",)),
            args=args,
        )

        self.assertEqual(config.line_length, 103)
        self.assertEqual(config.select, ("PDF", "PCF"))
        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))

    def test_toml_map_cli_repeated_patterns_append_values(self) -> None:
        args = argparse.Namespace(
            per_file_ignores=[
                '{"tests/*.py" = ["PDF200"], "src/*.py" = ["PDF106"]}',
                '{"tests/*.py" = ["PDF110"]}',
            ],
        )

        config = pydocformatter_settings.SETTINGS_SCHEMA.load(args=args)

        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PDF200", "PDF110")), ("src/*.py", ("PDF106",))))

    def test_rule_selection_cli_comma_lists_strip_whitespace_as_documented_delta(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(args=argparse.Namespace(select=["PDF200, PDF110"]))

        self.assertEqual(config.select, ("PDF200", "PDF110"))

    def test_explicit_overrides_override_argparse_namespace_overrides(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            args=argparse.Namespace(line_length=102),
            field_overrides=CheckSettingsOverrides(line_length=103),
        )

        self.assertEqual(config.line_length, 103)

    def test_isolated_ignores_auto_discovered_pyproject_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 72\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_settings.SETTINGS_SCHEMA.load(global_values=pydocformatter_global_args.GlobalArgs(isolated=True))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)

    def test_isolated_accepts_inline_config_options(self) -> None:
        config = pydocformatter_settings.SETTINGS_SCHEMA.load(
            global_values=pydocformatter_global_args.GlobalArgs(config_options=("line-length = 104",), isolated=True),
        )

        self.assertEqual(config.line_length, 104)

    def test_isolated_rejects_explicit_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            config_path.write_text("line-length = 105\n", encoding="utf-8")

            with self.assertRaisesRegex(SettingsError, "--config=PATH"):
                pydocformatter_settings.SETTINGS_SCHEMA.load(
                    global_values=pydocformatter_global_args.GlobalArgs(config_options=(str(config_path),), isolated=True),
                )


if __name__ == "__main__":
    unittest.main()
