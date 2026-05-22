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

DEFAULT_SOURCE_PRIORITY = 0
CONFIG_FILE_SOURCE_PRIORITY = 1
INLINE_CONFIG_SOURCE_PRIORITY = 2
ARGUMENT_SOURCE_PRIORITY = 3
FIELD_OVERRIDE_SOURCE_PRIORITY = 4


class SettingsError(ValueError):
    """Raised when configuration cannot be resolved or validated.

    This exception represents user-facing configuration failures, including malformed TOML, unsupported table shapes,
    unknown setting keys, and invalid setting values. Constructor arguments are forwarded to `ValueError`.
    """


@dataclasses.dataclass(frozen=True)
class SettingsProfile(Generic[SettingsT]):
    """Resolved settings plus source-base and source-priority metadata."""

    settings: SettingsT
    field_bases: Mapping[str, str]
    field_priorities: Mapping[str, int]

    def base_for_field(self, field: str) -> str:
        """Return the absolute base directory associated with a resolved field."""
        return self.field_bases.get(field, os.getcwd())

    def priority_for_field(self, field: str) -> int:
        """Return the configuration-source priority associated with a resolved field."""
        return self.field_priorities.get(field, DEFAULT_SOURCE_PRIORITY)


@dataclasses.dataclass(frozen=True)
class SettingsResolver(Generic[SettingsT]):
    """Resolve settings for paths using Ruff-style closest-config semantics."""

    schema: SettingsSchema[SettingsT]
    global_values: GlobalArgs
    args: argparse.Namespace | None = None
    field_overrides: Mapping[str, Any] | None = None
    _profiles_by_start_dir: dict[str, SettingsProfile[SettingsT]] = dataclasses.field(default_factory=dict)

    def profile_for_path(self, path: str | None = None) -> SettingsProfile[SettingsT]:
        """Return settings for a path, caching by the path's containing directory."""
        start_dir = _settings_start_dir(path)
        cached_profile = self._profiles_by_start_dir.get(start_dir)
        if cached_profile is not None:
            return cached_profile
        profile = self.schema.load_profile(global_values=self.global_values, args=self.args, field_overrides=self.field_overrides, path=start_dir)
        self._profiles_by_start_dir[start_dir] = profile
        return profile


class SettingCLIValueKind(enum.StrEnum):
    """CLI value parsing strategy for a setting.

    Attributes:
        RAW (SettingCLIValueKind): Use argparse's parsed value directly.
        COMMA_LIST (SettingCLIValueKind): Split repeated CLI values on commas and return a tuple.
        TOML_MAP (SettingCLIValueKind): Parse repeated CLI values as TOML inline tables and merge them.
    """

    RAW = "raw"
    COMMA_LIST = "comma-list"
    TOML_MAP = "toml-map"


class SettingCLIOptions(TypedDict, total=False):
    """Unresolved argparse metadata for one setting.

    Attributes:
        flags (tuple[str, ...]): CLI option flags to register.
        action (SettingCLIAction | None): Argparse action to use.
        choices (SettingCLIChoices | None): Allowed CLI choices.
        type (SettingCLIType | None): Argparse value converter.
        metavar (SettingCLIMetavar | None): Argparse metavar.
        value_kind (SettingCLIValueKind): Post-parse conversion strategy.
        show_default (bool): Whether help text should include the current default.
    """

    flags: tuple[str, ...]
    action: SettingCLIAction | None
    choices: SettingCLIChoices | None
    type: SettingCLIType | None
    metavar: SettingCLIMetavar | None
    value_kind: SettingCLIValueKind
    show_default: bool


@dataclasses.dataclass(frozen=True)
class SettingCLIDefinition:
    """Resolved argparse metadata for one setting.

    Attributes:
        flags (tuple[str, ...]): CLI option flags to register.
        action (SettingCLIAction | None): Argparse action to use.
        choices (SettingCLIChoices | None): Allowed CLI choices.
        type (SettingCLIType | None): Argparse value converter.
        metavar (SettingCLIMetavar | None): Argparse metavar.
        value_kind (SettingCLIValueKind): Post-parse conversion strategy.
        show_default (bool): Whether help text should include the current default.
    """

    flags: tuple[str, ...] = ()
    action: SettingCLIAction | None = None
    choices: SettingCLIChoices | None = None
    type: SettingCLIType | None = None
    metavar: SettingCLIMetavar | None = None
    value_kind: SettingCLIValueKind = SettingCLIValueKind.RAW
    show_default: bool = True


