# Third-party imports
import pytest

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import rest_fields


def entry(
    kind: PDF_definition.DocstringEntryKind, *, field_name: str, field_argument: str | None = None, names: tuple[str, ...] = (), description: str = "", end_line: int = 1
) -> PDF_definition.DocstringEntry:
    return PDF_definition.DocstringEntry(
        kind=kind,
        names=names,
        name_slots=(None,) * len(names),
        type_info=None,
        description=description,
        description_lines=(),
        start_line=0,
        end_line=end_line,
        field_name=field_name,
        field_argument=field_argument,
    )


def line(text: str) -> PDF_definition.DocstringValueLine:
    return PDF_definition.DocstringValueLine(
        index=0, start_offset=0, end_offset=len(text), raw_text=text, text=text, raw_indent="", text_indent="", text_raw_start_column=0, text_virtual_prefix_length=0, source_line_number=1
    )


def test_label_renders_rest_field_with_optional_argument() -> None:
    assert rest_fields.label(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", field_argument="value")) == ":param value:"
    assert rest_fields.label(entry(PDF_definition.DocstringEntryKind.RETURN, field_name="returns")) == ":returns:"


def test_has_content_accepts_inline_or_continuation_content() -> None:
    assert rest_fields.has_content(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", description="Value."))
    assert rest_fields.has_content(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", end_line=2))
    assert not rest_fields.has_content(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param"))


def test_order_rank_groups_parameters_values_and_exceptions() -> None:
    assert rest_fields.order_rank(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param")) == 0
    assert rest_fields.order_rank(entry(PDF_definition.DocstringEntryKind.RETURN, field_name="returns")) == 1
    assert rest_fields.order_rank(entry(PDF_definition.DocstringEntryKind.YIELD, field_name="yields")) == 1
    assert rest_fields.order_rank(entry(PDF_definition.DocstringEntryKind.EXCEPTION, field_name="raises")) == 2
    assert rest_fields.order_rank(entry(PDF_definition.DocstringEntryKind.FIELD, field_name="meta")) is None


def test_repetition_key_distinguishes_rest_field_kinds() -> None:
    assert rest_fields.repetition_key(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", names=("value",))) is None
    assert rest_fields.repetition_key(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="value")) is None
    assert rest_fields.repetition_key(entry(PDF_definition.DocstringEntryKind.RETURN, field_name="returns")) == ("return", "", "")
    assert rest_fields.repetition_key(entry(PDF_definition.DocstringEntryKind.FIELD, field_name="meta", field_argument="private")) == ("field", "meta", "private")
    assert rest_fields.repetition_key(entry(PDF_definition.DocstringEntryKind.EXCEPTION, field_name="raises")) is None
    assert rest_fields.repetition_key(entry(PDF_definition.DocstringEntryKind.ATTRIBUTE, field_name="ivar", names=("value",))) is None


def test_named_repetition_keys_describe_pdf412_rest_entries() -> None:
    assert rest_fields.named_repetition_keys(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", names=("*value",))) == (
        rest_fields.NamedRepetitionKey(("rest-parameter", "value"), "value", "reST parameter"),
    )
    assert rest_fields.named_repetition_keys(entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="*value")) == (
        rest_fields.NamedRepetitionKey(("rest-parameter-type", "value"), "value", "reST parameter type"),
    )
    assert rest_fields.named_repetition_keys(entry(PDF_definition.DocstringEntryKind.ATTRIBUTE, field_name="ivar", names=("value",))) == (
        rest_fields.NamedRepetitionKey(("rest-attribute", "value"), "value", "reST attribute"),
    )
    assert rest_fields.named_repetition_keys(entry(PDF_definition.DocstringEntryKind.ATTRIBUTE, field_name="vartype", field_argument="value")) == (
        rest_fields.NamedRepetitionKey(("rest-attribute-type", "value"), "value", "reST attribute type"),
    )
    assert rest_fields.named_repetition_keys(entry(PDF_definition.DocstringEntryKind.EXCEPTION, field_name="raises", names=("ValueError",))) == (
        rest_fields.NamedRepetitionKey(("rest-exception", "ValueError"), "ValueError", "reST exception"),
    )
    assert rest_fields.named_repetition_keys(entry(PDF_definition.DocstringEntryKind.RETURN, field_name="returns")) == ()


def test_parameter_value_aliases_pair_with_star_normalized_type_fields() -> None:
    for field_name in ("param", "parameter", "arg", "argument", "key", "keyword", "kwarg"):
        value_entry = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name=field_name, names=("*items",))
        type_entry = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="items", names=("items",))
        pairing = rest_fields.pair_value_and_type_fields((type_entry, value_entry), PDF_definition.DocstringEntryKind.PARAMETER)

        assert pairing.pairs[0].value is pairing.value_parts[0]
        assert pairing.pairs[0].type.entry is type_entry
        assert pairing.orphan_types == ()


def test_return_yield_and_attribute_pairing_keys_follow_field_semantics() -> None:
    return_pairing = rest_fields.pair_value_and_type_fields(
        (entry(PDF_definition.DocstringEntryKind.RETURN, field_name="rtype"), entry(PDF_definition.DocstringEntryKind.RETURN, field_name="returns")), PDF_definition.DocstringEntryKind.RETURN
    )
    yield_pairing = rest_fields.pair_value_and_type_fields(
        (entry(PDF_definition.DocstringEntryKind.YIELD, field_name="yield"), entry(PDF_definition.DocstringEntryKind.YIELD, field_name="ytype", field_argument="item", names=("item",))),
        PDF_definition.DocstringEntryKind.YIELD,
    )
    attribute_pairing = rest_fields.pair_value_and_type_fields(
        (
            entry(PDF_definition.DocstringEntryKind.ATTRIBUTE, field_name="vartype", field_argument="Value", names=("Value",)),
            entry(PDF_definition.DocstringEntryKind.ATTRIBUTE, field_name="ivar", names=("value",)),
        ),
        PDF_definition.DocstringEntryKind.ATTRIBUTE,
    )

    assert len(return_pairing.pairs) == 1
    assert len(yield_pairing.value_parts) == 1
    assert not yield_pairing.pairs
    assert len(yield_pairing.orphan_types) == 1
    assert len(attribute_pairing.value_parts) == 1
    assert not attribute_pairing.pairs
    assert len(attribute_pairing.orphan_types) == 1


def test_pairing_is_fifo_one_to_one_and_retains_source_order() -> None:
    first_type = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="value", names=("value",), description="int")
    value = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", field_argument="value", names=("value",), description="Value.")
    second_type = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="value", names=("value",), description="str")
    pairing = rest_fields.pair_value_and_type_fields((first_type, value, second_type), PDF_definition.DocstringEntryKind.PARAMETER)

    assert pairing.pairs[0].type.entry is first_type
    assert pairing.orphan_types[0].entry is second_type
    assert (pairing.pairs[0].type.order, pairing.orphan_types[0].order) == (0, 2)
    assert pairing.value_parts[0].order == 1


