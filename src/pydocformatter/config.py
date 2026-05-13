import argparse
import dataclasses
import json
import os
import tomllib
from collections.abc import Callable
from typing import Any, Literal

import pydocformatter.rules as rules

IndentStyle = Literal["space", "tab"]
LineEnding = Literal["auto", "lf", "cr-lf", "native"]
OutputFormat = Literal["grouped"]
RuleSelectorMap = tuple[tuple[str, tuple[str, ...]], ...]
ConfigOptionKind = Literal["path", "inline"]

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
DEFAULT_RULE_SELECT = (rules.ALL_RULE_CODE,)
DEFAULT_RULE_FIXABLE = (rules.ALL_RULE_CODE,)


def add_global_arguments(parser: argparse.ArgumentParser, *, dest_prefix: str) -> None:
    """Add global configuration arguments to a parser."""
    global_options = parser.add_argument_group("Global options")
    global_options.add_argument(
        "--config",
        action="append",
        default=None,
        dest=f"{dest_prefix}_config",
        metavar="CONFIG",
        help="Path to a TOML configuration file or TOML '<KEY> = <VALUE>' override.",
    )
    global_options.add_argument(
        "--isolated",
        action="store_true",
        default=False,
        dest=f"{dest_prefix}_isolated",
        help="Ignore all configuration files.",
    )


def _key_to_field(key: str) -> str:
    """Return the settings field name for a TOML setting key."""
    return key.replace("-", "_")


def _field_to_key(field: str) -> str:
    """Return the TOML setting key for a settings field name."""
    return field.replace("_", "-")


def _enabled_label(value: bool) -> str:
    """Return a human-readable enabled state."""
    return "enabled" if value else "disabled"


_RULE_SELECTOR_FIELDS = frozenset(
    {
        "select",
        "ignore",
        "extend_select",
        "fixable",
        "unfixable",
        "extend_fixable",
    }
)
_RULE_SELECTOR_MAP_FIELDS = frozenset({"per_file_ignores", "extend_per_file_ignores"})


class ConfigError(ValueError):
    """Raised when pydocformatter configuration cannot be resolved or validated.

    This exception represents user-facing configuration failures, including malformed TOML, unsupported table shapes,
    unknown setting keys, and invalid setting values.
    """


