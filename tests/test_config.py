import os
import tempfile
import unittest
from pathlib import Path

import pydocformatter.config as pydocformatter_config
from pydocformatter.config import (
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    ConfigError,
    SettingsOverrides,
)


class TestConfig(unittest.TestCase):
    def test_load_config_defaults_without_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                config = pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)
        self.assertEqual(config.indent_style, "space")
        self.assertEqual(config.indent_width, 4)
        self.assertTrue(config.respect_gitignore)
        self.assertFalse(config.force_exclude)
        self.assertEqual(config.include, DEFAULT_INCLUDE)
        self.assertEqual(config.extend_include, ())
        self.assertEqual(config.exclude, DEFAULT_EXCLUDE)
        self.assertEqual(config.extend_exclude, ())
        self.assertEqual(config.select, ("ALL",))
        self.assertEqual(config.extend_select, ())
        self.assertEqual(config.ignore, ())
        self.assertEqual(config.fixable, ("ALL",))
        self.assertEqual(config.extend_fixable, ())
        self.assertEqual(config.unfixable, ())
        self.assertEqual(config.per_file_ignores, ())
        self.assertEqual(config.extend_per_file_ignores, ())

    def test_shared_rule_settings_accept_all_rule_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\n"
                'select = ["RD", "PCF"]\n'
                'ignore = ["PDF001"]\n'
                'fixable = ["ALL"]\n'
                "[tool.pydocformatter.per-file-ignores]\n"
                '"tests/*.py" = ["PCF001"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.select, ("RD", "PCF"))
        self.assertEqual(config.ignore, ("PDF001",))
        self.assertEqual(config.fixable, ("ALL",))
        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))

    def test_tool_specific_rule_settings_reject_other_tool_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pydocfmt]\n" 'select = ["PCF"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "PCF"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_inline_per_file_rule_settings_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pycommentfmt]\n"
                'per-file-ignores = {"tests/*.py" = ["PCF001"]}\n'
                'extend-per-file-ignores = {"generated/*.py" = ["PCF002"]}\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config("pycommentfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))
        self.assertEqual(
            config.extend_per_file_ignores, (("generated/*.py", ("PCF002",)),)
        )

    def test_cli_rule_overrides_are_applied(self) -> None:
        config = pydocformatter_config.load_config(
            "pycommentfmt",
            SettingsOverrides(
                select=("PCF",),
                ignore=("PCF002",),
                per_file_ignores=(("tests/*.py", ("PCF001",)),),
            ),
        )

        self.assertEqual(config.select, ("PCF",))
        self.assertEqual(config.ignore, ("PCF002",))
        self.assertEqual(config.per_file_ignores, (("tests/*.py", ("PCF001",)),))

    def test_shared_and_tool_specific_overrides_replace_independent_list_keys(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\n"
                "line-length = 90\n"
                'indent-style = "tab"\n'
                "indent-width = 2\n"
                'include = ["*.pyi"]\n'
                'extend-include = ["*.py"]\n'
                'exclude = ["build"]\n'
                'extend-exclude = ["dist"]\n'
                "force-exclude = true\n"
                "[tool.pydocformatter.pydocfmt]\n"
                "line-length = 77\n"
                'indent-style = "space"\n'
                "indent-width = 3\n"
                'extend-include = ["*.pyw"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 77)
        self.assertEqual(config.indent_style, "space")
        self.assertEqual(config.indent_width, 3)
        self.assertEqual(config.include, ("*.pyi",))
        self.assertEqual(config.extend_include, ("*.pyw",))
        self.assertEqual(config.exclude, ("build",))
        self.assertEqual(config.extend_exclude, ("dist",))
        self.assertTrue(config.force_exclude)

    def test_cli_overrides_replace_extend_lists(self) -> None:
        config = pydocformatter_config.load_config(
            "pydocfmt",
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

    def test_cli_overrides_replace_pydocfmt_indent_settings(self) -> None:
        config = pydocformatter_config.load_config(
            "pydocfmt",
            SettingsOverrides(indent_style="tab", indent_width=2),
        )

        self.assertEqual(config.indent_style, "tab")
        self.assertEqual(config.indent_width, 2)

    def test_shared_pydocfmt_indent_settings_are_ignored_by_pycommentfmt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\n" 'indent-style = "tab"\n' "indent-width = 2\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config("pycommentfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.indent_style, "space")
        self.assertEqual(config.indent_width, 4)

    def test_pycommentfmt_specific_indent_style_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pycommentfmt]\n" 'indent-style = "tab"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "indent-style"):
                    pydocformatter_config.load_config("pycommentfmt")
            finally:
                os.chdir(previous_cwd)

    def test_pycommentfmt_specific_indent_width_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pycommentfmt]\n" "indent-width = 2\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "indent-width"):
                    pydocformatter_config.load_config("pycommentfmt")
            finally:
                os.chdir(previous_cwd)

    def test_unselected_tool_table_unknown_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pycommentfmt]\nunknown-key = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "unknown-key"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_unselected_tool_table_invalid_value_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter.pydocfmt]\nindent-width = 0\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "indent-width"):
                    pydocformatter_config.load_config("pycommentfmt")
            finally:
                os.chdir(previous_cwd)

    def test_legacy_top_level_tool_table_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocfmt]\nline-length = 101\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)

    def test_unknown_hyphenated_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\nunknown-key = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "unknown-key"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_underscore_alias_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\nline_length = 100\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "line_length"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_bool_line_length_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\nline-length = true\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "line-length"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_invalid_indent_style_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocformatter]\nindent-style = "spaces"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "indent-style"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_invalid_indent_width_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\nindent-width = 0\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "indent-width"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_formatter_config_must_be_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool]\npydocformatter = false\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(
                    ConfigError, "pydocformatter must be a table"
                ):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_tool_specific_config_must_be_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\npydocfmt = false\n",
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(
                    ConfigError, "pydocformatter.pydocfmt must be a table"
                ):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_invalid_list_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocformatter]\ninclude = "*.py"\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ConfigError, "include"):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_invalid_config_include_glob_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocformatter]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(
                    ConfigError, "include pattern must target files"
                ):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_invalid_tool_specific_include_glob_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocformatter.pydocfmt]\ninclude = ["src/"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(
                    ConfigError, "include pattern must target files"
                ):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_invalid_config_exclude_glob_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.pydocformatter]\nexclude = [""]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(
                    ConfigError, "exclude patterns must not be empty"
                ):
                    pydocformatter_config.load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

    def test_invalid_cli_include_glob_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                with self.assertRaisesRegex(
                    ConfigError, "include patterns must not be empty"
                ):
                    pydocformatter_config.load_config(
                        "pydocfmt",
                        SettingsOverrides(include=("",)),
                    )
            finally:
                os.chdir(previous_cwd)

    def test_invalid_cli_exclude_glob_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                with self.assertRaisesRegex(
                    ConfigError, "exclude patterns must not be empty"
                ):
                    pydocformatter_config.load_config(
                        "pydocfmt",
                        SettingsOverrides(exclude=("",)),
                    )
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
