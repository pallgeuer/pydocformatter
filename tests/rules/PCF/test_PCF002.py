# Third-party imports
import pytest

# First-party imports
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PCF.PCF002_trailing_comment_spacing import PCF002TrailingCommentSpacing


def test_trailing_comment_spacing_and_empty_comment_are_canonicalized() -> None:
    source = "first = 1 #bad spacing\nsecond = 2 #   \n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "first = 1  # bad spacing\nsecond = 2  #\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("if enabled:\n    value = compute()#comment\n", "if enabled:\n    value = compute()  # comment\n"),
        ("if enabled:\n    value = compute() \t\f #  comment   \n", "if enabled:\n    value = compute()  # comment\n"),
        ("value = compute()  ### heading-like content\n", "value = compute()  # ## heading-like content\n"),
        ("value = compute()#", "value = compute()  #"),
    ],
)
def test_trailing_comment_normalization_covers_missing_spacing_whitespace_and_additional_hashes(source: str, expected: str) -> None:
    assert pcf_helpers.format_pcf(source).new_source == expected


def test_spacing_does_not_extract_when_selected_alone() -> None:
    source = "value = compute()#This trailing comment has enough words that extraction would move it.\n"
    settings = CheckSettings(select=("PCF002",), line_length=42)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()  # This trailing comment has enough words that extraction would move it.\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF002": 1}


def test_spacing_preserves_existing_line_endings_outside_replacement() -> None:
    source = "first = compute()#bad spacing\r\nsecond = compute()#also bad\n"
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == "first = compute()  # bad spacing\r\nsecond = compute()  # also bad\n"


def test_protected_trailing_comments_only_normalize_code_to_hash_spacing() -> None:
    source = "value = compute() # type: ignore\nother = compute() # nosec\n"
    settings = CheckSettings(select=("PCF002",), line_length=20)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()  # type: ignore\nother = compute()  # nosec\n"


def test_protected_trailing_comments_strip_terminal_whitespace() -> None:
    source = "value = compute() # type: ignore   \n"
    settings = CheckSettings(select=("PCF002",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()  # type: ignore\n"


@pytest.mark.parametrize(
    ("directive", "expected_gap"),
    [
        ("# type: ignore", "  "),
        ("# TYPE : ignore", "  "),
        ("# noqa", " "),
        ("# nosec", "  "),
        ("# nosemgrep", "  "),
        ("# pylint: disable=x", "  "),
        ("# pyright: ignore", "  "),
        ("# mypy: ignore-errors", "  "),
        ("# ruff: noqa", "  "),
        ("# flake8: noqa", "  "),
        ("# fmt: off", "  "),
        ("# isort: skip", "  "),
        ("# pragma: no cover", "  "),
    ],
)
def test_all_protected_trailing_directive_families_preserve_payload_after_hash(directive: str, expected_gap: str) -> None:
    source = f"value = compute() {directive}\n"
    settings = CheckSettings(select=("PCF002",), line_length=10)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == f"value = compute(){expected_gap}{directive}\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("value = compute()#noqa\n", "value = compute()  #noqa\n"),
        ("value = compute() #   nosec reason\n", "value = compute()  #   nosec reason\n"),
        ("value = compute() # TYPE : ignore[x]\n", "value = compute()  # TYPE : ignore[x]\n"),
    ],
)
def test_directives_keep_hash_payload_when_spacing_selected_alone(source: str, expected: str) -> None:
    settings = CheckSettings(select=("PCF002",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == expected


def test_trailing_spacing_rule_does_not_modify_standalone_comments_when_selected_alone() -> None:
    source = "#bad standalone spacing\nvalue = 1 #bad trailing spacing\n"
    settings = CheckSettings(select=("PCF002",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "#bad standalone spacing\nvalue = 1  # bad trailing spacing\n"


def test_spacing_check_reports_original_line() -> None:
    source = "value = 1 #bad trailing spacing\n"
    settings = CheckSettings(select=("PCF002",))
    checked = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert tuple(finding.line_numbers for finding in checked.unfixed_findings) == ((1,),)


def test_formats_multiline_fstring_trailing_comment_on_python_311() -> None:
    source = 'x = f"""{(\n    1#inner\n)}"""\n#outer\n'
    expected = 'x = f"""{(\n    1  # inner\n)}"""\n#outer\n'
    settings = CheckSettings(select=("PCF002",))

    checked = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    fixed = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    repeated = formatter.format_source(expected, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert tuple(finding.line_numbers for finding in checked.unfixed_findings) == ((2,),)
    assert fixed.new_source == expected
    assert fixed.fixed_findings[PCF002TrailingCommentSpacing.meta] == 1
    assert not fixed.errors
    assert not repeated.modified
    assert not repeated.errors


def test_spacing_fixes_preserve_unicode_barriers_in_regular_and_directive_payloads() -> None:
    source = "regular = 1#Keep\u202epayload  \ndirective = 2#noqa\u2060  \n"
    settings = CheckSettings(select=("PCF002",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == "regular = 1  #Keep\u202epayload  \ndirective = 2  #noqa\u2060  \n"
    assert result.fixed_findings[PCF002TrailingCommentSpacing.meta] == 2
