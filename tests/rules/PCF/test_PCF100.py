# Third-party imports
import pytest

# First-party imports
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PCF.PCF100_comment_directive_normalization import PCF100CommentDirectiveNormalization


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("value = compute()#noqa\n", "value = compute()  # noqa\n"),
        ("value = compute()#noqa   \n", "value = compute()  # noqa\n"),
        ("value = compute() #   nosec reason\n", "value = compute()  # nosec reason\n"),
        ("value = compute()\t#TYPE : ignore[assignment]\n", "value = compute()  # type: ignore[assignment]\n"),
        ("value = compute() # TY : ignore[invalid-argument-type]\n", "value = compute()  # ty: ignore[invalid-argument-type]\n"),
        ("value = compute() # ruff: noqa: F401\n", "value = compute()  # ruff: noqa: F401\n"),
        ("value = compute() # PYDOCFMT : ignore [ pdf101, pcf000, ]\n", "value = compute()  # pydocfmt: ignore[PDF101, PCF000]\n"),
        ("value = compute()#ruff: ignore[line-too-long]\n", "value = compute()  # ruff: ignore[line-too-long]\n"),
        ("value = compute()#noinspection PyTypeChecker\n", "value = compute()  # noinspection PyTypeChecker\n"),
        ("value = compute()#language=SQL prefix=SELECT suffix=FROM table\n", "value = compute()  # language=SQL prefix=SELECT suffix=FROM table\n"),
        ("value = compute()#@formatter:off\n", "value = compute()  # @formatter:off\n"),
        ("value = compute() # pragma: no cover\n", "value = compute()  # pragma: no cover\n"),
    ],
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
    [
        ("#ruff: noqa\n", "# ruff: noqa\n"),
        ("#PYDOCFMT : noqa : pdf101,pcf000\n", "# pydocfmt: noqa: PDF101, PCF000\n"),
        ("#PYDOCFMT : file-ignore [ pdf101, pcf000, ]\n", "# pydocfmt: file-ignore[PDF101, PCF000]\n"),
        ("#   pylint : disable-next = missing-docstring,unused-argument\n", "# pylint: disable-next=missing-docstring, unused-argument\n"),
        ("    #fmt : off\n", "    # fmt: off\n"),
        ("#TYPE : ignore[assignment,arg-type]\n", "# type: ignore[assignment, arg-type]\n"),
        ("#TY : ignore[invalid-argument-type,unresolved-import]\n", "# ty: ignore[invalid-argument-type, unresolved-import]\n"),
        ("#ruff:ignore[F401,E501]\n", "# ruff: ignore[F401, E501]\n"),
        ("# ruff : disable [ E741, F841, ]\n", "# ruff: disable[E741, F841]\n"),
        ("# ruff: file-ignore[unused-import,unused-function-argument]\n", "# ruff: file-ignore[unused-import, unused-function-argument]\n"),
        ("# ruff: isort: skip_file\n", "# ruff: isort: skip_file\n"),
        ("# ruff : isort : ON\n", "# ruff: isort: on\n"),
        ("#NoInspection PyTypeChecker\n", "# noinspection PyTypeChecker\n"),
        ("#NoInspection\n", "# noinspection\n"),
        ("#noinspection PyTypeChecker,PyUnresolvedReferences\n", "# noinspection PyTypeChecker, PyUnresolvedReferences\n"),
        ("# LANGUAGE = SQL prefix=SELECT suffix=FROM table\n", "# language=SQL prefix=SELECT suffix=FROM table\n"),
        ("# @formatter : OFF\n", "# @formatter:off\n"),
        ("# @formatter : ON\n", "# @formatter:on\n"),
    ],
)
def test_directive_normalization_normalizes_standalone_directives(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
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
    ],
)
def test_directive_normalization_does_not_add_trailing_space_for_empty_payloads(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == expected
    assert result.new_source is not None
    assert all(not line.endswith((" ", "\t", "\f")) for line in result.new_source.splitlines())


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("value = compute()#TYPE : ignore[assignment,arg-type]\n", "value = compute()  # type: ignore[assignment, arg-type]\n"),
        ("value = compute()#TYPE : ignore[arg-type,ty:invalid-argument-type]\n", "value = compute()  # type: ignore[arg-type, ty:invalid-argument-type]\n"),
        ("value = compute()#TY : ignore[invalid-argument-type,unresolved-import]\n", "value = compute()  # ty: ignore[invalid-argument-type, unresolved-import]\n"),
        ("value = compute()#noqa: f401,e501\n", "value = compute()  # noqa: F401, E501\n"),
        ("value = compute()#ruff : noqa : ruf100, f401\n", "value = compute()  # ruff: noqa: RUF100, F401\n"),
        ("value = compute()#PYDOCFMT : noqa : pdf101, pcf000\n", "value = compute()  # pydocfmt: noqa: PDF101, PCF000\n"),
        ("value = compute()#ruff:ignore[F401,E501]\n", "value = compute()  # ruff: ignore[F401, E501]\n"),
        ("value = compute()#ruff : enable [ E741, F841, ]  # reason\n", "value = compute()  # ruff: enable[E741, F841]  # reason\n"),
        ("value = compute()#ruff : isort : SKIP_FILE\n", "value = compute()  # ruff: isort: skip_file\n"),
        ("value = compute()#ruff : isort : SPLIT\n", "value = compute()  # ruff: isort: split\n"),
        ("value = compute()#NoInspection PyTypeChecker,PyUnresolvedReferences\n", "value = compute()  # noinspection PyTypeChecker, PyUnresolvedReferences\n"),
        ("value = compute()#LANGUAGE = RegExp prefix=^ suffix=$\n", "value = compute()  # language=RegExp prefix=^ suffix=$\n"),
        ("value = compute()#@formatter : OFF\n", "value = compute()  # @formatter:off\n"),
        ("value = compute()#pylint:disable=missing-docstring,unused-argument\n", "value = compute()  # pylint: disable=missing-docstring, unused-argument\n"),
    ],
)
def test_directive_normalization_normalizes_safe_machine_readable_payloads(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("# type: ignore[assignment, ty:assignment, assignment]\n", "# type: ignore[assignment, ty:assignment]\n"),
        ("# ty: ignore[invalid-argument-type, invalid-argument-type]\n", "# ty: ignore[invalid-argument-type]\n"),
        ("# noqa: f401, e501, F401, E501  # generated\n", "# noqa: F401, E501  # generated\n"),
        ("# ruff: noqa: f401, F401, e501, E501\n", "# ruff: noqa: F401, E501\n"),
        ("# flake8: noqa: f401, F401\n", "# flake8: noqa: F401\n"),
        ("# pydocfmt: noqa: pdf101, PDF101, pcf000\n", "# pydocfmt: noqa: PDF101, PCF000\n"),
        ("# pydocfmt: ignore[pdf101, PDF101, pcf000,]\n", "# pydocfmt: ignore[PDF101, PCF000]\n"),
        ("# pydocfmt: file-ignore[pdf101, PDF101,]\n", "# pydocfmt: file-ignore[PDF101]\n"),
        ("# ruff: ignore[F401, F401, f401]\n", "# ruff: ignore[F401, f401]\n"),
        ("# ruff: file-ignore[unused-import, unused-import, F401]\n", "# ruff: file-ignore[unused-import, F401]\n"),
        ("# pylint: disable=missing-docstring, missing-docstring, Missing-Docstring\n", "# pylint: disable=missing-docstring, Missing-Docstring\n"),
        ("# noinspection PyTypeChecker, PyTypeChecker, pytypechecker\n", "# noinspection PyTypeChecker, pytypechecker\n"),
    ],
)
def test_directive_normalization_stably_deduplicates_safe_list_families(source: str, expected: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == expected
    assert not pcf_helpers.format_pcf(expected).modified


def test_directive_normalization_preserves_ruff_range_item_order_and_multiplicity() -> None:
    source = "# RUFF : disable [ E501, E501, F401, ]\nvalue = 1\n# RUFF : enable [ E501, F401, E501, ]\n"
    result = pcf_helpers.format_pcf(source)

    assert result.new_source == "# ruff: disable[E501, E501, F401]\nvalue = 1\n# ruff: enable[E501, F401, E501]\n"


def test_directive_normalization_deduplicates_a_trailing_payload_without_owning_delimiter_spacing() -> None:
    source = "value = compute()#NOQA: f401, F401, e501\n"
    settings = CheckSettings(select=("PCF100",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == "value = compute()# noqa: F401, E501\n"
    assert result.fixed_findings[PCF100CommentDirectiveNormalization.meta] == 1


@pytest.mark.parametrize(
    "source", ["# type: ignore[assignment, prose words, assignment]\n", "# ruff: ignore[F401, unsafe code, F401]\n", "# pylint: disable=missing-docstring, unsafe message, missing-docstring\n"]
)
def test_directive_normalization_does_not_partly_deduplicate_malformed_lists(source: str) -> None:
    result = pcf_helpers.format_pcf(source)
    assert result.new_source == source


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
    settings = CheckSettings(select=("PCF100",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (3,))


def test_directive_normalization_respects_configured_unfixable_selection_in_fix_mode() -> None:
    source = "value = compute()#noqa\n"
    settings = CheckSettings(select=("PCF100",), unfixable=("PCF100",))

    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == source
    assert tuple((finding.rule, finding.fixable) for finding in result.unfixed_findings) == ((PCF100CommentDirectiveNormalization.meta, False),)


def test_directive_normalization_applies_in_syntax_sensitive_positions_without_extraction() -> None:
    source = "@decorator#noqa\ndef function():\n    call(\n        value,# type: ignore[arg-type]\n    )\n    if enabled:#nosec\n        pass\n"
    result = pcf_helpers.format_pcf(source, line_length=8)
    assert result.new_source == "@decorator  # noqa\ndef function():\n    call(\n        value,  # type: ignore[arg-type]\n    )\n    if enabled:  # nosec\n        pass\n"


def test_directive_normalization_and_regular_trailing_extraction_apply_together_without_overlap() -> None:
    source = "directive = compute()#noqa\nordinary = compute()#ordinary trailing words that need moving\n"
    result = pcf_helpers.format_pcf(source, line_length=28)
    assert result.new_source == "directive = compute()  # noqa\n# ordinary trailing words\n# that need moving\nordinary = compute()\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF001": 2, "PCF100": 1, "PCF002": 1}


def test_directive_normalization_treats_additional_hashes_as_directive_payload() -> None:
    source = "value = compute()#TY : ignore[invalid-argument-type]  # fmt: skip\nother = compute()#noqa  # keep this tool-specific payload\n"
    result = pcf_helpers.format_pcf(source, line_length=20)
    assert result.new_source == "value = compute()  # ty: ignore[invalid-argument-type]  # fmt: skip\nother = compute()  # noqa  # keep this tool-specific payload\n"


def test_directive_normalization_preserves_ambiguous_payloads_after_safe_prefix_cleanup() -> None:
    source = "value = compute()#noqa: not a code list because prose\n#pylint:disable=missing-docstring because prose\n#ruff:ignore[not safe because prose]\n#noinspection not a clear list because prose\n#@formatter:off because prose\n"
    result = pcf_helpers.format_pcf(source)
    assert (
        result.new_source
        == "value = compute()  # noqa: not a code list because prose\n# pylint: disable=missing-docstring because prose\n# ruff: ignore[not safe because prose]\n# noinspection not a clear list because prose\n# @formatter:off because prose\n"
    )


def test_directive_normalization_preserves_trailing_code_to_hash_spacing_when_selected_alone() -> None:
    source = "value = compute()#noqa\nother = compute()#ordinary prose\n"
    settings = CheckSettings(select=("PCF100",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()# noqa\nother = compute()#ordinary prose\n"


def test_directive_normalization_does_not_modify_unknown_directives() -> None:
    source = "value = compute()#not-a-known-directive\n#noqa\n"
    settings = CheckSettings(select=("PCF100",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)
    assert result.new_source == "value = compute()#not-a-known-directive\n# noqa\n"


def test_trailing_directive_spacing_and_normalization_report_separate_defects_in_check_mode() -> None:
    source = "gap = 1 # type: ignore\ncontent = 2  #TYPE : ignore\nboth = 3 #TYPE : ignore\n"
    settings = CheckSettings(select=("PCF001", "PCF100"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)
    assert result.new_source == source
    assert tuple((finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings) == (("PCF001", (1,)), ("PCF001", (3,)), ("PCF100", (2,)), ("PCF100", (3,)))


def test_directive_normalization_skips_only_payloads_containing_unicode_barriers() -> None:
    source = "first = 1#NOQA\nsecond = 2#NOQA\u2060\n#RUFF : noqa\u2060\n#TYPE : ignore\nthird = 3#TYPE : ignore\n"
    settings = CheckSettings(select=("PCF100",))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == "first = 1# noqa\nsecond = 2#NOQA\u2060\n#RUFF : noqa\u2060\n# type: ignore\nthird = 3# type: ignore\n"
    assert result.fixed_findings[PCF100CommentDirectiveNormalization.meta] == 3


def test_directive_normalization_canonicalizes_names_and_deduplicates_semantic_aliases() -> None:
    source = "# PYDOCFMT : ignore [ Docstring-Reflow, pdf101, PCF, ]  # reason\n"

    result = pcf_helpers.format_pcf(source)

    assert result.new_source == "# pydocfmt: ignore[docstring-reflow, PCF]  # reason\n"


def test_directive_normalization_retains_first_semantic_alias_in_both_orders() -> None:
    code_first = pcf_helpers.format_pcf("# pydocfmt: ignore[PDF101, docstring-reflow]\n")
    name_first = pcf_helpers.format_pcf("# pydocfmt: ignore[docstring-reflow, PDF101]\n")

    assert code_first.new_source == "# pydocfmt: ignore[PDF101]\n"
    assert name_first.new_source == "# pydocfmt: ignore[docstring-reflow]\n"


def test_directive_normalization_does_not_rewrite_tokens_in_an_unsafe_pydocfmt_list() -> None:
    source = "# PYDOCFMT : IGNORE [ pdf101,, Docstring-Reflow, ]  # reason\n"

    result = pcf_helpers.format_pcf(source)

    assert result.new_source == "# pydocfmt: ignore[ pdf101,, Docstring-Reflow, ]  # reason\n"


def test_directive_normalization_preserves_invalid_pydocfmt_token_spelling() -> None:
    source = "# PYDOCFMT : IGNORE [ foo_bar, foo_bar, FOO_BAR, future.rule ]\n"

    result = pcf_helpers.format_pcf(source)

    assert result.new_source == "# pydocfmt: ignore[foo_bar, FOO_BAR, future.rule]\n"


def test_directive_normalization_collapses_whitespace_only_pydocfmt_list() -> None:
    result = pcf_helpers.format_pcf("# pydocfmt: ignore[ ]\n")

    assert result.new_source == "# pydocfmt: ignore[]\n"


@pytest.mark.parametrize("source", ["# pydocfmt: ignore[PDF101]   \n", "value = 1# pydocfmt: ignore[PDF101]\t\f\n"])
def test_directive_normalization_owns_terminal_whitespace_for_bracket_directives(source: str) -> None:
    settings = CheckSettings(select=("PCF100",))

    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == source.rstrip(" \t\f\n") + "\n"
