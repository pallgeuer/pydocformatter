import dataclasses
import enum
from typing import TypedDict

import pydocformatter.rules.models as rule_models
import pydocformatter.settings as settings_core
from pydocformatter.settings import MultiStringMap, SettingDefinition, SettingsSchema, StringList

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
DEFAULT_RULE_SELECT = (rule_models.ALL_RULE_SELECTOR_TAG,)
DEFAULT_RULE_FIXABLE = (rule_models.ALL_RULE_SELECTOR_TAG,)


class IndentStyle(enum.StrEnum):
    """Indentation styles for generated docstring sections.

    Attributes:
        SPACE (IndentStyle): Use spaces for generated section indentation.
        TAB (IndentStyle): Use tabs for generated section indentation.
    """

    SPACE = "space"
    TAB = "tab"


class LineEnding(enum.StrEnum):
    """Line ending modes for rewritten files.

    Attributes:
        AUTO (LineEnding): Preserve the first detected line ending in each file, defaulting to LF.
        LF (LineEnding): Rewrite generated lines with LF endings.
        CR_LF (LineEnding): Rewrite generated lines with CRLF endings.
        NATIVE (LineEnding): Rewrite generated lines with the platform-native line ending.
    """

    AUTO = "auto"
    LF = "lf"
    CR_LF = "cr-lf"
    NATIVE = "native"


class OutputFormat(enum.StrEnum):
    """Output formats for rule findings.

    Attributes:
        GROUPED (OutputFormat): Group diagnostics by file.
    """

    GROUPED = "grouped"