@dataclasses.dataclass(frozen=True)
class FormatterSettings:
    """Resolved formatter settings for pydocformatter.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        experimental (bool): Whether to use the experimental rule-based formatter implementation.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated docstring section indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        select (tuple[str, ...]): Base selected pydocformatter rule selectors.
        ignore (tuple[str, ...]): Rule selectors to ignore.
        extend_select (tuple[str, ...]): Additional selected rule selectors.
        per_file_ignores (RuleSelectorMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (RuleSelectorMap): Additional file-specific ignores.
        fixable (tuple[str, ...]): Rule selectors eligible for automatic fixes.
        unfixable (tuple[str, ...]): Rule selectors ineligible for automatic fixes.
        extend_fixable (tuple[str, ...]): Additional fixable rule selectors.
        include (tuple[str, ...]): Base glob patterns that identify format-eligible files.
        extend_include (tuple[str, ...]): Additional include glob patterns appended to `include`.
        exclude (tuple[str, ...]): Base glob patterns for files or directories to ignore.
        extend_exclude (tuple[str, ...]): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether include, exclude, and gitignore rules apply to explicitly passed paths.
    """

    output_format: OutputFormat = "grouped"
    experimental: bool = False
    line_length: int = 88
    line_ending: LineEnding = "auto"
    indent_style: IndentStyle = "space"
    indent_width: int = 4
    select: tuple[str, ...] = DEFAULT_RULE_SELECT
    ignore: tuple[str, ...] = ()
    extend_select: tuple[str, ...] = ()
    per_file_ignores: RuleSelectorMap = ()
    extend_per_file_ignores: RuleSelectorMap = ()
    fixable: tuple[str, ...] = DEFAULT_RULE_FIXABLE
    unfixable: tuple[str, ...] = ()
    extend_fixable: tuple[str, ...] = ()
    include: tuple[str, ...] = DEFAULT_INCLUDE
    extend_include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    extend_exclude: tuple[str, ...] = ()
    respect_gitignore: bool = True
    force_exclude: bool = False

    @property
    def include_patterns(self) -> tuple[str, ...]:
        """Return the final include patterns used by file selection."""
        return self.include + self.extend_include

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Return the final exclude patterns used by file selection."""
        return self.exclude + self.extend_exclude


@dataclasses.dataclass(frozen=True)
class SettingsOverrides:
    """Optional formatter settings from one precedence layer."""

    output_format: OutputFormat | None = None
    experimental: bool | None = None
    line_length: int | None = None
    line_ending: LineEnding | None = None
    indent_style: IndentStyle | None = None
    indent_width: int | None = None
    select: tuple[str, ...] | None = None
    ignore: tuple[str, ...] | None = None
    extend_select: tuple[str, ...] | None = None
    per_file_ignores: RuleSelectorMap | None = None
    extend_per_file_ignores: RuleSelectorMap | None = None
    fixable: tuple[str, ...] | None = None
    unfixable: tuple[str, ...] | None = None
    extend_fixable: tuple[str, ...] | None = None
    include: tuple[str, ...] | None = None
    extend_include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None
    extend_exclude: tuple[str, ...] | None = None
    respect_gitignore: bool | None = None
    force_exclude: bool | None = None


_SETTING_KEYS = tuple(_field_to_key(field.name) for field in dataclasses.fields(FormatterSettings))


def load_config(
    cli_overrides: SettingsOverrides | None = None,
    *,
    config_options: tuple[str, ...] = (),
    isolated: bool = False,
) -> FormatterSettings:
    """Resolve settings from defaults, config files, inline config, and optional CLI overrides."""
    settings = FormatterSettings()

    classified_options = tuple((_classify_config_option(option), option) for option in config_options)
    if isolated:
        path_options = [option for kind, option in classified_options if kind == "path"]
        if path_options:
            raise ConfigError("The argument --config=PATH cannot be used with --isolated")

    if not isolated:
        settings = _apply_pyproject_config(settings)

    for kind, option in classified_options:
        if kind == "path":
            settings = _apply_explicit_config_file(settings, option)
    for kind, option in classified_options:
        if kind == "inline":
            settings = _apply_inline_config_option(settings, option)

    return _apply_overrides(settings, cli_overrides, "command line")


def format_settings(settings: FormatterSettings) -> str:
    """Return resolved settings in a stable TOML-like form."""
    lines = ["[tool.pydocfmt]"]
    for field in dataclasses.fields(FormatterSettings):
        key = _field_to_key(field.name)
        value = getattr(settings, field.name)
        if field.name in _RULE_SELECTOR_MAP_FIELDS:
            rendered = _format_rule_selector_map(value)
        elif isinstance(value, tuple):
            rendered = _format_string_list(value)
        elif isinstance(value, str):
            rendered = _format_string(value)
        elif isinstance(value, bool):
            rendered = str(value).lower()
        else:
            rendered = str(value)
        lines.append(f"{key} = {rendered}")
    lines.append("")
    return "\n".join(lines)


def _format_rule_selector_map(value: RuleSelectorMap) -> str:
    """Format a rule selector mapping as a TOML inline table."""
    entries = [f"{_format_string(pattern)} = {_format_string_list(selectors)}" for pattern, selectors in value]
    return "{" + ", ".join(entries) + "}"


def _format_string_list(values: tuple[str, ...]) -> str:
    """Format string values as a TOML list."""
    return "[" + ", ".join(_format_string(value) for value in values) + "]"


def _format_string(value: str) -> str:
    """Format a string value for TOML output."""
    return json.dumps(value)


def _apply_pyproject_config(settings: FormatterSettings) -> FormatterSettings:
    """Apply auto-discovered pyproject.toml configuration from the current directory."""
    config = _load_toml_file("pyproject.toml", required=False)
    tool_config = config.get("tool", {})
    if not isinstance(tool_config, dict):
        if "tool" in config:
            raise ConfigError("The [tool] section of pyproject.toml must be a table")
        return settings

    if "pydocfmt" in tool_config:
        formatter_config = tool_config["pydocfmt"]
        if not isinstance(formatter_config, dict):
            raise ConfigError("The [tool.pydocfmt] section must be a table")
        settings = _apply_config_section(settings, formatter_config, "tool.pydocfmt")

    return settings


def _apply_explicit_config_file(settings: FormatterSettings, path: str) -> FormatterSettings:
    """Apply one explicit config file from --config PATH."""
    config = _load_toml_file(path, required=True)
    if os.path.basename(path) == "pyproject.toml" or "tool" in config:
        return _apply_explicit_pyproject_config(settings, config, path)
    return _apply_config_section(settings, config, path)


def _apply_explicit_pyproject_config(
    settings: FormatterSettings,
    config: dict[str, Any],
    path: str,
) -> FormatterSettings:
    """Apply one explicit pyproject-style config file from --config PATH."""
    tool_config = config.get("tool", {})
    if not isinstance(tool_config, dict):
        if "tool" in config:
            raise ConfigError(f"{path}: The [tool] section must be a table")
        raise ConfigError(f"{path}: Must contain [tool.pydocfmt]")

    formatter_config = tool_config.get("pydocfmt")
    if formatter_config is None:
        raise ConfigError(f"{path}: Must contain [tool.pydocfmt]")
    if not isinstance(formatter_config, dict):
        raise ConfigError(f"{path}: The [tool.pydocfmt] section must be a table")
    return _apply_config_section(settings, formatter_config, f"{path}.tool.pydocfmt")


def _apply_inline_config_option(settings: FormatterSettings, option: str) -> FormatterSettings:
    """Apply one inline TOML --config option."""
    try:
        section = tomllib.loads(option)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Failed to decode --config inline TOML: {error}") from error
    return _apply_config_section(settings, section, "--config")


def _classify_config_option(option: str) -> ConfigOptionKind:
    """Classify a --config option as a file path or inline TOML setting."""
    if "=" in option and not os.path.exists(option):
        return "inline"
    return "path"


def _load_toml_file(path: str, *, required: bool) -> dict[str, Any]:
    """Load a TOML file, returning an empty config if an optional file is absent."""
    if not os.path.exists(path):
        if required:
            raise ConfigError(f"Configuration file not found: {path}")
        return {}

    try:
        file = open(path, "rb")
    except OSError as error:
        raise ConfigError(f"Failed to read configuration file {path}: {error}") from error

    with file:
        try:
            config = tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"Failed to decode {path}: {error}") from error

    if not isinstance(config, dict):
        raise ConfigError(f"{path}: Must contain a TOML table")
    return config


def _apply_config_section(
    settings: FormatterSettings,
    section: dict[str, Any],
    context: str,
) -> FormatterSettings:
    """Apply one TOML configuration section after validating allowed keys."""
    _validate_config_section_keys(section, context, _SETTING_KEYS)
    _validate_config_section_values(section, context)

    values = {_key_to_field(key): section[key] for key in _SETTING_KEYS if key in section}
    return _apply_field_values(settings, values, context)


def _validate_config_section_keys(
    section: dict[str, Any],
    context: str,
    allowed_keys: tuple[str, ...],
) -> None:
    """Reject unknown keys in one TOML configuration section."""
    unknown_keys = sorted(str(key) for key in section if key not in allowed_keys)
    if unknown_keys:
        joined_keys = ", ".join(unknown_keys)
        raise ConfigError(f"{context} contains unknown setting(s): {joined_keys}")


def _validate_config_section_values(
    section: dict[str, Any],
    context: str,
) -> None:
    """Validate known setting values in one TOML configuration section."""
    values = {_key_to_field(key): section[key] for key in _SETTING_KEYS if key in section}
    _apply_field_values(FormatterSettings(), values, context)


def _apply_overrides(
    settings: FormatterSettings,
    overrides: SettingsOverrides | None,
    context: str,
) -> FormatterSettings:
    """Apply non-None values from an override layer to formatter settings."""
    if overrides is None:
        return settings

    values = {field.name: value for field in dataclasses.fields(SettingsOverrides) if (value := getattr(overrides, field.name)) is not None}
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
            f"{context}.{_field_to_key(field)}",
        )
        for field, value in values.items()
    }
    _validate_rule_selectors(updates, context)
    return dataclasses.replace(settings, **updates)


def _validate_line_length(value: Any, context: str) -> int:
    """Validate and return a configured maximum line length."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{context} must be an integer")
    if not 0 < value <= 320:
        raise ConfigError(f"{context} must be greater than 0 and less than or equal to 320")
    return int(value)


