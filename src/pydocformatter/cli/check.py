from __future__ import annotations

import argparse
import contextlib
import os
import sys
import tomllib
import typing
from collections import defaultdict
from collections.abc import Iterator

import pydocformatter.config as config
import pydocformatter.file_selection as file_selection
import pydocformatter.formatter as formatter
import pydocformatter.formatters.pydocfmt as pydocfmt
import pydocformatter.utils.diagnostics as diagnostics
from pydocformatter.formatter import FormatterResult, Rule, RuleFinding

LEGACY_CHECK_RULE = Rule(rule_code="000", rule_name="legacy-formatting-needed", message="Needs formatting", fixable=True)


class OutputError(Exception):
    """Raised when an output stream cannot be opened or prepared."""


def add_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    settings: config.FormatterSettings,
    formatter_class: type[argparse.HelpFormatter],
) -> argparse.ArgumentParser:
    """Add the check subcommand parser."""
    parser = subparsers.add_parser(
        "check",
        description="Check and optionally fix Python docstrings and comments.",
        help="Check and optionally fix Python docstrings and comments",
        formatter_class=formatter_class,
    )
    add_arguments(parser, settings)
    parser.set_defaults(func=run)
    return parser


def add_arguments(parser: argparse.ArgumentParser, settings: config.FormatterSettings) -> None:
    """Add CLI arguments for the check subcommand."""
    arguments = parser.add_argument_group("Arguments")
    arguments.add_argument(
        "files",
        nargs="*",
        default=None,
        metavar="PATH",
        help="Python files or directories to check, or '-' to read from stdin (default: current directory).",
    )

    options = parser.add_argument_group("Options")
    options.add_argument(
        "--fix",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Apply fixes instead of only checking for needed changes.",
    )
    options.add_argument(
        "--output-format",
        choices=("grouped",),
        default=None,
        help=f"Output format for experimental rule findings (default: {settings.output_format}).",
    )
    options.add_argument(
        "-o",
        "--output-file",
        default=None,
        metavar="FILE",
        help="Specify file to write output to (default: stdout).",
    )
    options.add_argument(
        "--show-files",
        action="store_true",
        help="Show file-selection decisions without checking or fixing files.",
    )
    options.add_argument(
        "--show-settings",
        action="store_true",
        help="Show resolved settings without checking or fixing files.",
    )
    options.add_argument(
        "--experimental",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Use the experimental rule-based formatter implementation (default: {config._enabled_label(settings.experimental)}).",
    )

    formatting = parser.add_argument_group("Formatting")
    formatting.add_argument(
        "--line-length",
        type=int,
        default=None,
        metavar="LENGTH",
        help=f"Maximum line length for docstrings and comments (default: {settings.line_length}).",
    )
    formatting.add_argument(
        "--line-ending",
        choices=("auto", "lf", "cr-lf", "native"),
        default=None,
        help=f"Line ending to use when rewriting files (default: {settings.line_ending}).",
    )
    formatting.add_argument(
        "--indent-style",
        choices=("space", "tab"),
        default=None,
        help=f"Indentation style for generated docstring sections (default: {settings.indent_style}).",
    )
    formatting.add_argument(
        "--indent-width",
        type=int,
        default=None,
        metavar="WIDTH",
        help=f"Indentation width for generated docstring sections (default: {settings.indent_width}).",
    )

    rule_selection = parser.add_argument_group("Rule selection")
    rule_selection.add_argument(
        "--select",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) to enable.",
    )
    rule_selection.add_argument(
        "--ignore",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) to ignore.",
    )
    rule_selection.add_argument(
        "--extend-select",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated additional rule selector(s) to enable.",
    )
    rule_selection.add_argument(
        "--per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to ignored rule selectors.",
    )
    rule_selection.add_argument(
        "--extend-per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to additional ignored rule selectors.",
    )
    rule_selection.add_argument(
        "--fixable",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) eligible for automatic fixes.",
    )
    rule_selection.add_argument(
        "--unfixable",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) ineligible for automatic fixes.",
    )
    rule_selection.add_argument(
        "--extend-fixable",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated additional rule selector(s) eligible for automatic fixes.",
    )

    file_selection_group = parser.add_argument_group("File selection")
    file_selection_group.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated glob pattern(s) for files to include.",
    )
    file_selection_group.add_argument(
        "--extend-include",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated additional glob pattern(s) for files to include.",
    )
    file_selection_group.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated glob pattern(s) for files or directories to exclude.",
    )
    file_selection_group.add_argument(
        "--extend-exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated additional glob pattern(s) for files or directories to exclude.",
    )
    file_selection_group.add_argument(
        "--respect-gitignore",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Respect .gitignore when discovering files (default: {config._enabled_label(settings.respect_gitignore)}).",
    )
    file_selection_group.add_argument(
        "--force-exclude",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Apply include/exclude/gitignore rules even to files passed explicitly (default: {config._enabled_label(settings.force_exclude)}).",
    )

    miscellaneous = parser.add_argument_group("Miscellaneous")
    miscellaneous.add_argument(
        "--stdin-filename",
        default=None,
        metavar="FILENAME",
        help="The name of the file when passing it through stdin.",
    )
    exit_options = miscellaneous.add_mutually_exclusive_group()
    exit_options.add_argument(
        "-e",
        "--exit-zero",
        action="store_true",
        help='Exit with status code "0", even upon detecting formatting violations.',
    )
    exit_options.add_argument(
        "--exit-non-zero-on-fix",
        action="store_true",
        help="Exit with a non-zero status code if any files were modified via fix, even if no formatting violations remain.",
    )

    config.add_global_arguments(parser, dest_prefix="command")


