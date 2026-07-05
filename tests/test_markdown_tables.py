import pathlib
import subprocess

import pytest

import tools.fix_markdown_tables as markdown_tables

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX_COMMAND = "uv run python tools/fix_markdown_tables.py"


def test_markdown_tables_are_pycharm_style_aligned_and_minimal() -> None:
    """Check that repository Markdown pipe tables use minimal PyCharm-style alignment."""
    failures: list[str] = []
    for path in markdown_tables.tracked_markdown_paths():
        failures.extend(markdown_tables.markdown_table_failures(path))

    assert not failures, f"Markdown table style failures. Run: {FIX_COMMAND}\n" + "\n".join(failures)


def test_tracked_markdown_paths_ignores_missing_worktree_files(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that unstaged Markdown renames do not leave stale tracked paths."""
    existing = tmp_path / "existing.md"
    existing.write_text("# Existing\n", encoding="utf-8")
    monkeypatch.setattr(markdown_tables, "ROOT", tmp_path)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "existing.md\nmissing.md\n")

    assert markdown_tables.tracked_markdown_paths() == (existing,)


def test_table_failures_rejects_oversized_columns() -> None:
    """Check that table columns cannot be wider than their stripped content requires."""
    table_lines = [
        "| Name  | Value |",
        "|-------|-------|",
        "| one   | two   |",
    ]

    failures = markdown_tables.table_failures(ROOT / "example.md", 0, table_lines)

    assert failures == [
        "example.md:1: expected '| Name | Value |', found '| Name  | Value |'",
        "example.md:2: expected '|------|-------|', found '|-------|-------|'",
        "example.md:3: expected '| one  | two   |', found '| one   | two   |'",
    ]


def test_table_failures_accepts_minimal_pycharm_style_table() -> None:
    """Check that minimally sized PyCharm-style tables are accepted."""
    table_lines = [
        "| Name | Value |",
        "|------|-------|",
        "| one  | two   |",
    ]

    assert markdown_tables.table_failures(ROOT / "example.md", 0, table_lines) == []


def test_table_failures_preserves_separator_alignment_markers() -> None:
    """Check that separator rows stay unpadded and keep their alignment style."""
    table_lines = [
        "| Default | Left | Center | Right |",
        "|---------|:-----|:------:|------:|",
        "| a       | b    |   c    |     d |",
    ]

    assert markdown_tables.table_failures(ROOT / "example.md", 0, table_lines) == []


def test_normalize_markdown_tables_text_rewrites_tables_and_preserves_fences() -> None:
    """Check that the helper rewrites tables outside fences only."""
    source = "\n".join(
        [
            "| Name  | Value |",
            "|-------|-------|",
            "| one   | two   |",
            "",
            "```",
            "| Name  | Value |",
            "|-------|-------|",
            "```",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == "\n".join(
        [
            "| Name | Value |",
            "|------|-------|",
            "| one  | two   |",
            "",
            "```",
            "| Name  | Value |",
            "|-------|-------|",
            "```",
            "",
        ]
    )


def test_normalize_markdown_tables_text_preserves_table_indentation() -> None:
    """Check that table normalization uses the header row indentation."""
    source = "\n".join(
        [
            "  | Name  | Value |",
            "|-------|-------|",
            "    | one   | two   |",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == "\n".join(
        [
            "  | Name | Value |",
            "  |------|-------|",
            "  | one  | two   |",
            "",
        ]
    )


@pytest.mark.parametrize("indent", ("    ", "\t"))
def test_normalize_markdown_tables_text_preserves_indented_code_blocks(indent: str) -> None:
    """Check that indented code blocks that look like tables are not rewritten."""
    source = "\n".join(
        [
            f"{indent}| Name  | Value |",
            f"{indent}|-------|-------|",
            f"{indent}| one   | two   |",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == source


def test_normalize_markdown_tables_text_removes_mixed_indentation_when_header_is_unindented() -> None:
    """Check that mixed table indentation normalizes to the header row indentation."""
    source = "\n".join(
        [
            "| Name  | Value |",
            "  |-------|-------|",
            "    | one   | two   |",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == "\n".join(
        [
            "| Name | Value |",
            "|------|-------|",
            "| one  | two   |",
            "",
        ]
    )


def test_normalize_markdown_tables_text_treats_four_space_code_as_non_fence() -> None:
    """Check that indented code lines do not suppress later real tables."""
    source = "\n".join(
        [
            "    ```",
            "| Name  | Value |",
            "|-------|-------|",
            "| one   | two   |",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == "\n".join(
        [
            "    ```",
            "| Name | Value |",
            "|------|-------|",
            "| one  | two   |",
            "",
        ]
    )


def test_normalize_markdown_tables_text_rejects_invalid_closing_fence() -> None:
    """Check that invalid closing fences keep table-like fenced content untouched."""
    source = "\n".join(
        [
            "```",
            "``` not a close",
            "| Name  | Value |",
            "|-------|-------|",
            "| one   | two   |",
            "```",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == source


def test_normalize_markdown_tables_text_rejects_invalid_backtick_opening_fence() -> None:
    """Check that backticks in backtick-fence info strings do not suppress tables."""
    source = "\n".join(
        [
            "``` info `",
            "| Name  | Value |",
            "|-------|-------|",
            "| one   | two   |",
            "```",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == "\n".join(
        [
            "``` info `",
            "| Name | Value |",
            "|------|-------|",
            "| one  | two   |",
            "```",
            "",
        ]
    )


def test_normalize_markdown_tables_text_allows_backticks_in_tilde_fence_info() -> None:
    """Check that tilde-fence info strings may contain backticks."""
    source = "\n".join(
        [
            "~~~ info `",
            "| Name  | Value |",
            "|-------|-------|",
            "~~~",
            "",
        ]
    )

    assert markdown_tables.normalize_markdown_tables_text(source) == source


def test_table_failures_accepts_escaped_pipes_in_cell_content() -> None:
    """Check that escaped Markdown pipes do not create extra table cells."""
    table_lines = [
        "| A    | B |",
        "|------|---|",
        "| x\\|y | z |",
    ]

    assert markdown_tables.table_failures(ROOT / "example.md", 0, table_lines) == []


def test_table_failures_accepts_inline_code_pipes_in_cell_content() -> None:
    """Check that Markdown pipes inside inline code do not create extra table cells."""
    table_lines = [
        "| A       | B |",
        "|---------|---|",
        "| `x | y` | z |",
    ]

    assert markdown_tables.table_failures(ROOT / "example.md", 0, table_lines) == []


def test_table_failures_accepts_unmatched_backtick_pipes_as_cell_boundaries() -> None:
    """Check that unmatched backticks do not hide real table cell boundaries."""
    table_lines = [
        "| A  | B |",
        "|----|---|",
        "| `x | y |",
    ]

    assert markdown_tables.table_failures(ROOT / "example.md", 0, table_lines) == []


def test_normalize_markdown_tables_text_rewrites_inline_code_pipe_tables() -> None:
    """Check that Markdown pipes inside inline code stay in their original table cell."""
    source = "| A | B |\n|---|---|\n| `x | y` | z |\n"

    assert markdown_tables.normalize_markdown_tables_text(source) == "| A       | B |\n|---------|---|\n| `x | y` | z |\n"


def test_normalize_markdown_tables_file_check_reports_without_writing(tmp_path: pathlib.Path) -> None:
    """Check that check mode reports needed fixes without modifying files."""
    path = tmp_path / "example.md"
    source = "| Name  | Value |\n|-------|-------|\n| one   | two   |\n"
    path.write_text(source, encoding="utf-8")

    assert markdown_tables.normalize_markdown_tables_file(path, check=True)
    assert path.read_text(encoding="utf-8") == source


def test_normalize_markdown_tables_file_preserves_existing_newlines(tmp_path: pathlib.Path) -> None:
    """Check that table fixes preserve each line's existing newline spelling."""
    path = tmp_path / "example.md"
    path.write_bytes(b"| Name  | Value |\r\n|-------|-------|\n| one   | two   |\r\n")

    assert markdown_tables.normalize_markdown_tables_file(path)
    assert path.read_bytes() == b"| Name | Value |\r\n|------|-------|\n| one  | two   |\r\n"


def test_normalize_markdown_tables_file_writes_fix(tmp_path: pathlib.Path) -> None:
    """Check that the helper writes normalized Markdown tables."""
    path = tmp_path / "example.md"
    path.write_text("| Name  | Value |\n|-------|-------|\n| one   | two   |\n", encoding="utf-8")

    assert markdown_tables.normalize_markdown_tables_file(path)
    assert path.read_text(encoding="utf-8") == "| Name | Value |\n|------|-------|\n| one  | two   |\n"


def test_main_check_reports_pending_table_fix(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Check that the command-line check mode reports files that need fixes."""
    path = tmp_path / "example.md"
    path.write_text("| Name  | Value |\n|-------|-------|\n| one   | two   |\n", encoding="utf-8")

    assert markdown_tables.main(["--check", str(path)]) == 1

    captured = capsys.readouterr()
    assert "Markdown table style fixes needed:" in captured.err
    assert path.as_posix() in captured.err


def test_main_check_reports_non_fixable_table_failures(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Check that check mode fails for malformed tables the fixer cannot rewrite."""
    path = tmp_path / "example.md"
    source = "| A | B |\n|---|---|\n| 1 | 2 | 3 |\n"
    path.write_text(source, encoding="utf-8")

    assert markdown_tables.main(["--check", str(path)]) == 1

    captured = capsys.readouterr()
    assert "Markdown table validation failures:" in captured.err
    assert f"{path.as_posix()}:3: expected 2 cells, found 3" in captured.err
    assert path.read_text(encoding="utf-8") == source


def test_main_write_reports_remaining_non_fixable_table_failures(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Check that write mode fails when malformed tables remain after fixing."""
    path = tmp_path / "example.md"
    path.write_text("| A | B |\n|---|---|\n| 1 | 2 | 3 |\n", encoding="utf-8")

    assert markdown_tables.main([str(path)]) == 1

    captured = capsys.readouterr()
    assert "Markdown table validation failures:" in captured.err
    assert f"{path.as_posix()}:3: expected 2 cells, found 3" in captured.err
