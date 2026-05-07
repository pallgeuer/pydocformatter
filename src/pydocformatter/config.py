import os
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from typing import Any, Literal

from pydocformatter.glob_matcher import (
    GlobPatternError,
    validate_exclude_patterns,
    validate_include_patterns,
)

ToolName = Literal["pydocfmt", "pycommentfmt"]
IndentStyle = Literal["space", "tab"]

DEFAULT_EXCLUDE = (
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".git-rewrite",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".pytype",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "buck-out",
    "dist",
    "node_modules",
    "venv",
)

DEFAULT_INCLUDE = ("*.py", "*.pyi", "*.pyw")

TOOL_NAMES = ("pydocfmt", "pycommentfmt")

_KEY_TO_FIELD = {
    "line-length": "line_length",
    "indent-style": "indent_style",
    "indent-width": "indent_width",
    "respect-gitignore": "respect_gitignore",
    "force-exclude": "force_exclude",
    "include": "include",
    "extend-include": "extend_include",
    "exclude": "exclude",
    "extend-exclude": "extend_exclude",
}
_FIELD_TO_KEY = {field: key for key, field in _KEY_TO_FIELD.items()}
_COMMON_SETTING_KEYS = frozenset(
    {
        "line-length",
        "respect-gitignore",
        "force-exclude",
        "include",
        "extend-include",
        "exclude",
        "extend-exclude",
    }
)
_PYDOCFMT_SETTING_KEYS = _COMMON_SETTING_KEYS | {"indent-style", "indent-width"}
_TOOL_SETTING_KEYS = {
    "pydocfmt": _PYDOCFMT_SETTING_KEYS,
    "pycommentfmt": _COMMON_SETTING_KEYS,
}
_SHARED_SETTING_KEYS = _PYDOCFMT_SETTING_KEYS


class ConfigError(ValueError):
    """Raised when pydocformatter configuration cannot be resolved or validated.

    This exception represents user-facing configuration failures, including malformed
    TOML, unsupported table shapes, unknown setting keys, invalid tool names, and
    invalid setting values.
    """


