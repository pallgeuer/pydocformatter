import pydocformatter.cli.common as cli_common
import pydocformatter.formatters.pycommentfmt as pycommentfmt


def main() -> int:
    """Run the pycommentfmt command-line entry point."""
    return cli_common.run_formatter(
        tool_name="pycommentfmt",
        description="Format Python comments.",
        line_length_subject="comments",
        format_file=pycommentfmt.format_comments,
    )
