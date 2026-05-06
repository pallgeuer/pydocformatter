import os
import tempfile
import unittest
from pathlib import Path

from pydocformatter.config import (
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    ConfigError,
    SettingsOverrides,
    apply_cli_overrides,
    load_config,
)


class TestConfig(unittest.TestCase):
    def test_load_config_defaults_without_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            previous_cwd = os.getcwd()
            os.chdir(td)
            try:
                config = load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 88)
        self.assertTrue(config.respect_gitignore)
        self.assertFalse(config.force_exclude)
        self.assertEqual(config.include, DEFAULT_INCLUDE)
        self.assertEqual(config.extend_include, ())
        self.assertEqual(config.exclude, DEFAULT_EXCLUDE)
        self.assertEqual(config.extend_exclude, ())

    def test_shared_and_tool_specific_overrides_replace_independent_list_keys(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[tool.pydocformatter]\n"
                "line-length = 90\n"
                'include = ["*.pyi"]\n'
                'extend-include = ["*.py"]\n'
                'exclude = ["build"]\n'
                'extend-exclude = ["dist"]\n'
                "force-exclude = true\n"
                "[tool.pydocformatter.pydocfmt]\n"
                "line-length = 77\n"
                'extend-include = ["*.pyw"]\n',
                encoding="utf-8",
            )
            previous_cwd = os.getcwd()
            os.chdir(root)
            try:
                config = load_config("pydocfmt")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(config.line_length, 77)
        self.assertEqual(config.include, ("*.pyi",))
        self.assertEqual(config.extend_include, ("*.pyw",))
        self.assertEqual(config.exclude, ("build",))
        self.assertEqual(config.extend_exclude, ("dist",))
        self.assertTrue(config.force_exclude)

    def test_cli_overrides_replace_extend_lists(self) -> None:
        config = apply_cli_overrides(
            load_config("pydocfmt"),
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
                config = load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    load_config("pydocfmt")
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
                    apply_cli_overrides(
                        load_config("pydocfmt"),
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
                    apply_cli_overrides(
                        load_config("pydocfmt"),
                        SettingsOverrides(exclude=("",)),
                    )
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
