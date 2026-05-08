import argparse
import sys
import tomllib
from collections.abc import Callable

import pydocformatter.config as config
import pydocformatter.file_selection as file_selection
import pydocformatter.types as formatter_types

FormatFile = Callable[[str, config.FormatterSettings, bool], bool]


def add_common_arguments(
    parser: argparse.ArgumentParser,
    settings: config.FormatterSettings,
    *,
    tool_name: formatter_types.ToolName,
    line_length_subject: str,
) -> None:
    """Add CLI arguments for one pydocformatter tool."""
    parser.add_argument(
        "files",
        nargs="*",
        default=["."],
        help="Python files to format (default: current directory).",
    )
    parser.add_argument(
        "--line-length",
        type=int,
        default=None,
        help=f"Maximum line length for {line_length_subject} (default: {settings.line_length}).",
    )
    if tool_name == "pydocfmt":
        parser.add_argument(
            "--indent-style",
            choices=("space", "tab"),
            default=None,
            help=f"Indentation style for generated docstring sections (default: {settings.indent_style}).",
        )
        parser.add_argument(
            "--indent-width",
            type=int,
            default=None,
            help=f"Indentation width for generated docstring sections (default: {settings.indent_width}).",
        )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files are formatted correctly without modifying them.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Glob pattern(s) for files to include.",
    )
    parser.add_argument(
        "--extend-include",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Additional glob pattern(s) for files to include.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Glob pattern(s) for files to exclude.",
    )
    parser.add_argument(
        "--extend-exclude",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Additional glob pattern(s) for files to exclude.",
    )
    parser.add_argument(
        "--select",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) to enable.",
    )
    parser.add_argument(
        "--extend-select",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Additional rule selector(s) to enable.",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) to ignore.",
    )
    parser.add_argument(
        "--fixable",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) eligible for automatic fixes.",
    )
    parser.add_argument(
        "--extend-fixable",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Additional rule selector(s) eligible for automatic fixes.",
    )
    parser.add_argument(
        "--unfixable",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) ineligible for automatic fixes.",
    )
    parser.add_argument(
        "--per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to ignored rule selectors.",
    )
    parser.add_argument(
        "--extend-per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to additional ignored rule selectors.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit messages about included and ignored files.",
    )
    parser.add_argument(
        "--respect-gitignore",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Respect .gitignore when discovering files "
            f"(default: {_enabled_label(settings.respect_gitignore)})."
        ),
    )
    parser.add_argument(
        "--force-exclude",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Apply include/exclude/gitignore rules even to files passed explicitly (default: {_enabled_label(settings.force_exclude)}).",
    )


def load_settings(
    tool_name: formatter_types.ToolName,
    args: argparse.Namespace,
) -> config.FormatterSettings | None:
    """Load settings with command-line overrides, returning None on failure."""
    try:
        overrides = _settings_overrides_from_args(args)
        return config.load_config(tool_name, overrides)
    except config.ConfigError as error:
        print(f"{tool_name}: configuration error: {error}", file=sys.stderr)
        return None
    except tomllib.TOMLDecodeError as error:
        print(
            f"{tool_name}: configuration error: invalid TOML inline table: {error}",
            file=sys.stderr,
        )
        return None


def run_formatter(
    *,
    tool_name: formatter_types.ToolName,
    description: str,
    line_length_subject: str,
    format_file: FormatFile,
) -> int:
    """Run a formatter CLI with shared argument and file-selection behavior."""
    parser = argparse.ArgumentParser(description=description)
    add_common_arguments(
        parser,
        config.FormatterSettings(),
        tool_name=tool_name,
        line_length_subject=line_length_subject,
    )
    args = parser.parse_args()

    settings = load_settings(tool_name, args)
    if settings is None:
        return 2

    selection = file_selection.select_files(args.files, settings)
    if args.verbose:
        print_verbose_decisions(selection.decisions)

    modified = False
    for path in selection.accepted_files:
        try:
            changed = format_file(path, settings, args.check)
        except UnicodeDecodeError as error:
            print(f"{path} ignored WARNING: failed to decode as UTF-8 ({error})")
            continue
        except OSError as error:
            print(f"{path} ignored WARNING: failed to read or write file ({error})")
            continue
        if changed:
            modified = True

    return 1 if args.check and modified else 0


def print_verbose_decisions(decisions: tuple[file_selection.FileDecision, ...]) -> None:
    """Print file-selection decisions in verbose mode."""
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} included")
        else:
            print(f"{decision.path} ignored: {decision.message}")


def _settings_overrides_from_args(args: argparse.Namespace) -> config.SettingsOverrides:
    """Build settings overrides from parsed command-line arguments."""
    return config.SettingsOverrides(
        line_length=args.line_length,
        indent_style=getattr(args, "indent_style", None),
        indent_width=getattr(args, "indent_width", None),
        respect_gitignore=args.respect_gitignore,
        force_exclude=args.force_exclude,
        include=_flatten_option_groups(args.include),
        extend_include=_flatten_option_groups(args.extend_include),
        exclude=_flatten_option_groups(args.exclude),
        extend_exclude=_flatten_option_groups(args.extend_exclude),
        select=_flatten_option_groups(args.select),
        extend_select=_flatten_option_groups(args.extend_select),
        ignore=_flatten_option_groups(args.ignore),
        fixable=_flatten_option_groups(args.fixable),
        extend_fixable=_flatten_option_groups(args.extend_fixable),
        unfixable=_flatten_option_groups(args.unfixable),
        per_file_ignores=_parse_per_file_options(args.per_file_ignores),
        extend_per_file_ignores=_parse_per_file_options(args.extend_per_file_ignores),
    )


def _flatten_option_groups(groups: list[list[str]] | None) -> tuple[str, ...] | None:
    """Flatten repeated CLI option groups while preserving an omitted option as None."""
    if groups is None:
        return None
    return tuple(value for group in groups for value in group)


def _parse_per_file_options(groups: list[str] | None) -> config.RuleSelectorMap | None:
    """Parse repeated TOML inline per-file ignore maps from CLI options."""
    if groups is None:
        return None

    merged: dict[str, tuple[str, ...]] = {}
    for group in groups:
        parsed = tomllib.loads(f"value = {group}")
        value = parsed["value"]
        if not isinstance(value, dict):
            raise config.ConfigError("per-file ignore CLI value must be a TOML table")
        for pattern, selectors in value.items():
            if not isinstance(pattern, str):
                raise config.ConfigError("per-file ignore CLI patterns must be strings")
            if not isinstance(selectors, (list, tuple)) or not all(
                isinstance(selector, str) for selector in selectors
            ):
                raise config.ConfigError(
                    "per-file ignore CLI selectors must be lists of strings"
                )
            merged[pattern] = tuple(selectors)
    return tuple((pattern, selectors) for pattern, selectors in merged.items())


def _enabled_label(value: bool) -> str:
    """Return a human-readable enabled state."""
    return "enabled" if value else "disabled"
