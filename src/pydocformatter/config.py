from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import os
import tomllib
from collections.abc import Callable, Iterable, Mapping
from types import GenericAlias
from typing import Any, Generic, TypeAlias, TypedDict, TypeVar, cast

from pydocformatter.cli.global_args import GlobalArgs

SettingsT = TypeVar("SettingsT")
StrEnumT = TypeVar("StrEnumT", bound=enum.StrEnum)
SettingValueT = TypeVar("SettingValueT")
StringList: TypeAlias = tuple[str, ...]
MultiStringMap: TypeAlias = tuple[tuple[str, StringList], ...]
SettingValidator: TypeAlias = Callable[[Any, str], SettingValueT]
SettingCLIAction: TypeAlias = str | type[argparse.Action]
SettingCLIChoices: TypeAlias = Iterable[Any]
SettingCLIType: TypeAlias = Callable[[str], Any] | argparse.FileType | str
SettingCLIMetavar: TypeAlias = str | tuple[str, ...]
SettingsOverridesType: TypeAlias = type[Any] | GenericAlias


class ConfigError(ValueError):
    """Raised when configuration cannot be resolved or validated.

    This exception represents user-facing configuration failures, including malformed TOML, unsupported table shapes,
    unknown setting keys, and invalid setting values.
    """


class ConfigOptionKind(enum.StrEnum):
    """Kinds of --config options."""

    PATH = "path"
    INLINE = "inline"


class SettingCLIValueKind(enum.StrEnum):
    """CLI value parsing strategy for a setting."""

    RAW = "raw"
    COMMA_LIST = "comma-list"
    TOML_MAP = "toml-map"


class SettingCLIOptions(TypedDict, total=False):
    """Unresolved argparse metadata for one setting."""

    flags: tuple[str, ...]
    action: SettingCLIAction | None
    choices: SettingCLIChoices | None
    type: SettingCLIType | None
    metavar: SettingCLIMetavar | None
    value_kind: SettingCLIValueKind
    show_default: bool


@dataclasses.dataclass(frozen=True)
class SettingCLIDefinition:
    """Resolved argparse metadata for one setting."""

    flags: tuple[str, ...] = ()
    action: SettingCLIAction | None = None
    choices: SettingCLIChoices | None = None
    type: SettingCLIType | None = None
    metavar: SettingCLIMetavar | None = None
    value_kind: SettingCLIValueKind = SettingCLIValueKind.RAW
    show_default: bool = True


