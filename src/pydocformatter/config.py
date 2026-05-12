import dataclasses
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

_KEY_TO_FIELD = {
    "line-length": "line_length",
    "line-ending": "line_ending",
    "indent-style": "indent_style",
    "indent-width": "indent_width",
    "include": "include",
    "extend-include": "extend_include",
    "exclude": "exclude",
    "extend-exclude": "extend_exclude",
    "respect-gitignore": "respect_gitignore",
    "force-exclude": "force_exclude",
    "experimental": "experimental",
    "output-format": "output_format",
    "select": "select",
    "extend-select": "extend_select",
    "ignore": "ignore",
    "fixable": "fixable",
    "extend-fixable": "extend_fixable",
    "unfixable": "unfixable",
    "per-file-ignores": "per_file_ignores",
    "extend-per-file-ignores": "extend_per_file_ignores",
}
_FIELD_TO_KEY = {field: key for key, field in _KEY_TO_FIELD.items()}
_SETTING_KEYS = frozenset(_KEY_TO_FIELD)
_RULE_SELECTOR_FIELDS = frozenset(
    {
        "select",
        "extend_select",
        "ignore",
        "fixable",
        "extend_fixable",
        "unfixable",
    }
)
_RULE_SELECTOR_MAP_FIELDS = frozenset({"per_file_ignores", "extend_per_file_ignores"})
_RULE_SETTING_KEYS = frozenset(
    {
        "select",
        "extend-select",
        "ignore",
        "fixable",
        "extend-fixable",
        "unfixable",
        "per-file-ignores",
        "extend-per-file-ignores",
    }
)


class ConfigError(ValueError):
    """Raised when pydocformatter configuration cannot be resolved or validated.

    This exception represents user-facing configuration failures, including malformed TOML, unsupported table shapes,
    unknown setting keys, and invalid setting values.
    """


@dataclasses.dataclass(frozen=True)
class FormatterSettings:
    """Resolved formatter settings for pydocformatter.

    Attributes:
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated docstring section indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        include (tuple[str, ...]): Base glob patterns that identify format-eligible files.
        extend_include (tuple[str, ...]): Additional include glob patterns appended to `include`.
        exclude (tuple[str, ...]): Base glob patterns for files or directories to ignore.
        extend_exclude (tuple[str, ...]): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether include, exclude, and gitignore rules apply to explicitly passed paths.
        experimental (bool): Whether to use the experimental rule-based formatter implementation.
        output_format (OutputFormat): Output format used for rule findings.
        select (tuple[str, ...]): Base selected pydocformatter rule selectors.
        extend_select (tuple[str, ...]): Additional selected rule selectors.
        ignore (tuple[str, ...]): Rule selectors to ignore.
        fixable (tuple[str, ...]): Rule selectors eligible for automatic fixes.
        extend_fixable (tuple[str, ...]): Additional fixable rule selectors.
        unfixable (tuple[str, ...]): Rule selectors ineligible for automatic fixes.
        per_file_ignores (RuleSelectorMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (RuleSelectorMap): Additional file-specific ignores.
    """

    line_length: int = 88
    line_ending: LineEnding = "auto"
    indent_style: IndentStyle = "space"
    indent_width: int = 4
    include: tuple[str, ...] = DEFAULT_INCLUDE
    extend_include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    extend_exclude: tuple[str, ...] = ()
    respect_gitignore: bool = True
    force_exclude: bool = False
    experimental: bool = False
    output_format: OutputFormat = "grouped"
    select: tuple[str, ...] = DEFAULT_RULE_SELECT
    extend_select: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    fixable: tuple[str, ...] = DEFAULT_RULE_FIXABLE
    extend_fixable: tuple[str, ...] = ()
    unfixable: tuple[str, ...] = ()
    per_file_ignores: RuleSelectorMap = ()
    extend_per_file_ignores: RuleSelectorMap = ()

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

    line_length: int | None = None
    line_ending: LineEnding | None = None
    indent_style: IndentStyle | None = None
    indent_width: int | None = None
    include: tuple[str, ...] | None = None
    extend_include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None
    extend_exclude: tuple[str, ...] | None = None
    respect_gitignore: bool | None = None
    force_exclude: bool | None = None
    experimental: bool | None = None
    output_format: OutputFormat | None = None
    select: tuple[str, ...] | None = None
    extend_select: tuple[str, ...] | None = None
    ignore: tuple[str, ...] | None = None
    fixable: tuple[str, ...] | None = None
    extend_fixable: tuple[str, ...] | None = None
    unfixable: tuple[str, ...] | None = None
    per_file_ignores: RuleSelectorMap | None = None
    extend_per_file_ignores: RuleSelectorMap | None = None


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
            raise ConfigError("the argument --config=PATH cannot be used with --isolated")

    if not isolated:
        settings = _apply_pyproject_config(settings)

    for kind, option in classified_options:
        if kind == "path":
            settings = _apply_explicit_config_file(settings, option)
    for kind, option in classified_options:
        if kind == "inline":
            settings = _apply_inline_config_option(settings, option)

    return _apply_overrides(settings, cli_overrides, "command line")


