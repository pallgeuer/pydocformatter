"""Layered pydocformatter settings resolution.

Attributes:
    SettingsT (TypeVar): Settings dataclass type carried by generic schemas, profiles, and path-aware resolvers.
    SettingsKeyT (TypeVar): Hashable settings identity type used by cached profile keys.
    StrEnumT (TypeVar): String enum type accepted by enum parsing and formatting helpers.
    SettingValueT (TypeVar): Validated setting value type returned by schema validators.
    StringList (TypeAlias): Repeated string setting values from TOML or comma-separated CLI input.
    StringMap (TypeAlias): Ordered mapping representation for string keys and values.
    MultiStringMap (TypeAlias): Ordered mapping representation for glob-pattern keys whose values are rule-selector or
        string lists.
    PerFileSettingsMap (TypeAlias): Ordered mapping representation for glob-pattern keys whose values are field-keyed
        settings overrides.
    SettingValidator (TypeAlias): Callable contract for converting raw setting input into the normalized value stored on
        a settings dataclass.
    SettingCLIAction (TypeAlias): Argparse action specifier accepted by setting definitions when exposing a field as a
        dedicated command-line option.
    SettingCLIChoices (TypeAlias): Allowed CLI choices advertised for a setting after schema-level validation has
        normalized the value.
    SettingCLIType (TypeAlias): Argparse type hook shape used for setting options that need command-line value
        conversion before schema validation.
    SettingCLIMetavar (TypeAlias): Display placeholder passed to argparse for generated setting option help.
    SettingsOverridesType (TypeAlias): Runtime type shape accepted for inline `--config` overrides before field-specific
        validation runs.
    DEFAULT_SOURCE_PRIORITY (int): Base priority for settings supplied by dataclass defaults.
    CONFIG_FILE_SOURCE_PRIORITY (int): Priority assigned to values loaded from discovered or explicit TOML configuration
        files.
    INLINE_CONFIG_SOURCE_PRIORITY (int): Priority assigned to `--config KEY=VALUE` overrides.
    ARGUMENT_SOURCE_PRIORITY (int): Priority assigned to dedicated command-line options.
    FIELD_OVERRIDE_SOURCE_PRIORITY (int): Priority assigned to internal field overrides injected by callers after normal
        CLI and config loading.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import enum
import json
import math
import typing
import tomllib
import argparse
import itertools
import dataclasses
from collections.abc import Callable, Iterable, Mapping
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Generic, TypeAlias, TypedDict, TypeVar

# First-party imports
from pydocformatter.cli.global_args import GlobalArgs


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.utils.argparser as argparser_utils


SettingsT = TypeVar("SettingsT")
SettingsKeyT = TypeVar("SettingsKeyT")
StrEnumT = TypeVar("StrEnumT", bound=enum.StrEnum)
SettingValueT = TypeVar("SettingValueT")

StringList: TypeAlias = tuple[str, ...]
StringMap: TypeAlias = tuple[tuple[str, str], ...]
MultiStringMap: TypeAlias = tuple[tuple[str, StringList], ...]
PerFileSettingsMap: TypeAlias = tuple[tuple[str, tuple[tuple[str, object], ...]], ...]
SettingValidator: TypeAlias = Callable[[Any, str], SettingValueT]
SettingCLIAction: TypeAlias = str | type[argparse.Action]
SettingCLIChoices: TypeAlias = Iterable[Any]
SettingCLIType: TypeAlias = Callable[[str], Any] | str
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
    """Resolved settings plus source-base and source-priority metadata.

    Attributes:
        settings (SettingsT): Fully resolved settings object for a path or config layer.
        field_bases (Mapping[str, str]): Absolute base directories used to interpret path-like fields.
        field_priorities (Mapping[str, int]): Configuration-source priorities that supplied each field.
        project_root (str): Root established by auto-discovered configuration, or the invocation working directory.
    """

    @dataclasses.dataclass(frozen=True)
    class Key(Generic[SettingsKeyT]):
        """Hashable identity for equivalent resolved settings profiles.

        Attributes:
            settings (SettingsKeyT): Hashable representation of the resolved settings object.
            field_bases (tuple[tuple[str, str], ...]): Sorted source-base mapping for path-like settings.
            field_priorities (tuple[tuple[str, int], ...]): Sorted priority mapping for resolved setting fields.
            project_root (str): Root established by auto-discovered configuration or the invocation directory.
        """

        settings: SettingsKeyT
        field_bases: tuple[tuple[str, str], ...]
        field_priorities: tuple[tuple[str, int], ...]
        project_root: str

    settings: SettingsT
    field_bases: Mapping[str, str]
    field_priorities: Mapping[str, int]
    project_root: str

    def key(self) -> SettingsProfile.Key[SettingsT]:
        """Return a stable hashable identity for this resolved settings profile.

        Returns:
            SettingsProfile.Key[SettingsT]: Cache key combining settings values, field bases, and field priorities.
        """
        return SettingsProfile.Key(
            settings=self.settings, field_bases=tuple(sorted(self.field_bases.items())), field_priorities=tuple(sorted(self.field_priorities.items())), project_root=self.project_root
        )

    def base_for_field(self, field: str) -> str:
        """Return the absolute base directory associated with a resolved field.

        Args:
            field (str): Settings field name whose path base should be queried.

        Returns:
            str: Config-relative base directory for `field`, or the current working directory for defaulted fields.
        """
        return self.field_bases.get(field, os.getcwd())

    def priority_for_field(self, field: str) -> int:
        """Return the configuration-source priority associated with a resolved field.

        Args:
            field (str): Settings field name whose winning source should be queried.

        Returns:
            int: Priority for the source that supplied `field`, defaulting to dataclass-default priority.
        """
        return self.field_priorities.get(field, DEFAULT_SOURCE_PRIORITY)


class _SettingsProfileSourceKind(enum.Enum):
    """Configuration source category used to share equivalent resolver profiles."""

    ISOLATED = enum.auto()
    EXPLICIT = enum.auto()
    AUTO = enum.auto()
    NO_CONFIG = enum.auto()


@dataclasses.dataclass(frozen=True)
class _SettingsProfileSource:
    """Identity of the configuration source and lookup base used to build a profile.

    Attributes:
        kind (_SettingsProfileSourceKind): Configuration discovery mode that selected the source.
        config_path (str | None): Explicit spelling or absolute auto-discovered path of the selected config file.
        cwd_base (str): Working directory captured for this uncached lookup and used by non-auto source layers.
    """

    kind: _SettingsProfileSourceKind
    config_path: str | None
    cwd_base: str


@dataclasses.dataclass
class _SettingsConfigInputs:
    """Classified global configuration inputs for one resolver working-directory base.

    Attributes:
        inline_options (tuple[str, ...]): Ordered inline TOML strings from global configuration options.
        explicit_path (str | None): Sole explicit config path spelling, if supplied.
        parsed_inline_sections (tuple[dict[str, Any], ...] | None): Successfully parsed inline documents, or None before
            parsing succeeds.
    """

    inline_options: tuple[str, ...]
    explicit_path: str | None
    parsed_inline_sections: tuple[dict[str, Any], ...] | None = None


@dataclasses.dataclass
class _SettingsResolutionContext(Generic[SettingsT]):
    """Mutable invocation snapshot shared by one path-aware settings resolver.

    Successfully parsed TOML documents are shared read-only because table extraction only navigates them and flattening
    copies the selected section before validation. Discovery and profile caches deliberately snapshot filesystem
    configuration for the resolver lifetime. Config input classification and source identity retain the working
    directory captured for each uncached lookup so a resolver used across working-directory changes preserves existing
    lookup-time bases. Resolver arguments, global values, and field overrides are invocation inputs and must not be
    mutated after lookups begin.

    Attributes:
        parsed_toml_by_path (dict[str, dict[str, Any]]): Successful TOML documents keyed by normalized absolute lexical
            path.
        closest_auto_config_by_start_dir (dict[str, str | None]): Closest applicable auto config or negative discovery
            result for searched absolute directories.
        profiles_by_source (dict[_SettingsProfileSource, SettingsProfile[SettingsT]]): Fully layered profiles shared by
            explicit source identity rather than settings equality.
        config_inputs_by_cwd (dict[str, _SettingsConfigInputs]): Lazily classified global config options for each
            lookup-time working directory.
        argument_overrides (dict[str, Any] | None): Successfully computed dedicated CLI overrides, or None before
            computation.
    """

    parsed_toml_by_path: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    closest_auto_config_by_start_dir: dict[str, str | None] = dataclasses.field(default_factory=dict)
    profiles_by_source: dict[_SettingsProfileSource, SettingsProfile[SettingsT]] = dataclasses.field(default_factory=dict)
    config_inputs_by_cwd: dict[str, _SettingsConfigInputs] = dataclasses.field(default_factory=dict)
    argument_overrides: dict[str, Any] | None = None

    def load_toml_file(self, path: str, *, required: bool) -> dict[str, Any] | None:
        """Load and cache one successful TOML document by normalized lexical path.

        Args:
            path (str): Original file spelling retained for opening and user-facing errors.
            required (bool): Whether an absent file raises instead of returning None.

        Returns:
            dict[str, Any] | None: Shared successfully parsed document, or None for an optional absent file.

        Raises:
            SettingsError: If a required file is missing or an existing file cannot be read or decoded.
        """
        cache_key = os.path.normcase(os.path.abspath(os.path.normpath(path)))
        cached_config = self.parsed_toml_by_path.get(cache_key)
        if cached_config is not None:
            return cached_config
        config = _load_toml_file(path, required=required)
        if config is not None:
            self.parsed_toml_by_path[cache_key] = config
        return config

    def config_inputs_for_cwd(self, global_values: GlobalArgs, cwd_base: str) -> _SettingsConfigInputs:
        """Return lazily classified global config options for one working-directory base.

        Args:
            global_values (GlobalArgs): Invocation inputs containing ordered inline or path config options and isolated
                mode.
            cwd_base (str): Lookup-time working directory used to classify relative spellings containing an equals sign.

        Returns:
            _SettingsConfigInputs: Cached successful classification for `cwd_base`.

        Raises:
            SettingsError: If multiple explicit paths are supplied or isolated mode is combined with an explicit path.
        """
        cached_inputs = self.config_inputs_by_cwd.get(cwd_base)
        if cached_inputs is not None:
            return cached_inputs

        inline_options: list[str] = []
        path_options: list[str] = []
        for option in global_values.config_options:
            candidate = option if os.path.isabs(option) else os.path.join(cwd_base, option)
            if "=" in option and not os.path.exists(candidate):
                inline_options.append(option)
            else:
                path_options.append(option)
        if len(path_options) > 1:
            raise SettingsError("Only one --config=PATH configuration file can be supplied")
        if global_values.isolated and path_options:
            raise SettingsError("The argument --config=PATH cannot be used with --isolated")

        config_inputs = _SettingsConfigInputs(inline_options=tuple(inline_options), explicit_path=path_options[0] if path_options else None)
        self.config_inputs_by_cwd[cwd_base] = config_inputs
        return config_inputs

    @staticmethod
    def inline_sections(config_inputs: _SettingsConfigInputs) -> Iterable[dict[str, Any]]:
        """Yield inline TOML sections in parse and application order.

        Args:
            config_inputs (_SettingsConfigInputs): Classified inputs whose inline strings should be parsed.

        Yields:
            dict[str, Any]: Next ordered inline section, with the complete sequence cached after the caller processes
                every string.

        Raises:
            SettingsError: If an inline TOML string cannot be decoded.
        """
        if config_inputs.parsed_inline_sections is not None:
            yield from config_inputs.parsed_inline_sections
            return

        sections: list[dict[str, Any]] = []
        for option in config_inputs.inline_options:
            try:
                section = tomllib.loads(option)
            except tomllib.TOMLDecodeError as error:
                raise SettingsError(f"Failed to decode --config inline TOML: {error}") from error
            sections.append(section)
            yield section
        config_inputs.parsed_inline_sections = tuple(sections)

    def argument_overrides_for(self, schema: SettingsSchema[SettingsT], args: argparse.Namespace | None) -> dict[str, Any]:
        """Return dedicated CLI overrides after one successful lazy computation.

        Args:
            schema (SettingsSchema[SettingsT]): Schema that converts command arguments into field overrides.
            args (argparse.Namespace | None): Parsed invocation arguments, or None when no dedicated layer exists.

        Returns:
            dict[str, Any]: Shared field-keyed argument overrides, which may be empty.

        Raises:
            tomllib.TOMLDecodeError: If a TOML-map command argument cannot be decoded.
        """
        if self.argument_overrides is None:
            self.argument_overrides = {} if args is None else schema.argument_overrides(args)
        return self.argument_overrides


@dataclasses.dataclass(frozen=True)
class SettingsResolver(Generic[SettingsT]):
    """Resolve settings for paths using an invocation-scoped configuration snapshot.

    Exact starting directories retain first-level aliases, while equivalent source identities share one fully layered
    profile. Successfully parsed files and searched ancestors remain snapshots for this resolver's lifetime. Separate
    resolvers start empty and observe current filesystem state. Lookup-time working directories remain part of source
    identity, and exact directory aliases resolved before a working-directory change remain unchanged. Global values,
    argparse values, and field overrides are treated as immutable invocation inputs once resolution begins.

    Attributes:
        schema (SettingsSchema[SettingsT]): Settings schema used to load and validate profiles.
        global_values (GlobalArgs): Global CLI options that affect config discovery and inline overrides.
        args (argparse.Namespace | None): Command-specific argparse namespace whose options override config files.
        field_overrides (Mapping[str, Any] | None): Programmatic overrides applied with highest precedence.
    """

    schema: SettingsSchema[SettingsT]
    global_values: GlobalArgs
    args: argparse.Namespace | None = None
    field_overrides: Mapping[str, Any] | None = None
    _profiles_by_start_dir: dict[str, SettingsProfile[SettingsT]] = dataclasses.field(default_factory=dict)
    _context: _SettingsResolutionContext[SettingsT] = dataclasses.field(default_factory=_SettingsResolutionContext, compare=False, repr=False)

    def profile_for_path(self, path: str | None = None) -> SettingsProfile[SettingsT]:
        """Return settings for a path from exact-directory and shared-source caches.

        Args:
            path (str | None): File or directory path whose closest applicable config should be resolved, or the current
                working directory when omitted.

        Returns:
            SettingsProfile[SettingsT]: Settings and source metadata for the containing directory.
        """
        start_dir = _settings_start_dir(path)
        cached_profile = self._profiles_by_start_dir.get(start_dir)
        if cached_profile is not None:
            return cached_profile

        cwd_base = os.getcwd()
        config_inputs = self._context.config_inputs_for_cwd(self.global_values, cwd_base)
        if self.global_values.isolated:
            source = _SettingsProfileSource(kind=_SettingsProfileSourceKind.ISOLATED, config_path=None, cwd_base=cwd_base)
        elif config_inputs.explicit_path is not None:
            source = _SettingsProfileSource(kind=_SettingsProfileSourceKind.EXPLICIT, config_path=config_inputs.explicit_path, cwd_base=cwd_base)
        else:
            auto_path = _auto_discovered_pyproject_path_for_path_with_context(start_dir, table_path=self.schema.table_path, context=self._context)
            source = _SettingsProfileSource(kind=_SettingsProfileSourceKind.NO_CONFIG if auto_path is None else _SettingsProfileSourceKind.AUTO, config_path=auto_path, cwd_base=cwd_base)

        profile = self._context.profiles_by_source.get(source)
        if profile is None:
            profile = _load_profile_from_source(self.schema, args=self.args, field_overrides=self.field_overrides, cwd_base=cwd_base, source=source, config_inputs=config_inputs, context=self._context)
            self._context.profiles_by_source[source] = profile
        self._profiles_by_start_dir[start_dir] = profile
        return profile


class SettingCLIValueKind(enum.StrEnum):
    """CLI value parsing strategy for a setting.

    Attributes:
        RAW: Use argparse's parsed value directly.
        COMMA_LIST: Split repeated CLI values on commas and return a tuple.
        TOML_MAP: Parse repeated CLI values as TOML inline tables and merge them.
        EXTENSION_MAP: Parse repeated extension-to-language pairs.
    """

    RAW = "raw"
    COMMA_LIST = "comma-list"
    TOML_MAP = "toml-map"
    EXTENSION_MAP = "extension-map"


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
        help: str,  # ruff: ignore[builtin-argument-shadowing]
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
            TypeError: If no default validator exists for `value_type` and no validator is supplied.
        """
        resolved_key = key or field.replace("_", "-")
        resolved_validator = typing.cast("SettingValidator[SettingValueT]", _default_validator_for_type(value_type)) if validator is None else validator
        resolved_documentation = documentation or help
        resolved_example = example or ""

        resolved_cli: SettingCLIDefinition | None
        if available_in_cli:
            if cli is None:
                cli_options: SettingCLIOptions = {}
            elif isinstance(cli, SettingCLIDefinition):
                cli_options = typing.cast("SettingCLIOptions", {field.name: getattr(cli, field.name) for field in dataclasses.fields(cli)})
            else:
                cli_options = typing.cast("SettingCLIOptions", dict(cli))

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
            if value_type is float and cli_type is None:
                cli_type = float
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
                choices = tuple(member.value for member in typing.cast("type[enum.StrEnum]", value_type))

            show_default = cli_options.get("show_default", value_kind == SettingCLIValueKind.RAW)

            resolved_cli = SettingCLIDefinition(flags=flags, action=action, choices=choices, type=cli_type, metavar=metavar, value_kind=value_kind, show_default=show_default)
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
        settings_type (type[SettingsT]): Resolved dataclass type constructed for defaults and returned by config
            loading.
        overrides_type (SettingsOverridesType): TypedDict-like class describing partial field overrides accepted from
            CLI/config layers.
        group_type (type[enum.StrEnum]): Enum type that defines accepted settings groups and argparse group ordering.
        definitions (tuple[SettingDefinition[Any], ...]): Ordered metadata mapping settings dataclass fields to TOML
            keys, CLI options, validation, and help text.
        table_path (tuple[str, ...]): Nested TOML table to read from files named `pyproject.toml`, expressed as
            non-empty path segments. For example, `("tool", "pydocfmt")` reads settings from `[tool.pydocfmt]`. Explicit
            config files with any other basename are treated as dedicated config files and read settings from the
            top-level table instead.
        table_name (str): Dotted TOML table name derived from table_path.
        post_validate (Callable[[dict[str, Any], str], None] | None): Optional validation hook called after per-field
            validation with only the updates from the current layer, keyed by dataclass field name, and a user-facing
            path string. The hook should raise SettingsError for cross-field or domain validation failures and should
            not mutate values.
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
            ValueError: If the TOML table path is empty or contains empty segments.
            TypeError: If a setting definition uses a group outside `group_type`.
            AssertionError: If CLI availability and resolved CLI metadata disagree.
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
            SettingsError: If any configuration source cannot be loaded or validated.
            tomllib.TOMLDecodeError: If a TOML-map CLI value is malformed.
        """
        return self.load_profile(global_values=global_values, args=args, field_overrides=field_overrides).settings

    def resolver(self, *, global_values: GlobalArgs | None = None, args: argparse.Namespace | None = None, field_overrides: Mapping[str, Any] | None = None) -> SettingsResolver[SettingsT]:
        """Return a path-aware settings resolver for repeated per-path lookups.

        Args:
            global_values (GlobalArgs | None): Global configuration options and isolated-mode flag.
            args (argparse.Namespace | None): Parsed CLI namespace for dedicated option overrides.
            field_overrides (Mapping[str, Any] | None): Final field-keyed raw overrides.

        Returns:
            SettingsResolver[SettingsT]: Resolver that caches settings profiles by containing directory.
        """
        return SettingsResolver(schema=self, global_values=GlobalArgs() if global_values is None else global_values, args=args, field_overrides=field_overrides)

    def load_profile(
        self, *, global_values: GlobalArgs | None = None, args: argparse.Namespace | None = None, field_overrides: Mapping[str, Any] | None = None, path: str | None = None
    ) -> SettingsProfile[SettingsT]:
        """Resolve fresh settings and source metadata for one path.

        Args:
            global_values (GlobalArgs | None): Global configuration options and isolated-mode flag.
            args (argparse.Namespace | None): Parsed CLI namespace for dedicated option overrides.
            field_overrides (Mapping[str, Any] | None): Final field-keyed raw overrides.
            path (str | None): Path whose closest auto-discovered configuration should be used, defaulting to cwd.

        Returns:
            SettingsProfile[SettingsT]: Resolved settings plus field source bases and source priorities.

        Raises:
            SettingsError: If any configuration source cannot be loaded or validated.
            tomllib.TOMLDecodeError: If a TOML-map CLI value is malformed.
        """
        return self.resolver(global_values=global_values, args=args, field_overrides=field_overrides).profile_for_path(path)

    def format(self, settings: SettingsT) -> str:
        """Return resolved settings in a stable TOML-like form.

        Args:
            settings (SettingsT): Settings object to render.

        Returns:
            str: TOML-like settings text in schema definition order.
        """
        lines: list[str] = [f"[{self.table_name}]"] if self.table_name else []
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
            AssertionError: If schema definitions cannot be mapped consistently to argparse groups.
        """
        handled_definitions: list[SettingDefinition[Any]] = []
        for group in self.group_type:
            argument_group = parser.add_argument_group(group.value)
            for definition in self.definitions:
                if definition.group == group:
                    handled_definitions.append(definition)
                    if definition.available_in_cli:
                        _add_setting_argument(argument_group, definition, settings)

        if len(handled_definitions) != len(self.definitions):
            handled_fields = {definition.field for definition in handled_definitions}
            missing_fields = tuple(definition.field for definition in self.definitions if definition.field not in handled_fields)
            raise AssertionError(f"Not all settings definitions were added to argparse groups: {', '.join(missing_fields)}")

    def add_argument(self, parser: argparse.ArgumentParser, settings: SettingsT, field: str) -> None:
        """Add one schema-backed CLI setting argument to a parser.

        Args:
            parser (argparse.ArgumentParser): Parser that should receive the setting argument.
            settings (SettingsT): Settings object supplying the current default for help text.
            field (str): Dataclass field whose CLI definition should be added.

        Raises:
            KeyError: If the field is unknown.
            ValueError: If the setting is unavailable on the CLI.
        """
        try:
            definition = next(definition for definition in self.definitions if definition.field == field)
        except StopIteration:
            raise KeyError(field) from None
        if not definition.available_in_cli:
            raise ValueError(f"Setting {field!r} is not available on the CLI")
        _add_setting_argument(parser, definition, settings)

    def argument_overrides(self, args: argparse.Namespace) -> dict[str, Any]:
        """Build settings overrides dict from parsed command-line arguments.

        Args:
            args (argparse.Namespace): Parsed command-line namespace.

        Returns:
            dict[str, Any]: Field-keyed raw override values supplied through dedicated CLI options.

        Raises:
            SettingsError: If a TOML-map CLI value does not parse to a TOML table.
            tomllib.TOMLDecodeError: If a TOML-map CLI value is malformed.
            AssertionError: If a setting has an unknown CLI value kind.
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
                elif definition.cli.value_kind == SettingCLIValueKind.EXTENSION_MAP:
                    pairs: list[tuple[str, str]] = []
                    for group in value:
                        extension, separator, language = group.partition(":")
                        if not separator or not extension or not language:
                            raise SettingsError(f"{definition.cli.flags[-1]} values must use EXT:LANGUAGE")
                        pairs.append((extension, language))
                    values[definition.field] = tuple(pairs)
                else:
                    raise AssertionError(f"Unknown CLI value kind: {definition.cli.value_kind}")
        return values


def _add_setting_argument(parser: argparser_utils.ArgumentContainer, definition: SettingDefinition[Any], settings: Any) -> None:
    """Add one resolved schema definition to an argparse container."""
    if definition.cli is None:
        raise AssertionError(f"Setting definition for {definition.field!r} has no CLI metadata")
    kwargs: dict[str, Any] = {"default": None, "dest": definition.field, "help": _format_cli_help(definition, settings)}
    if definition.cli.action is not None:
        kwargs["action"] = definition.cli.action
    if definition.cli.choices is not None:
        kwargs["choices"] = definition.cli.choices
    if definition.cli.type is not None:
        kwargs["type"] = definition.cli.type
    if definition.cli.metavar is not None:
        kwargs["metavar"] = definition.cli.metavar
    parser.add_argument(*definition.cli.flags, **kwargs)


def _format_cli_help(definition: SettingDefinition[Any], settings: Any) -> str:
    """Return argparse help text for one setting definition."""
    if definition.cli is None or not definition.cli.show_default:
        return definition.help
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
    if value_type_ is str:
        return _format_string(value)
    if value_type_ is float:
        return repr(value)
    if _is_str_enum_type(value_type_):
        return _format_string(value.value)
    if value_type_ == StringList:
        return _format_string_list(value)
    if value_type_ == StringMap:
        return _format_string_map(value)
    if value_type_ == MultiStringMap:
        return _format_multi_string_map(value)
    if value_type_ == PerFileSettingsMap:
        return _format_per_file_settings_map(value)
    return str(value)


def _format_string_list(values: tuple[Any, ...]) -> str:
    """Format values as a TOML list."""
    return "[" + ", ".join(_format_string(value.value if isinstance(value, enum.StrEnum) else value) for value in values) + "]"


def _format_inline_table(value: Any, entry_formatter: Callable[[Any, Any], str]) -> str:
    """Format mapping or iterable pairs as a TOML inline table."""
    items = tuple(value.items()) if isinstance(value, Mapping) else tuple(value)
    entries = list(itertools.starmap(entry_formatter, items))
    return "{" + ", ".join(entries) + "}"


def _format_multi_string_map(value: Any) -> str:
    """Format a string-keyed multi-string mapping as a TOML inline table."""
    return _format_inline_table(value, lambda pattern, selectors: f"{_format_string(pattern)} = {_format_string_list(selectors)}")


def _format_string_map(value: Any) -> str:
    """Format a string-keyed string mapping as a TOML inline table."""
    return _format_inline_table(value, lambda key, item: f"{key} = {_format_string(item)}")


def _format_per_file_settings_map(value: Any) -> str:
    """Format a per-file settings mapping as a TOML inline table."""
    return _format_inline_table(value, lambda pattern, updates: f"{_format_string(pattern)} = {_format_flat_settings_map(updates)}")


def _format_flat_settings_map(value: Any) -> str:
    """Format a flat setting-keyed override mapping as a TOML inline table."""
    return _format_inline_table(value, lambda key, setting_value: f"{key} = {_format_resolved_setting_value(setting_value)}")


def _format_resolved_setting_value(value: Any) -> str:
    """Format one already validated setting value as TOML."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, enum.StrEnum):
        return _format_string(value.value)
    if isinstance(value, str):
        return _format_string(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, tuple):
        return _format_string_list(value)
    return str(value)


