import argparse
import dataclasses


@dataclasses.dataclass(frozen=True)
class GlobalArgs:
    """Resolved global pydocfmt CLI arguments.

    Attributes:
        config_options (tuple[str, ...]): Ordered `--config` values supplied at all parser levels.
        isolated (bool): Whether auto-discovered configuration files should be ignored.
    """

    config_options: tuple[str, ...] = ()
    isolated: bool = False


def add_global_arguments(parser: argparse.ArgumentParser, *, dest_prefix: str) -> None:
    """Add global configuration arguments to a parser.

    Args:
        parser (argparse.ArgumentParser): Parser that should receive shared global options.
        dest_prefix (str): Prefix used for argparse destination names so multiple parser levels can coexist.
    """
    global_options = parser.add_argument_group("Global options")
    global_options.add_argument(
        "--config",
        action="append",
        default=None,
        dest=f"{dest_prefix}_config",
        metavar="CONFIG",
        help="Path to a TOML configuration file or TOML '<KEY> = <VALUE>' override.",
    )
    global_options.add_argument(
        "--isolated",
        action="store_true",
        default=False,
        dest=f"{dest_prefix}_isolated",
        help="Ignore all configuration files.",
    )


def global_values_from_arguments(args: argparse.Namespace, *, dest_prefixes: tuple[str, ...]) -> GlobalArgs:
    """Resolve global arguments from all parser levels in precedence order.

    Args:
        args (argparse.Namespace): Parsed command-line namespace.
        dest_prefixes (tuple[str, ...]): Destination prefixes to inspect in increasing precedence order.

    Returns:
        GlobalArgs: Combined global argument values.
    """
    config_options: list[str] = []
    isolated = False
    for dest_prefix in dest_prefixes:
        config_value = getattr(args, f"{dest_prefix}_config", None)
        if config_value is not None:
            config_options.extend(config_value)
        isolated = isolated or bool(getattr(args, f"{dest_prefix}_isolated", False))
    return GlobalArgs(config_options=tuple(config_options), isolated=isolated)
