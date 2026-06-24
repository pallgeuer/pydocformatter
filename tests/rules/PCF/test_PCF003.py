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
        ("value = compute()\t#TYPE : ignore[assignment]\n", "value = compute()  # type: ignore[assignment]\n"),
        ("value = compute() # TY : ignore[invalid-argument-type]\n", "value = compute()  # ty: ignore[invalid-argument-type]\n"),
        ("value = compute() # ruff: noqa: F401\n", "value = compute()  # ruff: noqa: F401\n"),
        ("value = compute() # pragma: no cover\n", "value = compute()  # pragma: no cover\n"),
    ),
)
def test_directive_normalization_normalizes_known_trailing_directives(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source, line_length=10)
    assert result.new_source == expected


def test_directive_normalization_preserves_payload_after_marker_space() -> None:
    source = "value = compute()#   PyLiNt : disable = missing-docstring  # reason\n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "value = compute()  # pylint: disable=missing-docstring  # reason\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("#ruff: noqa\n", "# ruff: noqa\n"),
        ("#   pylint : disable-next = missing-docstring,unused-argument\n", "# pylint: disable-next=missing-docstring, unused-argument\n"),
        ("    #fmt : off\n", "    # fmt: off\n"),
        ("#TYPE : ignore[assignment,arg-type]\n", "# type: ignore[assignment, arg-type]\n"),
        ("#TY : ignore[invalid-argument-type,unresolved-import]\n", "# ty: ignore[invalid-argument-type, unresolved-import]\n"),
    ),
)
def test_directive_normalization_normalizes_standalone_directives(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("#noqa:\n", "# noqa:\n"),
        ("#noqa:   \n", "# noqa:\n"),
        ("#ruff: noqa:\n", "# ruff: noqa:\n"),
        ("#TY : ignore\n", "# ty: ignore\n"),
        ("#mypy:\n", "# mypy:\n"),
        ("#fmt:\n", "# fmt:\n"),
        ("value = compute()#noqa:\n", "value = compute()  # noqa:\n"),
        ("value = compute()#TY : ignore\n", "value = compute()  # ty: ignore\n"),
        ("value = compute()#fmt:\n", "value = compute()  # fmt:\n"),
        ("#noqa:  # reason\n", "# noqa: # reason\n"),
    ),
)
def test_directive_normalization_does_not_add_trailing_space_for_empty_payloads(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == expected
    assert all(not line.endswith((" ", "\t", "\f")) for line in result.new_source.splitlines())


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("value = compute()#TYPE : ignore[assignment,arg-type]\n", "value = compute()  # type: ignore[assignment, arg-type]\n"),
        ("value = compute()#TYPE : ignore[arg-type,ty:invalid-argument-type]\n", "value = compute()  # type: ignore[arg-type, ty:invalid-argument-type]\n"),
        ("value = compute()#TY : ignore[invalid-argument-type,unresolved-import]\n", "value = compute()  # ty: ignore[invalid-argument-type, unresolved-import]\n"),
        ("value = compute()#noqa: f401,e501\n", "value = compute()  # noqa: F401, E501\n"),
        ("value = compute()#ruff : noqa : ruf100, f401\n", "value = compute()  # ruff: noqa: RUF100, F401\n"),
        ("value = compute()#pylint:disable=missing-docstring,unused-argument\n", "value = compute()  # pylint: disable=missing-docstring, unused-argument\n"),
    ),
)
def test_directive_normalization_normalizes_safe_machine_readable_payloads(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == expected


def test_directive_normalization_preserves_eof_without_final_newline() -> None:
    source = "value = compute()#noqa"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "value = compute()  # noqa"


def test_directive_normalization_preserves_existing_line_endings_outside_replacement() -> None:
    source = "value = compute()#noqa\r\nother = compute()#nosec\r\n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "value = compute()  # noqa\r\nother = compute()  # nosec\r\n"


def test_directive_normalization_reports_original_lines_in_check_mode() -> None:
    source = "first = compute()  # noqa\nsecond = compute()#noqa\nthird = compute() #   nosec\n"
    settings = CheckSettings(select=("PCF003",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (3,))


def test_directive_normalization_applies_in_syntax_sensitive_positions_without_extraction() -> None:
    source = "@decorator#noqa\ndef function():\n    call(\n        value,# type: ignore[arg-type]\n    )\n    if enabled:#nosec\n        pass\n"
    result = pcf_helpers.format_pcf(source, line_length=8)
    assert result.new_source == "@decorator  # noqa\ndef function():\n    call(\n        value,  # type: ignore[arg-type]\n    )\n    if enabled:  # nosec\n        pass\n"


def test_directive_normalization_and_regular_trailing_extraction_apply_together_without_overlap() -> None:
    source = "directive = compute()#noqa\nordinary = compute()#ordinary trailing words that need moving\n"
    result = pcf_helpers.format_pcf(source, line_length=28)
    assert result.new_source == "directive = compute()  # noqa\n# ordinary trailing words\n# that need moving\nordinary = compute()\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF002": 2, "PCF003": 1, "PCF004": 1}


def test_directive_normalization_treats_additional_hashes_as_directive_payload() -> None:
    source = "value = compute()#TY : ignore[invalid-argument-type]  # fmt: skip\nother = compute()#noqa  # keep this tool-specific payload\n"
    result = pcf_helpers.format_pcf(source, line_length=20)
    assert result.new_source == "value = compute()  # ty: ignore[invalid-argument-type]  # fmt: skip\nother = compute()  # noqa  # keep this tool-specific payload\n"


def test_directive_normalization_preserves_ambiguous_payloads_after_safe_prefix_cleanup() -> None:
    source = "value = compute()#noqa: not a code list because prose\n#pylint:disable=missing-docstring because prose\n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "value = compute()  # noqa: not a code list because prose\n# pylint: disable=missing-docstring because prose\n"


def test_directive_normalization_preserves_trailing_code_to_hash_spacing_when_selected_alone() -> None:
    source = "value = compute()#noqa\nother = compute()#ordinary prose\n"
    settings = CheckSettings(select=("PCF003",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()# noqa\nother = compute()#ordinary prose\n"


def test_directive_normalization_does_not_modify_unknown_directives() -> None:
    source = "value = compute()#not-a-known-directive\n#noqa\n"
    settings = CheckSettings(select=("PCF003",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()#not-a-known-directive\n# noqa\n"


def test_trailing_directive_spacing_and_normalization_report_separate_defects_in_check_mode() -> None:
    source = "gap = 1 # type: ignore\ncontent = 2  #TYPE : ignore\nboth = 3 #TYPE : ignore\n"
    settings = CheckSettings(select=("PCF002", "PCF003"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert tuple((finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings) == (("PCF002", (1,)), ("PCF002", (3,)), ("PCF003", (2,)), ("PCF003", (3,)))