@dataclasses.dataclass(frozen=True, init=False)
class SettingDefinition(Generic[SettingValueT]):
    """Central metadata for one setting.

    Attributes:
        field (str): Dataclass field name used for resolved settings.
        value_type (type[SettingValueT] | GenericAlias): Declared validated setting type.
        group (enum.StrEnum): Settings group used for CLI/help ordering.
        help (str): Short help text for CLI output.
        key (str): TOML key used for configuration.
        available_in_cli (bool): Whether a dedicated CLI option should be registered.
        available_in_toml (bool): Whether the setting can be loaded from TOML.
        validator (SettingValidator[SettingValueT]): Validator that converts raw values to resolved values.
        cli (SettingCLIDefinition | None): Resolved CLI metadata, or None when unavailable in CLI.
        documentation (str): Longer user-facing configuration documentation.
        example (str): Optional TOML example text.
    """

    field: str
    value_type: type[SettingValueT] | GenericAlias
    group: enum.StrEnum
    help: str
    key: str = ""
    available_in_cli: bool = True
    available_in_toml: bool = True
    validator: SettingValidator[SettingValueT] = dataclasses.field(init=False)
    cli: SettingCLIDefinition | None = None
    documentation: str = ""
    example: str = ""

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
        example: str | None = None,
    ) -> None:
        """Initialize setting metadata with derived defaults.

        Args:
            field (str): Dataclass field name used for resolved settings.
            value_type (type[SettingValueT] | GenericAlias): Declared validated setting type.
            group (enum.StrEnum): Settings group used for CLI/help ordering.
            help (str): Short help text for CLI output.
            key (str): TOML key, defaulting to the field name with underscores replaced by dashes.
            available_in_cli (bool): Whether a dedicated CLI option should be registered.
            available_in_toml (bool): Whether the setting can be loaded from TOML.
            validator (SettingValidator[SettingValueT] | None): Optional validator, defaulting from `value_type`.
            cli (SettingCLIOptions | SettingCLIDefinition | dict[str, Any] | None): Optional unresolved or resolved CLI
                metadata.
            documentation (str | None): Optional longer configuration documentation, defaulting to `help`.
            example (str | None): Optional TOML example text.

        Raises:
            `TypeError`: If no default validator exists for `value_type` and no validator is supplied.
        """
        resolved_key = key or field.replace("_", "-")
        resolved_validator = cast(SettingValidator[SettingValueT], _default_validator_for_type(value_type)) if validator is None else validator
        resolved_documentation = documentation or help
        resolved_example = example or ""

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
        object.__setattr__(self, "example", resolved_example)