@dataclasses.dataclass(frozen=True, init=False)
class SettingDefinition(Generic[SettingValueT]):
    """Central metadata for one setting."""

    field: str
    value_type: type[SettingValueT] | GenericAlias
    group: enum.StrEnum
    help: str
    key: str = ""
    available_in_cli: bool = True
    available_in_toml: bool = True
    validator: SettingValidator[SettingValueT] | None = None
    cli: SettingCLIDefinition | None = None
    documentation: str = ""

    def __init__(
        self,
        *,
        field: str,
        value_type: type[SettingValueT] | GenericAlias,
        group: enum.StrEnum,
        help: str,
        key: str = "",
        available_in_cli: bool = True,
        available_in_toml: bool = True,
        validator: SettingValidator[SettingValueT] | None = None,
        cli: SettingCLIOptions | SettingCLIDefinition | dict[str, Any] | None = None,
        documentation: str | None = None,
    ) -> None:
        """Initialize setting metadata with derived defaults."""
        resolved_key = key or field.replace("_", "-")
        resolved_validator = cast(SettingValidator[SettingValueT], _default_validator_for_type(value_type)) if validator is None else validator
        resolved_documentation = documentation or help

        resolved_cli: SettingCLIDefinition | None
        if available_in_cli:
            if cli is None:
                cli_options: SettingCLIOptions = {}
            elif isinstance(cli, SettingCLIDefinition):
                cli_options = cast(SettingCLIOptions, {field.name: getattr(cli, field.name) for field in dataclasses.fields(cli)})
            else:
                cli_options = cast(SettingCLIOptions, dict(cli))

            flags = cli_options.get("flags", ()) or (f"--{resolved_key}",)
            action = cli_options.get("action")
            choices = cli_options.get("choices")
            cli_type = cli_options.get("type")
            metavar = cli_options.get("metavar")
            value_kind = cli_options.get("value_kind", SettingCLIValueKind.RAW)

            if value_type is bool and action is None:
                action = argparse.BooleanOptionalAction
            if value_type is int and cli_type is None:
                cli_type = int
            if value_type == StringList:
                if action is None:
                    action = "append"
                if "value_kind" not in cli_options:
                    value_kind = SettingCLIValueKind.COMMA_LIST
            if value_type == MultiStringMap:
                if action is None:
                    action = "append"
                if "value_kind" not in cli_options:
                    value_kind = SettingCLIValueKind.TOML_MAP
            if _is_str_enum_type(value_type) and choices is None:
                choices = tuple(member.value for member in cast(type[enum.StrEnum], value_type))

            show_default = cli_options.get("show_default", value_kind == SettingCLIValueKind.RAW)

            resolved_cli = SettingCLIDefinition(
                flags=flags,
                action=action,
                choices=choices,
                type=cli_type,
                metavar=metavar,
                value_kind=value_kind,
                show_default=show_default,
            )
        else:
            resolved_cli = None

        object.__setattr__(self, "field", field)
        object.__setattr__(self, "value_type", value_type)
        object.__setattr__(self, "group", group)
        object.__setattr__(self, "help", help)
        object.__setattr__(self, "key", resolved_key)
        object.__setattr__(self, "available_in_cli", available_in_cli)
        object.__setattr__(self, "available_in_toml", available_in_toml)
        object.__setattr__(self, "validator", resolved_validator)
        object.__setattr__(self, "cli", resolved_cli)
        object.__setattr__(self, "documentation", resolved_documentation)


