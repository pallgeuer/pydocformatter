# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import rest_fields


def entry(
    kind: PDF_definition.DocstringEntryKind, *, field_name: str, field_argument: str | None = None, names: tuple[str, ...] = (), description: str = "", end_line: int = 1
) -> PDF_definition.DocstringEntry:
    return PDF_definition.DocstringEntry(
        kind=kind, names=names, type_text=None, description=description, description_lines=(), start_line=0, end_line=end_line, field_name=field_name, field_argument=field_argument
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


def test_field_name_span_stops_at_rest_field_delimiters() -> None:
    assert rest_fields.field_name_span(line(":param value: Description.")) == (1, 6)
    assert rest_fields.field_name_span(line("  :returns: Result.")) == (3, 10)
    assert rest_fields.field_name_span(line("\t:custom-field  value: Description.")) == (2, 14)
    assert rest_fields.field_name_span(line("::")) == (1, 1)