@dataclasses.dataclass(frozen=True)
class SettingsSchema(Generic[SettingsT]):
    """Generic schema describing one dataclass-backed settings object.

    Attributes:
        settings_type: Resolved dataclass type constructed for defaults and returned by config loading.
        overrides_type: TypedDict-like class describing partial field overrides accepted from CLI/config layers.
        group_type: Enum type that defines accepted settings groups and argparse group ordering.
        definitions: Ordered metadata mapping settings dataclass fields to TOML keys, CLI options, validation, and help
            text.
        table_path: Nested TOML table to read from files named `pyproject.toml`, expressed as non-empty path segments.
            For example, `("tool", "pydocfmt")` reads settings from `[tool.pydocfmt]`. Explicit config files with any
            other basename are treated as dedicated config files and read settings from the top-level table instead.
        table_name: Dotted TOML table name derived from table_path.
        post_validate: Optional validation hook called after per-field validation with only the updates from the current
            layer, keyed by dataclass field name, and a user-facing path string. The hook should raise SettingsError for
            cross-field or domain validation failures and should not mutate values.
    """

    settings_type: type[SettingsT]
    overrides_type: SettingsOverridesType
    group_type: type[enum.StrEnum]
    definitions: tuple[SettingDefinition[Any], ...]
    table_path: tuple[str, ...]
    table_name: str = dataclasses.field(init=False)
    post_validate: Callable[[dict[str, Any], str], None] | None = None

    def __post_init__(self) -> None:
        """Validate schema group metadata.

        Raises:
            `ValueError`: If the TOML table path is empty or contains empty segments.
            `TypeError`: If a setting definition uses a group outside `group_type`.
            `AssertionError`: If CLI availability and resolved CLI metadata disagree.
        """
        if not self.table_path or any(not key for key in self.table_path):
            raise ValueError("Settings schema table_path must contain non-empty path segments")
        table_name = ".".join(self.table_path)
        if not table_name:
            raise ValueError("Settings schema table_name must not be empty")
        object.__setattr__(self, "table_name", table_name)

        invalid_definitions = tuple(definition for definition in self.definitions if not isinstance(definition.group, self.group_type))
        if invalid_definitions:
            invalid_fields = ", ".join(f"{definition.field}={definition.group!r}" for definition in invalid_definitions)
            raise TypeError(f"Settings definitions must belong to {self.group_type.__name__}: {invalid_fields}")
        invalid_definitions = tuple(definition for definition in self.definitions if definition.available_in_cli != (definition.cli is not None))
        if invalid_definitions:
            invalid_fields = ", ".join(f"{definition.field}: {definition.available_in_cli}/{definition.cli is not None}" for definition in invalid_definitions)
            raise AssertionError(f"Inconsistent settings definitions found in terms of CLI availability: {invalid_fields}")

    def load(self, *, global_values: GlobalArgs | None = None, args: argparse.Namespace | None = None, field_overrides: Mapping[str, Any] | None = None) -> SettingsT:
        """Resolve settings from defaults, config files, inline config, and optional CLI overrides.

        Args:
            global_values (GlobalArgs | None): Global configuration options and isolated-mode flag.
            args (argparse.Namespace | None): Parsed CLI namespace for dedicated option overrides.
            field_overrides (Mapping[str, Any] | None): Final field-keyed raw overrides.

        Returns:
            SettingsT: Resolved settings dataclass instance.

        Raises:
            `SettingsError`: If any configuration source cannot be loaded or validated.
            `tomllib.TOMLDecodeError`: If a TOML-map CLI value is malformed.
        """
        return self.load_profile(global_values=global_values, args=args, field_overrides=field_overrides).settings

    def resolver(self, *, global_values: GlobalArgs | None = None, args: argparse.Namespace | None = None, field_overrides: Mapping[str, Any] | None = None) -> SettingsResolver[SettingsT]:
        """Return a path-aware settings resolver for repeated per-path lookups."""
        return SettingsResolver(
            schema=self,
            global_values=GlobalArgs() if global_values is None else global_values,
            args=args,
            field_overrides=field_overrides,
        )

    def load_profile(
        self, *, global_values: GlobalArgs | None = None, args: argparse.Namespace | None = None, field_overrides: Mapping[str, Any] | None = None, path: str | None = None
    ) -> SettingsProfile[SettingsT]:
        """Resolve settings and source metadata for one path.

        Args:
            global_values (GlobalArgs | None): Global configuration options and isolated-mode flag.
            args (argparse.Namespace | None): Parsed CLI namespace for dedicated option overrides.
            field_overrides (Mapping[str, Any] | None): Final field-keyed raw overrides.
            path (str | None): Path whose closest auto-discovered configuration should be used, defaulting to cwd.

        Returns:
            SettingsProfile[SettingsT]: Resolved settings plus field source bases and source priorities.

        Raises:
            `SettingsError`: If any configuration source cannot be loaded or validated.
            `tomllib.TOMLDecodeError`: If a TOML-map CLI value is malformed.
        """
        if global_values is None:
            global_values = GlobalArgs()

        inline_options: list[str] = []
        path_options: list[str] = []
        for option in global_values.config_options:
            if "=" in option and not os.path.exists(option):
                inline_options.append(option)
            else:
                path_options.append(option)
        if len(path_options) > 1:
            raise SettingsError("Only one --config=PATH configuration file can be supplied")

        cwd_base = os.getcwd()
        profile = SettingsProfile(
            settings=self.settings_type(),
            field_bases={definition.field: cwd_base for definition in self.definitions},
            field_priorities={definition.field: DEFAULT_SOURCE_PRIORITY for definition in self.definitions},
        )

        if global_values.isolated:
            if path_options:
                raise SettingsError("The argument --config=PATH cannot be used with --isolated")
        else:
            if not path_options:
                auto_path = _auto_discovered_pyproject_path_for_path(path, table_path=self.table_path)
                if auto_path is not None:
                    profile = _apply_toml_file_profile(
                        self,
                        profile,
                        path=auto_path,
                        required=False,
                        source_base=os.path.dirname(os.path.abspath(auto_path)),
                        source_priority=CONFIG_FILE_SOURCE_PRIORITY,
                    )
            for option in path_options:
                profile = _apply_toml_file_profile(self, profile, path=option, required=True, source_base=cwd_base, source_priority=CONFIG_FILE_SOURCE_PRIORITY)

        for option in inline_options:
            try:
                section = tomllib.loads(option)
            except tomllib.TOMLDecodeError as error:
                raise SettingsError(f"Failed to decode --config inline TOML: {error}") from error
            profile = _apply_toml_section_profile(self, profile, section=section, context="<--config>", source_base=cwd_base, source_priority=INLINE_CONFIG_SOURCE_PRIORITY)

        if args is not None:
            argument_overrides = self.argument_overrides(args)
            if argument_overrides:
                profile = _apply_field_values_profile(self, profile, values=argument_overrides, context="<argparse>", key_based=False, source_base=cwd_base, source_priority=ARGUMENT_SOURCE_PRIORITY)

        if field_overrides:
            profile = _apply_field_values_profile(self, profile, values=field_overrides, context="<overrides>", key_based=False, source_base=cwd_base, source_priority=FIELD_OVERRIDE_SOURCE_PRIORITY)

        return profile

    def format(self, settings: SettingsT) -> str:
        """Return resolved settings in a stable TOML-like form.

        Args:
            settings (SettingsT): Settings object to render.

        Returns:
            str: TOML-like settings text in schema definition order.
        """
        lines = [f"[{self.table_name}]"] if self.table_name else []
        for definition in self.definitions:
            if not definition.available_in_toml:
                continue
            value = getattr(settings, definition.field)
            rendered = format_value(value, definition.value_type)
            lines.append(f"{definition.key} = {rendered}")
        lines.append("")
        return "\n".join(lines)

    def add_arguments(self, parser: argparse.ArgumentParser, settings: SettingsT) -> None:
        """Add argparse arguments for every settings group in schema order.

        Args:
            parser (argparse.ArgumentParser): Parser that should receive setting arguments.
            settings (SettingsT): Settings object supplying current defaults for help text.

        Raises:
            `AssertionError`: If schema definitions cannot be mapped consistently to argparse groups.
        """
        handled_definitions: list[SettingDefinition[Any]] = []
        for group in self.group_type:
            argument_group = parser.add_argument_group(group.value)
            for definition in self.definitions:
                if definition.group == group:
                    handled_definitions.append(definition)
                    if definition.available_in_cli:
                        if definition.cli is None:
                            raise AssertionError(f"Setting definition for {definition.field!r} has no CLI metadata")
                        kwargs: dict[str, Any] = {
                            "default": None,
                            "dest": definition.field,
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

        if len(handled_definitions) != len(self.definitions):
            handled_fields = {definition.field for definition in handled_definitions}
            missing_fields = tuple(definition.field for definition in self.definitions if definition.field not in handled_fields)
            raise AssertionError(f"Not all settings definitions were added to argparse groups: {', '.join(missing_fields)}")

    def argument_overrides(self, args: argparse.Namespace) -> dict[str, Any]:
        """Build settings overrides dict from parsed command-line arguments.

        Args:
            args (argparse.Namespace): Parsed command-line namespace.

        Returns:
            dict[str, Any]: Field-keyed raw override values supplied through dedicated CLI options.

        Raises:
            `SettingsError`: If a TOML-map CLI value does not parse to a TOML table.
            `tomllib.TOMLDecodeError`: If a TOML-map CLI value is malformed.
            `AssertionError`: If a setting has an unknown CLI value kind.
        """
        values: dict[str, Any] = {}
        for definition in self.definitions:
            if definition.available_in_cli:
                value = getattr(args, definition.field, None)
                if value is None:
                    continue
                if definition.cli is None or definition.cli.value_kind == SettingCLIValueKind.RAW:
                    values[definition.field] = value
                elif definition.cli.value_kind == SettingCLIValueKind.COMMA_LIST:
                    values[definition.field] = tuple(item.strip() for group in value for item in group.split(","))
                elif definition.cli.value_kind == SettingCLIValueKind.TOML_MAP:
                    merged: dict[str, Any] = {}
                    for group in value:
                        parsed = tomllib.loads(f"value = {group}")
                        parsed_value = parsed["value"]
                        if not isinstance(parsed_value, dict):
                            raise SettingsError("TOML map CLI value must be a TOML table")
                        for pattern, selectors in parsed_value.items():
                            if pattern in merged and isinstance(merged[pattern], list) and isinstance(selectors, list):
                                merged[pattern].extend(selectors)
                            else:
                                merged[pattern] = selectors
                    values[definition.field] = merged
                else:
                    raise AssertionError(f"Unknown CLI value kind: {definition.cli.value_kind}")
        return values


def _format_cli_help(definition: SettingDefinition[Any], settings: Any) -> str:
    """Return argparse help text for one setting definition."""
    if definition.cli is None or not definition.cli.show_default:
        return definition.help
    else:
        value = getattr(settings, definition.field)
        if isinstance(value, bool):
            default = "enabled" if value else "disabled"
        elif isinstance(value, enum.StrEnum):
            default = value.value
        else:
            default = str(value)
        return f"{definition.help.rstrip('.!?')} (default: {default})."


def _format_string(value: Any) -> str:
    """Format a string value for TOML output."""
    return json.dumps(value)


def format_value(value: Any, value_type: type[Any] | GenericAlias) -> str:
    """Format a setting value as a TOML literal.

    Args:
        value (Any): Resolved setting value.
        value_type (type[Any] | GenericAlias): Declared setting value type.

    Returns:
        str: TOML-compatible literal representation.
    """
    value_type_: object = value_type
    if value_type_ is bool:
        return str(value).lower()
    elif value_type_ is str:
        return _format_string(value)
    elif _is_str_enum_type(value_type_):
        return _format_string(value.value)
    elif value_type_ == StringList:
        return _format_string_list(value)
    elif value_type_ == MultiStringMap:
        return _format_multi_string_map(value)
    else:
        return str(value)


def _format_string_list(values: tuple[Any, ...]) -> str:
    """Format values as a TOML list."""
    return "[" + ", ".join(_format_string(value.value if isinstance(value, enum.StrEnum) else value) for value in values) + "]"


def _format_multi_string_map(value: Any) -> str:
    """Format a string-keyed multi-string mapping as a TOML inline table."""
    if isinstance(value, Mapping):
        items = tuple(value.items())
    else:
        items = tuple(value)
    entries = [f"{_format_string(pattern)} = {_format_string_list(selectors)}" for pattern, selectors in items]
    return "{" + ", ".join(entries) + "}"


def validate_bool(value: Any, context: str) -> bool:
    """Validate and return a boolean setting value.

    Args:
        value (Any): Raw value to validate.
        context (str): User-facing configuration location for error messages.

    Returns:
        bool: Validated boolean value.

    Raises:
        `SettingsError`: If the raw value is not a boolean.
    """
    if not isinstance(value, bool):
        raise SettingsError(f"{context} must be a boolean")
    return value


def validate_int(*, min_value: int | None = None, max_value: int | None = None) -> Callable[[Any, str], int]:
    """Return a validator for integer settings with optional inclusive bounds.

    Args:
        min_value (int | None): Optional inclusive lower bound.
        max_value (int | None): Optional inclusive upper bound.

    Returns:
        Callable[[Any, str], int]: Validator that converts raw values to bounded integers.
    """

    def validate(value: Any, context: str) -> int:
        """Validate one integer setting value."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise SettingsError(f"{context} must be an integer")
        if min_value is not None and value < min_value:
            raise SettingsError(f"{context} must be greater than or equal to {min_value}")
        if max_value is not None and value > max_value:
            raise SettingsError(f"{context} must be less than or equal to {max_value}")
        return value

    return validate


def validate_str_enum(enum_class: type[StrEnumT]) -> Callable[[Any, str], StrEnumT]:
    """Return a validator that converts setting values to members of a string enum.

    Args:
        enum_class (type[StrEnumT]): String enum class to validate against.

    Returns:
        Callable[[Any, str], StrEnumT]: Validator that converts raw values to enum members.
    """

    def validate(value: Any, context: str) -> StrEnumT:
        """Validate one string enum setting value."""
        try:
            return enum_class(value)
        except ValueError as error:
            options = "{" + ", ".join(f"'{member.value}'" for member in enum_class) + "}"
            raise SettingsError(f"{context} must be one of {options}") from error

    return validate


def validate_string_list(value: Any, context: str) -> StringList:
    """Validate and return a tuple of string list values.

    Args:
        value (Any): Raw value to validate.
        context (str): User-facing configuration location for error messages.

    Returns:
        StringList: Validated string tuple.

    Raises:
        `SettingsError`: If the raw value is not a list or tuple of strings.
    """
    if not isinstance(value, (list, tuple)):
        raise SettingsError(f"{context} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise SettingsError(f"{context} must be a list of strings")
    return tuple(value)


def validate_non_empty_string_list(value: Any, context: str) -> StringList:
    """Validate and return a tuple of non-empty string list values.

    Args:
        value (Any): Raw value to validate.
        context (str): User-facing configuration location for error messages.

    Returns:
        StringList: Validated string tuple.

    Raises:
        `SettingsError`: If any item is not a string or is empty.
    """
    values = validate_string_list(value, context)
    if any(not value for value in values):
        raise SettingsError(f"{context} must not contain empty strings")
    return values


def validate_multi_string_map(value: Any, context: str) -> MultiStringMap:
    """Validate and return a mapping of strings to non-empty string lists.

    Args:
        value (Any): Raw mapping or tuple of key/value pairs to validate.
        context (str): User-facing configuration location for error messages.

    Returns:
        MultiStringMap: Validated tuple of string keys and non-empty string-list values.

    Raises:
        `SettingsError`: If the raw value is not a string-keyed mapping to non-empty string lists.
    """
    if isinstance(value, tuple):
        items = value
    elif isinstance(value, dict):
        items = tuple(value.items())
    else:
        raise SettingsError(f"{context} must be a table mapping strings to string lists")

    entries = []
    for key, values in items:
        if not isinstance(key, str):
            raise SettingsError(f"{context} keys must be strings")
        if not key:
            raise SettingsError(f"{context} keys must not be empty")
        entries.append((key, validate_non_empty_string_list(values, f"{context}.{key}")))
    return tuple(entries)


def _default_validator_for_type(setting_type: type[SettingValueT] | GenericAlias) -> Callable[[Any, str], Any]:
    """Return the default validator for a setting type."""
    if setting_type is bool:
        return validate_bool
    elif setting_type is int:
        return validate_int()
    elif _is_str_enum_type(setting_type):
        return validate_str_enum(cast(type[enum.StrEnum], setting_type))
    elif setting_type == StringList:
        return validate_string_list
    elif setting_type == MultiStringMap:
        return validate_multi_string_map
    else:
        raise TypeError(f"No default validator for setting type: {setting_type!r}")


def _is_str_enum_type(setting_type: Any) -> bool:
    """Return whether a setting type is a string enum class."""
    return isinstance(setting_type, type) and issubclass(setting_type, enum.StrEnum)


def _load_toml_file(path: str, *, required: bool) -> dict[str, Any] | None:
    """Load a TOML file, returning None if an optional file is absent."""
    try:
        file = open(path, "rb")
    except FileNotFoundError as error:
        if required:
            raise SettingsError(f"Configuration file not found: {path}") from error
        return None
    except OSError as error:
        raise SettingsError(f"Failed to read configuration file {path}: {error}") from error

    with file:
        try:
            config = tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            raise SettingsError(f"Failed to decode {path}: {error}") from error

    if not isinstance(config, dict):
        raise SettingsError(f"{path}: Must contain a TOML table")
    return config


def _settings_start_dir(path: str | None) -> str:
    """Return the directory used to resolve path-specific configuration."""
    if path is None:
        return os.getcwd()
    absolute_path = os.path.abspath(path)
    if os.path.isdir(absolute_path):
        return absolute_path
    return os.path.dirname(absolute_path)


def _auto_discovered_pyproject_path_for_path(path: str | None, *, table_path: tuple[str, ...]) -> str | None:
    """Return the closest containing pyproject with the configured table."""
    current_dir = _settings_start_dir(path)
    while True:
        candidate = os.path.join(current_dir, "pyproject.toml")
        if os.path.exists(candidate):
            config = _load_toml_file(candidate, required=True)
            if config is not None and _toml_section_at_table_path(config, path=candidate, table_path=table_path, required=False) is not None:
                return candidate

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            return None
        current_dir = parent_dir


def _toml_section_at_table_path(config: dict[str, Any], *, path: str, table_path: tuple[str, ...], required: bool) -> dict[str, Any] | None:
    """Return a nested TOML table at the requested path."""
    section: Any = config
    traversed: list[str] = []
    for key in table_path:
        traversed.append(key)
        if not isinstance(section, dict):
            table = ".".join(traversed[:-1])
            raise SettingsError(f"{path}: The [{table}] section must be a table")
        if key not in section:
            if required:
                raise SettingsError(f"{path}: Must contain [{'.'.join(table_path)}]")
            return None
        section = section[key]

    if not isinstance(section, dict):
        raise SettingsError(f"{path}: The [{'.'.join(table_path)}] section must be a table")
    return cast(dict[str, Any], section)


def _apply_toml_file_profile(
    schema: SettingsSchema[SettingsT], profile: SettingsProfile[SettingsT], *, path: str, required: bool, source_base: str, source_priority: int
) -> SettingsProfile[SettingsT]:
    """Apply one config file to the passed settings profile."""
    section = _load_toml_file(path, required=required)  # Only returns None if the file is both absent and not required
    if section is None:
        return profile

    if os.path.basename(path) == "pyproject.toml":
        # Only returns None if the section is both absent and not required
        section = _toml_section_at_table_path(section, path=path, table_path=schema.table_path, required=required)
        if section is None:
            return profile
        context = f"<{path}>.{schema.table_name}"
    else:
        context = f"<{path}>"

    return _apply_toml_section_profile(schema, profile, section=section, context=context, source_base=source_base, source_priority=source_priority)


def _apply_toml_section_profile(
    schema: SettingsSchema[SettingsT], profile: SettingsProfile[SettingsT], *, section: dict[str, Any], context: str, source_base: str, source_priority: int
) -> SettingsProfile[SettingsT]:
    """Apply one TOML configuration section to a settings profile."""
    schema_toml_keys = set(definition.key for definition in schema.definitions if definition.available_in_toml)
    unknown_keys = [key for key in section if key not in schema_toml_keys]
    if unknown_keys:
        unknown_keys.sort()
        joined_keys = ", ".join(unknown_keys)
        raise SettingsError(f"{context} contains unknown setting(s): {joined_keys}")

    values = {definition.field: section[definition.key] for definition in schema.definitions if definition.available_in_toml and definition.key in section}
    return _apply_field_values_profile(schema, profile, values=values, context=context, key_based=True, source_base=source_base, source_priority=source_priority)


def _validated_field_updates(schema: SettingsSchema[SettingsT], *, values: Mapping[str, Any], context: str, key_based: bool) -> dict[str, Any]:
    """Validate raw field values and return resolved field updates."""
    definitions_by_field = {definition.field: definition for definition in schema.definitions}
    updates: dict[str, Any] = {}
    for field, value in values.items():
        definition = definitions_by_field[field]
        updates[field] = definition.validator(value, f"{context}.{definition.key if key_based else field}")
    if schema.post_validate is not None:
        schema.post_validate(updates, context)
    return updates


def _apply_field_values_profile(
    schema: SettingsSchema[SettingsT], profile: SettingsProfile[SettingsT], *, values: Mapping[str, Any], context: str, key_based: bool, source_base: str, source_priority: int
) -> SettingsProfile[SettingsT]:
    """Validate raw field values and return an updated settings profile."""
    updates = _validated_field_updates(schema, values=values, context=context, key_based=key_based)
    settings = cast(SettingsT, dataclasses.replace(cast(Any, profile.settings), **updates))
    field_bases = dict(profile.field_bases)
    field_priorities = dict(profile.field_priorities)
    absolute_source_base = os.path.abspath(source_base)
    for field in updates:
        field_bases[field] = absolute_source_base
        field_priorities[field] = source_priority
    return SettingsProfile(settings=settings, field_bases=field_bases, field_priorities=field_priorities)