@dataclasses.dataclass(frozen=True)
class SettingsSchema(Generic[SettingsT]):
    """Generic schema describing one dataclass-backed settings object.

    Attributes:
        settings_type: Resolved dataclass type constructed for defaults and returned by config loading.
        overrides_type: TypedDict-like class describing partial field overrides accepted from CLI/config layers.
        group_type: Enum type that defines accepted settings groups and argparse group ordering.
        definitions: Ordered metadata mapping settings dataclass fields to TOML keys, CLI options, validation, and help
            text.
        table_path: TOML table path used for pyproject-style configuration. Empty schemas read top-level TOML tables
            only when explicitly supplied.
        table_name: Dotted TOML table name derived from table_path.
        post_validate: Optional validation hook called after per-field validation with only the updates from the current
            layer, keyed by dataclass field name, and a user-facing context string. The hook should raise ConfigError
            for cross-field or domain validation failures and should not mutate values.
    """

    settings_type: type[SettingsT]
    overrides_type: SettingsOverridesType
    group_type: type[enum.StrEnum]
    definitions: tuple[SettingDefinition[Any], ...]
    table_path: tuple[str, ...]
    table_name: str = dataclasses.field(init=False)
    post_validate: Callable[[dict[str, Any], str], None] | None = None

    def __post_init__(self) -> None:
        """Validate schema group metadata."""
        invalid_definitions = tuple(definition for definition in self.definitions if not isinstance(definition.group, self.group_type))
        if invalid_definitions:
            invalid_fields = ", ".join(f"{definition.field}={definition.group!r}" for definition in invalid_definitions)
            raise TypeError(f"Settings definitions must belong to {self.group_type.__name__}: {invalid_fields}")
        invalid_definitions = tuple(definition for definition in self.definitions if definition.available_in_cli != (definition.cli is not None))
        if invalid_definitions:
            invalid_fields = ", ".join(f"{definition.field}: {definition.available_in_cli}/{definition.cli is not None}" for definition in invalid_definitions)
            raise AssertionError(f"Inconsistent settings definitions found in terms of CLI availability: {invalid_fields}")
        object.__setattr__(self, "table_name", ".".join(self.table_path))

    def definitions_by_field(self) -> dict[str, SettingDefinition[Any]]:
        """Return setting definitions keyed by dataclass field name."""
        return {definition.field: definition for definition in self.definitions}

    def definitions_by_key(self) -> dict[str, SettingDefinition[Any]]:
        """Return setting definitions keyed by TOML setting key."""
        return {definition.key: definition for definition in self.definitions}

    def toml_definitions(self) -> tuple[SettingDefinition[Any], ...]:
        """Return setting definitions available in TOML configuration."""
        return tuple(definition for definition in self.definitions if definition.available_in_toml)

    def toml_keys(self) -> tuple[str, ...]:
        """Return TOML keys accepted by this settings schema."""
        return tuple(definition.key for definition in self.definitions if definition.available_in_toml)

    def cli_definitions(self) -> tuple[SettingDefinition[Any], ...]:
        """Return setting definitions available as dedicated CLI options."""
        return tuple(definition for definition in self.definitions if definition.available_in_cli)

    def cli_keys(self) -> tuple[str, ...]:
        """Return setting keys available as dedicated CLI options."""
        return tuple(definition.key for definition in self.definitions if definition.available_in_cli)

    def cli_flags(self) -> tuple[str, ...]:
        """Return CLI flags accepted by this settings schema."""
        return tuple(flag for definition in self.definitions if definition.cli is not None for flag in definition.cli.flags)

    def load(self, cli_overrides: Mapping[str, Any] | None = None, *, global_args: GlobalArgs = GlobalArgs()) -> SettingsT:
        """Resolve settings from defaults, config files, inline config, and optional CLI overrides."""
        settings = self.settings_type()

        classified_options = tuple((_classify_config_option(option), option) for option in global_args.config_options)
        if global_args.isolated:
            path_options = [option for kind, option in classified_options if kind == ConfigOptionKind.PATH]
            if path_options:
                raise ConfigError("The argument --config=PATH cannot be used with --isolated")

        if not global_args.isolated:
            settings = _apply_pyproject_config(self, settings)

        for kind, option in classified_options:
            if kind == ConfigOptionKind.PATH:
                settings = _apply_explicit_config_file(self, settings, option)
        for kind, option in classified_options:
            if kind == ConfigOptionKind.INLINE:
                settings = _apply_inline_config_option(self, settings, option)

        return settings_from_overrides(self, cli_overrides, base=settings, context="command line")

    def format(self, settings: SettingsT) -> str:
        """Return resolved settings in a stable TOML-like form."""
        lines = [f"[{self.table_name}]"] if self.table_path else []
        for definition in self.definitions:
            if not definition.available_in_toml:
                continue
            value = getattr(settings, definition.field)
            if definition.value_type == MultiStringMap:
                rendered = _format_multi_string_map(value)
            elif definition.value_type == StringList:
                rendered = _format_string_list(value)
            elif definition.value_type is str:
                rendered = _format_string(value)
            elif _is_str_enum_type(definition.value_type):
                rendered = _format_string(value.value)
            elif definition.value_type is bool:
                rendered = str(value).lower()
            else:
                rendered = str(value)
            lines.append(f"{definition.key} = {rendered}")
        lines.append("")
        return "\n".join(lines)

    def add_arguments(self, parser: argparse.ArgumentParser, settings: SettingsT, *, dest_prefix: str | None = None) -> None:
        """Add argparse arguments for every settings group in schema order."""
        handled_definitions: list[SettingDefinition[Any]] = []
        for group in self.group_type:
            argument_group = parser.add_argument_group(group.value)
            for definition in self.definitions:
                if definition.group == group:
                    handled_definitions.append(definition)
                    if definition.available_in_cli:
                        _add_setting_argument(argument_group, definition, settings, dest_prefix=dest_prefix)

        if len(handled_definitions) != len(self.definitions):
            handled_fields = {definition.field for definition in handled_definitions}
            missing_fields = tuple(definition.field for definition in self.definitions if definition.field not in handled_fields)
            raise AssertionError(f"Not all settings definitions were added to argparse groups: {', '.join(missing_fields)}")

    def overrides_from_namespace(self, args: argparse.Namespace, *, dest_prefix: str | None = None) -> dict[str, Any]:
        """Build settings overrides from parsed command-line arguments."""
        values: dict[str, Any] = {}
        for definition in self.definitions:
            if definition.available_in_cli:
                value = getattr(args, _dest_name(definition.field, dest_prefix), None)
                parsed = _parse_cli_setting_value(definition, value)
                if parsed is not None:
                    values[definition.field] = parsed
        return values