def _apply_pyproject_config(settings: FormatterSettings) -> FormatterSettings:
    """Apply auto-discovered pyproject.toml configuration from the current directory."""
    config = _load_toml_file("pyproject.toml", required=False)
    tool_config = config.get("tool", {})
    if not isinstance(tool_config, dict):
        if "tool" in config:
            raise ConfigError("pyproject.toml [tool] must be a table")
        return settings

    if "pydocfmt" in tool_config:
        formatter_config = tool_config["pydocfmt"]
        if not isinstance(formatter_config, dict):
            raise ConfigError("tool.pydocfmt must be a table")
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
            raise ConfigError(f"{path} [tool] must be a table")
        raise ConfigError(f"{path} must contain [tool.pydocfmt]")

    formatter_config = tool_config.get("pydocfmt")
    if formatter_config is None:
        raise ConfigError(f"{path} must contain [tool.pydocfmt]")
    if not isinstance(formatter_config, dict):
        raise ConfigError(f"{path} tool.pydocfmt must be a table")
    return _apply_config_section(settings, formatter_config, f"{path}.tool.pydocfmt")


def _apply_inline_config_option(settings: FormatterSettings, option: str) -> FormatterSettings:
    """Apply one inline TOML --config option."""
    try:
        section = tomllib.loads(option)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"failed to decode --config inline TOML: {error}") from error
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
            raise ConfigError(f"configuration file not found: {path}")
        return {}

    try:
        file = open(path, "rb")
    except OSError as error:
        raise ConfigError(f"failed to read configuration file {path}: {error}") from error

    with file:
        try:
            config = tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"failed to decode {path}: {error}") from error

    if not isinstance(config, dict):
        raise ConfigError(f"{path} must contain a TOML table")
    return config


def _apply_config_section(
    settings: FormatterSettings,
    section: dict[str, Any],
    context: str,
) -> FormatterSettings:
    """Apply one TOML configuration section after validating allowed keys."""
    _validate_config_section_keys(section, context, _SETTING_KEYS)
    _validate_config_section_values(section, context)

    values = {_KEY_TO_FIELD[key]: section[key] for key in _SETTING_KEYS if key in section}
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
) -> None:
    """Validate known setting values in one TOML configuration section."""
    values = {_KEY_TO_FIELD[key]: section[key] for key in _SETTING_KEYS if key in section}
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
            f"{context}.{_FIELD_TO_KEY[field]}",
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
            key = _FIELD_TO_KEY[field]
            raise ConfigError(f"{context}.{key} contains unknown selector: {selector}")


_SETTING_VALIDATORS: dict[str, Callable[[Any, str], Any]] = {
    "line_length": _validate_line_length,
    "line_ending": _validate_line_ending,
    "indent_style": _validate_indent_style,
    "indent_width": _validate_indent_width,
    "include": _validate_non_empty_string_list,
    "extend_include": _validate_non_empty_string_list,
    "exclude": _validate_non_empty_string_list,
    "extend_exclude": _validate_non_empty_string_list,
    "respect_gitignore": _validate_bool,
    "force_exclude": _validate_bool,
    "experimental": _validate_bool,
    "output_format": _validate_output_format,
    "select": _validate_selector_list,
    "extend_select": _validate_selector_list,
    "ignore": _validate_selector_list,
    "fixable": _validate_selector_list,
    "extend_fixable": _validate_selector_list,
    "unfixable": _validate_selector_list,
    "per_file_ignores": _validate_selector_mapping,
    "extend_per_file_ignores": _validate_selector_mapping,
}