def _validate_indent_style(value: Any, context: str) -> IndentStyle:
    """Validate and return a configured indentation style."""
    if value == "space":
        return "space"
    if value == "tab":
        return "tab"
    raise ConfigError(f"{context} must be either 'space' or 'tab'")


def _validate_line_ending(value: Any, context: str) -> LineEnding:
    """Validate and return a configured line ending style."""
    if value == "auto":
        return "auto"
    if value == "lf":
        return "lf"
    if value == "cr-lf":
        return "cr-lf"
    if value == "native":
        return "native"
    raise ConfigError(f"{context} must be one of 'auto', 'lf', 'cr-lf', or 'native'")


def _validate_indent_width(value: Any, context: str) -> int:
    """Validate and return a configured indentation width."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{context} must be an integer")
    if not 0 < value <= 255:
        raise ConfigError(f"{context} must be greater than 0 and less than or equal to 255")
    return int(value)


def _validate_bool(value: Any, context: str) -> bool:
    """Validate and return a boolean setting value."""
    if not isinstance(value, bool):
        raise ConfigError(f"{context} must be a boolean")
    return value


def _validate_output_format(value: Any, context: str) -> OutputFormat:
    """Validate and return a configured output format."""
    if value == "grouped":
        return "grouped"
    raise ConfigError(f"{context} must be 'grouped'")


def _validate_string_list(value: Any, context: str) -> tuple[str, ...]:
    """Validate and return a tuple of string list values."""
    if not isinstance(value, (list, tuple)):
        raise ConfigError(f"{context} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{context} must be a list of strings")
    return tuple(value)


def _validate_non_empty_string_list(value: Any, context: str) -> tuple[str, ...]:
    """Validate and return a tuple of non-empty string list values."""
    patterns = _validate_string_list(value, context)
    if any(not pattern for pattern in patterns):
        raise ConfigError(f"{context} must not contain empty strings")
    return patterns


def _validate_selector_list(value: Any, context: str) -> tuple[str, ...]:
    """Validate rule selectors and return them as a tuple."""
    selectors = _validate_string_list(value, context)
    if any(not selector for selector in selectors):
        raise ConfigError(f"{context} must not contain empty selectors")
    return selectors


def _validate_selector_mapping(value: Any, context: str) -> RuleSelectorMap:
    """Validate per-file rule selector mappings."""
    if isinstance(value, tuple):
        items = value
    elif isinstance(value, dict):
        items = tuple(value.items())
    else:
        raise ConfigError(f"{context} must be a table mapping file patterns to selectors")

    entries = []
    for pattern, selectors in items:
        if not isinstance(pattern, str):
            raise ConfigError(f"{context} file patterns must be strings")
        if not pattern:
            raise ConfigError(f"{context} file patterns must not be empty")
        entries.append((pattern, _validate_selector_list(selectors, f"{context}.{pattern}")))
    return tuple(entries)


def _validate_rule_selectors(
    values: dict[str, Any],
    context: str,
) -> None:
    """Validate rule selectors against the known rule scope."""
    selector_values = [(field, selector) for field, selectors in values.items() if field in _RULE_SELECTOR_FIELDS for selector in selectors]
    selector_values.extend((field, selector) for field, mapping in values.items() if field in _RULE_SELECTOR_MAP_FIELDS for _, selectors in mapping for selector in selectors)

    for field, selector in selector_values:
        if not rules.selector_matches_known_rule(selector):
            key = _field_to_key(field)
            raise ConfigError(f"{context}.{key} contains unknown selector: {selector}")


_SETTING_VALIDATORS: dict[str, Callable[[Any, str], Any]] = {
    "output_format": _validate_output_format,
    "experimental": _validate_bool,
    "line_length": _validate_line_length,
    "line_ending": _validate_line_ending,
    "indent_style": _validate_indent_style,
    "indent_width": _validate_indent_width,
    "select": _validate_selector_list,
    "ignore": _validate_selector_list,
    "extend_select": _validate_selector_list,
    "per_file_ignores": _validate_selector_mapping,
    "extend_per_file_ignores": _validate_selector_mapping,
    "fixable": _validate_selector_list,
    "unfixable": _validate_selector_list,
    "extend_fixable": _validate_selector_list,
    "include": _validate_non_empty_string_list,
    "extend_include": _validate_non_empty_string_list,
    "exclude": _validate_non_empty_string_list,
    "extend_exclude": _validate_non_empty_string_list,
    "respect_gitignore": _validate_bool,
    "force_exclude": _validate_bool,
}
