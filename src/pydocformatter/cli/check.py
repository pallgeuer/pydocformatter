from __future__ import annotations

import argparse
import contextlib
import os
import sys
import tomllib
import typing
from collections import defaultdict
from collections.abc import Iterator

import pydocformatter.cli.global_args as global_args
import pydocformatter.cli.settings_check as settings_check
import pydocformatter.cli.utils as cli_utils
import pydocformatter.config as config
import pydocformatter.file_selection as file_selection
import pydocformatter.formatter as formatter
import pydocformatter.formatters.pydocfmt as pydocfmt
import pydocformatter.utils.misc as misc
from pydocformatter.formatter import FormatterResult, Rule, RuleFinding

LEGACY_CHECK_RULE = Rule(rule_code="000", rule_name="legacy-formatting-needed", message="Needs formatting", fixable=True)


class OutputError(Exception):
    """Raised when an output stream cannot be opened or prepared."""


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    """Add the check subcommand parser."""
    parser = cli_utils.create_subparser(
        subparsers,
        name="check",
        description="Check and optionally fix Python docstrings and comments.",
        help="Check and optionally fix Python docstrings and comments",
    )
    add_arguments(parser, settings_check.CheckSettings())
    parser.set_defaults(func=run)
    return parser


def add_arguments(parser: argparse.ArgumentParser, settings: settings_check.CheckSettings) -> None:
    """Add CLI arguments for the check subcommand."""
    parser.add_argument(
        "files",
        nargs="*",
        default=None,
        metavar="PATH",
        help="Python files or directories to check, or '-' to read from stdin (default: current directory).",
    )

    parser.add_argument(
        "--fix",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Apply fixes instead of only checking for needed changes.",
    )
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="Show file-selection decisions without checking or fixing files.",
    )
    parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Show resolved settings without checking or fixing files.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default=None,
        metavar="FILE",
        help="Specify file to write output to (default: stdout).",
    )

    settings_check.SETTINGS_SCHEMA.add_arguments(parser, settings)

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

    global_args.add_global_arguments(parser, dest_prefix="command")


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
        if use_stdin and args.files:
            errors.extend(f"Using standard input instead of input path: {path}" for path in args.files if path != "-")

        if use_stdin and args.stdin_filename is None:
            selection = file_selection.SelectionResult(
                accepted_paths=tuple(files),
                decisions=tuple(file_selection.FileDecision(path=file, accepted=True, reason=file_selection.DecisionReason.INCLUDED, explicit=True) for file in files),
            )
        else:
            try:
                if use_stdin:
                    selection = file_selection.select_virtual_file(args.stdin_filename, settings)
                else:
                    selection = file_selection.select_files(files, settings)
            except file_selection.FileSelectionError as error:
                print(f"pydocfmt check: File selection error: {error}", file=sys.stderr)
                return 2

        if args.show_files:
            with output_stream(args.output_file) as output:
                print_file_selection_decisions(selection.decisions, output=output)
            return 0

        if settings.experimental:
            if use_stdin and len(selection.accepted_paths) > 1:
                raise AssertionError(f"Expect at most one accepted path when using stdin: {selection.accepted_paths}")
            results = [formatter.format_file_exp(path, file=sys.stdin if use_stdin else None, settings=settings, fix=args.fix) for path in selection.accepted_paths]
        else:
            if use_stdin:
                print("pydocfmt check: Argument error: Cannot process input from stdin when using non-experimental mode", file=sys.stderr)
                return 2
            results = format_files(selection.accepted_paths, settings=settings, fix=args.fix)

        if use_stdin and args.fix and results:
            if len(results) != 1:
                raise AssertionError(f"Expect at most one result when fixing stdin: Got {len(results)}")
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


def format_files(paths: tuple[str, ...], *, settings: settings_check.CheckSettings, fix: bool) -> list[FormatterResult]:
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


def load_settings(args: argparse.Namespace) -> settings_check.CheckSettings | None:
    """Load settings with command-line overrides, returning None on failure."""
    try:
        global_values = global_args.global_args_from_namespace(args, dest_prefixes=("global", "command"))
        overrides = settings_check.SETTINGS_SCHEMA.overrides_from_namespace(args)
        return settings_check.SETTINGS_SCHEMA.load(overrides, global_args=global_values)
    except config.ConfigError as error:
        print(f"pydocfmt check: Configuration error: {error}", file=sys.stderr)
        return None
    except tomllib.TOMLDecodeError as error:
        print(f"pydocfmt check: Configuration error: Invalid TOML inline table: {error}", file=sys.stderr)
        return None


def print_settings(settings: settings_check.CheckSettings, *, output: typing.TextIO | None) -> None:
    """Print resolved settings in a stable TOML-like form."""
    print(settings_check.SETTINGS_SCHEMA.format(settings), end="", file=output)


def print_file_selection_decisions(decisions: tuple[file_selection.FileDecision, ...], *, output: typing.TextIO | None) -> None:
    """Print file-selection decisions."""
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} INCLUDED", file=output)
        else:
            print(f"{decision.path} IGNORED: {decision.message}", file=output)


def print_results(errors: list[str], results: list[FormatterResult], *, settings: settings_check.CheckSettings, output: typing.TextIO | None) -> None:
    """Print formatter results in the configured output format."""
    if settings.output_format == settings_check.OutputFormat.GROUPED:
        print_results_grouped(errors, results, output=output)
    else:
        raise AssertionError(f"Unknown output format: {settings.output_format}")


def print_results_grouped(errors: list[str], results: list[FormatterResult], *, output: typing.TextIO | None) -> None:
    """Print remaining findings grouped by file."""
    num_operational_errors = 0
    for error in errors:
        print(f"ERROR: {error}", file=output)
        num_operational_errors += 1
    for result in results:
        for error in result.errors:
            print(f"ERROR: {error}", file=output)
            num_operational_errors += 1
    if num_operational_errors != 0:
        print(file=output)

    num_findings = 0
    num_fixable_findings = 0
    for result in results:
        if result.findings:
            print(f"{result.path}:", file=output)
            for finding in _group_findings(result.findings):
                print(f"  {_format_grouped_finding(finding)}", file=output)
            print(file=output)
            num_findings += len(result.findings)
            num_fixable_findings += sum(1 for finding in result.findings if finding.fixable)

    if num_operational_errors != 0 or num_findings != 0:
        parts: list[str] = []
        if num_operational_errors != 0:
            parts.append(f"{num_operational_errors} operational {misc.auto_plural(num_operational_errors, 'error')}")
        if num_findings != 0:
            parts.append(f"{num_findings} rule check {misc.auto_plural(num_findings, 'error')} ({num_fixable_findings} fixable)")
        print(f"Found {' and '.join(parts)}.", file=output)
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
    ranges = misc.format_line_ranges(list(finding.line_numbers))
    fixable = "*" if finding.fixable else ""
    message = finding.message
    message_end = "" if message.endswith((".", "!", "?")) else "."
    return f"{finding.rule.rule_code}{fixable} {message}{message_end} {label} {ranges}"