@contextlib.contextmanager
def output_stream(output_file: str | None) -> Iterator[typing.TextIO | None]:
    """Yield the configured output stream."""
    if output_file is None:
        yield None
        return

    parent = os.path.dirname(output_file)
    try:
        if parent:
            try:
                os.mkdir(parent)
            except FileExistsError:
                pass
        file = open(output_file, "w", encoding="utf-8", newline="")
    except OSError as error:
        raise OutputError(str(error)) from error
    with file:
        yield file


def run(args: argparse.Namespace) -> int:
    """Run the check subcommand."""
    if args.show_files and args.show_settings:
        print("pydocfmt check: Argument error: Cannot use --show-files and --show-settings together", file=sys.stderr)
        return 2

    settings = load_settings(args)
    if settings is None:
        return 2

    errors: list[str] = []
    try:
        if args.show_settings:
            with output_stream(args.output_file) as output:
                print_settings(settings, output=output)
            return 0

        use_stdin = False
        if args.stdin_filename is not None:
            files = [args.stdin_filename]
            use_stdin = True
        elif args.files:
            if "-" in args.files:
                files = ["-"]
                use_stdin = True
            else:
                files = args.files
        else:
            files = ["."]

        if use_stdin:
            if args.files:
                errors.extend(f"Using standard input instead of input path: {path}" for path in args.files if path != "-")
            selection = file_selection.SelectionResult(
                accepted_paths=tuple(files),
                decisions=tuple(file_selection.FileDecision(path=file, accepted=True, reason=file_selection.DecisionReason.INCLUDED, explicit=True) for file in files),
            )
        else:
            try:
                selection = file_selection.select_files(files, settings)
            except file_selection.FileSelectionError as error:
                print(f"pydocfmt check: File selection error: {error}", file=sys.stderr)
                return 2

        if args.show_files:
            with output_stream(args.output_file) as output:
                print_file_selection_decisions(selection.decisions, output=output)
            return 0

        if settings.experimental:
            if use_stdin and len(selection.accepted_paths) != 1:
                raise AssertionError(f"Expect exactly one accepted path when using stdin: {selection.accepted_paths}")
            results = [formatter.format_file_exp(path, file=sys.stdin if use_stdin else None, settings=settings, fix=args.fix) for path in selection.accepted_paths]
        else:
            if use_stdin:
                print("pydocfmt check: Argument error: Cannot process input from stdin when using non-experimental mode", file=sys.stderr)
                return 2
            results = format_files(selection.accepted_paths, settings=settings, fix=args.fix)

        if use_stdin and args.fix:
            if len(results) != 1:
                raise AssertionError(f"Expect exactly one result when fixing stdin: Got {len(results)}")
            if results[0].source is not None:
                print(results[0].source, end="")

        if use_stdin and args.fix and args.output_file is None:
            print_results(errors, results, settings=settings, output=sys.stderr)
        else:
            with output_stream(args.output_file) as output:
                print_results(errors, results, settings=settings, output=output)

    except OutputError as error:
        print(f"pydocfmt check: Output error: {error}", file=sys.stderr)
        return 2

    if args.exit_zero:
        return 0
    elif errors or any(result.errors or result.findings for result in results):
        return 1
    elif args.fix and args.exit_non_zero_on_fix and any(result.modified for result in results):
        return 1
    else:
        return 0


