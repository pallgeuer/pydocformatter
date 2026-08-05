"""Tests for comment formatting helpers."""

# First-party imports
from pydocformatter.cli.settings_check import CheckSettings, CommentTaskMarkerMode
from pydocformatter.rules.definition_helpers import comment_formatting


def test_comment_rendering_and_width_helpers_cover_tabs_tiny_widths_and_empty_content() -> None:
    assert comment_formatting.available_comment_width("\t", line_length=12, tab_width=4, prefix="> ") == 4
    assert comment_formatting.render_comment("", indent="    ") == "    #"


def test_task_marker_unwrapped_normalization_preserves_supplied_blank_continuations() -> None:
    texts = ("value = compute()", "", "next = call()")
    no_wrap = CheckSettings(comment_task_marker_mode=CommentTaskMarkerMode.NO_WRAP)
    code_like_hanging = CheckSettings(comment_task_marker_mode=CommentTaskMarkerMode.HANGING)

    assert comment_formatting.format_task_marker_lines("TODO", texts, indent="", settings=no_wrap) == ("TODO: value = compute()", "", "      next = call()")
    assert comment_formatting.format_task_marker_lines("TODO", texts, indent="", settings=code_like_hanging) == ("TODO: value = compute()", "", "      next = call()")
