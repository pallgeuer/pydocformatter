import os
import tempfile
import unittest
from pathlib import Path

import pydocformatter.config as pydocformatter_config
from pydocformatter.config import (
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    ConfigError,
    FormatterSettings,
    SettingsOverrides,
)


class TestConfig(unittest.TestCase):
    def test_load_config_defaults_without_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                config = pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)
        self.assertEqual(config.line_ending, "auto")
        self.assertEqual(config.indent_style, "space")
        self.assertEqual(config.indent_width, 4)
        self.assertEqual(config.include, DEFAULT_INCLUDE)
        self.assertEqual(config.extend_include, ())
        self.assertEqual(config.exclude, DEFAULT_EXCLUDE)
        self.assertEqual(config.extend_exclude, ())
        self.assertTrue(config.respect_gitignore)
        self.assertFalse(config.force_exclude)
        self.assertFalse(config.experimental)
        self.assertEqual(config.output_format, "grouped")
        self.assertEqual(config.select, ("ALL",))
        self.assertEqual(config.extend_select, ())
        self.assertEqual(config.ignore, ())
        self.assertEqual(config.fixable, ("ALL",))
        self.assertEqual(config.extend_fixable, ())
        self.assertEqual(config.unfixable, ())
        self.assertEqual(config.per_file_ignores, ())
        self.assertEqual(config.extend_per_file_ignores, ())

    def test_rule_settings_accept_all_rule_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\n" 'select = ["PDF", "PCF"]\n' 'ignore = ["PDF001"]\n' 'fixable = ["ALL"]\n' "[tool.pydocfmt.per-file-ignores]\n" '"tests/*.py" = ["PCF001"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.select, ("PDF", "PCF"))
        self.assertEqual(config.ignore, ("PDF001",))
        self.assertEqual(config.fixable, ("ALL",))
        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))

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
                config = pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))
        self.assertEqual(config.extend_per_file_ignores, (("generated/*.py", ("PCF002",)),))

    def test_cli_rule_overrides_are_applied(self) -> None:
        config = pydocformatter_config.load_config(
            SettingsOverrides(
                select=("PCF",),
                ignore=("PCF002",),
                per_file_ignores=(("tests/*.py", ("PCF001",)),),
            ),
        )

        self.assertEqual(config.select, ("PCF",))
        self.assertEqual(config.ignore, ("PCF002",))
        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))

    def test_format_settings_returns_stable_toml_output(self) -> None:
        settings = FormatterSettings(
            line_ending="lf",
            select=("PDF", "PCF"),
            per_file_ignores=(('tests/"quoted"/*.py', ("PCF001",)),),
        )

        output = pydocformatter_config.format_settings(settings)

        self.assertIn("[tool.pydocfmt]\n", output)
        self.assertLess(output.index("output-format"), output.index("experimental"))
        self.assertLess(output.index("experimental"), output.index("line-length"))
        self.assertIn('line-ending = "lf"\n', output)
        self.assertIn('select = ["PDF", "PCF"]\n', output)
        self.assertIn('per-file-ignores = {"tests/\\"quoted\\"/*.py" = ["PCF001"]}\n', output)

    def test_experimental_setting_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nexperimental = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

        self.assertTrue(config.experimental)

    def test_experimental_cli_override_is_applied(self) -> None:
        config = pydocformatter_config.load_config(
            SettingsOverrides(experimental=True),
        )

        self.assertTrue(config.experimental)

    def test_experimental_setting_must_be_boolean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\nexperimental = "yes"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "experimental"):
                    pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

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
                config = pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.output_format, "grouped")

    def test_output_format_cli_override_is_applied(self) -> None:
        config = pydocformatter_config.load_config(
            SettingsOverrides(output_format="grouped"),
        )

        self.assertEqual(config.output_format, "grouped")

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
                with self.assertRaisesRegex(ConfigError, "output-format"):
                    pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

    def test_config_overrides_replace_independent_list_keys(self) -> None:
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
                config = pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 77)
        self.assertEqual(config.line_ending, "cr-lf")
        self.assertEqual(config.indent_style, "space")
        self.assertEqual(config.indent_width, 3)
        self.assertEqual(config.include, ("*.pyi",))
        self.assertEqual(config.extend_include, ("*.pyw",))
        self.assertEqual(config.exclude, ("build",))
        self.assertEqual(config.extend_exclude, ("dist",))
        self.assertTrue(config.force_exclude)

    def test_cli_overrides_replace_extend_lists(self) -> None:
        config = pydocformatter_config.load_config(
            SettingsOverrides(
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

    def test_cli_overrides_replace_indent_settings(self) -> None:
        config = pydocformatter_config.load_config(
            SettingsOverrides(indent_style="tab", indent_width=2),
        )

        self.assertEqual(config.indent_style, "tab")
        self.assertEqual(config.indent_width, 2)

    def test_cli_overrides_replace_line_ending(self) -> None:
        config = pydocformatter_config.load_config(
            SettingsOverrides(line_ending="native"),
        )

        self.assertEqual(config.line_ending, "native")

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
                with self.assertRaisesRegex(ConfigError, "unknown-key"):
                    pydocformatter_config.load_config()
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
                with self.assertRaisesRegex(ConfigError, "line_length"):
                    pydocformatter_config.load_config()
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
                with self.assertRaisesRegex(ConfigError, "line-length"):
                    pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

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
                with self.assertRaisesRegex(ConfigError, "indent-style"):
                    pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

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
                with self.assertRaisesRegex(ConfigError, "line-ending"):
                    pydocformatter_config.load_config()
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
                with self.assertRaisesRegex(ConfigError, "indent-width"):
                    pydocformatter_config.load_config()
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
                with self.assertRaisesRegex(ConfigError, r"\[tool\.pydocfmt\] section must be a table"):
                    pydocformatter_config.load_config()
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
                with self.assertRaisesRegex(ConfigError, "pydocfmt"):
                    pydocformatter_config.load_config()
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
                with self.assertRaisesRegex(ConfigError, "include"):
                    pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

    def test_config_include_pattern_shape_is_not_file_selection_validated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config()
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
                with self.assertRaisesRegex(ConfigError, "exclude.*empty strings"):
                    pydocformatter_config.load_config()
            finally:
                os.chdir(previous_cwd)

    def test_empty_cli_include_string_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                with self.assertRaisesRegex(ConfigError, "include.*empty strings"):
                    pydocformatter_config.load_config(
                        SettingsOverrides(include=("",)),
                    )
            finally:
                os.chdir(previous_cwd)

    def test_empty_cli_exclude_string_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                with self.assertRaisesRegex(ConfigError, "exclude.*empty strings"):
                    pydocformatter_config.load_config(
                        SettingsOverrides(exclude=("",)),
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
                config = pydocformatter_config.load_config(config_options=(str(config_path),))
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
                config = pydocformatter_config.load_config(config_options=(str(config_path),))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_ending, "lf")
        self.assertEqual(config.select, ("PCF",))

    def test_inline_config_option_is_applied(self) -> None:
        config = pydocformatter_config.load_config(
            config_options=('line-length = 101\nignore = ["PCF001"]',),
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
            config = pydocformatter_config.load_config(
                config_options=(str(config_path), "line-length = 91"),
            )

        self.assertEqual(config.line_length, 91)

    def test_command_line_overrides_override_inline_config_options(self) -> None:
        config = pydocformatter_config.load_config(
            SettingsOverrides(line_length=103),
            config_options=("line-length = 102",),
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
                config = pydocformatter_config.load_config(isolated=True)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)

    def test_isolated_accepts_inline_config_options(self) -> None:
        config = pydocformatter_config.load_config(
            config_options=("line-length = 104",),
            isolated=True,
        )

        self.assertEqual(config.line_length, 104)

    def test_isolated_rejects_explicit_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "pydocfmt.toml"
            config_path.write_text("line-length = 105\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigError, "--config=PATH"):
                pydocformatter_config.load_config(
                    config_options=(str(config_path),),
                    isolated=True,
                )


if __name__ == "__main__":
    unittest.main()
