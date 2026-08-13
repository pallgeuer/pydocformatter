"""Tests for Markdown fenced Python source support."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import pathlib
import collections
import dataclasses
from io import StringIO
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import pydocformatter.markdown as markdown_source
import pydocformatter.rules.runner as rule_runner
from pydocformatter import formatter, rules_selection
from pydocformatter.cli import settings_check
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.models import SourceContext


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


def format_markdown(source: str, *, select: tuple[str, ...] = ("PDF001",), fix: bool = False) -> formatter.FormatterResult:
    """Format Markdown with an isolated exact rule selection."""
    settings = CheckSettings(select=select, source_context=SourceContext.FRAGMENT)
    return formatter.format_source(source, "example.md", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=fix)


def python_fences(source: str) -> tuple[markdown_source.MarkdownFence, ...]:
    """Return supported Python fences, including skipped fences, for test inspection."""
    return tuple(fence for fence in markdown_source.markdown_fences(source) if fence.is_python)


def test_python_fences_recognize_supported_languages_and_markers() -> None:
    source = "Prose.\n\n```python\none = 1\n```\n\n~~~py option\ntwo = 2\n~~~~\n\n```python3\nthree = 3\n```\n"

    fences = python_fences(source)

    assert tuple(source[fence.body_start : fence.body_end] for fence in fences) == ("one = 1\n", "two = 2\n", "three = 3\n")
    assert tuple(fence.body_start_line for fence in fences) == (4, 8, 12)
    assert not any(fence.skipped for fence in fences)


def test_python_fences_ignore_other_indented_and_unclosed_fences() -> None:
    source = "````text\n```python\ninside = 1\n```\n````\n\n    ```python\n    indented = 2\n    ```\n\n```python\nunclosed = 3\n"

    assert not python_fences(source)


def test_python_fences_do_not_interpret_commonmark_container_prefixes() -> None:
    source = "> ```python\n> quoted = 1\n> ```\n\n- item\n\n    ```python\n    listed = 2\n    ```\n"

    assert not python_fences(source)


@pytest.mark.parametrize("separator", ["\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"])
def test_fence_discovery_only_treats_cr_and_lf_as_physical_line_endings(separator: str) -> None:
    source = f"```python\nvalue = 1{separator}```\n"

    assert not markdown_source.markdown_fences(source)


def test_python_fences_record_standalone_skip_token() -> None:
    source = "```python pydocfmt-skip title=before\nskipped = 1\n```\n\n```python pydocfmt-skipped\nchecked = 2\n```\n"

    fences = python_fences(source)

    assert tuple(fence.skipped for fence in fences) == (True, False)


def test_check_maps_findings_to_markdown_lines() -> None:
    source = "Heading\n=======\n\n```python\ndef example():\n    '''Return an example.'''\n```\n"

    result = format_markdown(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert not result.errors


def test_fix_rewrites_only_python_fence_bodies() -> None:
    source = "Before.\n\n```python\ndef example():\n    '''Return an example.'''\n```\n\n```text\ndef unchanged():\n    '''Not Python.'''\n```\n\nAfter.\n"
    expected = source.replace("    '''Return an example.'''", '    """Return an example."""')

    result = format_markdown(source, fix=True)

    assert result.new_source == expected
    assert result.modified
    assert sum(result.fixed_findings.values()) == 1
    assert not result.unfixed_findings
    assert not result.errors


def test_skip_token_leaves_python_fence_untouched() -> None:
    source = "```python pydocfmt-skip\ndef example():\n    '''Return an example.'''\n```\n"

    result = format_markdown(source, fix=True)

    assert result.new_source == source
    assert not result.modified
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_malformed_python_fence_makes_fix_atomic() -> None:
    source = "```python\ndef example():\n    '''Return an example.'''\n```\n\n```python\ndef broken(:\n```\n"

    result = format_markdown(source, fix=True)

    assert result.new_source == source
    assert not result.modified
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3,),)
    assert len(result.errors) == 1
    assert "@ 7:" in result.errors[0]


def test_fix_offsets_later_unfixed_findings_after_line_count_changes() -> None:
    source = '```python\ndef first():\n    """Return a value after explaining enough detail to require multiline reflow."""\n```\n\n```python\ndef second():\n    """Return a value with a summary that is deliberately much too long."""\n```\n'
    settings = CheckSettings(select=("PDF101", "PDF203"), source_context=SourceContext.FRAGMENT, line_length=40)

    result = formatter.format_source(source, "example.md", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source is not None
    expected_line = next(line_number for line_number, line in enumerate(result.new_source.splitlines(), start=1) if "Return a value with" in line)
    assert len(result.unfixed_findings) == 2
    assert result.unfixed_findings[-1].line_numbers[0] == expected_line
    assert expected_line > 8
    assert result.modified
    assert not result.errors


def test_module_only_rules_are_inapplicable_in_fragment_context() -> None:
    source = "```python\ndef undocumented():\n    return None\n```\n"

    result = format_markdown(source, select=("PDF602", "PDF608"))

    assert not result.unfixed_findings
    assert not result.errors


@pytest.mark.parametrize(("path", "extension"), [pytest.param("example.md", (), id="built-in"), pytest.param("example.mdx", (("mdx", "markdown"),), id="custom")])
def test_direct_source_formatter_applies_markdown_language_defaults(path: str, extension: settings_check.StringMap) -> None:
    source = "```python\ndef undocumented():\n    return None\n```\n"
    settings = CheckSettings(select=("PDF602", "PDF608"), extension=extension, docstring_missing_documentation=settings_check.DocstringMissingDocumentation.ALL_DOCSTRINGS)
    selection = rules_selection.select_rules(settings)

    default = formatter.format_source(source, path, settings=settings, rule_selection=selection, fix=False)
    opted_out = formatter.format_source(source, path, settings=settings, rule_selection=selection, fix=False, apply_language_defaults=False)

    assert not default.unfixed_findings
    assert tuple(finding.rule.code.tag for finding in opted_out.unfixed_findings) == ("PDF602", "PDF608")
    assert not default.errors
    assert not opted_out.errors


def test_direct_stream_formatter_applies_markdown_language_defaults() -> None:
    source = "```python\ndef undocumented():\n    return None\n```\n"
    settings = CheckSettings(select=("PDF602",), docstring_missing_documentation=settings_check.DocstringMissingDocumentation.ALL_DOCSTRINGS)

    result = formatter.format_stream("example.md", file=StringIO(source), settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

    assert not result.unfixed_findings
    assert not result.errors


@pytest.mark.parametrize("indent_width", range(4))
def test_fence_indentation_is_removed_from_logical_source_and_restored_for_changes(indent_width: int) -> None:
    indent = " " * indent_width
    source = f"{indent}```python\n{indent}def example():\n{indent}    '''Return an example.'''\n{indent}```\n"
    expected = source.replace("'''Return an example.'''", '"""Return an example."""')

    fence = python_fences(source)[0]
    result = format_markdown(source, fix=True)

    assert fence.source == "def example():\n    '''Return an example.'''\n"
    assert result.new_source == expected
    assert result.modified
    assert not result.errors


def test_fence_reconstruction_preserves_unchanged_lines_with_shorter_indentation() -> None:
    source = "   ```python\n value = 1\n   def example():\n       '''Return an example.'''\n   ```\n"
    expected = source.replace("'''Return an example.'''", '"""Return an example."""')

    result = format_markdown(source, fix=True)

    assert result.new_source == expected
    assert result.new_source.startswith("   ```python\n value = 1\n")
    assert not result.errors


def test_fence_reconstruction_does_not_indent_generated_blank_lines() -> None:
    fence = python_fences("  ```python\n  original = 1\n  ```\n")[0]

    rendered = fence.render_body("first = 1\n\nsecond = 2\n")

    assert rendered == "  first = 1\n\n  second = 2\n"


def test_fence_body_replacement_reconstructs_multiple_fences_in_one_pass() -> None:
    source = "Before.\n\n```python\nfirst = 1\n```\n\nBetween.\n\n~~~python\nsecond = 2\n~~~\n\nAfter.\n"
    fences = python_fences(source)

    result = markdown_source.replace_fence_bodies(source, ((fences[0], "first = 10\n"), (fences[1], "")))

    assert result == "Before.\n\n```python\nfirst = 10\n```\n\nBetween.\n\n~~~python\n~~~\n\nAfter.\n"


def test_fence_body_replacement_rejects_invalid_ranges() -> None:
    source = "```python\nfirst = 1\n```\n\n```python\nsecond = 2\n```\n"
    first, second = python_fences(source)

    with pytest.raises(ValueError, match="source order"):
        markdown_source.replace_fence_bodies(source, ((second, second.source), (first, first.source)))
    with pytest.raises(ValueError, match="source order"):
        markdown_source.replace_fence_bodies(source, ((first, first.source), (dataclasses.replace(second, body_start=first.body_end - 1), second.source)))
    with pytest.raises(ValueError, match="outside"):
        markdown_source.replace_fence_bodies(source, ((dataclasses.replace(first, body_end=len(source) + 1), first.source),))


def test_fence_body_replacement_handles_dense_documents() -> None:
    source = "".join(f"```python\nvalue_{index} = {index}\n```\n" for index in range(3000))
    fences = python_fences(source)

    result = markdown_source.replace_fence_bodies(source, tuple((fence, fence.source) for fence in fences))

    assert len(fences) == 3000
    assert result == source


def test_first_line_fence_after_utf8_bom_is_formatted_without_moving_bom() -> None:
    source = "\ufeff```python\ndef example():\n    '''Return an example.'''\n```\n"

    result = format_markdown(source, fix=True)

    assert result.new_source == source.replace("'''Return an example.'''", '"""Return an example."""')
    assert result.new_source.startswith("\ufeff```python")
    assert not result.errors


def test_crlf_fence_without_final_newline_preserves_host_line_endings_and_terminator() -> None:
    source = "```python\r\ndef example():\r\n    '''Return an example.'''\r\n```"

    result = format_markdown(source, fix=True)

    assert result.new_source == source.replace("'''Return an example.'''", '"""Return an example."""')
    assert result.new_source is not None
    assert not result.new_source.endswith(("\n", "\r"))
    assert not result.errors


def test_empty_closed_python_fence_is_a_clean_source() -> None:
    source = "Before.\n\n```python\n```\n\nAfter.\n"

    result = format_markdown(source, fix=True)

    assert result.new_source == source
    assert not result.modified
    assert not result.fixed_findings
    assert not result.unfixed_findings
    assert not result.errors


def test_parse_diagnostic_uses_host_coordinates_without_embedded_parser_coordinates() -> None:
    source = "Heading\n\n   ```python\n   def broken(:\n   ```\n"

    result = format_markdown(source)

    assert len(result.errors) == 1
    assert "Syntax Error @ 4:4" in result.errors[0]
    assert "error at " not in result.errors[0]
    assert "   def broken(:\n   ^" in result.errors[0]


def test_malformed_block_checks_each_other_parseable_block_once(mocker: MockerFixture) -> None:
    source = "```python\ndef example():\n    '''Return an example.'''\n```\n\n```python\ndef broken(:\n```\n"
    run = mocker.spy(rule_runner, "run_rule_plan")

    result = format_markdown(source, fix=True)

    assert run.call_count == 1
    assert run.call_args.kwargs["fix"] is False
    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3,),)
    assert len(result.errors) == 1


def test_fix_runs_each_parseable_block_rule_plan_once(mocker: MockerFixture) -> None:
    source = "```python\ndef first():\n    '''Return the first.'''\n```\n\n```python\ndef second():\n    '''Return the second.'''\n```\n"
    run = mocker.spy(rule_runner, "run_rule_plan")

    result = format_markdown(source, fix=True)

    assert run.call_count == 2
    assert all(call.kwargs["fix"] is True for call in run.call_args_list)
    assert result.modified
    assert not result.errors


def test_fix_scans_markdown_fences_once_before_and_once_after_rewrite(mocker: MockerFixture) -> None:
    source = "```python\ndef example():\n    '''Return an example.'''\n```\n"
    scan = mocker.spy(markdown_source, "markdown_fences")

    result = format_markdown(source, fix=True)

    assert scan.call_count == 2
    assert result.modified
    assert not result.errors


def test_rule_operational_error_details_use_markdown_host_lines(mocker: MockerFixture) -> None:
    source = "Heading\n\n```python\nvalue = 1\n```\n"
    settings = CheckSettings(select=("PDF001",), source_context=SourceContext.FRAGMENT)
    metadata = rules_selection.select_rules(settings).candidate_rules[0].rule
    error = rule_runner.RuleOperationalError("example.md: automatic fix iteration limit reached", line_details=(rule_runner.RuleErrorLineDetails(rule=metadata, line_numbers=(1,)),))
    mocker.patch.object(
        rule_runner, "run_rule_plan", return_value=rule_runner.RuleRunResult(source="value = 1\n", initial_findings=(), fixed_findings=(), unfixed_findings=(), source_changed=False, errors=(error,))
    )

    result = formatter.format_source(source, "example.md", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

    assert result.errors == ("example.md: automatic fix iteration limit reached; likely rules and lines: PDF001 lines 4",)


def test_rule_operational_error_rolls_back_complete_markdown_fix(mocker: MockerFixture) -> None:
    source = "```python\nvalue = 1\n```\n"
    settings = CheckSettings(select=("PDF001",), source_context=SourceContext.FRAGMENT)
    error = rule_runner.RuleOperationalError("example.md: PDF001 automatic fix failed: broken fix")
    mocker.patch.object(
        rule_runner, "run_rule_plan", return_value=rule_runner.RuleRunResult(source="value = 2\n", initial_findings=(), fixed_findings=(), unfixed_findings=(), source_changed=True, errors=(error,))
    )

    result = formatter.format_source(source, "example.md", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == source
    assert not result.modified
    assert not result.fixed_findings
    assert result.errors == (error.message,)


def test_fix_rejects_formatted_source_that_would_change_fence_topology() -> None:
    source = '````python\n"""Summary.\n\n    ````\n"""\n````\n'
    settings = CheckSettings(select=("PDF100",), source_context=SourceContext.FRAGMENT, docstring_convention=DocstringConvention.GOOGLE)

    result = formatter.format_source(source, "example.md", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == source
    assert not result.modified
    assert not result.fixed_findings
    assert tuple((finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings) == (("PDF100", (4,)),)
    assert len(result.errors) == 1
    assert "Unsafe Markdown rewrite" in result.errors[0]


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DOCUMENTED_FENCE_CASES = (
    ("docs/devel/rule_implementation_spec.md", 0, collections.Counter()),
    ("docs_site/checking.md", 0, collections.Counter()),
    ("docs_site/formatting.md", 0, collections.Counter({"PDF101": 1, "PDF300": 1, "PDF304": 1, "PDF309": 2, "PDF310": 2})),
    ("docs_site/formatting.md", 1, collections.Counter()),
    ("src/pydocformatter/rules/definitions/PDF/PDF.md", 0, collections.Counter()),
    ("src/pydocformatter/rules/definitions/PDF/PDF.md", 1, collections.Counter()),
    ("src/pydocformatter/rules/definitions/PDF/PDF.md", 2, collections.Counter()),
    ("src/pydocformatter/rules/definitions/PDF/PDF413_section_name_superfluous_colon.md", 0, collections.Counter({"PDF100": 1})),
    ("src/pydocformatter/rules/definitions/PDF/PDF413_section_name_superfluous_colon.md", 1, collections.Counter({"PDF100": 1, "PDF404": 1})),
)
_FENCE_LANGUAGE_RE = re.compile(r"^( {0,3}(?:`{3,}|~{3,})[ \t]*(?:python3|python|py))(?=[ \t\r\n]|$)", flags=re.IGNORECASE)
_FENCE_SKIP_RE = re.compile(r"[ \t]+pydocfmt-skip(?=[ \t\r\n]|$)")


def _activate_only_python_fence(source: str, target_index: int) -> str:
    """Return Markdown with only one Python fence not carrying a skip token."""
    replacements: list[tuple[int, int, str]] = []
    for index, fence in enumerate(python_fences(source)):
        opening_start = fence.body_start - len(fence.opening_line)
        if index == target_index:
            opening_line = _FENCE_SKIP_RE.sub("", fence.opening_line, count=1)
        elif fence.skipped:
            opening_line = fence.opening_line
        else:
            opening_line = _FENCE_LANGUAGE_RE.sub(r"\1 pydocfmt-skip", fence.opening_line, count=1)
        replacements.append((opening_start, fence.body_start, opening_line))
    candidate = source
    for opening_start, body_start, opening_line in reversed(replacements):
        candidate = f"{candidate[:opening_start]}{opening_line}{candidate[body_start:]}"
    return candidate


@pytest.mark.parametrize(("relative_path", "fence_index", "expected_codes"), _DOCUMENTED_FENCE_CASES)
def test_repository_markdown_python_fence_findings_without_skip(relative_path: str, fence_index: int, expected_codes: collections.Counter[str]) -> None:
    path = _ROOT / relative_path
    source = _activate_only_python_fence(path.read_text(encoding="utf-8"), fence_index)
    profile = settings_check.SETTINGS_SCHEMA.load_profile(path=str(path))
    effective_profile = settings_check.effective_profile_for_path(profile, str(path))
    selection = rules_selection.select_rules(profile.settings, profile=profile)

    result = formatter.format_source(source, str(path), settings=effective_profile.settings, rule_selection=selection, fix=False)
    finding_codes = collections.Counter(finding.rule.code.tag for finding in result.unfixed_findings for _ in finding.line_numbers)

    assert finding_codes == expected_codes
    assert not result.errors
