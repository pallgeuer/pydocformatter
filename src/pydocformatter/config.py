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
    "respect-gitignore": "respect_gitignore",
    "force-exclude": "force_exclude",
    "include": "include",
    "extend-include": "extend_include",
    "exclude": "exclude",
    "extend-exclude": "extend_exclude",
}
_FIELD_TO_KEY = {field: key for key, field in _KEY_TO_FIELD.items()}
_ALLOWED_SETTING_KEYS = frozenset(_KEY_TO_FIELD)


class ConfigError(ValueError):
    """Raised when pydocformatter configuration is invalid."""


@dataclass(frozen=True)
class FormatterSettings:
    """Resolved settings shared by pydocfmt and pycommentfmt."""

    line_length: int = 88
    respect_gitignore: bool = True
    force_exclude: bool = False
    include: tuple[str, ...] = DEFAULT_INCLUDE
    extend_include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    extend_exclude: tuple[str, ...] = ()

    @property
    def include_patterns(self) -> tuple[str, ...]:
        """Return final include patterns used by file selection."""
        return self.include + self.extend_include

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Return final exclude patterns used by file selection."""
        return self.exclude + self.extend_exclude


@dataclass(frozen=True)
class SettingsOverrides:
    """Optional settings from one precedence layer."""

    line_length: int | None = None
    respect_gitignore: bool | None = None
    force_exclude: bool | None = None
    include: tuple[str, ...] | None = None
    extend_include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None
    extend_exclude: tuple[str, ...] | None = None


def load_config(tool_name: ToolName) -> FormatterSettings:
    """Load resolved pyproject configuration for one formatter tool."""
    return resolve_settings(tool_name)


def resolve_settings(
    tool_name: ToolName,
    cli_overrides: SettingsOverrides | None = None,
) -> FormatterSettings:
    """Resolve settings from defaults, pyproject config, and CLI overrides."""
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
            allow_tool_tables=True,
        )

        if tool_name in formatter_config:
            tool_specific = formatter_config[tool_name]
            if not isinstance(tool_specific, dict):
                raise ConfigError(f"tool.pydocformatter.{tool_name} must be a table")
            settings = _apply_config_section(
                settings,
                tool_specific,
                f"tool.pydocformatter.{tool_name}",
                allow_tool_tables=False,
            )

    return _apply_overrides(settings, cli_overrides, "command line")


def apply_cli_overrides(
    settings: FormatterSettings,
    cli_overrides: SettingsOverrides,
) -> FormatterSettings:
    """Apply command-line overrides to already-resolved config settings."""
    return _apply_overrides(settings, cli_overrides, "command line")


def _load_pyproject_config() -> dict[str, Any]:
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
    if tool_name not in TOOL_NAMES:
        raise ConfigError("tool_name must be either 'pydocfmt' or 'pycommentfmt'")


def _apply_config_section(
    settings: FormatterSettings,
    section: dict[str, Any],
    context: str,
    *,
    allow_tool_tables: bool,
) -> FormatterSettings:
    allowed_keys = set(_ALLOWED_SETTING_KEYS)
    if allow_tool_tables:
        allowed_keys.update(TOOL_NAMES)

    unknown_keys = sorted(str(key) for key in section if key not in allowed_keys)
    if unknown_keys:
        joined_keys = ", ".join(unknown_keys)
        raise ConfigError(f"{context} contains unknown setting(s): {joined_keys}")

    values = {
        _KEY_TO_FIELD[key]: section[key] for key in _KEY_TO_FIELD if key in section
    }
    return _apply_field_values(settings, values, context)


def _apply_overrides(
    settings: FormatterSettings,
    overrides: SettingsOverrides | None,
    context: str,
) -> FormatterSettings:
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
    updates = {
        field: _SETTING_VALIDATORS[field](
            value,
            f"{context}.{_FIELD_TO_KEY[field]}",
        )
        for field, value in values.items()
    }
    return replace(settings, **updates)


def _validate_line_length(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{context} must be an integer")
    if not 0 < value <= 320:
        raise ConfigError(
            f"{context} must be greater than 0 and less than or equal to 320"
        )
    return int(value)


def _validate_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{context} must be a boolean")
    return value


def _validate_string_list(value: Any, context: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ConfigError(f"{context} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{context} must be a list of strings")
    return tuple(value)


def _validate_include_string_list(value: Any, context: str) -> tuple[str, ...]:
    patterns = _validate_string_list(value, context)
    try:
        validate_include_patterns(patterns)
    except GlobPatternError as error:
        raise ConfigError(f"{context}: {error}") from error
    return patterns


def _validate_exclude_string_list(value: Any, context: str) -> tuple[str, ...]:
    patterns = _validate_string_list(value, context)
    try:
        validate_exclude_patterns(patterns)
    except GlobPatternError as error:
        raise ConfigError(f"{context}: {error}") from error
    return patterns


_SETTING_VALIDATORS: dict[str, Callable[[Any, str], Any]] = {
    "line_length": _validate_line_length,
    "respect_gitignore": _validate_bool,
    "force_exclude": _validate_bool,
    "include": _validate_include_string_list,
    "extend_include": _validate_include_string_list,
    "exclude": _validate_exclude_string_list,
    "extend_exclude": _validate_exclude_string_list,
}