def validate_bool(value: Any, context: str) -> bool:
    """Validate and return a boolean setting value.

    Args:
        value (Any): Raw value to validate.
        context (str): User-facing configuration location for error messages.

    Returns:
        bool: Validated boolean value.

    Raises:
        SettingsError: If the raw value is not a boolean.
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
        """Validate one integer setting value.

        Args:
            value (Any): Raw value supplied by a config file, inline override, or CLI conversion.
            context (str): User-facing setting label included in validation errors.

        Returns:
            int: Integer value within the configured bounds.

        Raises:
            SettingsError: If the value is not an integer or violates the bounds captured by the validator.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise SettingsError(f"{context} must be an integer")
        if min_value is not None and value < min_value:
            raise SettingsError(f"{context} must be greater than or equal to {min_value}")
        if max_value is not None and value > max_value:
            raise SettingsError(f"{context} must be less than or equal to {max_value}")
        return value

    return validate


def validate_float(*, min_value: float | None = None, max_value: float | None = None) -> Callable[[Any, str], float]:
    """Return a validator for float settings with optional inclusive bounds.

    Args:
        min_value (float | None): Optional inclusive lower bound.
        max_value (float | None): Optional inclusive upper bound.

    Returns:
        Callable[[Any, str], float]: Validator that converts integer and float values to bounded floats.
    """

    def validate(value: Any, context: str) -> float:
        """Validate one float setting value.

        Args:
            value (Any): Raw numeric value supplied by a config file, inline override, or CLI conversion.
            context (str): User-facing setting label included in validation errors.

        Returns:
            float: Finite float value within the configured bounds.

        Raises:
            SettingsError: If the value is not numeric, is not finite, or violates the bounds captured by the validator.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SettingsError(f"{context} must be a number")
        float_value = float(value)
        if not math.isfinite(float_value):
            raise SettingsError(f"{context} must be finite")
        if min_value is not None and float_value < min_value:
            raise SettingsError(f"{context} must be greater than or equal to {min_value:g}")
        if max_value is not None and float_value > max_value:
            raise SettingsError(f"{context} must be less than or equal to {max_value:g}")
        return float_value

    return validate


def validate_str_enum(enum_class: type[StrEnumT]) -> Callable[[Any, str], StrEnumT]:
    """Return a validator that converts setting values to members of a string enum.

    Args:
        enum_class (type[StrEnumT]): String enum class to validate against.

    Returns:
        Callable[[Any, str], StrEnumT]: Validator that converts raw values to enum members.
    """

    def validate(value: Any, context: str) -> StrEnumT:
        """Validate one string enum setting value.

        Args:
            value (Any): Raw value to convert through the captured enum class.
            context (str): User-facing setting label included in validation errors.

        Returns:
            StrEnumT: Enum member matching the supplied string value.

        Raises:
            SettingsError: If the value is not one of the enum's configured string values.
        """
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
        SettingsError: If the raw value is not a list or tuple of strings.
    """
    if not isinstance(value, (list, tuple)):
        raise SettingsError(f"{context} must be a list of strings")
    validated: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise SettingsError(f"{context} must be a list of strings")
        validated.append(item)
    return tuple(validated)