@dataclass(frozen=True)
class FormatterSettings:
    """Resolved formatter settings for pydocformatter tools.

    Attributes:
        line_length (int): Maximum line length used when wrapping docstrings or
            comments.
        indent_style (IndentStyle): Indentation style used by `pydocfmt` for generated
            docstring section indentation. This setting is not used by `pycommentfmt`.
        indent_width (int): Number of spaces per generated `pydocfmt` docstring
            indentation level, or the visual width of a tab. This setting is not used by
            `pycommentfmt`.
        respect_gitignore (bool): Whether discovered files are filtered through
            `.gitignore`.
        force_exclude (bool): Whether include, exclude, and gitignore rules apply to
            explicitly passed paths.
        include (tuple[str, ...]): Base glob patterns that identify format-eligible
            files.
        extend_include (tuple[str, ...]): Additional include glob patterns appended to
            `include`.
        exclude (tuple[str, ...]): Base glob patterns for files or directories to
            ignore.
        extend_exclude (tuple[str, ...]): Additional exclude glob patterns appended to
            `exclude`.
    """

    line_length: int = 88
    indent_style: IndentStyle = "space"
    indent_width: int = 4
    respect_gitignore: bool = True
    force_exclude: bool = False
    include: tuple[str, ...] = DEFAULT_INCLUDE
    extend_include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    extend_exclude: tuple[str, ...] = ()

    @property
    def include_patterns(self) -> tuple[str, ...]:
        """Return the final include patterns used by file selection.

        Returns:
            tuple[str, ...]: The base include patterns followed by any extension
                patterns.
        """
        return self.include + self.extend_include

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Return the final exclude patterns used by file selection.

        Returns:
            tuple[str, ...]: The base exclude patterns followed by any extension
                patterns.
        """
        return self.exclude + self.extend_exclude


@dataclass(frozen=True)
class SettingsOverrides:
    """Optional formatter settings from one precedence layer.

    Attributes:
        line_length (int | None): Optional maximum line length override.
        indent_style (IndentStyle | None): Optional `pydocfmt` generated docstring
            indentation style override.
        indent_width (int | None): Optional `pydocfmt` generated docstring indentation
            width override.
        respect_gitignore (bool | None): Optional gitignore filtering override.
        force_exclude (bool | None): Optional force-exclude override.
        include (tuple[str, ...] | None): Optional replacement include patterns.
        extend_include (tuple[str, ...] | None): Optional replacement include
            extensions.
        exclude (tuple[str, ...] | None): Optional replacement exclude patterns.
        extend_exclude (tuple[str, ...] | None): Optional replacement exclude
            extensions.
    """

    line_length: int | None = None
    indent_style: IndentStyle | None = None
    indent_width: int | None = None
    respect_gitignore: bool | None = None
    force_exclude: bool | None = None
    include: tuple[str, ...] | None = None
    extend_include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None
    extend_exclude: tuple[str, ...] | None = None


def load_config(tool_name: ToolName) -> FormatterSettings:
    """Load resolved pyproject configuration for one formatter tool.

    Args:
        tool_name (ToolName): Formatter tool whose shared and tool-specific settings
            should be loaded.

    Returns:
        FormatterSettings: Settings resolved from defaults and `pyproject.toml`.

    Raises:
        `ConfigError`: If the tool name or configuration file contents are invalid.
    """
    return resolve_settings(tool_name)


def resolve_settings(
    tool_name: ToolName,
    cli_overrides: SettingsOverrides | None = None,
) -> FormatterSettings:
    """Resolve settings from defaults, pyproject config, and optional CLI overrides.

    Shared `[tool.pydocformatter]` settings are applied before the selected tool's
    nested table, and `cli_overrides` has the highest precedence. `pydocfmt`-only
    indentation settings are accepted in the shared table but ignored when resolving
    `pycommentfmt`. Known nested tool tables are validated even when they are not the
    selected tool.

    Args:
        tool_name (ToolName): Formatter tool to resolve settings for.
        cli_overrides (SettingsOverrides | None): Optional command-line settings to
            apply last.

    Returns:
        FormatterSettings: Fully resolved settings for the requested tool.

    Raises:
        `ConfigError`: If the tool name, TOML structure, setting names, or setting
            values are invalid.
    """
    _validate_tool_name(tool_name)
    settings = FormatterSettings()

    config = _load_pyproject_config()
    tool_config = config.get("tool", {})
    if not isinstance(tool_config, dict):
        if "tool" in config:
            raise ConfigError("pyproject.toml [tool] must be a table")
        return _apply_overrides(settings, cli_overrides, "command line")

    if "pydocformatter" in tool_config:
        formatter_config = tool_config["pydocformatter"]
        if not isinstance(formatter_config, dict):
            raise ConfigError("tool.pydocformatter must be a table")
        settings = _apply_config_section(
            settings,
            formatter_config,
            "tool.pydocformatter",
            allowed_setting_keys=_SHARED_SETTING_KEYS,
            applied_setting_keys=_TOOL_SETTING_KEYS[tool_name],
            allow_tool_tables=True,
        )

        for nested_tool_name in TOOL_NAMES:
            if nested_tool_name not in formatter_config:
                continue
            nested_tool_config = formatter_config[nested_tool_name]
            if not isinstance(nested_tool_config, dict):
                raise ConfigError(
                    f"tool.pydocformatter.{nested_tool_name} must be a table"
                )
            _validate_config_section_keys(
                nested_tool_config,
                f"tool.pydocformatter.{nested_tool_name}",
                _TOOL_SETTING_KEYS[nested_tool_name],
            )
            _validate_config_section_values(
                nested_tool_config,
                f"tool.pydocformatter.{nested_tool_name}",
                _TOOL_SETTING_KEYS[nested_tool_name],
            )

        if tool_name in formatter_config:
            tool_specific = formatter_config[tool_name]
            settings = _apply_config_section(
                settings,
                tool_specific,
                f"tool.pydocformatter.{tool_name}",
                allowed_setting_keys=_TOOL_SETTING_KEYS[tool_name],
                applied_setting_keys=_TOOL_SETTING_KEYS[tool_name],
                allow_tool_tables=False,
            )

    return _apply_overrides(settings, cli_overrides, "command line")


def apply_cli_overrides(
    settings: FormatterSettings,
    cli_overrides: SettingsOverrides,
) -> FormatterSettings:
    """Apply command-line overrides to already-resolved config settings.

    Args:
        settings (FormatterSettings): Settings resolved from defaults and configuration
            files.
        cli_overrides (SettingsOverrides): Command-line values to apply where not
            `None`.

    Returns:
        FormatterSettings: A new settings object with CLI overrides applied.

    Raises:
        `ConfigError`: If any override value is invalid.
    """
    return _apply_overrides(settings, cli_overrides, "command line")


def _load_pyproject_config() -> dict[str, Any]:
    """Load pyproject.toml from the current directory, returning an empty config if
    absent.
    """
    if not os.path.exists("pyproject.toml"):
        return {}

    with open("pyproject.toml", "rb") as file:
        try:
            config = tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"failed to decode pyproject.toml: {error}") from error

    if not isinstance(config, dict):
        raise ConfigError("pyproject.toml must contain a TOML table")
    return config


def _validate_tool_name(tool_name: str) -> None:
    """Reject unknown formatter tool names before resolving configuration."""
    if tool_name not in TOOL_NAMES:
        raise ConfigError("tool_name must be either 'pydocfmt' or 'pycommentfmt'")


def _apply_config_section(
    settings: FormatterSettings,
    section: dict[str, Any],
    context: str,
    *,
    allowed_setting_keys: frozenset[str],
    applied_setting_keys: frozenset[str],
    allow_tool_tables: bool,
) -> FormatterSettings:
    """Apply one TOML configuration section after validating allowed keys."""
    allowed_keys = set(allowed_setting_keys)
    if allow_tool_tables:
        allowed_keys.update(TOOL_NAMES)

    _validate_config_section_keys(section, context, frozenset(allowed_keys))
    _validate_config_section_values(section, context, allowed_setting_keys)

    values = {
        _KEY_TO_FIELD[key]: section[key]
        for key in applied_setting_keys
        if key in section
    }
    return _apply_field_values(settings, values, context)


def _validate_config_section_keys(
    section: dict[str, Any],
    context: str,
    allowed_keys: frozenset[str],
) -> None:
    """Reject unknown keys in one TOML configuration section."""
    unknown_keys = sorted(str(key) for key in section if key not in allowed_keys)
    if unknown_keys:
        joined_keys = ", ".join(unknown_keys)
        raise ConfigError(f"{context} contains unknown setting(s): {joined_keys}")


def _validate_config_section_values(
    section: dict[str, Any],
    context: str,
    setting_keys: frozenset[str],
) -> None:
    """Validate known setting values in one TOML configuration section."""
    values = {
        _KEY_TO_FIELD[key]: section[key] for key in setting_keys if key in section
    }
    _apply_field_values(FormatterSettings(), values, context)


def _apply_overrides(
    settings: FormatterSettings,
    overrides: SettingsOverrides | None,
    context: str,
) -> FormatterSettings:
    """Apply non-None values from an override layer to formatter settings."""
    if overrides is None:
        return settings

    values = {
        field.name: value
        for field in fields(SettingsOverrides)
        if (value := getattr(overrides, field.name)) is not None
    }
    return _apply_field_values(settings, values, context)


def _apply_field_values(
    settings: FormatterSettings,
    values: dict[str, Any],
    context: str,
) -> FormatterSettings:
    """Validate raw field values and return settings with those fields replaced."""
    updates = {
        field: _SETTING_VALIDATORS[field](
            value,
            f"{context}.{_FIELD_TO_KEY[field]}",
        )
        for field, value in values.items()
    }
    return replace(settings, **updates)


def _validate_line_length(value: Any, context: str) -> int:
    """Validate and return a configured maximum line length."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{context} must be an integer")
    if not 0 < value <= 320:
        raise ConfigError(
            f"{context} must be greater than 0 and less than or equal to 320"
        )
    return int(value)


