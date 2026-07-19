"""`pydocfmt check` command."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import sys
import math
import difflib
import tomllib
import argparse
import itertools
import contextlib
import dataclasses
import concurrent.futures
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import TYPE_CHECKING, TextIO

# First-party imports
import pydocformatter.settings as settings_core
import pydocformatter.cache.session as cache_session
from pydocformatter import file_selection, formatter, rules_selection
from pydocformatter.cache.models import CacheStats
from pydocformatter.cli import global_args, settings_check
from pydocformatter.cli.settings_check import SETTINGS_SCHEMA, CheckSettings, OutputFormat
from pydocformatter.file_selection import STDIN_VIRTUAL_FILE, FileSelectionError
from pydocformatter.formatter import FormatterResult
from pydocformatter.rules.models import FixAvailability
from pydocformatter.source_path import SourcePathContextBuilder
from pydocformatter.utils import argparser, misc


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.file_selection import FileDecision, SelectionResult
    from pydocformatter.rules.models import RuleFinding, RuleMetadata
    from pydocformatter.rules_selection import RuleSelection


_MAX_WINDOWS_PROCESS_POOL_WORKERS = 61
_DEFAULT_INPUT_PATH = "."
_ExecutorFactory = Callable[..., concurrent.futures.Executor]


@dataclasses.dataclass(frozen=True)
class CheckRunContext:
    """Path-aware settings context for one check invocation.

    Attributes:
        resolver (settings_core.SettingsResolver[CheckSettings]): Settings resolver shared by all paths in the command
            run.
        cwd_profile (settings_core.SettingsProfile[CheckSettings]): Settings profile resolved for the current working
            directory.
    """

    resolver: settings_core.SettingsResolver[CheckSettings]
    cwd_profile: settings_core.SettingsProfile[CheckSettings]

    @property
    def cwd_settings(self) -> CheckSettings:
        """Settings resolved for the current working directory.

        Returns:
            CheckSettings: Settings profile data used for command-level options such as output format and parallelism.
        """
        return self.cwd_profile.settings


@dataclasses.dataclass(frozen=True)
class FormatBatchResult:
    """Ordered formatting results, cache counters, and invocation warnings.

    Attributes:
        results (tuple[FormatterResult, ...]): Formatting results in selected-file order.
        cache_stats (CacheStats): Final persistent-cache counters.
        warnings (tuple[str, ...]): Invocation-level cache warnings to print once.
    """

    results: tuple[FormatterResult, ...]
    cache_stats: CacheStats
    warnings: tuple[str, ...]


class OutputError(Exception):
    """Raised when an output stream cannot be opened or prepared."""


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    """Add the check subcommand parser.

    Args:
        subparsers (argparse._SubParsersAction[argparse.ArgumentParser]): Top-level subparser action.

    Returns:
        argparse.ArgumentParser: Configured `check` subcommand parser.
    """
    parser = argparser.create_subparser(
        subparsers, name="check", description="Check and optionally fix Python docstrings and comments.", help="Check and optionally fix Python docstrings and comments"
    )
    add_arguments(parser, CheckSettings())
    parser.set_defaults(func=run)
    return parser


def add_arguments(parser: argparse.ArgumentParser, settings: CheckSettings) -> None:
    """Add CLI arguments for the check subcommand.

    Args:
        parser (argparse.ArgumentParser): Parser that should receive check-command arguments.
        settings (CheckSettings): Settings object supplying current defaults for help text.
    """
    parser.add_argument("files", nargs="*", default=None, metavar="PATH", help="Python files or directories to check, or '-' to read from stdin (default: current directory).")

    parser.add_argument("--fix", action=argparse.BooleanOptionalAction, default=False, help="Apply fixes instead of only checking for needed changes.")
    parser.add_argument(
        "--diff", action="store_true", help="Avoid writing any fixed files back; instead, output a diff for each changed file to stdout, and exit 0 if there are no diffs. Implies fix-only."
    )
    parser.add_argument("--show-settings", action="store_true", help="Show resolved settings without checking or fixing files.")
    parser.add_argument("--show-rules", action="store_true", help="Show the active rules without checking or fixing files.")
    parser.add_argument("--show-files", action="store_true", help="Show file-selection decisions without checking or fixing files.")
    parser.add_argument("-o", "--output-file", default=None, metavar="FILE", help="Specify file to write output to (default: stdout).")

    SETTINGS_SCHEMA.add_arguments(parser, settings)

    miscellaneous = parser.add_argument_group("Miscellaneous")
    miscellaneous.add_argument("--stdin-filename", default=None, metavar="FILENAME", help="The name of the file when passing it through stdin.")
    miscellaneous.add_argument("--cache-stats", action="store_true", help="Print concise persistent-cache statistics to stderr.")
    exit_options = miscellaneous.add_mutually_exclusive_group()
    exit_options.add_argument("-e", "--exit-zero", action="store_true", help='Exit with status code "0", even upon detecting formatting violations.')
    exit_options.add_argument("--exit-non-zero-on-fix", action="store_true", help="Exit with a non-zero status code if any files were modified via fix, even if no formatting violations remain.")

    global_args.add_global_arguments(parser, dest_prefix="command")


def run(args: argparse.Namespace) -> int:
    """Run the check subcommand.

    Args:
        args (argparse.Namespace): Parsed command arguments.

    Returns:
        int: Process exit status code.

    Raises:
        AssertionError: If stdin mode is paired with more than one accepted display path.
    """
    if args.show_settings + args.show_rules + args.show_files > 1:
        print("pydocfmt check: Argument error: Cannot use more than one of {--show-settings, --show-rules, --show-files} together", file=sys.stderr)
        return 2

    settings_context = load_settings(args)
    if settings_context is None:
        return 2
    settings = settings_context.cwd_settings

    if args.show_settings:
        try:
            with output_stream(args.output_file) as output:
                print_settings(settings, output=output)
        except OutputError as error:
            return _output_error_status(error)
        return 0

    if args.show_rules:
        selected_rules = rules_selection.select_rules(settings, profile=settings_context.cwd_profile)
        try:
            with output_stream(args.output_file) as output:
                print_rules(selected_rules, output=output)
        except OutputError as error:
            return _output_error_status(error)
        return 1 if selected_rules.errors else 0

    if args.show_files:
        try:
            files, errors = select_files(paths=args.files, stdin_filename=args.stdin_filename, resolver=settings_context.resolver)[:2]
        except FileSelectionError as error:
            print(f"pydocfmt check: File selection error: {error}", file=sys.stderr)
            return 2
        except settings_core.SettingsError as error:
            print(f"pydocfmt check: Configuration error: {error}", file=sys.stderr)
            return 2
        try:
            with output_stream(args.output_file) as output:
                print_file_selection_decisions(errors, files.decisions, output=output)
        except OutputError as error:
            return _output_error_status(error)
        return 1 if errors else 0

    try:
        return check_files(args=args, settings_context=settings_context)
    except OutputError as error:
        return _output_error_status(error)


def _output_error_status(error: OutputError) -> int:
    """Print an output error and return the corresponding check status."""
    print(f"pydocfmt check: Output error: {error}", file=sys.stderr)
    return 2


def select_files(*, paths: list[str] | None, stdin_filename: str | None, resolver: settings_core.SettingsResolver[CheckSettings]) -> tuple[SelectionResult, list[str], bool]:
    """Select input files and resolve stdin-related path handling.

    Args:
        paths (list[str] | None): CLI path arguments, or None when no path arguments were provided.
        stdin_filename (str | None): Optional display path to use for source read from stdin.
        resolver (settings_core.SettingsResolver[CheckSettings]): Path-aware settings resolver controlling file
            selection.

    Returns:
        tuple[SelectionResult, list[str], bool]: The selected files, operational warnings, and whether stdin should be
            read.
    """
    errors: list[str] = []

    use_stdin = False
    if stdin_filename is not None:
        file_paths = [stdin_filename]
        use_stdin = True
    elif paths:
        if STDIN_VIRTUAL_FILE in paths:
            file_paths = [STDIN_VIRTUAL_FILE]
            use_stdin = True
        else:
            file_paths = paths
    else:
        file_paths = [_DEFAULT_INPUT_PATH]

    if use_stdin and paths:
        errors.extend(f"Using standard input instead of input path: {path}" for path in paths if path != STDIN_VIRTUAL_FILE)

    files = file_selection.select_virtual_file(file_paths[0], resolver) if use_stdin else file_selection.select_files(file_paths, resolver)

    return files, errors, use_stdin


def check_files(*, args: argparse.Namespace, settings_context: CheckRunContext) -> int:
    """Check or fix selected input files and print diagnostics.

    Args:
        args (argparse.Namespace): Parsed check-command arguments controlling file selection, formatting mode, output
            routing, and exit-code behavior.
        settings_context (CheckRunContext): Path-aware settings context.

    Returns:
        int: Process exit status code.

    Raises:
        AssertionError: If stdin mode is paired with more than one accepted display path.
    """
    errors: list[str] = []

    try:
        files, files_errors, use_stdin = select_files(paths=args.files, stdin_filename=args.stdin_filename, resolver=settings_context.resolver)
        errors.extend(files_errors)
    except FileSelectionError as error:
        print(f"pydocfmt check: File selection error: {error}", file=sys.stderr)
        return 2
    except settings_core.SettingsError as error:
        print(f"pydocfmt check: Configuration error: {error}", file=sys.stderr)
        return 2

    rule_profiles = files.selected_files or (file_selection.SelectedFile(path="", profile=settings_context.cwd_profile),)
    seen_rule_profiles: set[settings_core.SettingsProfile.Key[CheckSettings]] = set()
    rule_selections: dict[settings_core.SettingsProfile.Key[CheckSettings], RuleSelection] = {}
    for selected_file in rule_profiles:
        profile_key = selected_file.profile.key()
        if profile_key in seen_rule_profiles:
            continue
        seen_rule_profiles.add(profile_key)
        selected_rules = rules_selection.select_rules(selected_file.profile.settings, profile=selected_file.profile)
        rule_selections[profile_key] = selected_rules
        errors.extend(selected_rules.errors)

    if use_stdin and len(files.accepted_paths) > 1:
        raise AssertionError(f"Expect at most one accepted path when using stdin: {files.accepted_paths}")

    batch = format_selected_files(
        files.selected_files,
        rule_selections=rule_selections,
        use_stdin=use_stdin,
        fix=args.fix or args.diff,
        write=not args.diff,
        parallelism=settings_context.cwd_settings.parallelism,
        cache_profile=settings_context.cwd_profile,
    )
    results = batch.results

    if use_stdin and args.fix and not args.diff and results:
        if len(results) != 1:
            raise AssertionError(f"Expect at most one result when fixing stdin: Got {len(results)}")
        if results[0].new_source is not None:
            print(results[0].new_source, end="")

    if args.diff:
        with output_stream(args.output_file) as output:
            print_diff_summary(errors, results, output=output)
        print_diff_results(results, output=None)
    elif use_stdin and args.fix and args.output_file is None:
        print_results(errors, results, output_format=settings_context.cwd_settings.output_format, output=sys.stderr)
    else:
        with output_stream(args.output_file) as output:
            print_results(errors, results, output_format=settings_context.cwd_settings.output_format, output=output)

    for warning in batch.warnings:
        print(warning, file=sys.stderr)
    if args.cache_stats:
        print_cache_stats(batch.cache_stats, output=sys.stderr)

    if args.exit_zero:
        return 0
    if (
        (args.diff and any(result.modified for result in results))
        or errors
        or any(result.errors or result.unfixed_findings for result in results)
        or (args.fix and args.exit_non_zero_on_fix and any(result.modified for result in results))
    ):
        return 1
    return 0


@contextlib.contextmanager
def output_stream(output_file: str | None) -> Iterator[TextIO | None]:
    """Yield the configured output stream.

    Args:
        output_file (str | None): Optional file path to open for diagnostics.

    Yields:
        TextIO | None: Open output stream, or None to let `print` use stdout.

    Raises:
        OutputError: If the output file or its direct parent cannot be created.
    """
    if output_file is None:
        yield None
        return

    parent = os.path.dirname(output_file)
    try:
        if parent:
            with contextlib.suppress(FileExistsError):
                os.mkdir(parent)
        output = open(output_file, "w", encoding="utf-8", newline="")  # noqa: SIM115
    except OSError as error:
        raise OutputError(str(error)) from error
    with output:
        yield output


def resolve_parallelism(parallelism: float) -> int:
    """Return the worker count represented by a parallelism setting.

    Args:
        parallelism (float): Configured parallelism value, where 0 means all CPUs, fractions scale CPUs, and integers
            are exact worker counts.

    Returns:
        int: Concrete worker count after validation and CPU-count expansion.
    """
    parallelism = settings_check.validate_parallelism(parallelism, "parallelism")
    if parallelism == 0:
        return max(1, os.cpu_count() or 1)
    if 0 < parallelism < 1:
        return max(1, math.ceil((os.cpu_count() or 1) * parallelism))
    return int(parallelism)


def _process_pool_worker_count(parallelism: float, selected_file_count: int) -> int:
    """Return a worker count supported by the current process pool platform."""
    workers = min(resolve_parallelism(parallelism), selected_file_count)
    if sys.platform == "win32":
        workers = min(workers, _MAX_WINDOWS_PROCESS_POOL_WORKERS)
    return workers


def format_selected_files(
    selected_files: tuple[file_selection.SelectedFile, ...],
    *,
    rule_selections: dict[settings_core.SettingsProfile.Key[CheckSettings], RuleSelection],
    use_stdin: bool,
    fix: bool,
    write: bool,
    parallelism: float,
    cache_profile: settings_core.SettingsProfile[CheckSettings] | None = None,
    executor_factory: _ExecutorFactory = concurrent.futures.ProcessPoolExecutor,
) -> FormatBatchResult:
    """Format selected files with each file's resolved settings profile.

    Args:
        selected_files (tuple[file_selection.SelectedFile, ...]): Accepted files in diagnostic output order.
        rule_selections (dict[settings_core.SettingsProfile.Key[CheckSettings], RuleSelection]): Rule selections keyed
            by the base settings profile for each selected file.
        use_stdin (bool): Whether the single selected file should read source from standard input.
        fix (bool): Whether selected fixes should be applied before returning results.
        write (bool): Whether fixed disk-backed files should be written in place.
        parallelism (float): Configured worker-count value used for disk-backed files.
        cache_profile (settings_core.SettingsProfile[CheckSettings] | None): Current-working-directory profile
            controlling run-level cache enablement and location, or None to disable caching for direct callers.
        executor_factory (_ExecutorFactory): Executor constructor used to parallelize disk-backed formatting.

    Returns:
        FormatBatchResult: Ordered formatting results, final cache counters, and invocation warnings.

    Raises:
        AssertionError: If stdin mode is requested with more than one selected file.
    """
    if not selected_files:
        return FormatBatchResult(results=(), cache_stats=CacheStats(), warnings=())
    if use_stdin:
        if len(selected_files) > 1:
            raise AssertionError(f"Expect at most one selected file when using stdin: {selected_files}")
        selected_file = selected_files[0]
        effective_profile = settings_check.effective_profile_for_path(selected_file.profile, selected_file.path)
        rule_selection = rule_selections[selected_file.profile.key()]
        result = formatter.format_stream(selected_file.path, file=sys.stdin, settings=effective_profile.settings, rule_selection=rule_selection, fix=fix)
        return FormatBatchResult(results=(result,), cache_stats=CacheStats(uncacheable=1), warnings=())

    session = cache_session.CacheSession.from_profile(cache_profile, parallelism=resolve_parallelism(parallelism))
    source_path_builder = SourcePathContextBuilder()
    candidates: list[cache_session.CacheCandidate] = []
    for index, selected_file in enumerate(selected_files):
        effective_profile = settings_check.effective_profile_for_path(selected_file.profile, selected_file.path)
        rule_selection = rule_selections[selected_file.profile.key()]
        candidates.append(
            cache_session.CacheCandidate(
                index=index,
                path=selected_file.path,
                profile=effective_profile,
                execution_plan=rule_selection.execution_plan_for_path(selected_file.path),
                source_path=source_path_builder.for_path(selected_file.path),
                selection_succeeded=not rule_selection.errors,
                fix=fix,
                write=write,
            )
        )
    prepared = session.prepare(tuple(candidates))
    probe = session.probe(prepared)
    miss_indexes = frozenset(probe.miss_indexes)
    hit_results = {hit.index: hit.result for hit in probe.hits}
    ordered_results: list[FormatterResult | None] = [hit_results.get(index) for index in range(len(selected_files))]
    miss_files = tuple(prepared_file for prepared_file in prepared.files if prepared_file.index in miss_indexes)
    executions: dict[int, formatter.DiskFormatResult] = {}
    workers = _process_pool_worker_count(parallelism, len(miss_files)) if miss_files else 0
    if workers == 1:
        for prepared_file in miss_files:
            execution = formatter.format_disk_file(prepared_file.format_request)
            executions[prepared_file.index] = execution
            ordered_results[prepared_file.index] = execution.result
    elif workers > 1:
        with executor_factory(max_workers=workers) as executor:
            futures = {executor.submit(formatter.format_disk_file, prepared_file.format_request): prepared_file.index for prepared_file in miss_files}
            for future in concurrent.futures.as_completed(futures):
                index = futures[future]
                execution = future.result()
                executions[index] = execution
                ordered_results[index] = execution.result

    persistence = session.persist(probe, executions)

    if any(result is None for result in ordered_results):
        raise AssertionError("Parallel formatting completed without producing a result for every selected file")
    return FormatBatchResult(results=tuple(result for result in ordered_results if result is not None), cache_stats=persistence.stats, warnings=persistence.warnings)


def print_cache_stats(stats: CacheStats, *, output: TextIO) -> None:
    """Print one concise debug-only cache statistics line.

    Args:
        stats (CacheStats): Internal counters collected by the cache coordinator.
        output (TextIO): Diagnostic stream that receives the line.
    """
    print(
        f"Cache: candidates={stats.candidates} hits={stats.hits} metadata-rejected={stats.metadata_rejected} digest-rejected={stats.digest_rejected} misses={stats.misses} uncacheable={stats.uncacheable} read-errors={stats.read_errors} writes={stats.writes} store-errors={stats.store_errors}",
        file=output,
    )


def load_settings(args: argparse.Namespace) -> CheckRunContext | None:
    """Load path-aware settings with command-line overrides, returning None on failure.

    Args:
        args (argparse.Namespace): Parsed command arguments.

    Returns:
        CheckRunContext | None: Resolved settings context, or None after printing a configuration error.
    """
    try:
        global_values = global_args.global_values_from_arguments(args, dest_prefixes=("global", "command"))
        resolver = SETTINGS_SCHEMA.resolver(global_values=global_values, args=args)
        return CheckRunContext(resolver=resolver, cwd_profile=resolver.profile_for_path(os.getcwd()))
    except settings_core.SettingsError as error:
        print(f"pydocfmt check: Configuration error: {error}", file=sys.stderr)
        return None
    except tomllib.TOMLDecodeError as error:
        print(f"pydocfmt check: Configuration error: Invalid TOML inline table: {error}", file=sys.stderr)
        return None


def print_settings(settings: CheckSettings, *, output: TextIO | None) -> None:
    """Print resolved settings in a stable TOML-like form.

    Args:
        settings (CheckSettings): Resolved settings to print.
        output (TextIO | None): Output stream, or stdout when None.
    """
    print(SETTINGS_SCHEMA.format(settings), end="", file=output)


def print_operational_errors(errors: Iterable[str], *, output: TextIO | None) -> int:
    """Print operational errors and return the number printed.

    Args:
        errors (Iterable[str]): Operational errors to print.
        output (TextIO | None): Output stream, or stdout when None.

    Returns:
        int: Number of operational errors printed.
    """
    num_operational_errors = 0
    for error in errors:
        print(f"ERROR: {error}", file=output)
        num_operational_errors += 1
    if num_operational_errors != 0:
        print(file=output)
    return num_operational_errors


def print_rules(selected_rules: RuleSelection, *, output: TextIO | None) -> None:
    """Print active rules.

    Args:
        selected_rules (RuleSelection): Effective global rule selection to print.
        output (TextIO | None): Output stream, or stdout when None.
    """
    print_operational_errors(selected_rules.errors, output=output)
    if selected_rules.rules:
        for selected_rule in selected_rules.rules:
            fixable = "*" if selected_rule.fixable else ""
            rule = selected_rule.rule
            print(f"{rule.code}{fixable} {rule.name} ({rule.message})", file=output)
    else:
        print("No active rules.", file=output)


def print_file_selection_decisions(errors: Iterable[str], decisions: tuple[FileDecision, ...], *, output: TextIO | None) -> None:
    """Print file-selection decisions.

    Args:
        errors (Iterable[str]): Operational errors accumulated during file selection.
        decisions (tuple[FileDecision, ...]): Ordered file-selection decisions to print.
        output (TextIO | None): Output stream, or stdout when None.
    """
    print_operational_errors(errors, output=output)
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} INCLUDED", file=output)
        else:
            print(f"{decision.path} IGNORED: {decision.message}", file=output)


def print_results(errors: Iterable[str], results: Sequence[FormatterResult], *, output_format: OutputFormat, output: TextIO | None) -> None:
    """Print formatter results in the configured output format.

    Args:
        errors (Iterable[str]): Operational errors accumulated outside individual formatter results.
        results (Sequence[FormatterResult]): Formatter results to print.
        output_format (OutputFormat): Configured diagnostic output format.
        output (TextIO | None): Output stream, or stdout when None.

    Raises:
        AssertionError: If `output_format` is unknown.
    """
    if output_format == OutputFormat.GROUPED:
        print_results_grouped(errors, results, output=output)
    else:
        raise AssertionError(f"Unknown output format: {output_format}")


def print_diff_results(results: Sequence[FormatterResult], *, output: TextIO | None) -> None:
    """Print unified diffs for modified formatter results.

    Args:
        results (Sequence[FormatterResult]): Formatter results to diff.
        output (TextIO | None): Output stream, or stdout when None.
    """
    printed_sep = False
    for result in results:
        if not result.modified or result.old_source is None or result.new_source is None:
            continue
        lines = difflib.unified_diff(result.old_source.splitlines(keepends=True), result.new_source.splitlines(keepends=True), fromfile=result.path, tofile=result.path, lineterm="")
        if output is None and lines and not printed_sep:
            print()
            printed_sep = True
        for line in lines:
            print(line, end="" if line.endswith("\n") else "\n", file=output)


def print_diff_summary(errors: Iterable[str], results: Sequence[FormatterResult], *, output: TextIO | None) -> None:
    """Print diff summary and operational errors.

    Args:
        errors (Iterable[str]): Operational errors accumulated outside individual formatter results.
        results (Sequence[FormatterResult]): Formatter results to summarize.
        output (TextIO | None): Output stream, or stdout when None.
    """
    num_operational_errors = print_operational_errors(itertools.chain(errors, *(result.errors for result in results)), output=output)
    _print_results_summary(num_operational_errors=num_operational_errors, results=results, would=True, output=output)


def print_results_grouped(errors: Iterable[str], results: Sequence[FormatterResult], *, output: TextIO | None) -> None:
    """Print remaining findings grouped by file.

    Args:
        errors (Iterable[str]): Operational errors accumulated outside individual formatter results.
        results (Sequence[FormatterResult]): Formatter results to print.
        output (TextIO | None): Output stream, or stdout when None.
    """
    num_operational_errors = print_operational_errors(itertools.chain(errors, *(result.errors for result in results)), output=output)

    for result in results:
        if result.fixed_findings or result.unfixed_findings:
            print(f"{result.path}:", file=output)
            for rule, count in sorted(result.fixed_findings.items()):
                print(f"  {_format_fixed_finding(rule, count)}", file=output)
            for finding in _group_unfixed_findings(result.unfixed_findings):
                print(f"  {_format_unfixed_finding(finding)}", file=output)
            print(file=output)

    _print_results_summary(num_operational_errors=num_operational_errors, results=results, would=False, output=output)


def _print_results_summary(*, num_operational_errors: int, results: Sequence[FormatterResult], would: bool, output: TextIO | None) -> None:
    """Print result summary lines."""
    num_fixed_findings = sum(result.fixed_findings.total() for result in results)
    num_findings = sum(len(result.unfixed_findings) for result in results)
    num_fixable_findings = sum(1 for result in results for finding in result.unfixed_findings if finding.fixable)

    if num_operational_errors != 0:
        print(f"Found {num_operational_errors} operational {misc.auto_plural(num_operational_errors, 'error')}.", file=output)
    if num_fixed_findings != 0 and num_findings != 0:
        if would:
            print(f"Would fix {num_fixed_findings} rule check {misc.auto_plural(num_fixed_findings, 'error')} and leave {num_findings} more unfixed ({num_fixable_findings} fixable).", file=output)
        else:
            print(f"Fixed {num_fixed_findings} rule check {misc.auto_plural(num_fixed_findings, 'error')} and left {num_findings} more unfixed ({num_fixable_findings} fixable).", file=output)
    elif num_fixed_findings != 0:
        prefix = "Would fix" if would else "Fixed"
        print(f"{prefix} {num_fixed_findings} rule check {misc.auto_plural(num_fixed_findings, 'error')}.", file=output)
    elif num_findings != 0:
        if would:
            print(f"Would leave {num_findings} rule check {misc.auto_plural(num_findings, 'error')} unfixed ({num_fixable_findings} fixable).", file=output)
        else:
            print(f"Found {num_findings} rule check {misc.auto_plural(num_findings, 'error')} ({num_fixable_findings} fixable).", file=output)
    elif num_operational_errors == 0:
        print("All checks passed!", file=output)


def _group_unfixed_findings(findings: tuple[RuleFinding, ...]) -> tuple[RuleFinding, ...]:
    """Group same-rule findings and sort them by grouping key."""
    grouped_lines: defaultdict[RuleFinding.Key, set[int]] = defaultdict(set)
    exemplars: dict[RuleFinding.Key, RuleFinding] = {}
    for finding in findings:
        key = finding.grouping_key
        exemplars.setdefault(key, finding)
        grouped_lines[key].update(finding.line_numbers)
    return tuple(exemplars[key].with_line_numbers(tuple(sorted(lines))) for key, lines in sorted(grouped_lines.items()))


def _format_fixed_finding(rule: RuleMetadata, count: int) -> str:
    """Format one fixed finding line."""
    fixable = "" if rule.fix_availability == FixAvailability.NEVER else "*"
    message = rule.message
    message_end = "" if message.endswith((".", "!", "?")) else "."
    return f"{rule.code}{fixable} {message}{message_end} Fixed {count} {misc.auto_plural(count, 'time')}."


def _format_unfixed_finding(finding: RuleFinding) -> str:
    """Format one unfixed finding line."""
    label = "Lines" if len(finding.line_numbers) != 1 else "Line"
    ranges = misc.format_line_ranges(list(finding.line_numbers))
    fixable = "*" if finding.fixable else ""
    message = finding.message
    message_end = "" if message.endswith((".", "!", "?")) else "."
    return f"{finding.rule.code}{fixable} {message}{message_end} {label} {ranges}"