def validate_non_empty_string_list(value: Any, context: str) -> StringList:
    """Validate and return a tuple of non-empty string list values.

    Args:
        value (Any): Raw value to validate.
        context (str): User-facing configuration location for error messages.

    Returns:
        StringList: Validated string tuple.

    Raises:
        SettingsError: If any item is not a string or is empty.
    """
    values = validate_string_list(value, context)
    if any(not value for value in values):
        raise SettingsError(f"{context} must not contain empty strings")
    return values


def validate_non_empty_path(value: Any, context: str) -> str:
    """Validate a non-empty filesystem path string without changing its spelling.

    Args:
        value (Any): Raw value supplied by a configuration source.
        context (str): User-facing setting label included in validation errors.

    Returns:
        str: Original non-empty path string.

    Raises:
        SettingsError: If the value is not a non-empty string.
    """
    if not isinstance(value, str):
        raise SettingsError(f"{context} must be a string path")
    if not value:
        raise SettingsError(f"{context} must not be empty")
    if "\0" in value:
        raise SettingsError(f"{context} must not contain NUL characters")
    return value


def validate_multi_string_map(value: Any, context: str) -> MultiStringMap:
    """Validate and return a mapping of strings to non-empty string lists.

    Args:
        value (Any): Raw mapping or tuple of key/value pairs to validate.
        context (str): User-facing configuration location for error messages.

    Returns:
        MultiStringMap: Validated tuple of string keys and non-empty string-list values.

    Raises:
        SettingsError: If the raw value is not a string-keyed mapping to non-empty string lists.
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
    if setting_type is int:
        return validate_int()
    if setting_type is float:
        return validate_float()
    if _is_str_enum_type(setting_type):
        return validate_str_enum(typing.cast("type[enum.StrEnum]", setting_type))
    if setting_type == StringList:
        return validate_string_list
    if setting_type == MultiStringMap:
        return validate_multi_string_map
    raise TypeError(f"No default validator for setting type: {setting_type!r}")


def _is_str_enum_type(setting_type: Any) -> bool:
    """Return whether a setting type is a string enum class."""
    return isinstance(setting_type, type) and issubclass(setting_type, enum.StrEnum)


def _load_toml_file(path: str, *, required: bool) -> dict[str, Any] | None:
    """Load a TOML file, returning None if an optional file is absent."""
    try:
        with open(path, "rb") as config_file:
            config = tomllib.load(config_file)
    except FileNotFoundError as error:
        if required:
            raise SettingsError(f"Configuration file not found: {path}") from error
        return None
    except OSError as error:
        raise SettingsError(f"Failed to read configuration file {path}: {error}") from error
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


def _auto_discovered_pyproject_path_for_path_with_context(path: str | None, *, table_path: tuple[str, ...], context: _SettingsResolutionContext[Any]) -> str | None:
    """Return the closest containing pyproject with child-first ancestor caching.

    Every uncached directory examines its own candidate before consulting a cached parent so an earlier parent lookup
    cannot hide an existing nested configuration.

    Args:
        path (str | None): File or directory whose containing ancestors should be searched, defaulting to cwd.
        table_path (tuple[str, ...]): Nested TOML table that makes a candidate applicable.
        context (_SettingsResolutionContext[Any]): Resolver-owned parsed-document and closest-result snapshot.

    Returns:
        str | None: Absolute closest applicable pyproject path, or None when no ancestor matches.

    Raises:
        SettingsError: If an existing candidate cannot be read, decoded, or traversed as the requested table shape.
    """
    current_dir = _settings_start_dir(path)
    visited: list[str] = []
    result: str | None
    while True:
        if current_dir in context.closest_auto_config_by_start_dir:
            result = context.closest_auto_config_by_start_dir[current_dir]
            break

        candidate = os.path.join(current_dir, "pyproject.toml")
        if os.path.exists(candidate):
            config = context.load_toml_file(candidate, required=True)
            if config is not None and _toml_section_at_table_path(config, path=candidate, table_path=table_path, required=False) is not None:
                result = candidate
                context.closest_auto_config_by_start_dir[current_dir] = result
                break

        visited.append(current_dir)
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            result = None
            break
        current_dir = parent_dir

    for visited_dir in visited:
        context.closest_auto_config_by_start_dir[visited_dir] = result
    return result


def _load_profile_from_source(
    schema: SettingsSchema[SettingsT],
    *,
    args: argparse.Namespace | None,
    field_overrides: Mapping[str, Any] | None,
    cwd_base: str,
    source: _SettingsProfileSource,
    config_inputs: _SettingsConfigInputs,
    context: _SettingsResolutionContext[SettingsT],
) -> SettingsProfile[SettingsT]:
    """Build one fully layered profile from an already resolved source identity.

    Args:
        schema (SettingsSchema[SettingsT]): Schema used for defaults, validation, and layer application.
        args (argparse.Namespace | None): Parsed command arguments applied after file and inline layers.
        field_overrides (Mapping[str, Any] | None): Programmatic overrides applied at the highest priority.
        cwd_base (str): Lookup-time working directory used for defaults and non-auto source bases.
        source (_SettingsProfileSource): Already discovered source kind, path, and working-directory identity.
        config_inputs (_SettingsConfigInputs): Classified and lazily parsed global config inputs for `cwd_base`.
        context (_SettingsResolutionContext[SettingsT]): Resolver-owned parsed-document and lazy-override snapshot.

    Returns:
        SettingsProfile[SettingsT]: Frozen resolved settings and source metadata.

    Raises:
        SettingsError: If any file, inline, argument, or field layer cannot be loaded or validated.
        tomllib.TOMLDecodeError: If a TOML-map command argument cannot be decoded.
    """
    profile = SettingsProfile(
        settings=schema.settings_type(),
        field_bases={definition.field: cwd_base for definition in schema.definitions},
        field_priorities={definition.field: DEFAULT_SOURCE_PRIORITY for definition in schema.definitions},
        project_root=cwd_base,
    )

    if source.kind is _SettingsProfileSourceKind.EXPLICIT:
        config_path = typing.cast("str", source.config_path)
        profile = _apply_toml_file_profile(schema, profile, path=config_path, required=True, source_base=cwd_base, source_priority=CONFIG_FILE_SOURCE_PRIORITY, context=context)
    elif source.kind is _SettingsProfileSourceKind.AUTO:
        config_path = typing.cast("str", source.config_path)
        project_root = os.path.dirname(os.path.abspath(config_path))
        profile = dataclasses.replace(profile, project_root=project_root)
        profile = _apply_toml_file_profile(schema, profile, path=config_path, required=False, source_base=project_root, source_priority=CONFIG_FILE_SOURCE_PRIORITY, context=context)

    for section in context.inline_sections(config_inputs):
        profile = _apply_toml_section_profile(schema, profile, section=section, context="<--config>", source_base=cwd_base, source_priority=INLINE_CONFIG_SOURCE_PRIORITY)

    argument_overrides = context.argument_overrides_for(schema, args)
    if argument_overrides:
        profile = _apply_field_values_profile(schema, profile, values=argument_overrides, context="<argparse>", key_based=False, source_base=cwd_base, source_priority=ARGUMENT_SOURCE_PRIORITY)

    if field_overrides:
        profile = _apply_field_values_profile(schema, profile, values=field_overrides, context="<overrides>", key_based=False, source_base=cwd_base, source_priority=FIELD_OVERRIDE_SOURCE_PRIORITY)

    return profile


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
    return typing.cast("dict[str, Any]", section)


def _apply_toml_file_profile(
    schema: SettingsSchema[SettingsT], profile: SettingsProfile[SettingsT], *, path: str, required: bool, source_base: str, source_priority: int, context: _SettingsResolutionContext[SettingsT]
) -> SettingsProfile[SettingsT]:
    """Apply one resolver-cached config file to the passed settings profile.

    Args:
        schema (SettingsSchema[SettingsT]): Schema used to locate and validate the applicable settings table.
        profile (SettingsProfile[SettingsT]): Profile to update from the selected file.
        path (str): Original config path spelling retained for loading and error context.
        required (bool): Whether an absent file or pyproject settings table raises.
        source_base (str): Base assigned to fields updated by this file.
        source_priority (int): Priority assigned to fields updated by this file.
        context (_SettingsResolutionContext[SettingsT]): Resolver-owned successful-document cache.

    Returns:
        SettingsProfile[SettingsT]: Updated profile, or the input profile for an optional absent source.

    Raises:
        SettingsError: If the file or applicable table cannot be loaded or validated.
    """
    # Only returns None if the file is both absent and not required
    section = context.load_toml_file(path, required=required)
    if section is None:
        return profile

    if os.path.basename(path) == "pyproject.toml":
        # Only returns None if the section is both absent and not required
        section = _toml_section_at_table_path(section, path=path, table_path=schema.table_path, required=required)
        if section is None:
            return profile
        section_context = f"<{path}>.{schema.table_name}"
    else:
        section_context = f"<{path}>"

    return _apply_toml_section_profile(schema, profile, section=section, context=section_context, source_base=source_base, source_priority=source_priority)


def _apply_toml_section_profile(
    schema: SettingsSchema[SettingsT], profile: SettingsProfile[SettingsT], *, section: dict[str, Any], context: str, source_base: str, source_priority: int
) -> SettingsProfile[SettingsT]:
    """Apply one TOML configuration section to a settings profile."""
    section = _flatten_prefixed_toml_setting_tables(section, prefixes=("docstring", "comment"), context=context)
    schema_toml_keys = {definition.key for definition in schema.definitions if definition.available_in_toml}
    unknown_keys = [key for key in section if key not in schema_toml_keys]
    if unknown_keys:
        unknown_keys.sort()
        joined_keys = ", ".join(unknown_keys)
        raise SettingsError(f"{context} contains unknown setting(s): {joined_keys}")

    values = {definition.field: section[definition.key] for definition in schema.definitions if definition.available_in_toml and definition.key in section}
    return _apply_field_values_profile(schema, profile, values=values, context=context, key_based=True, source_base=source_base, source_priority=source_priority)


def _flatten_prefixed_toml_setting_tables(section: dict[str, Any], *, prefixes: tuple[str, ...], context: str) -> dict[str, Any]:
    """Return a TOML section with supported one-level prefix tables flattened."""
    flattened = dict(section)
    for prefix in prefixes:
        if prefix not in flattened:
            continue
        table = flattened.pop(prefix)
        if not isinstance(table, dict):
            raise SettingsError(f"{context}.{prefix} must be a table")
        for key, value in table.items():
            flat_key = f"{prefix}-{key}"
            if isinstance(value, dict):
                raise SettingsError(f"{context}.{flat_key} must not be a table")
            if flat_key in flattened:
                raise SettingsError(f"{context} sets {flat_key} more than once")
            flattened[flat_key] = value
    return flattened


def _validated_field_updates(schema: SettingsSchema[SettingsT], *, values: Mapping[str, Any], context: str, key_based: bool) -> dict[str, Any]:
    """Validate raw field values and return resolved field updates."""
    definitions_by_field = {definition.field: definition for definition in schema.definitions}
    updates: dict[str, Any] = {}
    for field, value in values.items():
        definition = definitions_by_field.get(field)
        if definition is None:
            raise SettingsError(f"Unknown setting: {field}")
        updates[field] = definition.validator(value, f"{context}.{definition.key if key_based else field}")
    if schema.post_validate is not None:
        schema.post_validate(updates, context)
    return updates


def _apply_field_values_profile(
    schema: SettingsSchema[SettingsT], profile: SettingsProfile[SettingsT], *, values: Mapping[str, Any], context: str, key_based: bool, source_base: str, source_priority: int
) -> SettingsProfile[SettingsT]:
    """Validate raw field values and return an updated settings profile."""
    updates = _validated_field_updates(schema, values=values, context=context, key_based=key_based)
    settings = typing.cast("SettingsT", dataclasses.replace(typing.cast("Any", profile.settings), **updates))
    field_bases = dict(profile.field_bases)
    field_priorities = dict(profile.field_priorities)
    absolute_source_base = os.path.abspath(source_base)
    for field in updates:
        field_bases[field] = absolute_source_base
        field_priorities[field] = source_priority
    return SettingsProfile(settings=settings, field_bases=field_bases, field_priorities=field_priorities, project_root=profile.project_root)
