"""Focused named-selector tests for PCF006 and suppression matching."""

# Future imports
from __future__ import annotations

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings


def format_source(source: str, *, select: tuple[str, ...], fix: bool = False) -> formatter.FormatterResult:
    settings = CheckSettings(select=select, line_length=40)
    return formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=fix)


def test_canonical_name_suppresses_local_and_file_wide_findings() -> None:
    local = 'def function():\n    """This is a long summary that needs to wrap onto more than one physical line."""  # pydocfmt: ignore[docstring-reflow]\n'
    file_wide = '# pydocfmt: file-ignore[docstring-reflow]\n"""This is a long summary that needs to wrap onto more than one physical line."""\n'

    local_result = format_source(local, select=("PDF101",))
    file_result = format_source(file_wide, select=("PDF101",))

    assert local_result.unfixed_findings == ()
    assert file_result.unfixed_findings == ()


def test_mixed_case_name_is_accepted_and_normalized_by_pcf003() -> None:
    source = "# pydocfmt: ignore[Docstring-Reflow]\nvalue = 1\n"

    result = format_source(source, select=("PCF003",), fix=True)

    assert result.new_source == "# pydocfmt: ignore[docstring-reflow]\nvalue = 1\n"


def test_code_name_alias_pair_is_audited_once_when_unused() -> None:
    code_first = "# pydocfmt: ignore[PDF101, docstring-reflow]\nvalue = 1\n"
    name_first = "# pydocfmt: ignore[docstring-reflow, PDF101]\nvalue = 1\n"

    code_result = format_source(code_first, select=("PDF101", "PCF006"))
    name_result = format_source(name_first, select=("PDF101", "PCF006"))

    assert tuple(finding.message for finding in code_result.unfixed_findings) == ("Suppression selector 'PDF101' did not suppress any findings",)
    assert tuple(finding.message for finding in name_result.unfixed_findings) == ("Suppression selector 'docstring-reflow' did not suppress any findings",)


def test_code_name_alias_pair_suppresses_one_finding_without_unused_diagnostic() -> None:
    source = 'def function():\n    """This is a long summary that needs to wrap onto more than one physical line."""  # pydocfmt: ignore[docstring-reflow, PDF101]\n'

    result = format_source(source, select=("PDF101", "PCF006"))

    assert result.unfixed_findings == ()


def test_every_matching_broad_and_exact_alias_selector_receives_usage_credit() -> None:
    source = 'def function():\n    """This is a long summary that needs to wrap onto more than one physical line."""  # pydocfmt: ignore[PDF, docstring-reflow, PDF101]\n'

    result = format_source(source, select=("PDF101", "PCF006"))

    assert result.unfixed_findings == ()


def test_broad_and_exact_selectors_remain_distinct_for_unused_auditing() -> None:
    source = "# pydocfmt: ignore[ALL, PDF101]\nvalue = 1\n"

    result = format_source(source, select=("PDF101", "PCF006"))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Suppression selector 'ALL' did not suppress any findings", "Suppression selector 'PDF101' did not suppress any findings")


def test_semantic_deduplication_is_scoped_to_each_directive() -> None:
    source = "# pydocfmt: file-ignore[docstring-reflow, PDF101]\n# pydocfmt: ignore[PDF101, docstring-reflow]\nvalue = 1\n"

    result = format_source(source, select=("PDF101", "PCF006"))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Suppression selector 'docstring-reflow' did not suppress any findings",
        "Suppression selector 'PDF101' did not suppress any findings",
    )


def test_generic_and_pydocfmt_noqa_remain_code_only() -> None:
    generic = '"""This is a long summary that needs to wrap onto more than one physical line."""  # noqa: docstring-reflow\n'
    pydocfmt_noqa = '# pydocfmt: noqa: docstring-reflow\n"""This is a long summary that needs to wrap onto more than one physical line."""\n'

    generic_result = format_source(generic, select=("PDF101",))
    pydocfmt_result = format_source(pydocfmt_noqa, select=("PDF101",))

    assert tuple(str(finding.rule.code) for finding in generic_result.unfixed_findings) == ("PDF101",)
    assert tuple(str(finding.rule.code) for finding in pydocfmt_result.unfixed_findings) == ("PDF101",)


def test_synthesized_unused_suppression_finding_can_be_suppressed_by_rule_name() -> None:
    source = "# pydocfmt: file-ignore[unused-suppression]\n# pydocfmt: ignore[]\n# Short comment.\n"

    result = format_source(source, select=("PCF006",))

    assert result.unfixed_findings == ()


def test_non_ascii_confusable_name_is_invalid_and_cannot_suppress_a_rule() -> None:
    source = '# pydocfmt: file-ignore[docstring-blan\u212a-line-whitespace]\n"""Summary.\n \nMore.\n"""\n'

    result = format_source(source, select=("PDF103", "PCF006"))

    assert tuple((str(finding.rule.code), finding.line_numbers, finding.message) for finding in result.unfixed_findings) == (
        ("PDF103", (3,), "Blank docstring line has whitespace"),
        ("PCF006", (1,), "Invalid pydocfmt suppression selector 'docstring-blan\u212a-line-whitespace'"),
    )