def _validate_indent_style(value: Any, context: str) -> IndentStyle:
    """Validate and return a configured indentation style."""
    if value == "space":
        return "space"
    if value == "tab":
        return "tab"
    raise ConfigError(f"{context} must be either 'space' or 'tab'")


def _validate_indent_width(value: Any, context: str) -> int:
    """Validate and return a configured indentation width."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{context} must be an integer")
    if not 0 < value <= 255:
        raise ConfigError(
            f"{context} must be greater than 0 and less than or equal to 255"
        )
    return int(value)


def _validate_bool(value: Any, context: str) -> bool:
    """Validate and return a boolean setting value."""
    if not isinstance(value, bool):
        raise ConfigError(f"{context} must be a boolean")
    return value


def _validate_string_list(value: Any, context: str) -> tuple[str, ...]:
    """Validate and return a tuple of string list values."""
    if not isinstance(value, (list, tuple)):
        raise ConfigError(f"{context} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{context} must be a list of strings")
    return tuple(value)


def _validate_include_string_list(value: Any, context: str) -> tuple[str, ...]:
    """Validate include glob settings and return them as a tuple."""
    patterns = _validate_string_list(value, context)
    try:
        validate_include_patterns(patterns)
    except GlobPatternError as error:
        raise ConfigError(f"{context}: {error}") from error
    return patterns


def _validate_exclude_string_list(value: Any, context: str) -> tuple[str, ...]:
    """Validate exclude glob settings and return them as a tuple."""
    patterns = _validate_string_list(value, context)
    try:
        validate_exclude_patterns(patterns)
    except GlobPatternError as error:
        raise ConfigError(f"{context}: {error}") from error
    return patterns


_SETTING_VALIDATORS: dict[str, Callable[[Any, str], Any]] = {
    "line_length": _validate_line_length,
    "indent_style": _validate_indent_style,
    "indent_width": _validate_indent_width,
    "respect_gitignore": _validate_bool,
    "force_exclude": _validate_bool,
    "include": _validate_include_string_list,
    "extend_include": _validate_include_string_list,
    "exclude": _validate_exclude_string_list,
    "extend_exclude": _validate_exclude_string_list,
}