def format_files(paths: tuple[str, ...], *, settings: config.FormatterSettings, fix: bool) -> list[FormatterResult]:
    """Format files with the legacy formatter path."""
    results: list[FormatterResult] = []
    for path in paths:
        try:
            source_result = pydocfmt.format_file_source(path, settings, fix=fix)
        except UnicodeDecodeError as error:
            result = FormatterResult(path=path, source=None, modified=False, findings=(), errors=(f"Failed to decode {path} as UTF-8: {error}",))
        except OSError as error:
            result = FormatterResult(path=path, source=None, modified=False, findings=(), errors=(f"Failed to read or write file {path}: {error}",))
        else:
            if fix:
                result = FormatterResult(path=path, source=source_result.source, modified=source_result.modified, findings=(), errors=())
            else:
                if source_result.modified:
                    line_numbers_set = set(source_result.docstring_changed_lines + source_result.comment_changed_lines)
                    line_numbers = tuple(sorted(line_numbers_set)) if line_numbers_set else (0,)
                    findings: tuple[RuleFinding, ...] = (RuleFinding(rule=LEGACY_CHECK_RULE, line_numbers=line_numbers),)
                else:
                    findings = ()
                result = FormatterResult(path=path, source=source_result.original_source, modified=False, findings=findings, errors=())
        results.append(result)
    return results


def load_settings(args: argparse.Namespace) -> config.FormatterSettings | None:
    """Load settings with command-line overrides, returning None on failure."""
    try:
        overrides = _settings_overrides_from_args(args)
        return config.load_config(overrides, config_options=_config_options_from_args(args), isolated=_isolated_from_args(args))
    except config.ConfigError as error:
        print(f"pydocfmt check: Configuration error: {error}", file=sys.stderr)
        return None
    except tomllib.TOMLDecodeError as error:
        print(f"pydocfmt check: Configuration error: Invalid TOML inline table: {error}", file=sys.stderr)
        return None


def _settings_overrides_from_args(args: argparse.Namespace) -> config.SettingsOverrides:
    """Build settings overrides from parsed command-line arguments."""
    return config.SettingsOverrides(
        output_format=args.output_format,
        experimental=args.experimental,
        line_length=args.line_length,
        line_ending=args.line_ending,
        indent_style=args.indent_style,
        indent_width=args.indent_width,
        select=_parse_comma_option_groups(args.select),
        ignore=_parse_comma_option_groups(args.ignore),
        extend_select=_parse_comma_option_groups(args.extend_select),
        per_file_ignores=_parse_per_file_options(args.per_file_ignores),
        extend_per_file_ignores=_parse_per_file_options(args.extend_per_file_ignores),
        fixable=_parse_comma_option_groups(args.fixable),
        unfixable=_parse_comma_option_groups(args.unfixable),
        extend_fixable=_parse_comma_option_groups(args.extend_fixable),
        include=_parse_comma_option_groups(args.include),
        extend_include=_parse_comma_option_groups(args.extend_include),
        exclude=_parse_comma_option_groups(args.exclude),
        extend_exclude=_parse_comma_option_groups(args.extend_exclude),
        respect_gitignore=args.respect_gitignore,
        force_exclude=args.force_exclude,
    )


def _parse_comma_option_groups(groups: list[str] | None) -> tuple[str, ...] | None:
    """Parse repeated comma-separated CLI option groups while preserving omitted options as None."""
    if groups is None:
        return None
    return tuple(value.strip() for group in groups for value in group.split(","))


