"""`pydocfmt clean` cache cleanup command."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import sys
import tomllib
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.settings as settings_core
from pydocformatter.cache import directory as cache_directory
from pydocformatter.cli import global_args, settings_check
from pydocformatter.utils import argparser


if TYPE_CHECKING:
    # Standard library imports
    import argparse


def add_parser(subparsers: argparser.SubparserCollection) -> argparse.ArgumentParser:
    """Add the cache cleanup subcommand parser.

    Args:
        subparsers (argparser.SubparserCollection): Top-level subparser collection.

    Returns:
        argparse.ArgumentParser: Configured `clean` subcommand parser.
    """
    parser = argparser.create_subparser(subparsers, name="clean", description="Remove pydocfmt-owned persistent cache data.", help="Remove pydocfmt-owned persistent cache data")
    settings_check.SETTINGS_SCHEMA.add_argument(parser, settings_check.CheckSettings(), "cache_dir")
    global_args.add_global_arguments(parser, dest_prefix="command")
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace) -> int:
    """Resolve the configured cache root and remove only verified owned children.

    Args:
        args (argparse.Namespace): Parsed global configuration arguments.

    Returns:
        int: Process exit status code.
    """
    try:
        global_values = global_args.global_values_from_arguments(args, dest_prefixes=("global", "command"))
        profile = settings_check.SETTINGS_SCHEMA.load_profile(global_values=global_values, args=args, path=os.getcwd())
        cache_dir = cache_directory.cache_directory_for_profile(profile)
        result = cache_directory.clean_cache(cache_dir)
    except (settings_core.SettingsError, tomllib.TOMLDecodeError) as error:
        print(f"pydocfmt clean: Configuration error: {error}", file=sys.stderr)
        return 2
    except cache_directory.CacheDirectoryError as error:
        print(f"pydocfmt clean: Cache cleanup error: {error}", file=sys.stderr)
        return 2

    if result.removed_paths:
        print(f"Removed pydocfmt cache data from {result.root}.")
    else:
        print(f"No pydocfmt cache data found at {result.root}.")
    return 0