def test_pairing_uses_fifo_occurrences_when_repeated_types_precede_repeated_values() -> None:
    first_type = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="value", names=("value",), description="int")
    second_type = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="value", names=("value",), description="str")
    first_value = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", field_argument="value", names=("value",), description="First value.")
    second_value = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="argument", field_argument="value", names=("value",), description="Second value.")
    pairing = rest_fields.pair_value_and_type_fields((first_type, second_type, first_value, second_value), PDF_definition.DocstringEntryKind.PARAMETER)

    assert tuple((pair.value.entry, pair.type.entry) for pair in pairing.pairs) == ((first_value, first_type), (second_value, second_type))
    assert pairing.orphan_types == ()


def test_pairing_keeps_names_independent_and_retains_surplus_values() -> None:
    type_b = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="b", names=("b",))
    first_value_a = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", field_argument="a", names=("a",))
    value_b = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="keyword", field_argument="b", names=("b",))
    type_a = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="a", names=("a",))
    second_value_a = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="arg", field_argument="a", names=("a",))
    pairing = rest_fields.pair_value_and_type_fields((type_b, first_value_a, value_b, type_a, second_value_a), PDF_definition.DocstringEntryKind.PARAMETER)

    assert tuple((pair.value.entry, pair.type.entry) for pair in pairing.pairs) == ((first_value_a, type_a), (value_b, type_b))
    assert tuple(part.entry for part in pairing.value_parts) == (first_value_a, value_b, second_value_a)
    assert pairing.orphan_types == ()


def test_pairing_ignores_other_kinds_and_nonstandard_fields() -> None:
    custom_parameter = entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="custom", field_argument="value", names=("value",))
    attribute_type = entry(PDF_definition.DocstringEntryKind.ATTRIBUTE, field_name="vartype", field_argument="value", names=("value",))
    pairing = rest_fields.pair_value_and_type_fields((custom_parameter, attribute_type), PDF_definition.DocstringEntryKind.PARAMETER)

    assert pairing.value_parts == ()
    assert pairing.pairs == ()
    assert pairing.orphan_types == ()


def test_pairing_rejects_entry_kinds_without_value_type_semantics() -> None:
    with pytest.raises(ValueError, match="Unsupported reStructuredText value/type pairing kind: exception"):
        rest_fields.pair_value_and_type_fields((), PDF_definition.DocstringEntryKind.EXCEPTION)


def test_pairing_handles_large_field_collections_iteratively() -> None:
    entries = tuple(
        field
        for index in range(2000)
        for field in (
            entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", field_argument=f"value{index}", names=(f"value{index}",)),
            entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument=f"value{index}", names=(f"value{index}",)),
        )
    )
    pairing = rest_fields.pair_value_and_type_fields(entries, PDF_definition.DocstringEntryKind.PARAMETER)

    assert len(pairing.pairs) == 2000
    assert pairing.orphan_types == ()


def test_bulk_pairing_matches_per_kind_results_for_interleaved_families() -> None:
    entries = (
        entry(PDF_definition.DocstringEntryKind.ATTRIBUTE, field_name="vartype", field_argument="timeout", names=("timeout",)),
        entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="type", field_argument="value", names=("value",)),
        entry(PDF_definition.DocstringEntryKind.RETURN, field_name="returns"),
        entry(PDF_definition.DocstringEntryKind.PARAMETER, field_name="param", field_argument="value", names=("value",)),
        entry(PDF_definition.DocstringEntryKind.RETURN, field_name="rtype"),
    )
    bulk_pairings = rest_fields.pair_all_value_and_type_fields(entries)

    assert tuple(bulk_pairings) == (
        PDF_definition.DocstringEntryKind.PARAMETER,
        PDF_definition.DocstringEntryKind.RETURN,
        PDF_definition.DocstringEntryKind.YIELD,
        PDF_definition.DocstringEntryKind.ATTRIBUTE,
    )
    for kind, bulk_pairing in bulk_pairings.items():
        assert bulk_pairing == rest_fields.pair_value_and_type_fields(entries, kind)


def test_field_name_span_stops_at_rest_field_delimiters() -> None:
    assert rest_fields.field_name_span(line(":param value: Description.")) == (1, 6)
    assert rest_fields.field_name_span(line("  :returns: Result.")) == (3, 10)
    assert rest_fields.field_name_span(line("\t:custom-field  value: Description.")) == (2, 14)
    assert rest_fields.field_name_span(line("::")) == (1, 1)