@dataclasses.dataclass(frozen=True)
class CheckSettings:
    """Resolved formatter settings for pydocformatter.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        experimental (bool): Whether to use the experimental rule-based formatter implementation.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated docstring section indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        select (StringList): Base selected pydocformatter rule selectors.
        ignore (StringList): Rule selectors to ignore.
        extend_select (StringList): Additional selected rule selectors.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
        fixable (StringList): Rule selectors eligible for automatic fixes.
        unfixable (StringList): Rule selectors ineligible for automatic fixes.
        extend_fixable (StringList): Additional fixable rule selectors.
        include (StringList): Base glob patterns that identify format-eligible files.
        extend_include (StringList): Additional include glob patterns appended to `include`.
        exclude (StringList): Base glob patterns for files or directories to ignore.
        extend_exclude (StringList): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether exclude rules apply to explicitly passed paths.
    """

    output_format: OutputFormat = OutputFormat.GROUPED
    experimental: bool = False
    line_length: int = 88
    line_ending: LineEnding = LineEnding.AUTO
    indent_style: IndentStyle = IndentStyle.SPACE
    indent_width: int = 4
    select: StringList = DEFAULT_RULE_SELECT
    ignore: StringList = ()
    extend_select: StringList = ()
    per_file_ignores: MultiStringMap = ()
    extend_per_file_ignores: MultiStringMap = ()
    fixable: StringList = DEFAULT_RULE_FIXABLE
    unfixable: StringList = ()
    extend_fixable: StringList = ()
    include: StringList = DEFAULT_INCLUDE
    extend_include: StringList = ()
    exclude: StringList = DEFAULT_EXCLUDE
    extend_exclude: StringList = ()
    respect_gitignore: bool = True
    force_exclude: bool = False

    @property
    def include_patterns(self) -> tuple[str, ...]:
        """Return the final include patterns used by file selection.

        Returns:
            tuple[str, ...]: Base include patterns followed by extension include patterns.
        """
        return self.include + self.extend_include

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Return the final exclude patterns used by file selection.

        Returns:
            tuple[str, ...]: Base exclude patterns followed by extension exclude patterns.
        """
        return self.exclude + self.extend_exclude


class CheckSettingsOverrides(TypedDict, total=False):
    """Formatter settings supplied by one precedence layer.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        experimental (bool): Whether to use the experimental rule-based formatter implementation.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated docstring section indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        select (StringList): Base selected pydocformatter rule selectors.
        ignore (StringList): Rule selectors to ignore.
        extend_select (StringList): Additional selected rule selectors.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
        fixable (StringList): Rule selectors eligible for automatic fixes.
        unfixable (StringList): Rule selectors ineligible for automatic fixes.
        extend_fixable (StringList): Additional fixable rule selectors.
        include (StringList): Base glob patterns that identify format-eligible files.
        extend_include (StringList): Additional include glob patterns appended to `include`.
        exclude (StringList): Base glob patterns for files or directories to ignore.
        extend_exclude (StringList): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether exclude rules apply to explicitly passed paths.
    """

    output_format: OutputFormat
    experimental: bool
    line_length: int
    line_ending: LineEnding
    indent_style: IndentStyle
    indent_width: int
    select: StringList
    ignore: StringList
    extend_select: StringList
    per_file_ignores: MultiStringMap
    extend_per_file_ignores: MultiStringMap
    fixable: StringList
    unfixable: StringList
    extend_fixable: StringList
    include: StringList
    extend_include: StringList
    exclude: StringList
    extend_exclude: StringList
    respect_gitignore: bool
    force_exclude: bool


class SettingsGroup(enum.StrEnum):
    """Check settings groups used for ordered CLI/help presentation.

    Attributes:
        FORMATTING (SettingsGroup): Formatting behavior settings.
        RULE_SELECTION (SettingsGroup): Rule selection settings.
        FILE_SELECTION (SettingsGroup): File discovery and filtering settings.
    """

    FORMATTING = "Formatting"
    RULE_SELECTION = "Rule selection"
    FILE_SELECTION = "File selection"


SETTINGS_SCHEMA = SettingsSchema(
    settings_type=CheckSettings,
    overrides_type=CheckSettingsOverrides,
    group_type=SettingsGroup,
    definitions=(
        SettingDefinition(
            field="output_format",
            value_type=OutputFormat,
            group=SettingsGroup.FORMATTING,
            help="Output format for experimental rule findings.",
            documentation='Output format for rule findings; currently only "grouped" is supported.',
        ),
        SettingDefinition(
            field="experimental",
            value_type=bool,
            group=SettingsGroup.FORMATTING,
            help="Use the experimental rule-based formatter implementation.",
        ),
        SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Maximum line length for docstrings and comments.",
            validator=settings_core.validate_int(min_value=1, max_value=320),
            cli={"metavar": "LENGTH"},
        ),
        SettingDefinition(
            field="line_ending",
            value_type=LineEnding,
            group=SettingsGroup.FORMATTING,
            help="Line ending to use when rewriting files.",
            documentation='Line ending to use when rewriting files; one of "auto", "lf", "cr-lf", or "native".',
        ),
        SettingDefinition(
            field="indent_style",
            value_type=IndentStyle,
            group=SettingsGroup.FORMATTING,
            help="Indentation style for generated docstring sections.",
            documentation='Generated docstring section indentation style; one of "space" or "tab".',
        ),
        SettingDefinition(
            field="indent_width",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Indentation width for generated docstring sections.",
            validator=settings_core.validate_int(min_value=1, max_value=255),
            cli={"metavar": "WIDTH"},
            documentation="Generated docstring section indentation width.",
        ),
        SettingDefinition(
            field="select",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) to enable.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation='Rule selectors to enable; defaults to ["ALL"].',
        ),
        SettingDefinition(
            field="ignore",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) to ignore.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Rule selectors to ignore.",
        ),
        SettingDefinition(
            field="extend_select",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated additional rule selector(s) to enable.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Additional rule selectors to enable.",
        ),
        SettingDefinition(
            field="per_file_ignores",
            value_type=MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            help="TOML inline table mapping file patterns to ignored rule selectors.",
            cli={"metavar": "RULE_TOML"},
            documentation="File-pattern-specific ignored rule selectors.",
        ),
        SettingDefinition(
            field="extend_per_file_ignores",
            value_type=MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            help="TOML inline table mapping file patterns to additional ignored rule selectors.",
            cli={"metavar": "RULE_TOML"},
            documentation="Additional file-pattern-specific ignored rule selectors.",
        ),
        SettingDefinition(
            field="fixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) eligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation='Rule selectors eligible for automatic fixes; defaults to ["ALL"].',
        ),
        SettingDefinition(
            field="unfixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) ineligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Rule selectors ineligible for automatic fixes.",
        ),
        SettingDefinition(
            field="extend_fixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated additional rule selector(s) eligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Additional rule selectors eligible for automatic fixes.",
        ),
        SettingDefinition(
            field="include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated glob pattern(s) for files to include.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Glob patterns for files to include.",
        ),
        SettingDefinition(
            field="extend_include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated additional glob pattern(s) for files to include.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Additional include glob patterns.",
        ),
        SettingDefinition(
            field="exclude",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated glob pattern(s) for files or directories to exclude.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Glob patterns for files/directories to exclude.",
        ),
        SettingDefinition(
            field="extend_exclude",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated additional glob pattern(s) for files or directories to exclude.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Additional exclude glob patterns.",
        ),
        SettingDefinition(
            field="respect_gitignore",
            value_type=bool,
            group=SettingsGroup.FILE_SELECTION,
            help="Respect .gitignore when discovering files.",
        ),
        SettingDefinition(
            field="force_exclude",
            value_type=bool,
            group=SettingsGroup.FILE_SELECTION,
            help="Apply exclude rules even to files passed explicitly.",
        ),
    ),
    table_path=("tool", "pydocfmt"),
)