def validate_bool(value: Any, context: str) -> bool:
    """Validate and return a boolean setting value."""
    if not isinstance(value, bool):
        raise ConfigError(f"{context} must be a boolean")
    return value


def validate_int(*, min_value: int | None = None, max_value: int | None = None) -> Callable[[Any, str], int]:
    """Return a validator for integer settings with optional inclusive bounds."""

    def validate(value: Any, context: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{context} must be an integer")
        if min_value is not None and value < min_value:
            raise ConfigError(f"{context} must be greater than or equal to {min_value}")
        if max_value is not None and value > max_value:
            raise ConfigError(f"{context} must be less than or equal to {max_value}")
        return value

    return validate


def validate_string_list(value: Any, context: str) -> StringList:
    """Validate and return a tuple of string list values."""
    if not isinstance(value, (list, tuple)):
        raise ConfigError(f"{context} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{context} must be a list of strings")
    return tuple(value)


def validate_non_empty_string_list(value: Any, context: str) -> StringList:
    """Validate and return a tuple of non-empty string list values."""
    values = validate_string_list(value, context)
    if any(not value for value in values):
        raise ConfigError(f"{context} must not contain empty strings")
    return values


def validate_multi_string_map(value: Any, context: str) -> MultiStringMap:
    """Validate and return a mapping of strings to non-empty string lists."""
    if isinstance(value, tuple):
        items = value
    elif isinstance(value, dict):
        items = tuple(value.items())
    else:
        raise ConfigError(f"{context} must be a table mapping strings to string lists")

    entries = []
    for key, values in items:
        if not isinstance(key, str):
            raise ConfigError(f"{context} keys must be strings")
        if not key:
            raise ConfigError(f"{context} keys must not be empty")
        entries.append((key, validate_non_empty_string_list(values, f"{context}.{key}")))
    return tuple(entries)


def validate_str_enum(enum_class: type[StrEnumT]) -> Callable[[Any, str], StrEnumT]:
    """Return a validator that converts setting values to members of a string enum."""

    def validate(value: Any, context: str) -> StrEnumT:
        try:
            return enum_class(value)
        except ValueError as error:
            options = "{" + ", ".join(f"'{member.value}'" for member in enum_class) + "}"
            raise ConfigError(f"{context} must be one of {options}") from error

    return validate


def _default_validator_for_type(setting_type: type[SettingValueT] | GenericAlias) -> Callable[[Any, str], Any]:
    """Return the default validator for a setting type."""
    if setting_type is bool:
        return validate_bool
    elif setting_type is int:
        return validate_int()
    elif setting_type == StringList:
        return validate_string_list
    elif setting_type == MultiStringMap:
        return validate_multi_string_map
    elif _is_str_enum_type(setting_type):
        return validate_str_enum(cast(type[enum.StrEnum], setting_type))
    else:
        raise TypeError(f"No default validator for setting type: {setting_type!r}")


def _is_str_enum_type(setting_type: Any) -> bool:
    """Return whether a setting type is a string enum class."""
    return isinstance(setting_type, type) and issubclass(setting_type, enum.StrEnum)


def settings_from_overrides(
    schema: SettingsSchema[SettingsT],
    overrides: Mapping[str, Any] | None,
    *,
    base: SettingsT | None = None,
    context: str,
) -> SettingsT:
    """Apply non-None override values to a settings instance."""
    settings = schema.settings_type() if base is None else base
    if overrides is None:
        return settings
    return _apply_field_values(schema, settings, dict(overrides), context)


def parse_comma_option_groups(groups: list[str]) -> tuple[str, ...]:
    """Parse repeated comma-separated CLI option groups."""
    return tuple(value.strip() for group in groups for value in group.split(","))


def parse_toml_map_option_groups(groups: list[str]) -> dict[str, Any]:
    """Parse repeated TOML inline-table CLI option groups into one merged dictionary."""
    merged: dict[str, Any] = {}
    for group in groups:
        parsed = tomllib.loads(f"value = {group}")
        value = parsed["value"]
        if not isinstance(value, dict):
            raise ConfigError("TOML map CLI value must be a TOML table")
        merged.update(value)
    return merged


def _enabled_label(value: bool) -> str:
    """Return a human-readable enabled state."""
    return "enabled" if value else "disabled"


def _format_multi_string_map(value: Any) -> str:
    """Format a string-keyed multi-string mapping as a TOML inline table."""
    if isinstance(value, Mapping):
        items = tuple(value.items())
    else:
        items = tuple(value)
    entries = [f"{_format_string(pattern)} = {_format_string_list(selectors)}" for pattern, selectors in items]
    return "{" + ", ".join(entries) + "}"


def _format_string_list(values: tuple[Any, ...]) -> str:
    """Format values as a TOML list."""
    return "[" + ", ".join(_format_string(value.value if isinstance(value, enum.StrEnum) else value) for value in values) + "]"


def _format_string(value: Any) -> str:
    """Format a string value for TOML output."""
    return json.dumps(value)


def _apply_pyproject_config(schema: SettingsSchema[SettingsT], settings: SettingsT) -> SettingsT:
    """Apply auto-discovered pyproject.toml configuration from the current directory."""
    if not schema.table_path:
        return settings

    config = _load_toml_file("pyproject.toml", required=False)
    section = _section_at_table_path(config, schema.table_path, context="pyproject.toml", required=False)
    if section is None:
        return settings
    return _apply_config_section(schema, settings, section, schema.table_name)


def _apply_explicit_config_file(schema: SettingsSchema[SettingsT], settings: SettingsT, path: str) -> SettingsT:
    """Apply one explicit config file from --config PATH."""
    config = _load_toml_file(path, required=True)
    if schema.table_path and (os.path.basename(path) == "pyproject.toml" or schema.table_path[0] in config):
        return _apply_explicit_pyproject_config(schema, settings, config, path)
    return _apply_config_section(schema, settings, config, path)


def _apply_explicit_pyproject_config(
    schema: SettingsSchema[SettingsT],
    settings: SettingsT,
    config: dict[str, Any],
    path: str,
) -> SettingsT:
    """Apply one explicit pyproject-style config file from --config PATH."""
    section = _section_at_table_path(config, schema.table_path, context=path, required=True)
    if section is None:
        raise AssertionError("required=True must return a section or raise ConfigError")
    return _apply_config_section(schema, settings, section, f"{path}.{schema.table_name}")


def _section_at_table_path(
    config: dict[str, Any],
    table_path: tuple[str, ...],
    *,
    context: str,
    required: bool,
) -> dict[str, Any] | None:
    """Return a nested TOML table at the requested path."""
    section: Any = config
    traversed: list[str] = []
    for key in table_path:
        traversed.append(key)
        if not isinstance(section, dict):
            table = ".".join(traversed[:-1])
            raise ConfigError(f"{context}: The [{table}] section must be a table")
        if key not in section:
            if required:
                raise ConfigError(f"{context}: Must contain [{'.'.join(table_path)}]")
            return None
        section = section[key]

    if not isinstance(section, dict):
        if context == "pyproject.toml":
            raise ConfigError(f"The [{'.'.join(table_path)}] section must be a table")
        raise ConfigError(f"{context}: The [{'.'.join(table_path)}] section must be a table")
    return cast(dict[str, Any], section)


def _apply_inline_config_option(schema: SettingsSchema[SettingsT], settings: SettingsT, option: str) -> SettingsT:
    """Apply one inline TOML --config option."""
    try:
        section = tomllib.loads(option)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Failed to decode --config inline TOML: {error}") from error
    return _apply_config_section(schema, settings, section, "--config")


def _classify_config_option(option: str) -> ConfigOptionKind:
    """Classify a --config option as a file path or inline TOML setting."""
    if "=" in option and not os.path.exists(option):
        return ConfigOptionKind.INLINE
    return ConfigOptionKind.PATH


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


def _apply_config_section(schema: SettingsSchema[SettingsT], settings: SettingsT, section: dict[str, Any], context: str) -> SettingsT:
    """Apply one TOML configuration section after validating allowed keys."""
    _validate_config_section_keys(section, context, schema.toml_keys())

    values = {definition.field: section[definition.key] for definition in schema.toml_definitions() if definition.key in section}
    return _apply_field_values(schema, settings, values, context)


def _validate_config_section_keys(section: dict[str, Any], context: str, allowed_keys: tuple[str, ...]) -> None:
    """Reject unknown keys in one TOML configuration section."""
    unknown_keys = sorted(str(key) for key in section if key not in allowed_keys)
    if unknown_keys:
        joined_keys = ", ".join(unknown_keys)
        raise ConfigError(f"{context} contains unknown setting(s): {joined_keys}")


def _apply_field_values(schema: SettingsSchema[SettingsT], settings: SettingsT, values: dict[str, Any], context: str) -> SettingsT:
    """Validate raw field values and return settings with those fields replaced."""
    definitions_by_field = schema.definitions_by_field()
    updates: dict[str, Any] = {}
    for field, value in values.items():
        definition = definitions_by_field[field]
        validator = definition.validator
        if validator is None:
            raise AssertionError(f"Setting definition for {field!r} has no validator")
        updates[field] = validator(value, f"{context}.{definition.key}")
    if schema.post_validate is not None:
        schema.post_validate(updates, context)
    return cast(SettingsT, dataclasses.replace(cast(Any, settings), **updates))


def _add_setting_argument(
    argument_group: argparse._ActionsContainer,
    definition: SettingDefinition[Any],
    settings: Any,
    *,
    dest_prefix: str | None,
) -> None:
    """Add one settings argument to an argparse argument group."""
    if not definition.available_in_cli:
        return
    if definition.cli is None:
        raise AssertionError(f"Setting definition for {definition.field!r} has no CLI metadata")

    kwargs: dict[str, Any] = {
        "default": None,
        "dest": _dest_name(definition.field, dest_prefix),
        "help": _format_cli_help(definition, settings),
    }
    if definition.cli.action is not None:
        kwargs["action"] = definition.cli.action
    if definition.cli.choices is not None:
        kwargs["choices"] = definition.cli.choices
    if definition.cli.type is not None:
        kwargs["type"] = definition.cli.type
    if definition.cli.metavar is not None:
        kwargs["metavar"] = definition.cli.metavar
    argument_group.add_argument(*definition.cli.flags, **kwargs)


def _format_cli_help(definition: SettingDefinition[Any], settings: Any) -> str:
    """Return argparse help text for one setting definition."""
    if definition.cli is None or not definition.cli.show_default:
        return definition.help

    value = getattr(settings, definition.field)
    if isinstance(value, bool):
        default = _enabled_label(value)
    elif isinstance(value, enum.StrEnum):
        default = value.value
    else:
        default = str(value)
    return f"{definition.help.removesuffix('.')} (default: {default})."


def _dest_name(field: str, dest_prefix: str | None) -> str:
    """Return an argparse destination name for a setting field."""
    if dest_prefix is None:
        return field
    return f"{dest_prefix}_{field}"


def _parse_cli_setting_value(definition: SettingDefinition[Any], value: Any) -> Any:
    """Parse one argparse namespace value into a settings override value."""
    if value is None:
        return None
    if definition.cli is None or definition.cli.value_kind == SettingCLIValueKind.RAW:
        return value
    if definition.cli.value_kind == SettingCLIValueKind.COMMA_LIST:
        return parse_comma_option_groups(value)
    if definition.cli.value_kind == SettingCLIValueKind.TOML_MAP:
        return parse_toml_map_option_groups(value)
    raise AssertionError(f"Unknown CLI value kind: {definition.cli.value_kind}")
