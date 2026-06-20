import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter.cli.settings_check import CheckSettings


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("value = compute()#noqa\n", "value = compute()  # noqa\n"),
        ("value = compute()#noqa   \n", "value = compute()  # noqa\n"),
        ("value = compute() #   nosec reason\n", "value = compute()  # nosec reason\n"),
        ("value = compute()\t#TYPE : ignore[assignment]\n", "value = compute()  # TYPE : ignore[assignment]\n"),
        ("value = compute() # ruff: noqa: F401\n", "value = compute()  # ruff: noqa: F401\n"),
        ("value = compute() # pragma: no cover\n", "value = compute()  # pragma: no cover\n"),
    ),
)
def test_directive_spacing_normalizes_known_trailing_directives(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source, line_length=10)
    assert result.new_source == expected


def test_directive_spacing_preserves_payload_after_marker_space() -> None:
    source = "value = compute()#   PyLiNt : disable = missing-docstring  # reason\n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "value = compute()  # PyLiNt : disable = missing-docstring  # reason\n"


def test_directive_spacing_preserves_eof_without_final_newline() -> None:
    source = "value = compute()#noqa"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "value = compute()  # noqa"


def test_directive_spacing_preserves_existing_line_endings_outside_replacement() -> None:
    source = "value = compute()#noqa\r\nother = compute()#nosec\r\n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "value = compute()  # noqa\r\nother = compute()  # nosec\r\n"


def test_directive_spacing_reports_original_lines_in_check_mode() -> None:
    source = "first = compute()  # noqa\nsecond = compute()#noqa\nthird = compute() # nosec\n"
    settings = CheckSettings(select=("PCF003",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (3,))


def test_directive_spacing_applies_in_syntax_sensitive_positions_without_extraction() -> None:
    source = "@decorator#noqa\ndef function():\n    call(\n        value,# type: ignore[arg-type]\n    )\n    if enabled:#nosec\n        pass\n"
    result = pcf_helpers.format_pcf(source, line_length=8)
    assert result.new_source == "@decorator  # noqa\ndef function():\n    call(\n        value,  # type: ignore[arg-type]\n    )\n    if enabled:  # nosec\n        pass\n"


def test_directive_spacing_and_regular_trailing_extraction_apply_together_without_overlap() -> None:
    source = "directive = compute()#noqa\nordinary = compute()#ordinary trailing words that need moving\n"
    result = pcf_helpers.format_pcf(source, line_length=28)
    assert result.new_source == "directive = compute()  # noqa\n# ordinary trailing words\n# that need moving\nordinary = compute()\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF002": 1, "PCF003": 1}


def test_directive_spacing_treats_additional_hashes_as_directive_payload() -> None:
    source = "value = compute()#noqa  # keep this tool-specific payload\n"
    result = pcf_helpers.format_pcf(source, line_length=20)
    assert result.new_source == "value = compute()  # noqa  # keep this tool-specific payload\n"


def test_directive_spacing_is_independent_of_trailing_comment_formatting() -> None:
    source = "value = compute()#noqa\nother = compute()#ordinary prose\n"
    settings = CheckSettings(select=("PCF003",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()  # noqa\nother = compute()#ordinary prose\n"


def test_directive_spacing_does_not_modify_unknown_or_standalone_directives() -> None:
    source = "value = compute()#not-a-known-directive\n#noqa\n"
    settings = CheckSettings(select=("PCF003",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == source