def _parse_per_file_options(groups: list[str] | None) -> config.RuleSelectorMap | None:
    """Parse repeated TOML inline per-file ignore maps from CLI options."""
    if groups is None:
        return None

    merged: dict[str, tuple[str, ...]] = {}
    for group in groups:
        parsed = tomllib.loads(f"value = {group}")
        value = parsed["value"]
        if not isinstance(value, dict):
            raise config.ConfigError("Per-file ignore CLI value must be a TOML table")
        for pattern, selectors in value.items():
            if not isinstance(pattern, str):
                raise config.ConfigError("Per-file ignore CLI patterns must be strings")
            if not isinstance(selectors, (list, tuple)) or not all(isinstance(selector, str) for selector in selectors):
                raise config.ConfigError("Per-file ignore CLI selectors must be lists of strings")
            merged[pattern] = tuple(selectors)
    result: config.RuleSelectorMap = tuple((pattern, selectors) for pattern, selectors in merged.items())
    return result


def _config_options_from_args(args: argparse.Namespace) -> tuple[str, ...]:
    """Return --config values from the top-level and subcommand parsers."""
    options = []
    for name in ("global_config", "command_config"):
        value = getattr(args, name, None)
        if value is not None:
            options.extend(value)
    return tuple(options)


def _isolated_from_args(args: argparse.Namespace) -> bool:
    """Return whether any parser position specified --isolated."""
    return bool(getattr(args, "global_isolated", False) or getattr(args, "command_isolated", False))


def print_settings(settings: config.FormatterSettings, *, output: typing.TextIO | None) -> None:
    """Print resolved settings in a stable TOML-like form."""
    print(config.format_settings(settings), end="", file=output)


def print_file_selection_decisions(decisions: tuple[file_selection.FileDecision, ...], *, output: typing.TextIO | None) -> None:
    """Print file-selection decisions."""
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} INCLUDED", file=output)
        else:
            print(f"{decision.path} IGNORED: {decision.message}", file=output)


def print_results(errors: list[str], results: list[FormatterResult], *, settings: config.FormatterSettings, output: typing.TextIO | None) -> None:
    """Print formatter results in the configured output format."""
    if settings.output_format == "grouped":
        print_results_grouped(errors, results, output=output)
    else:
        raise AssertionError(f"Unknown output format: {settings.output_format}")


def print_results_grouped(errors: list[str], results: list[FormatterResult], *, output: typing.TextIO | None) -> None:
    """Print remaining findings grouped by file."""
    have_errors = False
    for error in errors:
        print(f"ERROR: {error}", file=output)
        have_errors = True
    for result in results:
        for error in result.errors:
            print(f"ERROR: {error}", file=output)
            have_errors = True
    if have_errors:
        print(file=output)

    have_findings = False
    for result in results:
        if result.findings:
            print(f"{result.path}:", file=output)
            for finding in _group_findings(result.findings):
                print(f"  {_format_grouped_finding(finding)}", file=output)
            print(file=output)
            have_findings = True

    if have_errors or have_findings:
        total_findings = sum(len(result.findings) for result in results)
        fixable_findings = sum(1 for result in results for finding in result.findings if finding.fixable)
        print(f"Found {total_findings} rule check errors ({fixable_findings} fixable).", file=output)
    else:
        print("All checks passed!", file=output)


def _group_findings(findings: tuple[RuleFinding, ...]) -> tuple[RuleFinding, ...]:
    """Group same-rule findings while preserving first-seen order."""
    grouped_lines: defaultdict[formatter.RuleFindingKey, set[int]] = defaultdict(set)
    exemplars: dict[formatter.RuleFindingKey, RuleFinding] = {}
    for finding in findings:
        key = finding.grouping_key
        exemplars.setdefault(key, finding)
        grouped_lines[key].update(finding.line_numbers)
    return tuple(exemplars[key].with_line_numbers(tuple(sorted(line_numbers))) for key, line_numbers in grouped_lines.items())


def _format_grouped_finding(finding: RuleFinding) -> str:
    """Format one grouped finding line."""
    label = "Lines" if len(finding.line_numbers) != 1 else "Line"
    ranges = diagnostics.format_line_ranges(list(finding.line_numbers))
    fixable = "*" if finding.fixable else ""
    message = finding.message
    message_end = "" if message.endswith((".", "!", "?")) else "."
    return f"{finding.rule.rule_code}{fixable} {message}{message_end} {label} {ranges}"
