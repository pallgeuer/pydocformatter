import argparse
import sys
from collections.abc import Callable

from pydocformatter.config import (
    ConfigError,
    FormatterSettings,
    SettingsOverrides,
    ToolName,
    apply_cli_overrides,
    load_config,
)
from pydocformatter.file_selection import FileDecision, select_files

FormatFile = Callable[[str, int, bool], bool]


def load_settings_or_exit(tool_name: ToolName) -> FormatterSettings:
    """Load pyproject settings or exit with a command-line error."""
    try:
        return load_config(tool_name)
    except ConfigError as error:
        print(f"{tool_name}: configuration error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


def add_common_arguments(
    parser: argparse.ArgumentParser,
    settings: FormatterSettings,
    *,
    line_length_subject: str,
) -> None:
    """Add shared CLI arguments for pydocformatter tools."""
    parser.add_argument("files", nargs="+", help="Python files to format.")
    parser.add_argument(
        "--line-length",
        type=int,
        default=None,
        help=f"Maximum line length for {line_length_subject} (default: {settings.line_length}).",
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
        help="Apply include/exclude/gitignore rules even to files passed explicitly.",
    )


def resolve_cli_settings(
    parser: argparse.ArgumentParser,
    settings: FormatterSettings,
    args: argparse.Namespace,
) -> FormatterSettings:
    """Apply parsed command-line settings to resolved config settings."""
    overrides = SettingsOverrides(
        line_length=args.line_length,
        respect_gitignore=args.respect_gitignore,
        force_exclude=args.force_exclude,
        include=_flatten_option_groups(args.include),
        extend_include=_flatten_option_groups(args.extend_include),
        exclude=_flatten_option_groups(args.exclude),
        extend_exclude=_flatten_option_groups(args.extend_exclude),
    )
    try:
        return apply_cli_overrides(settings, overrides)
    except ConfigError as error:
        parser.error(str(error))


def run_formatter(
    *,
    tool_name: ToolName,
    description: str,
    line_length_subject: str,
    format_file: FormatFile,
) -> None:
    """Run a formatter CLI with shared argument and file-selection behavior."""
    parser = argparse.ArgumentParser(description=description)
    add_common_arguments(
        parser,
        FormatterSettings(),
        line_length_subject=line_length_subject,
    )
    args = parser.parse_args()

    configured_settings = load_settings_or_exit(tool_name)
    settings = resolve_cli_settings(parser, configured_settings, args)

    selection = select_files(args.files, settings)
    if args.verbose:
        print_verbose_decisions(selection.decisions)

    modified = False
    for path in selection.accepted_files:
        try:
            changed = format_file(path, settings.line_length, args.check)
        except UnicodeDecodeError as error:
            print(f"{path} ignored WARNING: failed to decode as UTF-8 ({error})")
            continue
        except OSError as error:
            print(f"{path} ignored WARNING: failed to read or write file ({error})")
            continue
        if changed:
            modified = True

    if args.check and modified:
        sys.exit(1)


def print_verbose_decisions(decisions: tuple[FileDecision, ...]) -> None:
    """Print file-selection decisions in verbose mode."""
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} included")
        else:
            print(f"{decision.path} ignored: {decision.message}")


def _flatten_option_groups(groups: list[list[str]] | None) -> tuple[str, ...] | None:
    if groups is None:
        return None
    return tuple(value for group in groups for value in group)


def _enabled_label(value: bool) -> str:
    return "enabled" if value else "disabled"
