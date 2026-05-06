from pydocformatter.cli.common import run_formatter
from pydocformatter.formatters.pydocfmt import format_docstrings


def main() -> None:
    """Run the pydocfmt command-line entry point.

    Returns:
        None: The command runs the shared formatter CLI and may terminate the process
            through `run_formatter`.
    """
    run_formatter(
        tool_name="pydocfmt",
        description="Format Python docstrings.",
        line_length_subject="docstrings",
        format_file=format_docstrings,
    )
