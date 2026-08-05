# Future imports
from __future__ import annotations

# Standard library imports
import typing
import itertools
import dataclasses

# Third-party imports
import libcst as cst
import pytest
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.definitions.PDF.PDF414_malformed_convention_entry as PDF414_definition
import pydocformatter.rules.definitions.PDF.PDF415_convention_entry_indentation as PDF415_definition
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definition_helpers import attribute_documentation, source_text, string_literals, unicode_safety, value_documentation
from pydocformatter.rules.definitions.PDF.PDF import (
    PDF,
    AttributeInfo,
    AttributeOrigin,
    ConventionEntryIssueKind,
    DefinitionInfo,
    DefinitionKind,
    DocstringBlockKind,
    DocstringEntryKind,
    DocstringKind,
    escaped_closing_quote_body_source,
    first_summary_block,
    simple_docstring_body_source_candidates,
)
from pydocformatter.source_path import SourcePathContext


if typing.TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture

    # First-party imports
    from pydocformatter.rules.definitions.PDF.PDF import DocstringBlock, DocstringStructure, DocstringTextFragment


def reflow_texts(lines: tuple[DocstringTextFragment, ...]) -> tuple[str, ...]:
    return tuple(line.text for line in lines)


def entry_type_text(entry: PDF_definition.DocstringEntry) -> str | None:
    """Return semantic type text from one parsed entry."""
    return None if entry.type_info is None else entry.type_info.text


def category_context(source: str, *, settings: CheckSettings | None = None) -> RuleCategoryContext:
    module = cst.parse_module(source)
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    return RuleCategoryContext(
        path="example.py",
        source_path=SourcePathContext.for_path("example.py"),
        settings=CheckSettings() if settings is None else settings,
        module=module,
        metadata_wrapper=metadata_wrapper,
        positions=metadata_wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
        line_bounds=None,
    )


def rule_context(context: RuleCategoryContext, data: object | None) -> RuleContext:
    return RuleContext(
        path=context.path,
        source_path=context.source_path,
        settings=context.settings,
        module=context.module,
        metadata_wrapper=context.metadata_wrapper,
        positions=context.positions,
        line_ending=context.line_ending,
        source=context.source,
        source_lines=context.source_lines,
        line_bounds=context.line_bounds,
        category_data=data,
    )


def test_prepare_collects_definitions_docstrings_and_owner_metadata() -> None:
    source = '"""module doc"""\n@decorator\nclass Outer:\n    """class doc"""\n    async def method(self, value: int) -> str:\n        ("method doc")\n        return str(value)\n\n    def no_doc(self):\n        pass\n\ndef concatenated():\n    "first " "second"\n\ndef empty(): "" ; return None\ndef formatted():\n    f"not a docstring"\ndef binary():\n    b"not a docstring"\n'
    data = PDF.prepare(category_context(source))
    assert tuple((definition.kind, definition.qualified_name) for definition in data.definitions) == (
        (DefinitionKind.MODULE, "<module>"),
        (DefinitionKind.CLASS, "Outer"),
        (DefinitionKind.FUNCTION, "Outer.method"),
        (DefinitionKind.FUNCTION, "Outer.no_doc"),
        (DefinitionKind.FUNCTION, "concatenated"),
        (DefinitionKind.FUNCTION, "empty"),
        (DefinitionKind.FUNCTION, "formatted"),
        (DefinitionKind.FUNCTION, "binary"),
    )
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("<module>", "Outer", "Outer.method", "concatenated", "empty")
    assert tuple(docstring.kind for docstring in data.docstrings) == (DocstringKind.SIMPLE, DocstringKind.SIMPLE, DocstringKind.SIMPLE, DocstringKind.CONCATENATED, DocstringKind.SIMPLE)
    assert tuple(docstring.value for docstring in data.docstrings) == ("module doc", "class doc", "method doc", "first second", "")
    assert data.docstrings[2].source == '"method doc"'
    assert data.definitions[2].asynchronous
    assert len(data.definitions[1].decorators) == 1
    assert data.definitions[2].parameters is not None
    assert data.definitions[2].returns is not None
    assert data.definitions[2].parent is data.definitions[1]
    assert data._docstrings_by_owner_id is None
    assert data.docstring_for(data.definitions[1]) is data.docstrings[1]
    assert data._docstrings_by_owner_id is not None
    assert data.docstring_for(data.definitions[3]) is None
    assert data.docstring_for(dataclasses.replace(data.definitions[1])) is None
    duplicate_owner_data = dataclasses.replace(data, docstrings=(data.docstrings[1], dataclasses.replace(data.docstrings[2], owner=data.definitions[1])))
    assert duplicate_owner_data.docstring_for(data.definitions[1]) is data.docstrings[1]


def test_prepare_collects_attribute_docstrings_and_owner_metadata() -> None:
    source = '"""module doc"""\n"""module additional ignored"""\nmodule_plain = 1\n"""module attr doc"""\nmodule_annotated: int\n"""module annotated doc"""\nmodule_a = module_b = 2; "module multi doc"\n\nclass Client:\n    """class doc"""\n    """class additional ignored"""\n    class_plain = 1\n    """class attr doc"""\n    class_annotated: int = 2; "class annotated doc"\n    class_a = class_b = 3\n    "class multi doc"\n\n    def __init__(self, flag):\n        self.instance_plain = 1\n        "instance attr doc"\n        if flag:\n            self.conditional: int = 2; "conditional attr doc"\n        def nested():\n            self.not_instance = 1\n            "not collected"\n\n    def method(self):\n        local = 1; "not collected"\n'
    data = PDF.prepare(category_context(source))
    attribute_docstrings = tuple(docstring for docstring in data.docstrings if isinstance(docstring.owner, AttributeInfo))
    attribute_details = []
    for docstring in attribute_docstrings:
        owner = docstring.owner
        if isinstance(owner, AttributeInfo):
            attribute_details.append((owner.qualified_name, owner.targets, docstring.value))

    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == (
        "<module>",
        "module_plain",
        "module_annotated",
        "module_a, module_b",
        "Client",
        "Client.class_plain",
        "Client.class_annotated",
        "Client.class_a, Client.class_b",
        "Client.instance_plain",
        "Client.conditional",
    )
    assert tuple(attribute_details) == (
        ("module_plain", ("module_plain",), "module attr doc"),
        ("module_annotated", ("module_annotated",), "module annotated doc"),
        ("module_a, module_b", ("module_a", "module_b"), "module multi doc"),
        ("Client.class_plain", ("class_plain",), "class attr doc"),
        ("Client.class_annotated", ("class_annotated",), "class annotated doc"),
        ("Client.class_a, Client.class_b", ("class_a", "class_b"), "class multi doc"),
        ("Client.instance_plain", ("instance_plain",), "instance attr doc"),
        ("Client.conditional", ("conditional",), "conditional attr doc"),
    )
    assert tuple((attribute.qualified_name, attribute.targets, attribute.line_numbers, attribute.target_line_numbers, attribute.instance) for attribute in data.attributes) == (
        ("module_plain", ("module_plain",), (3,), ((3,),), False),
        ("module_annotated", ("module_annotated",), (5,), ((5,),), False),
        ("module_a, module_b", ("module_a", "module_b"), (7,), ((7,), (7,)), False),
        ("Client.class_plain", ("class_plain",), (12,), ((12,),), False),
        ("Client.class_annotated", ("class_annotated",), (14,), ((14,),), False),
        ("Client.class_a, Client.class_b", ("class_a", "class_b"), (15,), ((15,), (15,)), False),
        ("Client.instance_plain", ("instance_plain",), (19,), ((19,),), True),
        ("Client.conditional", ("conditional",), (22,), ((22,),), True),
    )
    assert all(docstring.owner in data.attributes for docstring in attribute_docstrings)
    assert all(docstring.owner.kind is DefinitionKind.ATTRIBUTE for docstring in attribute_docstrings)
    assert data.docstring_for(data.definitions[1]) is data.docstrings[4]
    assert data._attributes_by_owner_id is None
    assert tuple(attribute.qualified_name for attribute in data.attributes_for(data.definitions[0])) == ("module_plain", "module_annotated", "module_a, module_b")
    assert data._attributes_by_owner_id is not None
    assert data._attached_attribute_docstrings_by_owner_id is None
    attached_docstrings = data.attached_attribute_docstrings_by_name(data.definitions[0])
    assert set(attached_docstrings) == {"module_plain", "module_annotated", "module_a", "module_b"}
    assert tuple(name for name, _ in data.attached_attribute_docstring_name_pairs(data.definitions[0])) == ("module_plain", "module_annotated", "module_a", "module_b")
    with pytest.raises(TypeError):
        typing.cast("dict[str, tuple[object, ...]]", attached_docstrings)["other"] = ()
    assert data._attached_attribute_docstrings_by_owner_id is not None


def test_prepare_inserts_literal_slot_members_after_the_effective_assignment() -> None:
    source = 'class Point:\n    __slots__ = ("x", "y" "_axis", "__dict__", "__weakref__", "not valid", "class", "\\u03b1", "x")\n'
    data = PDF.prepare(category_context(source))
    owner = data.definitions[1]
    attributes = data.attributes_for(owner)

    assert tuple((attribute.origin, attribute.targets) for attribute in attributes) == (
        (AttributeOrigin.ASSIGNMENT, ("__slots__",)),
        (AttributeOrigin.SLOT_DECLARATION, ("x", "y_axis", "class", chr(0x3B1))),
    )
    assert attributes[1].target_line_numbers == ((2,), (2,), (2,), (2,))
    assert tuple(attribute.name for attribute in attribute_documentation.inventory_attributes(data, owner, include_instance=False)) == ("__slots__",)


def test_slot_inventory_preserves_first_position_but_enriches_real_assignment_facts() -> None:
    source = 'class Point:\n    __slots__ = (\n        "x",\n        "y",\n        "slot_only",\n    )\n    x: int\n\n    def __init__(self):\n        self.y: str = ""\n'
    data = PDF.prepare(category_context(source))
    owner = data.definitions[1]
    inventory = {attribute.name: attribute for attribute in attribute_documentation.inventory_attributes(data, owner, include_instance=True)}

    assert inventory["x"].line_numbers == (3,)
    assert inventory["x"].annotated_info is not None
    assert inventory["x"].annotated_info.line_numbers == (7,)
    assert inventory["x"].has_attachable_assignment
    assert inventory["y"].line_numbers == (4,)
    assert inventory["y"].annotated_info is not None
    assert inventory["y"].annotated_info.origin is AttributeOrigin.INITIALIZER_ASSIGNMENT
    assert not inventory["slot_only"].has_attachable_assignment
    assert inventory["slot_only"].annotated_info is None


def test_slot_inventory_deduplicates_after_applying_the_instance_policy() -> None:
    source = 'class Point:\n    __slots__ = ("x", "slot_only")\n    x: int\n\n    def __init__(self):\n        self.slot_only: str\n'
    data = PDF.prepare(category_context(source))
    owner = data.definitions[1]
    class_only = {attribute.name: attribute for attribute in attribute_documentation.inventory_attributes(data, owner, include_instance=False)}
    complete = {attribute.name: attribute for attribute in attribute_documentation.inventory_attributes(data, owner, include_instance=True)}

    assert class_only["x"].line_numbers == (3,)
    assert class_only["x"].annotated_info is not None
    assert class_only["x"].annotated_info.origin is AttributeOrigin.ASSIGNMENT
    assert "slot_only" not in class_only
    assert complete["x"].line_numbers == (2,)
    assert complete["x"].annotated_info is class_only["x"].annotated_info
    assert complete["slot_only"].line_numbers == (2,)
    assert complete["slot_only"].annotated_info is not None
    assert complete["slot_only"].annotated_info.origin is AttributeOrigin.INITIALIZER_ASSIGNMENT


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ('    __slots__ = "single" "_name"\n', ("single_name",)),
        ('    __slots__: tuple[str, ...] = ("annotated",)\n', ("annotated",)),
        ('    __slots__ = ("early",)\n    __slots__: tuple[str, ...]\n', ("early",)),
        ('    __slots__ = dynamic\n    __slots__ = ("recovered",)\n', ("recovered",)),
        ('    __slots__ = ("early",)\n    del __slots__\n    __slots__ = ("recovered",)\n', ("recovered",)),
        ('    __slots__ = ("outer",)\n    def method(self):\n        __slots__ = dynamic\n', ("outer",)),
        ('    __slots__ = ("outer",)\n    def method(self):\n        del __slots__\n', ("outer",)),
        ('    __slots__ = ("outer",)\n    callback = lambda: (__slots__ := ("nested",))\n', ("outer",)),
        ('    __slots__ = ("outer",)\n    values = [__slots__ for __slots__ in groups]\n', ("outer",)),
        ('    __slots__ = ("outer",)\n    def method(self, value):\n        match value:\n            case __slots__:\n                pass\n', ("outer",)),
        ('    __slots__ = ("outer",)\n    holder.__slots__ = ("attribute",)\n    slots_by_name["__slots__"] = ("subscript",)\n', ("outer",)),
        ('    __slots__ = ("outer",)\n    del holder.__slots__\n    del __slots__[0]\n', ("outer",)),
    ],
)
def test_final_direct_literal_slot_binding_is_inventoried(body: str, expected: tuple[str, ...]) -> None:
    data = PDF.prepare(category_context(f"class Owner:\n{body}"))
    slot_attributes = tuple(attribute for attribute in data.attributes_for(data.definitions[1]) if attribute.origin is AttributeOrigin.SLOT_DECLARATION)

    assert tuple(name for attribute in slot_attributes for name in attribute.targets) == expected


@pytest.mark.parametrize(
    "body",
    [
        '    __slots__ = ("early",)\n    __slots__ = dynamic\n',
        '    __slots__ = ("early",)\n    if enabled:\n        __slots__ = ("conditional",)\n',
        '    __slots__ = ("early",)\n    del __slots__\n',
        '    __slots__ = ("early",)\n    del __slots__\n    __slots__: tuple[str, ...]\n',
        '    __slots__ = ("early",)\n    del (__slots__, other)\n',
        '    __slots__ = ("early",)\n    __slots__ = ()\n',
        '    __slots__ += ("dynamic",)\n',
        "    __slots__, other = values\n",
        "    __slots__ = (__slots__, other) = values\n",
        '    holder.__slots__ = ("attribute",)\n',
        '    slots_by_name["__slots__"] = ("subscript",)\n',
        '    __slots__ = ("early",)\n    import slot_values as __slots__\n',
        '    __slots__ = ("early",)\n    for __slots__ in slot_values:\n        pass\n',
        '    __slots__ = ("early",)\n    with slot_context() as __slots__:\n        pass\n',
        '    __slots__ = ("early",)\n    def __slots__(self):\n        pass\n',
        '    __slots__ = ("early",)\n    class __slots__:\n        pass\n',
        '    __slots__ = ("early",)\n    try:\n        pass\n    except Exception as __slots__:\n        pass\n',
        '    __slots__ = ("early",)\n    if (__slots__ := dynamic):\n        pass\n',
        '    __slots__ = ("early",)\n    match value:\n        case __slots__:\n            pass\n',
        '    __slots__ = ("early",)\n    match value:\n        case 1 as __slots__:\n            pass\n',
        '    __slots__ = ("early",)\n    match value:\n        case [*__slots__]:\n            pass\n',
        '    __slots__ = ("early",)\n    match value:\n        case {**__slots__}:\n            pass\n',
        '    __slots__ = ("early",)\n    try:\n        pass\n    finally:\n        __slots__ = ("conditional",)\n',
        '    __slots__ = ["mutable"]\n',
        '    other = __slots__ = ["first", "second"]\n',
        '    __slots__ = ("early",)\n    __slots__ = ["mutable"]\n',
        '    __slots__ = ["x"]\n    __slots__.append("y")\n',
        '    __slots__ = ["x"]\n    alias = __slots__\n    alias.append("y")\n',
        '    __slots__ = b"bytes"\n',
        '    __slots__ = f"{name}"\n',
        '    __slots__ = ("partial", name)\n',
        '    __slots__ = ["partial", *names]\n',
        '    __slots__ = {"set"}\n',
        '    __slots__ = {"name": "value"}\n',
        "    __slots__ = [name for name in names]\n",
        '    __slots__ = ("left" if enabled else "right")\n',
    ],
)
def test_dynamic_or_invalid_final_slot_bindings_do_not_add_members(body: str) -> None:
    data = PDF.prepare(category_context(f"class Owner:\n{body}"))

    assert all(attribute.origin is not AttributeOrigin.SLOT_DECLARATION for attribute in data.attributes_for(data.definitions[1]))


def test_literal_slot_assignment_recovers_after_a_match_capture() -> None:
    source = 'class Owner:\n    __slots__ = ("early",)\n    match value:\n        case {"slot": __slots__}:\n            pass\n    __slots__ = ("recovered",)\n'
    data = PDF.prepare(category_context(source))

    assert tuple(attribute.targets for attribute in data.attributes_for(data.definitions[1]) if attribute.origin is AttributeOrigin.SLOT_DECLARATION) == (("recovered",),)


def test_slot_inventory_skips_metadata_without_slot_name_token(mocker: MockerFixture) -> None:
    context = category_context('def function():\n    """Mention `__slots__` as documentation text."""\n')
    metadata_wrapper = mocker.Mock(spec=cst_metadata.MetadataWrapper)
    context = dataclasses.replace(context, metadata_wrapper=typing.cast("cst_metadata.MetadataWrapper", metadata_wrapper))

    assert PDF_definition._literal_slot_attributes(context, ()) == {}
    metadata_wrapper.resolve.assert_not_called()


def test_nested_classes_have_independent_slot_inventories() -> None:
    source = 'class Outer:\n    __slots__ = ("outer",)\n\n    class Inner:\n        __slots__ = ("inner",)\n'
    data = PDF.prepare(category_context(source))
    owners = {definition.name: definition for definition in data.definitions if definition.kind is DefinitionKind.CLASS}

    assert tuple(attribute.targets for attribute in data.attributes_for(owners["Outer"]) if attribute.origin is AttributeOrigin.SLOT_DECLARATION) == (("outer",),)
    assert tuple(attribute.targets for attribute in data.attributes_for(owners["Inner"]) if attribute.origin is AttributeOrigin.SLOT_DECLARATION) == (("inner",),)


def test_literal_slots_in_a_compact_class_suite_are_inventoried() -> None:
    data = PDF.prepare(category_context('class Owner: __slots__ = ("compact",)\n'))

    assert tuple(attribute.targets for attribute in data.attributes_for(data.definitions[1]) if attribute.origin is AttributeOrigin.SLOT_DECLARATION) == (("compact",),)


def test_literal_slot_member_locations_use_each_string_expression_start() -> None:
    source = 'class Owner:\n    __slots__ = (\n        "first",\n        "second"\n        "_part",\n    )\n'
    data = PDF.prepare(category_context(source))
    slot_attribute = next(attribute for attribute in data.attributes_for(data.definitions[1]) if attribute.origin is AttributeOrigin.SLOT_DECLARATION)

    assert slot_attribute.targets == ("first", "second_part")
    assert slot_attribute.target_line_numbers == ((3,), (4,))
    assert slot_attribute.line_numbers == (3, 4)


def test_synthetic_slot_members_do_not_own_the_slot_declaration_docstring() -> None:
    source = 'class Owner:\n    __slots__ = ("x",)\n    """Document the slot declaration itself."""\n'
    data = PDF.prepare(category_context(source))
    owner = data.definitions[1]
    slot_attribute = next(attribute for attribute in data.attributes_for(owner) if attribute.origin is AttributeOrigin.SLOT_DECLARATION)

    assert all(docstring.owner is not slot_attribute for docstring in data.docstrings)
    assert set(data.attached_attribute_docstrings_by_name(owner)) == {"__slots__"}


def test_convention_entry_issue_metadata_covers_every_kind() -> None:
    """Keep precedence and rule ownership exhaustive as issue kinds evolve."""
    issue_kinds = set(ConventionEntryIssueKind)

    assert issue_kinds == set(PDF_definition._CONVENTION_ENTRY_ISSUE_PRECEDENCE)
    assert PDF414_definition._ISSUE_KINDS.isdisjoint(PDF415_definition._ISSUE_KINDS)
    assert issue_kinds == PDF414_definition._ISSUE_KINDS | PDF415_definition._ISSUE_KINDS


def test_exception_name_entry_kind_capability_is_exhaustive() -> None:
    """Keep exception-name syntax shared only by exceptions and warnings."""
    assert {kind for kind in DocstringEntryKind if PDF_definition.is_exception_name_entry_kind(kind)} == {DocstringEntryKind.EXCEPTION, DocstringEntryKind.WARNING}


def test_prepare_parses_docstrings_after_building_complete_owner_name_inventories() -> None:
    source = 'class Client:\n    """Client values.\n\n    Attributes:\n        value Stored value.\n\n    Methods:\n        run Execute the client.\n    """\n\n    value = 1\n\n    def run(self):\n        """Run the client."""\n'
    settings = CheckSettings(docstring_convention=DocstringConvention.GOOGLE)
    structure = PDF.prepare(category_context(source, settings=settings)).docstrings[0].structure

    assert tuple((issue.kind, issue.names) for issue in structure.convention_entry_issues) == (
        (ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR, ("value",)),
        (ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR, ("run",)),
    )


def test_prepare_uses_complete_function_parameter_inventory_case_sensitively() -> None:
    source = 'def convert(receiver, /, value, *args, option, **kwargs):\n    """Convert values.\n\n    Args:\n        receiver Receiver.\n        value Value.\n        *args Positional values.\n        option Option.\n        **kwargs Keyword values.\n        Value Different case.\n    """\n'
    settings = CheckSettings(docstring_convention=DocstringConvention.GOOGLE)
    structure = PDF.prepare(category_context(source, settings=settings)).docstrings[0].structure

    assert tuple(issue.names for issue in structure.convention_entry_issues) == (("receiver",), ("value",), ("*args",), ("option",), ("**kwargs",))


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_prepare_skips_malformed_entry_member_inventories_for_irrelevant_conventions(convention: DocstringConvention, monkeypatch: pytest.MonkeyPatch) -> None:
    source = 'class Client:\n    """Client values."""\n\n    value = 1\n\n    def run(self):\n        """Run the client."""\n'
    monkeypatch.setattr(PDF_definition, "_malformed_entry_inventories", pytest.fail)

    PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=convention)))


def test_attached_attribute_docstrings_by_name_deduplicates_repeated_assignment_targets() -> None:
    source = '_token, _token = values\n"""Token docs."""\n'
    data = PDF.prepare(category_context(source))

    attached_docstrings = data.attached_attribute_docstrings_by_name(data.definitions[0])

    assert tuple(attached_docstrings) == ("_token",)
    assert attached_docstrings["_token"] == (data.docstrings[0],)
    assert data.attached_attribute_docstring_name_pairs(data.definitions[0]) == (("_token", data.docstrings[0]),)


def test_attached_attribute_docstring_views_preserve_owner_source_and_target_order() -> None:
    source = 'class First:\n    _primary, public = values\n    """First values."""\n\n    later = 1\n    """Later value."""\n\nclass Second:\n    other, other = values\n    """Other value."""\n'
    data = PDF.prepare(category_context(source))
    owners = {definition.qualified_name: definition for definition in data.definitions}

    first_pairs = data.attached_attribute_docstring_name_pairs(owners["First"])
    second_pairs = data.attached_attribute_docstring_name_pairs(owners["Second"])

    assert tuple((name, docstring.value) for name, docstring in first_pairs) == (("_primary", "First values."), ("public", "First values."), ("later", "Later value."))
    assert tuple((name, docstring.value) for name, docstring in second_pairs) == (("other", "Other value."),)
    assert data.attached_attribute_docstring_name_pairs(owners["First"]) is first_pairs
    assert tuple(data.attached_attribute_docstrings_by_name(owners["First"])) == ("_primary", "public", "later")
    assert tuple(docstring.value for docstring in data.attached_attribute_docstrings_by_name(owners["First"])["_primary"]) == ("First values.",)
    assert not data.attached_attribute_docstring_name_pairs(owners["<module>"])
    assert not data.attached_attribute_docstrings_by_name(owners["<module>"])


def test_prepare_collects_tuple_unpacked_attribute_docstrings_and_owner_metadata() -> None:
    source = 'module_primary, module_fallback = endpoints\n"""module tuple doc"""\n\n(module_nested, (module_inner, *module_rest)) = endpoints\n"""module nested tuple doc"""\n\n[module_list, module_other] = endpoints\n"""module list ignored"""\n\nclass Client:\n    class_primary, class_fallback = endpoints\n    """class tuple doc"""\n    class_supported, other.value = endpoints\n    """class mixed tuple doc"""\n    (class_nested, (class_inner, *class_rest)) = endpoints\n    """class nested tuple doc"""\n    [class_list, class_other] = endpoints\n    """class list ignored"""\n\n    def __init__(self):\n        self.instance_primary, _ = endpoints\n        """instance mixed tuple doc"""\n        (self.instance_nested, (self.instance_inner, *self.instance_rest)) = endpoints\n        """instance nested tuple doc"""\n        self.instance_supported, helper.value = endpoints\n        """instance object mixed tuple doc"""\n        [self.instance_list, self.instance_other] = endpoints\n        """instance list ignored"""\n'
    data = PDF.prepare(category_context(source))
    attribute_docstrings = tuple(docstring for docstring in data.docstrings if isinstance(docstring.owner, AttributeInfo))
    attribute_details = []
    for docstring in attribute_docstrings:
        owner = docstring.owner
        if isinstance(owner, AttributeInfo):
            attribute_details.append((owner.qualified_name, owner.targets, docstring.value))

    assert tuple(attribute_details) == (
        ("module_primary, module_fallback", ("module_primary", "module_fallback"), "module tuple doc"),
        ("module_nested, module_inner, module_rest", ("module_nested", "module_inner", "module_rest"), "module nested tuple doc"),
        ("Client.class_primary, Client.class_fallback", ("class_primary", "class_fallback"), "class tuple doc"),
        ("Client.class_supported", ("class_supported",), "class mixed tuple doc"),
        ("Client.class_nested, Client.class_inner, Client.class_rest", ("class_nested", "class_inner", "class_rest"), "class nested tuple doc"),
        ("Client.instance_primary", ("instance_primary",), "instance mixed tuple doc"),
        ("Client.instance_nested, Client.instance_inner, Client.instance_rest", ("instance_nested", "instance_inner", "instance_rest"), "instance nested tuple doc"),
        ("Client.instance_supported", ("instance_supported",), "instance object mixed tuple doc"),
    )
    assert tuple((attribute.qualified_name, attribute.targets, attribute.line_numbers, attribute.target_line_numbers, attribute.instance) for attribute in data.attributes) == (
        ("module_primary, module_fallback", ("module_primary", "module_fallback"), (1,), ((1,), (1,)), False),
        ("module_nested, module_inner, module_rest", ("module_nested", "module_inner", "module_rest"), (4,), ((4,), (4,), (4,)), False),
        ("Client.class_primary, Client.class_fallback", ("class_primary", "class_fallback"), (11,), ((11,), (11,)), False),
        ("Client.class_supported", ("class_supported",), (13,), ((13,),), False),
        ("Client.class_nested, Client.class_inner, Client.class_rest", ("class_nested", "class_inner", "class_rest"), (15,), ((15,), (15,), (15,)), False),
        ("Client.instance_primary", ("instance_primary",), (21,), ((21,),), True),
        ("Client.instance_nested, Client.instance_inner, Client.instance_rest", ("instance_nested", "instance_inner", "instance_rest"), (23,), ((23,), (23,), (23,)), True),
        ("Client.instance_supported", ("instance_supported",), (25,), ((25,),), True),
    )


def test_prepare_collects_multiline_tuple_attribute_target_lines() -> None:
    source = '(\n    module_primary,\n    (\n        module_fallback,\n        *module_rest,\n    ),\n) = endpoints\n"""module tuple doc"""\n\nclass Client:\n    (\n        class_primary,\n        (\n            class_fallback,\n            *class_rest,\n        ),\n    ) = endpoints\n    """class tuple doc"""\n\n    def __init__(self):\n        (\n            self.instance_primary,\n            (\n                self.instance_fallback,\n                *self.instance_rest,\n            ),\n        ) = endpoints\n        """instance tuple doc"""\n'
    data = PDF.prepare(category_context(source))

    assert tuple((attribute.qualified_name, attribute.targets, attribute.line_numbers, attribute.target_line_numbers) for attribute in data.attributes) == (
        ("module_primary, module_fallback, module_rest", ("module_primary", "module_fallback", "module_rest"), (2, 4, 5), ((2,), (4,), (5,))),
        ("Client.class_primary, Client.class_fallback, Client.class_rest", ("class_primary", "class_fallback", "class_rest"), (12, 14, 15), ((12,), (14,), (15,))),
        ("Client.instance_primary, Client.instance_fallback, Client.instance_rest", ("instance_primary", "instance_fallback", "instance_rest"), (22, 24, 25), ((22,), (24,), (25,))),
    )


def test_prepare_ignores_attribute_like_strings_after_blank_or_comment_lines() -> None:
    source = 'module_valid = 1\n"""module valid doc"""\nmodule_blank = 1\n\n"""module blank ignored"""\nmodule_comment = 1\n# comment\n"""module comment ignored"""\n\nclass Client:\n    class_valid = 1\n    """class valid doc"""\n    class_blank = 1\n\n    """class blank ignored"""\n    class_comment = 1\n    # comment\n    """class comment ignored"""\n\n    def __init__(self):\n        self.valid = 1\n        """instance valid doc"""\n        self.blank = 1\n\n        """instance blank ignored"""\n        self.comment = 1\n        # comment\n        """instance comment ignored"""\n'
    data = PDF.prepare(category_context(source))
    attribute_docstrings = tuple(docstring for docstring in data.docstrings if isinstance(docstring.owner, AttributeInfo))

    assert tuple(docstring.owner.qualified_name for docstring in attribute_docstrings) == ("module_valid", "Client.class_valid", "Client.valid")
    assert tuple(docstring.value for docstring in attribute_docstrings) == ("module valid doc", "class valid doc", "instance valid doc")


def test_documented_function_facts_reuse_prepared_function_facts() -> None:
    source = 'class Base:\n    @abstractmethod\n    def abstract(self):\n        """Abstract."""\n        return 1\n\n\ndef concrete():\n    """Concrete."""\n    return 2\n\n\ndef stub():\n    """Stub."""\n    pass\n\n\ndef undocumented():\n    return 3\n'
    context = category_context(source)

    data = PDF.prepare(context)
    context_with_data = rule_context(context, data)
    function_definitions = tuple(definition for definition in data.definitions if definition.kind is DefinitionKind.FUNCTION)

    assert len(data.function_facts_by_definition_id) == len(function_definitions) == 4
    assert data._documented_function_facts is None
    facts = value_documentation.documented_function_facts(context_with_data)
    assert tuple(definition.qualified_name for definition, _, _ in facts) == ("concrete",)
    assert facts[0][2] is data.function_facts_by_definition_id[id(facts[0][0])]
    assert value_documentation.documented_function_facts(context_with_data) is facts
    assert data._documented_function_facts is facts


def test_function_facts_preserve_exception_occurrence_order_origins_and_nested_ownership() -> None:
    source = 'def outer(values):\n    """Validate outer."""\n    assert values\n    for value in values:\n        assert value\n    try:\n        raise ValueError("bad")\n    except ValueError:\n        assert False\n\n    class Nested:\n        def method(self):\n            """Validate method."""\n            assert False\n\n    def inner():\n        """Validate inner."""\n        assert True\n\n    return inner\n'
    data = PDF.prepare(category_context(source))
    facts_by_name = {definition.qualified_name: data.function_facts_by_definition_id[id(definition)] for definition in data.definitions if definition.kind is DefinitionKind.FUNCTION}

    assert tuple((occurrence.name, occurrence.line_numbers, occurrence.origin) for occurrence in facts_by_name["outer"].exception_occurrences) == (
        ("AssertionError", (3,), PDF_definition.ExceptionOccurrenceOrigin.ASSERT),
        ("AssertionError", (5,), PDF_definition.ExceptionOccurrenceOrigin.ASSERT),
        ("ValueError", (7,), PDF_definition.ExceptionOccurrenceOrigin.RAISE),
        ("AssertionError", (9,), PDF_definition.ExceptionOccurrenceOrigin.ASSERT),
    )
    assert tuple((occurrence.line_numbers, occurrence.origin) for occurrence in facts_by_name["outer.Nested.method"].exception_occurrences) == (
        ((14,), PDF_definition.ExceptionOccurrenceOrigin.ASSERT),
    )
    assert tuple((occurrence.line_numbers, occurrence.origin) for occurrence in facts_by_name["outer.inner"].exception_occurrences) == (((18,), PDF_definition.ExceptionOccurrenceOrigin.ASSERT),)


def test_value_documentation_has_no_body_walk_fallback() -> None:
    assert not hasattr(value_documentation, "_function_facts")
    assert not hasattr(value_documentation, "_FunctionBodyVisitor")
    settings = CheckSettings(select=("PDF001",))
    result = formatter.format_source('def documented():\n    """Documented."""\n    return 1\n', "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

    assert result.errors == ()


def test_prepare_preserves_multiline_crlf_source_and_physical_lines() -> None:
    source = 'def function():\r\n    r"""first\r\n    second"""\r\n    pass\r\n'
    data = PDF.prepare(category_context(source))
    docstring = data.docstrings[0]
    assert docstring.source == 'r"""first\r\n    second"""'
    assert tuple((line.line_number, line.start_column, line.end_column, line.source) for line in docstring.physical_lines) == ((2, 4, 13, 'r"""first'), (3, 0, 13, '    second"""'))
    assert docstring.value_lines == ("first", "    second")


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
@pytest.mark.parametrize(("source", "mapping_available"), [('"""supported\\t escape"""', True), (r'"""unsupported \z escape"""', False)])
def test_prepare_lazily_caches_source_maps_without_changing_value_semantics(source: str, mapping_available: bool, mocker: MockerFixture) -> None:
    parts_spy = mocker.spy(string_literals, "simple_string_parts")
    source_map_spy = mocker.spy(string_literals, "source_map_for_simple_string")

    docstring = PDF.prepare(category_context(f"{source}\n")).docstrings[0]
    equivalent = dataclasses.replace(docstring)
    original_repr = repr(docstring)

    assert parts_spy.call_count == 0
    assert source_map_spy.call_count == 0
    parts = docstring.simple_string_parts
    assert parts is not None
    assert docstring.simple_string_parts is parts
    assert parts_spy.call_count == 1
    assert source_map_spy.call_count == 1
    source_map = docstring.source_map
    assert (source_map is not None) is mapping_available
    assert docstring.source_map is source_map
    assert parts_spy.call_count == 1
    assert source_map_spy.call_count == 1
    assert repr(docstring) == original_repr
    assert docstring == equivalent


@pytest.mark.parametrize(("source", "expected_code_points"), [('"""plain text"""\n', ()), ('"""hazard\u202e"""\n', (0x202E,))])
def test_prepare_lazily_caches_unicode_occurrences_without_changing_value_semantics(source: str, expected_code_points: tuple[int, ...], mocker: MockerFixture) -> None:
    occurrence_spy = mocker.spy(unicode_safety, "suspicious_unicode_occurrences")

    docstring = PDF.prepare(category_context(source)).docstrings[0]
    equivalent = dataclasses.replace(docstring)
    original_repr = repr(docstring)

    assert occurrence_spy.call_count == 0
    occurrences = docstring.unicode_occurrences
    assert tuple(occurrence.code_point for occurrence in occurrences) == expected_code_points
    assert docstring.unicode_occurrences is occurrences
    assert docstring.has_unicode_rewrite_barrier is bool(expected_code_points)
    assert occurrence_spy.call_count == 1
    assert repr(docstring) == original_repr
    assert docstring == equivalent


def test_prepare_lazily_caches_concatenated_string_parts(mocker: MockerFixture) -> None:
    parts_spy = mocker.spy(string_literals, "simple_string_parts")
    docstring = PDF.prepare(category_context('"first" "\\u00a0second"\n')).docstrings[0]

    assert parts_spy.call_count == 0
    parts = docstring.simple_string_parts
    assert parts is not None
    assert tuple(part.value for part in parts) == ("first", "\u00a0second")
    assert docstring.simple_string_parts is parts
    assert docstring.source_map is None
    assert parts_spy.call_count == 1


def test_prepare_lazily_caches_entry_description_targets_and_structural_adjacency(mocker: MockerFixture) -> None:
    """Share prepared style targets while retaining summary and entry adjacency."""
    target_spy = mocker.spy(PDF_definition, "_entry_description_line_targets")
    adjacency_spy = mocker.spy(PDF_definition, "_blocks_with_following_nonblank_kind")
    source = 'def choose(value):\n    """Choose one,\n\n    - first\n\n    Args:\n        value: Choose one,\n            - fast\n    """\n'
    data = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE)))

    first_targets = data.entry_description_first_line_targets()
    assert adjacency_spy.call_count == 0
    terminal_targets = data.entry_description_terminal_line_targets()
    summary_target = data.summary_terminal_line_targets[0]
    adjacency_calls = adjacency_spy.call_count
    following_summary_kind = summary_target.following_block_kind

    assert data.entry_description_first_line_targets() is first_targets
    assert data.entry_description_terminal_line_targets() is terminal_targets
    assert target_spy.call_count == 2
    assert tuple(target.following_block_kinds for target in first_targets) == ((),)
    assert tuple(target.following_block_kinds for target in terminal_targets) == ((DocstringBlockKind.LIST_ITEM,),)
    assert following_summary_kind is DocstringBlockKind.LIST_ITEM
    assert summary_target.following_block_kind is following_summary_kind
    assert adjacency_spy.call_count == adjacency_calls + 1


def test_mapping_capability_is_separate_from_canonical_rewrite_policy() -> None:
    safe, hazardous = PDF.prepare(category_context('"""safe"""\n"""ignored additional"""\nvalue = 1\n"""hazard\u202e"""\n')).docstrings

    assert PDF_definition.is_safely_mapped_simple_docstring(safe)
    assert PDF_definition.can_canonically_rewrite_simple_docstring(safe)
    assert PDF_definition.is_safely_mapped_simple_docstring(hazardous)
    assert not PDF_definition.can_canonically_rewrite_simple_docstring(hazardous)


def test_prepare_accepts_only_string_valued_first_expressions_as_docstrings() -> None:
    source = 'def parenthesized():\n    (u"doc")\n    "not an additional docstring"\n\ndef later_string():\n    value = 1\n    "not a docstring"\n'
    data = PDF.prepare(category_context(source))
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("parenthesized",)
    assert data.docstrings[0].source == 'u"doc"'


def test_unicode_line_separator_inside_literal_is_not_a_physical_source_line() -> None:
    data = PDF.prepare(category_context('"""first\u2028second"""\n'))
    assert len(data.docstrings[0].physical_lines) == 1
    assert data.docstrings[0].physical_lines[0].source == '"""first\u2028second"""'


def test_require_data_validates_category_data_type() -> None:
    context = category_context('"""doc"""\n')
    data = PDF.prepare(context)
    assert PDF.require_data(rule_context(context, data)) is data
    with pytest.raises(TypeError, match="require PDFCategoryData"):
        PDF.require_data(rule_context(context, None))


def test_escaped_closing_quote_body_source_skips_single_character_delimiter() -> None:
    node = cst.ensure_type(cst.parse_expression("'Summary'"), cst.SimpleString)

    assert escaped_closing_quote_body_source(node, "Say '") is None


def test_simple_docstring_body_source_candidates_try_value_preserving_both_end_quote_escape_first() -> None:
    node = cst.ensure_type(cst.parse_expression('"""Summary"""'), cst.SimpleString)

    assert next(simple_docstring_body_source_candidates(node, '"quoted"', expected_value='"quoted"')) == ('\\"quoted\\"', '"quoted"')


def test_simple_docstring_body_source_candidates_include_separator_fallback_value_changes() -> None:
    node = cst.ensure_type(cst.parse_expression('r"""Summary"""'), cst.SimpleString)

    candidates = tuple(simple_docstring_body_source_candidates(node, "Path \\", expected_value="Path \\"))

    assert (" Path \\", " Path \\") in candidates
    assert ("Path \\ ", "Path \\ ") in candidates
    assert (" Path \\ ", " Path \\ ") in candidates


def block_kinds(blocks: tuple[DocstringBlock, ...]) -> tuple[DocstringBlockKind, ...]:
    """Return block kinds recursively in source order."""
    return tuple(kind for block in blocks for kind in (block.kind, *block_kinds(block.children)))


def structure_for(value: str, *, settings: CheckSettings | None = None) -> DocstringStructure:
    """Return prepared semantic structure for a module docstring value."""
    source = f'"""{value}"""\n'
    return PDF.prepare(category_context(source, settings=settings)).docstrings[0].structure


def top_level_blocks(value: str, *, settings: CheckSettings | None = None) -> tuple[tuple[DocstringBlockKind, int, int], ...]:
    """Return top-level block kinds and logical line ranges."""
    return tuple((block.kind, block.start_line, block.end_line) for block in structure_for(value, settings=settings).blocks)


def assert_block_partition(blocks: tuple[DocstringBlock, ...], start: int, end: int) -> None:
    """Assert that sibling blocks exactly partition a logical line range."""
    assert blocks
    assert blocks[0].start_line == start
    assert blocks[-1].end_line == end
    assert all(left.end_line == right.start_line for left, right in itertools.pairwise(blocks))
    for block in blocks:
        assert block.start_line < block.end_line
        if block.children:
            assert_block_partition(block.children, block.start_line, block.end_line)


def test_prepare_collects_deeply_nested_definitions_in_lexical_order() -> None:
    source = 'class Outer:\n    class Inner:\n        """inner"""\n        def method(self):\n            """method"""\n            def local():\n                """local"""\n                pass\n            return local\n\ndef top():\n    class LocalClass:\n        """local class"""\n    return LocalClass\n'
    data = PDF.prepare(category_context(source))
    assert tuple(definition.qualified_name for definition in data.definitions) == ("<module>", "Outer", "Outer.Inner", "Outer.Inner.method", "Outer.Inner.method.local", "top", "top.LocalClass")
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("Outer.Inner", "Outer.Inner.method", "Outer.Inner.method.local", "top.LocalClass")
    assert data.definitions[4].parent is data.definitions[3]
    assert data.definitions[6].parent is data.definitions[5]


def test_prepare_handles_simple_statement_suites_and_non_expression_first_statements() -> None:
    source = 'class Documented: "class doc"; value = 1\nclass Undocumented: value = 1; "late"\ndef documented(): "function doc"; return 1\ndef assigned_first(): value = 1; "late"\n'
    data = PDF.prepare(category_context(source))
    definition_docstrings = tuple(docstring for docstring in data.docstrings if isinstance(docstring.owner, DefinitionInfo))
    attribute_docstrings = tuple(docstring for docstring in data.docstrings if isinstance(docstring.owner, AttributeInfo))
    definition_statement_matches = []
    for docstring in definition_docstrings:
        owner = docstring.owner
        if isinstance(owner, DefinitionInfo):
            definition_statement_matches.append(docstring.statement is owner.body)

    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("Documented", "Undocumented.value", "documented")
    assert tuple(docstring.owner.qualified_name for docstring in definition_docstrings) == ("Documented", "documented")
    assert tuple(docstring.owner.qualified_name for docstring in attribute_docstrings) == ("Undocumented.value",)
    assert all(definition_statement_matches)


def test_comments_before_first_statements_do_not_prevent_docstring_collection() -> None:
    source = '#!/usr/bin/env python\n# module comment\n"""module doc"""\n\nclass Example:\n    # class comment\n    """class doc"""\n\n    def method(self):\n        # function comment\n        """method doc"""\n'
    data = PDF.prepare(category_context(source))
    assert tuple(docstring.owner.qualified_name for docstring in data.docstrings) == ("<module>", "Example", "Example.method")
    assert tuple(docstring.range.start.line for docstring in data.docstrings) == (3, 7, 11)
    assert tuple(docstring.structure.lines[0].source_line_number for docstring in data.docstrings) == (3, 7, 11)


def test_concatenations_containing_formatted_strings_are_not_docstrings() -> None:
    source = 'value = "dynamic"\ndef function():\n    "prefix " f"{value}"\n'
    data = PDF.prepare(category_context(source))
    assert tuple(definition.qualified_name for definition in data.definitions) == ("<module>", "function")
    assert data.docstrings == ()


def test_concatenated_docstring_preserves_exact_parenthesized_source_and_disables_source_mapping() -> None:
    source = 'def function():\n    (\n        "first\\n"\n        r"second"\n    )\n'
    docstring = PDF.prepare(category_context(source)).docstrings[0]
    assert docstring.source == '"first\\n"\n        r"second"'
    assert docstring.value == "first\nsecond"
    assert tuple(line.source_line_number for line in docstring.structure.lines) == (None, None)


def test_evaluated_escape_newline_disables_ambiguous_source_line_mapping() -> None:
    docstring = PDF.prepare(category_context(r'"""first\nsecond"""' + "\n")).docstrings[0]
    assert len(docstring.physical_lines) == 1
    assert tuple((line.raw_text, line.source_line_number) for line in docstring.structure.lines) == (("first", None), ("second", None))


def test_balanced_physical_and_evaluated_line_counts_do_not_imply_valid_source_mapping() -> None:
    source = 'def function():\n    """first\\nsecond\\\nthird"""\n'
    docstring = PDF.prepare(category_context(source)).docstrings[0]
    assert len(docstring.physical_lines) == len(docstring.structure.lines) == 2
    assert tuple(line.raw_text for line in docstring.structure.lines) == ("first", "secondthird")
    assert tuple(line.source_line_number for line in docstring.structure.lines) == (None, None)


def test_value_lines_track_offsets_dedentation_and_source_lines() -> None:
    source = 'def function():\n    """Summary.\n        over-indented\n    aligned\n    """\n'
    lines = PDF.prepare(category_context(source)).docstrings[0].structure.lines
    assert tuple((line.index, line.start_offset, line.end_offset, line.raw_text, line.text, line.source_line_number) for line in lines) == (
        (0, 0, 8, "Summary.", "Summary.", 2),
        (1, 9, 30, "        over-indented", "    over-indented", 3),
        (2, 31, 42, "    aligned", "aligned", 4),
        (3, 43, 47, "    ", "", 5),
    )


def test_nested_tab_indentation_uses_the_docstring_visual_column() -> None:
    source = 'class Outer:\n\tclass Inner:\n\t\tdef method(self):\n\t\t\t"""Summary.\n\t\t\tArgs:\n\t\t\t\tvalue: Description.\n\t\t\t"""\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary.", "Args:", "\tvalue: Description.", "")
    assert tuple(section.name for section in structure.sections) == ("Args",)
    assert tuple(entry.names for entry in structure.entries) == (("value",),)


def test_tab_crossing_docstring_margin_preserves_residual_indentation() -> None:
    source = 'def function():\n    """Summary::\n\tIndented literal.\n    """\n'
    structure = PDF.prepare(category_context(source)).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "    Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_simple_suite_docstring_uses_suite_indentation_instead_of_literal_column() -> None:
    source = 'def function(): """Summary::\n        Indented literal.\n    """\n'
    structure = PDF.prepare(category_context(source)).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "    Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_same_line_attribute_docstring_uses_continuation_indentation() -> None:
    source = 'class Client:\n    def __init__(self):\n        self.value = 1; """Return the instance value after validating\n                        that the configured value is finite."""\n'
    structure = PDF.prepare(category_context(source)).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Return the instance value after validating", "that the configured value is finite.")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.SUMMARY, 0, 2),)


def test_nested_simple_suite_docstring_includes_enclosing_indentation() -> None:
    source = 'class Outer:\n    def method(self): """Summary::\n            Indented literal.\n        """\n'
    structure = PDF.prepare(category_context(source)).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "    Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_simple_suite_docstring_uses_configured_indentation_width() -> None:
    source = 'def function(): """Summary::\n    Indented literal.\n  """\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(indent_width=2))).docstrings[0].structure
    assert tuple(line.text for line in structure.lines) == ("Summary::", "  Indented literal.", "")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 2), (DocstringBlockKind.BLANK, 2, 3))


def test_mixed_evaluated_newline_sequences_have_exact_offsets() -> None:
    docstring = PDF.prepare(category_context(r'"""first\r\nsecond\rthird\nfourth"""' + "\n")).docstrings[0]
    assert docstring.value_lines == ("first", "second", "third", "fourth")
    assert tuple((line.start_offset, line.end_offset, line.raw_text, line.source_line_number) for line in docstring.structure.lines) == (
        (0, 5, "first", None),
        (7, 13, "second", None),
        (14, 19, "third", None),
        (20, 26, "fourth", None),
    )
    assert reflow_texts(docstring.structure.reflow_regions[0].lines) == ("first", "second", "third", "fourth")


def test_reflow_region_lines_carry_description_offsets_when_text_matches_prefix() -> None:
    value = "Args:\n    x: x words around enough to wrap after a matching entry name."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    region = structure.reflow_regions[0]

    assert reflow_texts(region.lines) == ("x words around enough to wrap after a matching entry name.",)
    assert region.lines[0].start_offset == value.index("x words")
    assert region.lines[0].start_offset != value.index("x:")


def test_description_fragments_preserve_full_pretrim_value_offsets() -> None:
    """Retain exact evaluated boundaries without storing rule-specific safety state."""
    value = "Returns:\n    int: \u2003The return value.\u2003"
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    fragment = structure.entries[0].description_lines[0]

    assert fragment.text == "The return value."
    assert value[fragment.full_start_offset : fragment.full_end_offset] == "\u2003The return value.\u2003"
    assert value[fragment.start_offset : fragment.end_offset] == fragment.text


def test_trailing_evaluated_newline_does_not_create_a_phantom_logical_line() -> None:
    docstring = PDF.prepare(category_context(r'"""Summary.\n"""' + "\n")).docstrings[0]
    assert docstring.value_lines == ("Summary.",)
    assert tuple(line.raw_text for line in docstring.structure.lines) == ("Summary.",)
    assert top_level_blocks("Summary.\n") == ((DocstringBlockKind.SUMMARY, 0, 1),)


def test_concatenated_docstring_uses_common_value_indentation_and_preserves_interstitial_comments() -> None:
    source = 'def function():\n    ("Summary.\\n"\n     "        deeper\\n"\n     # Interstitial source comment.\n     "    aligned")\n'
    docstring = PDF.prepare(category_context(source)).docstrings[0]
    assert docstring.source == '"Summary.\\n"\n     "        deeper\\n"\n     # Interstitial source comment.\n     "    aligned"'
    assert tuple((line.raw_text, line.text) for line in docstring.structure.lines) == (("Summary.", "Summary."), ("        deeper", "    deeper"), ("    aligned", "aligned"))
    assert tuple(line.source_line_number for line in docstring.structure.lines) == (None, None, None)
    assert tuple(line.line_number for line in docstring.physical_lines) == (2, 3, 4, 5)


def test_empty_and_whitespace_only_docstrings_have_only_blank_semantics() -> None:
    empty = structure_for("")
    whitespace = structure_for("  \n\t")
    assert top_level_blocks("") == ((DocstringBlockKind.BLANK, 0, 1),)
    assert top_level_blocks("  \n\t") == ((DocstringBlockKind.BLANK, 0, 2),)
    assert empty.reflow_regions == ()
    assert whitespace.reflow_regions == ()


def test_summary_paragraph_blank_and_verbatim_blocks_preserve_ranges() -> None:
    value = "Summary first\nsummary second\n\nParagraph first\nparagraph second\n\n    indented\n    verbatim"
    structure = structure_for(value)
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 2),
        (DocstringBlockKind.BLANK, 2, 3),
        (DocstringBlockKind.PARAGRAPH, 3, 5),
        (DocstringBlockKind.BLANK, 5, 6),
        (DocstringBlockKind.VERBATIM, 6, 8),
    )
    assert tuple((region.kind, reflow_texts(region.lines), region.start_offset, region.end_offset) for region in structure.reflow_regions) == (
        (DocstringBlockKind.SUMMARY, ("Summary first", "summary second"), 0, 28),
        (DocstringBlockKind.PARAGRAPH, ("Paragraph first", "paragraph second"), 30, 62),
    )


def test_colon_header_blocks_split_prose_reflow_regions() -> None:
    value = "Summary first\nsummary second\n\nThe accepted values are:\npending, active, and disabled.\n\nTrailing prose\ncontinues here."
    structure = structure_for(value)

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 2),
        (DocstringBlockKind.BLANK, 2, 3),
        (DocstringBlockKind.COLON_HEADER, 3, 4),
        (DocstringBlockKind.PARAGRAPH, 4, 5),
        (DocstringBlockKind.BLANK, 5, 6),
        (DocstringBlockKind.PARAGRAPH, 6, 8),
    )
    assert tuple((region.kind, reflow_texts(region.lines)) for region in structure.reflow_regions) == (
        (DocstringBlockKind.SUMMARY, ("Summary first", "summary second")),
        (DocstringBlockKind.PARAGRAPH, ("pending, active, and disabled.",)),
        (DocstringBlockKind.PARAGRAPH, ("Trailing prose", "continues here.")),
    )


def test_colon_continuation_line_ends_current_reflow_region() -> None:
    value = "This sentence has been deliberately split\nover three physical lines and ends\nwith a colon:\nthe following two lines should be\nwrapped as their own paragraph."
    structure = structure_for(value)

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.SUMMARY, 0, 3), (DocstringBlockKind.PARAGRAPH, 3, 5))
    assert tuple((region.kind, reflow_texts(region.lines)) for region in structure.reflow_regions) == (
        (DocstringBlockKind.SUMMARY, ("This sentence has been deliberately split", "over three physical lines and ends", "with a colon:")),
        (DocstringBlockKind.PARAGRAPH, ("the following two lines should be", "wrapped as their own paragraph.")),
    )


def test_single_token_colon_label_stays_separate_from_preceding_prose() -> None:
    structure = structure_for("Use one of these values\nvalues:\npending, active, disabled.")

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 1),
        (DocstringBlockKind.COLON_HEADER, 1, 2),
        (DocstringBlockKind.PARAGRAPH, 2, 3),
    )
    assert tuple((region.kind, reflow_texts(region.lines)) for region in structure.reflow_regions) == (
        (DocstringBlockKind.SUMMARY, ("Use one of these values",)),
        (DocstringBlockKind.PARAGRAPH, ("pending, active, disabled.",)),
    )


def test_numeric_colon_label_stays_separate_from_preceding_prose() -> None:
    structure = structure_for("Choose one of these cases\n1:\nfirst case.")

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 1),
        (DocstringBlockKind.COLON_HEADER, 1, 2),
        (DocstringBlockKind.PARAGRAPH, 2, 3),
    )


def test_colon_header_after_complete_sentence_stays_separate() -> None:
    structure = structure_for("Summary.\nThe accepted values are:\npending, active, and disabled.")

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 1),
        (DocstringBlockKind.COLON_HEADER, 1, 2),
        (DocstringBlockKind.PARAGRAPH, 2, 3),
    )
    assert tuple((region.kind, reflow_texts(region.lines)) for region in structure.reflow_regions) == (
        (DocstringBlockKind.SUMMARY, ("Summary.",)),
        (DocstringBlockKind.PARAGRAPH, ("pending, active, and disabled.",)),
    )


def test_colon_header_first_content_line_is_not_summary() -> None:
    structure = structure_for("Accepted values:\npending, active, and disabled.")

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.COLON_HEADER, 0, 1), (DocstringBlockKind.PARAGRAPH, 1, 2))
    assert tuple(region.kind for region in structure.reflow_regions) == (DocstringBlockKind.PARAGRAPH,)


def test_colon_header_respects_more_specific_structure_precedence() -> None:
    google = structure_for("Args:\n    value: Description.", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    numpy = structure_for("Returns\n-------\nint\n    Result.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    literal = structure_for("Example::\n\n    value = 1")

    assert tuple(block.kind for block in google.blocks) == (DocstringBlockKind.SECTION,)
    assert tuple(block.kind for block in numpy.blocks) == (DocstringBlockKind.SECTION,)
    assert tuple(block.kind for block in literal.blocks) == (DocstringBlockKind.LITERAL_BLOCK,)


def test_verbatim_blocks_exclude_trailing_blank_lines() -> None:
    structure = structure_for("Summary.\n\n    indented\n    verbatim\n\n\nBody.")

    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.SUMMARY, 0, 1),
        (DocstringBlockKind.BLANK, 1, 2),
        (DocstringBlockKind.VERBATIM, 2, 4),
        (DocstringBlockKind.BLANK, 4, 6),
        (DocstringBlockKind.PARAGRAPH, 6, 7),
    )


def test_a_leading_protected_block_prevents_a_later_paragraph_becoming_summary() -> None:
    assert top_level_blocks("```\ncode\n```\nLater prose.") == ((DocstringBlockKind.CODE_FENCE, 0, 3), (DocstringBlockKind.PARAGRAPH, 3, 4))


@pytest.mark.parametrize(
    ("value", "expected_kind"), [("Summary.", DocstringBlockKind.SUMMARY), ("Result:", DocstringBlockKind.COLON_HEADER), ("Accepted values:\nfast and safe.", None), ("- item\n\nLater prose.", None)]
)
def test_first_summary_block_uses_the_category_summary_contract(value: str, expected_kind: DocstringBlockKind | None) -> None:
    source = f'"""{value}"""\n'
    docstring = PDF.prepare(category_context(source)).docstrings[0]
    summary = first_summary_block(docstring)

    assert (None if summary is None else summary.kind) is expected_kind


@pytest.mark.parametrize("header", ["Arg:", "Args:", "ARGS:", "Argument:", "Arguments", "Keyword Argument:", "Keyword Arguments:", "Other Arg:", "Other Args:", "wARnS:"])
def test_google_section_header_spellings_are_case_insensitive_and_preserved(header: str) -> None:
    structure = structure_for(f"Summary.\n\n{header}\n    value: Description.", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple(section.name for section in structure.sections) == (header.removesuffix(":"),)
    assert structure.sections[0].header_line == 2
    assert structure.sections[0].start_line == 2
    assert structure.sections[0].end_line == 4


def test_adjacent_empty_google_sections_have_nonoverlapping_header_only_blocks() -> None:
    structure = structure_for("Args:\nReturns:", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((section.name, section.start_line, section.end_line, section.entries) for section in structure.sections) == (("Args", 0, 1, ()), ("Returns", 1, 2, ()))
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.SECTION, 0, 1), (DocstringBlockKind.SECTION, 1, 2))
    assert all(tuple(child.kind for child in block.children) == (DocstringBlockKind.SECTION_HEADER,) for block in structure.blocks)


@pytest.mark.parametrize(
    "name",
    [
        "Args",
        "Arg",
        "Argument",
        "Arguments",
        "Attribute",
        "Attention",
        "Attributes",
        "Caution",
        "Danger",
        "Error",
        "Example",
        "Examples",
        "Hint",
        "Important",
        "Keyword Arg",
        "Keyword Args",
        "Keyword Argument",
        "Keyword Arguments",
        "Method",
        "Methods",
        "Note",
        "Notes",
        "Other Arg",
        "Other Args",
        "Other Argument",
        "Other Arguments",
        "Raise",
        "Raises",
        "Reference",
        "References",
        "Return",
        "Returns",
        "See Also",
        "Tip",
        "Todo",
        "Warning",
        "Warnings",
        "Warn",
        "Warns",
        "Yield",
        "Yields",
    ],
)
def test_all_google_section_names_are_recognized(name: str) -> None:
    structure = structure_for(f"{name}:\n    Content.", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple(section.name for section in structure.sections) == (name,)


def test_google_parameter_entries_support_stars_dotted_names_types_and_empty_descriptions() -> None:
    value = "Args:\n    *args (tuple[str, ...]): Positional values.\n    **kwargs (dict[str, object]):\n        Keyword values.\n    model.value: Untyped dotted name."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.names, entry_type_text(entry), entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("*args",), "tuple[str, ...]", "Positional values.", 1, 2),
        (("**kwargs",), "dict[str, object]", "Keyword values.", 2, 4),
        (("model.value",), None, "Untyped dotted name.", 4, 5),
    )


def test_google_parameter_entries_support_mild_spacing_around_type_and_colon() -> None:
    value = "Args:\n    value   ( int ) : Description."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.names, entry_type_text(entry), entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((("value",), "int", "Description.", 1, 2),)


def test_google_entries_expose_parser_owned_type_slot_spans() -> None:
    """Expose complete and semantic Google type spans without reparsing entry lines."""
    value = "Args:\n    value (  list[int]  ): Description."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    entry = structure.entries[0]
    type_info = entry.type_info

    assert type_info is not None
    slot = type_info.slot
    assert slot is not None
    line = structure.lines[slot.line_index]
    assert line.text[slot.full_start_column : slot.full_end_column] == "  list[int]  "
    assert line.text[slot.semantic_start_column : slot.semantic_end_column] == "list[int]"
    assert type_info.text == "list[int]"


def test_google_fallback_method_entries_expose_parser_owned_type_slot_spans() -> None:
    """Expose type slots for starred method entries that cannot be opaque signatures."""
    value = "Methods:\n    *args (  list[int]  ): Description."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    entry = structure.entries[0]
    type_info = entry.type_info

    assert entry.kind is DocstringEntryKind.METHOD
    assert type_info is not None
    slot = type_info.slot
    assert slot is not None
    line = structure.lines[slot.line_index]
    assert line.text[slot.full_start_column : slot.full_end_column] == "  list[int]  "
    assert line.text[slot.semantic_start_column : slot.semantic_end_column] == "list[int]"
    assert type_info.text == "list[int]"


def test_google_parameter_entries_support_balanced_nested_type_delimiters() -> None:
    value = 'Args:\n    callback (Callable[[tuple[int, str]], Literal[")"]]): Description.'
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.names, entry_type_text(entry), entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("callback",), 'Callable[[tuple[int, str]], Literal[")"]]', "Description.", 1, 2),
    )


def test_malformed_google_entry_is_not_added_to_semantic_entries() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        value Value.\n    """\n'
    settings = CheckSettings(docstring_convention=DocstringConvention.GOOGLE)
    structure = PDF.prepare(category_context(source, settings=settings)).docstrings[0].structure

    assert not structure.entries
    assert tuple(issue.kind for issue in structure.convention_entry_issues) == (ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR,)


def test_malformed_numpy_entries_are_distinct_non_reflowable_section_blocks() -> None:
    source = 'def combine(first, second):\n    """Combine values.\n\n    Parameters\n    ----------\n    first tuple[int, int]\n    second list[str]\n    """\n'
    settings = CheckSettings(docstring_convention=DocstringConvention.NUMPY)
    structure = PDF.prepare(category_context(source, settings=settings)).docstrings[0].structure

    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[-1].children) == (
        (DocstringBlockKind.SECTION_HEADER, 2, 4),
        (DocstringBlockKind.CONVENTION_ENTRY_ISSUE, 4, 5),
        (DocstringBlockKind.CONVENTION_ENTRY_ISSUE, 5, 6),
        (DocstringBlockKind.BLANK, 6, 7),
    )
    assert all(region.start_line not in {4, 5} for region in structure.reflow_regions)


def test_malformed_entry_detection_skips_protected_google_content() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        ```text\n        value Value.\n        ```\n    """\n'
    settings = CheckSettings(docstring_convention=DocstringConvention.GOOGLE)
    structure = PDF.prepare(category_context(source, settings=settings)).docstrings[0].structure

    assert not structure.convention_entry_issues


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    [
        ("Returns", "str: Result.", DocstringEntryKind.RETURN, (), "str"),
        ("Return", "str: Result.", DocstringEntryKind.RETURN, (), "str"),
        ("Yields", "tuple[int, int]: Pair.", DocstringEntryKind.YIELD, (), "tuple[int, int]"),
        ("Yield", "tuple[int, int]: Pair.", DocstringEntryKind.YIELD, (), "tuple[int, int]"),
        ("Raises", "ValueError: Invalid value.", DocstringEntryKind.EXCEPTION, ("ValueError",), None),
        ("Raise", "ValueError: Invalid value.", DocstringEntryKind.EXCEPTION, ("ValueError",), None),
        ("Warns", "RuntimeWarning: Possibly unstable.", DocstringEntryKind.WARNING, ("RuntimeWarning",), None),
        ("Warn", "RuntimeWarning: Possibly unstable.", DocstringEntryKind.WARNING, ("RuntimeWarning",), None),
        ("Warnings", "RuntimeWarning: Possibly unstable.", DocstringEntryKind.FIELD, ("RuntimeWarning",), None),
        ("Attributes", "name (str): Public name.", DocstringEntryKind.ATTRIBUTE, ("name",), "str"),
        ("Attribute", "name (str): Public name.", DocstringEntryKind.ATTRIBUTE, ("name",), "str"),
        ("Methods", "run: Execute it.", DocstringEntryKind.METHOD, ("run",), None),
        ("Method", "run: Execute it.", DocstringEntryKind.METHOD, ("run",), None),
        ("Notes", "topic: General note.", DocstringEntryKind.FIELD, ("topic",), None),
        ("Note", "topic: General note.", DocstringEntryKind.FIELD, ("topic",), None),
    ],
)
def test_google_section_names_determine_entry_semantics(section: str, entry_text: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...], expected_type: str | None) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry_type_text(entry)) == (expected_kind, expected_names, expected_type)


def test_google_method_signatures_are_names_with_opaque_balanced_arguments() -> None:
    """Parse method signatures without exposing their arguments as type text."""
    structure = structure_for(
        """Methods:
    run(): Execute it.
    convert(value: tuple[int, str], *, mode=Literal[")", "safe"]): Convert it.""",
        settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE),
    )

    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.METHOD, ("run",), None, "Execute it."),
        (DocstringEntryKind.METHOD, ("convert",), None, "Convert it."),
    )
    assert all(entry.type_info is None for entry in structure.entries)


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind"),
    [("Returns", "None", DocstringEntryKind.RETURN), ("Returns", "None.", DocstringEntryKind.RETURN), ("Yields", "None", DocstringEntryKind.YIELD), ("Yields", "None.", DocstringEntryKind.YIELD)],
)
def test_google_return_and_yield_sections_parse_bare_none_as_empty_typed_entry(section: str, entry_text: str, expected_kind: DocstringEntryKind) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((expected_kind, (), "None", "", 1, 2),)
    assert structure.entries[0].type_info is not None
    assert structure.entries[0].type_info.slot is None
    assert structure.reflow_regions == ()


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    [
        ("Returns", "Mapping[ str, Sequence[int  ]]: Result.", DocstringEntryKind.RETURN, (), "Mapping[ str, Sequence[int  ]]"),
        ("Yields", "Iterator[tuple[str, int | None]]: Item.", DocstringEntryKind.YIELD, (), "Iterator[tuple[str, int | None]]"),
        ("Raises", "mypkg.errors.CustomError: Bad value.", DocstringEntryKind.EXCEPTION, ("mypkg.errors.CustomError",), None),
        ("Raises", "ValueError | TypeError: Bad value.", DocstringEntryKind.EXCEPTION, ("ValueError", "TypeError"), None),
    ],
)
def test_google_return_yield_and_raise_entries_preserve_generic_looking_type_text(
    section: str, entry_text: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...], expected_type: str | None
) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    entry = structure.entries[0]

    assert (entry.kind, entry.names, entry_type_text(entry), entry.description) == (expected_kind, expected_names, expected_type, entry_text.rpartition(":")[2].strip())


def test_google_malformed_exception_entry_skips_continuation_before_later_entry() -> None:
    value = "Raises:\n    If the value is bad: explain the condition.\n        `ValueError` | TypeError : prose continuation.\n    `RuntimeError` | LookupError: Bad runtime."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))

    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((("RuntimeError", "LookupError"), "Bad runtime.", 3, 4),)
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.VERBATIM, 1, 3),
        (DocstringBlockKind.SECTION_ENTRY, 3, 4),
    )


@pytest.mark.parametrize(("section", "entry_text"), [("Returns", "str."), ("Yields", "Iterator[int]."), ("Raises", "None.")])
def test_google_bare_none_entry_special_case_does_not_apply_to_other_content(section: str, entry_text: str) -> None:
    structure = structure_for(f"{section}:\n    {entry_text}", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert structure.entries == ()


def test_google_section_boundaries_and_non_entry_content_are_nested_correctly() -> None:
    value = "Args:\n    Introductory prose without a field.\n\n    value: Description.\n\nExamples:\n    >>> call(value)\n    result\n\nTrailing prose."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((section.name, section.start_line, section.end_line, len(section.entries)) for section in structure.sections) == (("Args", 0, 5, 1), ("Examples", 5, 10, 0))
    assert tuple(block.kind for block in structure.blocks) == (DocstringBlockKind.SECTION, DocstringBlockKind.SECTION)
    assert DocstringBlockKind.VERBATIM in block_kinds(structure.blocks)
    assert DocstringBlockKind.DOCTEST in block_kinds(structure.blocks)


def test_google_section_headers_and_entries_inside_code_fences_are_opaque() -> None:
    value = "Args:\n    value: Description.\n\n```text\nReturns:\n    fake: Not an entry.\n```\n\nReturns:\n    str: Real result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((section.name, section.start_line, section.end_line) for section in structure.sections) == (("Args", 0, 8), ("Returns", 8, 10))
    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), None, "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Real result."),
    )
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.SECTION_ENTRY, 1, 2),
        (DocstringBlockKind.BLANK, 2, 3),
        (DocstringBlockKind.CODE_FENCE, 3, 7),
        (DocstringBlockKind.BLANK, 7, 8),
    )


def test_indented_google_section_name_is_entry_description_text() -> None:
    value = "Args:\n    value: First line.\n        Returns:\n        Still the value description.\nReturns:\n    str: Actual result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.kind, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, "First line. Returns: Still the value description.", 1, 4),
        (DocstringEntryKind.RETURN, "Actual result.", 5, 6),
    )


def test_indented_google_section_headers_are_recognized_as_malformed_sections() -> None:
    value = "Summary.\n\n  Args:\n      value: Description.\n\n  Returns:\n      str: Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), None, "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Result."),
    )
    assert tuple((region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions if region.kind == DocstringBlockKind.SECTION_ENTRY) == (
        ("    value: ", "        "),
        ("    str: ", "        "),
    )


def test_nested_protected_blocks_are_not_folded_into_google_entry_descriptions() -> None:
    value = "Args:\n    value: Description.\n        - First choice.\n        - Second choice.\n        ```text\n        value: code, not prose\n        ```\n    other: Other description."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((("value",), "Description.", 1, 2), (("other",), "Other description.", 7, 8))
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.SECTION_ENTRY, 1, 2),
        (DocstringBlockKind.LIST_ITEM, 2, 3),
        (DocstringBlockKind.LIST_ITEM, 3, 4),
        (DocstringBlockKind.CODE_FENCE, 4, 7),
        (DocstringBlockKind.SECTION_ENTRY, 7, 8),
    )


def test_rest_fields_and_generic_reflow_regions_stay_in_source_order() -> None:
    value = ":param first: First description.\n- Interposed list item.\n:param second: Second description.\n> Quoted text.\n:param third: Third description."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    assert tuple((entry.names, entry.start_line) for entry in structure.entries) == ((("first",), 0), (("second",), 2), (("third",), 4))
    assert tuple((region.kind, region.start_line) for region in structure.reflow_regions) == (
        (DocstringBlockKind.REST_FIELD, 0),
        (DocstringBlockKind.LIST_ITEM, 1),
        (DocstringBlockKind.REST_FIELD, 2),
        (DocstringBlockKind.BLOCK_QUOTE, 3),
        (DocstringBlockKind.REST_FIELD, 4),
    )


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.NUMPY])
def test_google_sections_are_only_parsed_for_google_convention(convention: DocstringConvention) -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (int): A value.\n    """\n'
    data = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=convention)))
    assert data.docstrings[0].structure.sections == ()


def test_google_sections_parse_entries_and_reflow_descriptions() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (int): A value described on\n            two physical lines.\n\n    Returns:\n        str: The result.\n    """\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), "int", "A value described on two physical lines."),
        (DocstringEntryKind.RETURN, (), "str", "The result."),
    )
    assert tuple(reflow_texts(region.lines) for region in structure.reflow_regions) == (("Summary.",), ("A value described on", "two physical lines."), ("The result.",))


def test_numpy_sections_are_only_parsed_for_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        A value.\n    """\n'
    numpy = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))).docstrings[0].structure
    google = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    assert tuple(section.name for section in numpy.sections) == ("Parameters",)
    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in numpy.entries) == ((DocstringEntryKind.PARAMETER, ("value",), "int", "A value."),)
    assert google.sections == ()


def test_indented_numpy_section_headers_are_recognized_as_malformed_sections() -> None:
    value = "Summary.\n\n  Parameters\n  ----------\n  value : int\n      Description.\n\n  Returns\n  -------\n  str\n      Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))

    assert tuple(section.name for section in structure.sections) == ("Parameters", "Returns")
    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("value",), "int", "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Result."),
    )
    assert tuple((region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions if region.kind == DocstringBlockKind.SECTION_ENTRY) == (("    ", "    "), ("    ", "    "))


@pytest.mark.parametrize("header", ["Parameters\n----------", "PARAMETERS\n==========", "Other Parameters", "Returns"])
def test_numpy_section_header_variants_are_recognized(header: str) -> None:
    structure = structure_for(f"{header}\nvalue : int\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert len(structure.sections) == 1
    section = structure.sections[0]
    assert section.name == header.splitlines()[0]
    assert section.header_line == 0
    assert entry_type_text(section.entries[0]) == "int"


@pytest.mark.parametrize(
    "name",
    [
        "Attribute",
        "Attributes",
        "Example",
        "Examples",
        "Extended Summary",
        "Method",
        "Methods",
        "Note",
        "Notes",
        "Other Parameter",
        "Other Parameters",
        "Other Param",
        "Other Params",
        "Parameter",
        "Parameters",
        "Raise",
        "Raises",
        "Receive",
        "Receives",
        "Reference",
        "References",
        "Return",
        "Returns",
        "See Also",
        "Short Summary",
        "Warning",
        "Warnings",
        "Warn",
        "Warns",
        "Yield",
        "Yields",
    ],
)
def test_all_numpy_section_names_are_recognized(name: str) -> None:
    structure = structure_for(f"{name}\n{'-' * len(name)}\nContent.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple(section.name for section in structure.sections) == (name,)


def test_numpy_parameter_entries_support_multiple_names_stars_and_multiline_descriptions() -> None:
    value = "Parameters\n----------\nx, y : int | None\n    First description line.\n    Second description line.\n*args : tuple[str, ...]\n    Positional values.\n**kwargs : dict[str, object]"
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple((entry.names, entry_type_text(entry), entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == (
        (("x", "y"), "int | None", "First description line. Second description line.", 2, 5),
        (("*args",), "tuple[str, ...]", "Positional values.", 5, 7),
        (("**kwargs",), "dict[str, object]", "", 7, 8),
    )
    assert tuple((region.start_line, region.end_line, reflow_texts(region.lines), region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions) == (
        (3, 5, ("First description line.", "Second description line."), "    ", "    "),
        (6, 7, ("Positional values.",), "    ", "    "),
    )


def test_numpy_entries_expose_named_bare_and_legacy_method_type_slots() -> None:
    """Expose NumPy type slots while keeping signature-shaped methods opaque."""
    value = (
        "Parameters\n----------\nvalue :  list[int]  \n    Value.\n\n"
        "Returns\n-------\n  dict[str, int]  \n    Mapping.\n\n"
        "Methods\n-------\nconnect(value: int)\n    Connect.\nclose : Callable[[], None]\n    Close."
    )
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    type_infos = tuple(entry.type_info for entry in structure.entries)
    slots = tuple(type_info.slot if type_info is not None else None for type_info in type_infos)

    assert tuple(type_info.text if type_info is not None else None for type_info in type_infos) == ("list[int]", "dict[str, int]", None, "Callable[[], None]")
    assert tuple(structure.lines[slot.line_index].text[slot.full_start_column : slot.full_end_column] if slot is not None else None for slot in slots) == (
        "list[int]  ",
        "dict[str, int]",
        None,
        "Callable[[], None]",
    )


def test_numpy_section_headers_and_entries_inside_code_fences_are_opaque() -> None:
    value = "Parameters\n----------\nx : int\n    Description.\n\n```text\nReturns\n-------\nfake : entry\n```\n\nReturns\n-------\nstr\n    Real result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple((section.name, section.start_line, section.end_line) for section in structure.sections) == (("Parameters", 0, 11), ("Returns", 11, 15))
    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.PARAMETER, ("x",), "int", "Description."),
        (DocstringEntryKind.RETURN, (), "str", "Real result."),
    )
    assert DocstringBlockKind.CODE_FENCE in block_kinds(structure.blocks[0].children)


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    [
        ("Returns", "str", DocstringEntryKind.RETURN, (), "str"),
        ("Yields", "Iterator[int]", DocstringEntryKind.YIELD, (), "Iterator[int]"),
        ("Yield", "Iterator[int]", DocstringEntryKind.YIELD, (), "Iterator[int]"),
        ("Raises", "ValueError", DocstringEntryKind.EXCEPTION, ("ValueError",), None),
        ("Raise", "ValueError", DocstringEntryKind.EXCEPTION, ("ValueError",), None),
        ("Warns", "RuntimeWarning", DocstringEntryKind.WARNING, ("RuntimeWarning",), None),
        ("Warn", "RuntimeWarning", DocstringEntryKind.WARNING, ("RuntimeWarning",), None),
        ("Attributes", "name : str", DocstringEntryKind.ATTRIBUTE, ("name",), "str"),
        ("Attribute", "name : str", DocstringEntryKind.ATTRIBUTE, ("name",), "str"),
        ("Methods", "run : Callable[[], None]", DocstringEntryKind.METHOD, ("run",), "Callable[[], None]"),
        ("Method", "run : Callable[[], None]", DocstringEntryKind.METHOD, ("run",), "Callable[[], None]"),
        ("Receives", "value : int", DocstringEntryKind.PARAMETER, ("value",), "int"),
        ("Receive", "value : int", DocstringEntryKind.PARAMETER, ("value",), "int"),
        ("Parameter", "value : int", DocstringEntryKind.PARAMETER, ("value",), "int"),
        ("Other Parameter", "value : int", DocstringEntryKind.PARAMETER, ("value",), "int"),
        ("Other Param", "value : int", DocstringEntryKind.PARAMETER, ("value",), "int"),
    ],
)
def test_numpy_section_names_determine_entry_semantics(section: str, entry_text: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...], expected_type: str | None) -> None:
    structure = structure_for(f"{section}\n{'-' * len(section)}\n{entry_text}\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry_type_text(entry), entry.description) == (expected_kind, expected_names, expected_type, "Description.")


def test_numpy_method_signatures_are_names_with_opaque_balanced_arguments() -> None:
    """Parse canonical NumPy method signatures and their continuation descriptions."""
    structure = structure_for(
        """Methods
-------
colorspace(c='rgb')
    Represent the photo.
convert(value: tuple[int, str], mode=Literal[")", "safe"])
    Convert it.""",
        settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY),
    )

    assert tuple((entry.kind, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        (DocstringEntryKind.METHOD, ("colorspace",), None, "Represent the photo."),
        (DocstringEntryKind.METHOD, ("convert",), None, "Convert it."),
    )


@pytest.mark.parametrize("section", ["Warning", "Warnings"])
def test_numpy_warning_caution_sections_are_narrative(section: str) -> None:
    structure = structure_for(f"{section}\n{'-' * len(section)}\nExperimental", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))

    assert tuple(parsed_section.name for parsed_section in structure.sections) == (section,)
    assert structure.entries == ()


def test_numpy_colon_header_is_not_misclassified_as_a_section() -> None:
    structure = structure_for("Parameters:\nvalue : int\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert structure.sections == ()


def test_numpy_exception_colon_entry_parses_as_exception_description_not_type() -> None:
    structure = structure_for("Raises\n------\n`ValueError` | errors.CustomError : Bad value.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    entry = structure.entries[0]

    assert (entry.kind, entry.names, entry_type_text(entry), entry.description) == (DocstringEntryKind.EXCEPTION, ("ValueError", "errors.CustomError"), None, "Bad value.")


def test_numpy_malformed_exception_entry_skips_continuation_before_later_entry() -> None:
    value = "Raises\n------\nIf the value is bad: explain the condition.\n    `ValueError` | TypeError : prose continuation.\n`RuntimeError` | LookupError\n    Bad runtime."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))

    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((("RuntimeError", "LookupError"), "Bad runtime.", 4, 6),)
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 2),
        (DocstringBlockKind.PARAGRAPH, 2, 3),
        (DocstringBlockKind.VERBATIM, 3, 4),
        (DocstringBlockKind.SECTION_ENTRY, 4, 6),
    )


def test_numpy_bare_return_without_description_does_not_create_reflow_region() -> None:
    structure = structure_for("Returns\n-------\nstr", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    assert tuple((entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (((), "str", ""),)
    assert structure.reflow_regions == ()


@pytest.mark.parametrize(
    ("section", "entry_text", "expected_kind", "expected_names", "expected_type"),
    [
        ("Returns", "Mapping[str, Sequence[int]]", DocstringEntryKind.RETURN, (), "Mapping[str, Sequence[int]]"),
        ("Yields", "Iterator[tuple[str, int | None]]", DocstringEntryKind.YIELD, (), "Iterator[tuple[str, int | None]]"),
        ("Raises", "mypkg.errors.CustomError", DocstringEntryKind.EXCEPTION, ("mypkg.errors.CustomError",), None),
    ],
)
def test_numpy_return_yield_and_raise_entries_preserve_generic_looking_type_text(
    section: str, entry_text: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...], expected_type: str | None
) -> None:
    structure = structure_for(f"{section}\n{'-' * len(section)}\n{entry_text}\n    Description.", settings=CheckSettings(docstring_convention=DocstringConvention.NUMPY))
    entry = structure.entries[0]

    assert (entry.kind, entry.names, entry_type_text(entry), entry.description) == (expected_kind, expected_names, expected_type, "Description.")


def test_section_block_contains_header_entries_blanks_and_generic_children() -> None:
    structure = structure_for("Args:\n\n    value: Description.\n\n    - nested item\n      continuation", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    section_block = structure.blocks[0]
    assert section_block.kind == DocstringBlockKind.SECTION
    assert tuple((child.kind, child.start_line, child.end_line) for child in section_block.children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.BLANK, 1, 2),
        (DocstringBlockKind.SECTION_ENTRY, 2, 3),
        (DocstringBlockKind.BLANK, 3, 4),
        (DocstringBlockKind.LIST_ITEM, 4, 6),
    )
    assert section_block.children[2].entry is structure.entries[0]


@pytest.mark.parametrize(
    ("field", "expected_kind", "expected_names"),
    [
        (":param value: Description.", DocstringEntryKind.PARAMETER, ("value",)),
        (":key value: Description.", DocstringEntryKind.PARAMETER, ("value",)),
        (":kwarg option: Description.", DocstringEntryKind.PARAMETER, ("option",)),
        (":type value: int", DocstringEntryKind.PARAMETER, ("value",)),
        (":returns: Description.", DocstringEntryKind.RETURN, ()),
        (":returns : Description.", DocstringEntryKind.RETURN, ()),
        (":returns  : Description.", DocstringEntryKind.RETURN, ()),
        (":rtype: str", DocstringEntryKind.RETURN, ()),
        (":rtype : str", DocstringEntryKind.RETURN, ()),
        (":yield item: Description.", DocstringEntryKind.YIELD, ("item",)),
        (":raises ValueError: Description.", DocstringEntryKind.EXCEPTION, ("ValueError",)),
        (":ivar timeout: Description.", DocstringEntryKind.ATTRIBUTE, ("timeout",)),
        (":cvar timeout: Description.", DocstringEntryKind.ATTRIBUTE, ("timeout",)),
        (":var timeout: Description.", DocstringEntryKind.ATTRIBUTE, ("timeout",)),
        (":vartype timeout: float", DocstringEntryKind.ATTRIBUTE, ("timeout",)),
        (":attribute timeout: Description.", DocstringEntryKind.FIELD, ("timeout",)),
        (":cvartype timeout: float", DocstringEntryKind.FIELD, ("timeout",)),
        (":meta private: Description.", DocstringEntryKind.FIELD, ("private",)),
    ],
)
def test_rest_field_aliases_map_to_semantic_entry_kinds(field: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...]) -> None:
    structure = structure_for(field, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry.description) == (expected_kind, expected_names, field.rpartition(":")[2].strip())
    assert structure.blocks[0].entry is entry


@pytest.mark.parametrize(
    ("field", "expected_names", "expected_type"),
    [
        (":param int first: Description.", ("first",), "int"),
        (":param int\tfirst: Description.", ("first",), "int"),
        (":param int first : Description.", ("first",), "int"),
        (":param dict[str, int] options: Description.", ("options",), "dict[str, int]"),
        (":param tuple[str, ...] *args: Description.", ("*args",), "tuple[str, ...]"),
        (":kwarg Mapping[str, object] **kwargs: Description.", ("**kwargs",), "Mapping[str, object]"),
    ],
)
def test_typed_rest_parameter_fields_split_type_from_name(field: str, expected_names: tuple[str, ...], expected_type: str) -> None:
    structure = structure_for(field, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    entry = structure.entries[0]
    assert (entry.kind, entry.names, entry_type_text(entry), entry.description) == (DocstringEntryKind.PARAMETER, expected_names, expected_type, "Description.")


@pytest.mark.parametrize(
    ("convention", "value", "expected_names"),
    [
        (DocstringConvention.GOOGLE, "Args:\n    *args: Values.", ("*args",)),
        (DocstringConvention.NUMPY, "Parameters\n----------\nvalue, *args : object\n    Values.", ("value", "*args")),
        (DocstringConvention.REST, ":param tuple[object, ...] *args: Values.", ("*args",)),
    ],
)
def test_entries_expose_parser_owned_name_slots(convention: DocstringConvention, value: str, expected_names: tuple[str, ...]) -> None:
    """Align every parsed name with the exact logical source span that produced it."""
    structure = structure_for(value, settings=CheckSettings(docstring_convention=convention))
    entry = structure.entries[0]

    assert entry.names == expected_names
    assert tuple(None if slot is None else structure.lines[slot.line_index].text[slot.start_column : slot.end_column] for slot in entry.name_slots) == expected_names


@pytest.mark.parametrize(
    ("convention", "value", "expected"),
    [
        (DocstringConvention.GOOGLE, "Raises:\n    `ValueError` | TypeError   : Bad value.", "`ValueError` | TypeError"),
        (DocstringConvention.NUMPY, "Raises\n------\nValueError,TypeError   : Bad value.", "ValueError,TypeError"),
        (DocstringConvention.NUMPY, "Raises\n------\n  `ValueError` | TypeError  \n    Bad value.", "`ValueError` | TypeError"),
        (DocstringConvention.REST, ":raises   `ValueError | TypeError`  : Bad value.", "`ValueError | TypeError`"),
    ],
)
def test_exception_entries_expose_parser_owned_name_list_edit_slots(convention: DocstringConvention, value: str, expected: str) -> None:
    structure = structure_for(value, settings=CheckSettings(docstring_convention=convention))
    entry = structure.entries[0]
    slot = entry.name_list_edit_slot

    assert slot is not None
    assert structure.lines[slot.line_index].text[slot.start_column : slot.end_column] == expected


def test_non_exception_entries_do_not_expose_name_list_edit_slots() -> None:
    structure = structure_for("Args:\n    value: Description.", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))

    assert structure.entries[0].name_list_edit_slot is None


def test_google_entries_expose_parser_owned_type_edit_slots() -> None:
    """Retain complete insertion and removal bounds without reparsing entry text."""
    structure = structure_for("Args:\n    value: Value.\n    other  ( list[int] ): Other.", settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    insertion_slot = structure.entries[0].type_edit_slot
    removal_slot = structure.entries[1].type_edit_slot

    assert insertion_slot is not None
    assert structure.lines[insertion_slot.line_index].text[insertion_slot.insertion_column :] == ": Value."
    assert insertion_slot.removal_start_column is None
    assert insertion_slot.removal_end_column is None
    assert removal_slot is not None
    assert removal_slot.removal_start_column is not None
    assert removal_slot.removal_end_column is not None
    assert structure.lines[removal_slot.line_index].text[removal_slot.removal_start_column : removal_slot.removal_end_column] == "  ( list[int] )"


def test_docstring_entry_rejects_misaligned_name_slots() -> None:
    """Reject parser results whose semantic names and source slots cannot be paired."""
    with pytest.raises(ValueError, match="name slots must align"):
        PDF_definition.DocstringEntry(kind=DocstringEntryKind.PARAMETER, names=("value",), name_slots=(), type_info=None, description="", description_lines=(), start_line=0, end_line=1)


def test_rest_entries_expose_inline_and_type_field_slots() -> None:
    """Expose reStructuredText inline and orphan type-field spans."""
    structure = structure_for(":param  list[int]  value: Description.\n:rtype:  dict[str, int]  ", settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    type_infos = tuple(entry.type_info for entry in structure.entries)
    slots = tuple(type_info.slot if type_info is not None else None for type_info in type_infos)

    assert tuple(type_info.text if type_info is not None else None for type_info in type_infos) == ("list[int]", "dict[str, int]")
    assert tuple(structure.lines[slot.line_index].text[slot.full_start_column : slot.full_end_column] if slot is not None else None for slot in slots) == ("list[int]", "dict[str, int]  ")


def test_rest_multiline_type_fields_preserve_complete_semantics_without_slots() -> None:
    """Keep complete continued type text while withholding partial source spans."""
    structure = structure_for(":type value:\n    list[str]\n:rtype: tuple[\n    str, int]", settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    type_infos = tuple(entry.type_info for entry in structure.entries)

    assert tuple(type_info.text if type_info is not None else None for type_info in type_infos) == ("list[str]", "tuple[ str, int]")
    assert all(type_info is not None and type_info.slot is None for type_info in type_infos)


def test_typed_rest_name_slot_uses_the_final_argument_name() -> None:
    """Distinguish the parameter name from the same spelling inside its inline type."""
    structure = structure_for(":param value.Type value: Description.", settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    entry = structure.entries[0]
    (slot,) = entry.name_slots

    assert slot is not None
    assert slot.start_column == structure.lines[0].text.rfind("value")


@pytest.mark.parametrize(
    ("convention", "value"),
    [
        (DocstringConvention.GOOGLE, "Args:\n    value (\f((none)).\f): Description."),
        (DocstringConvention.NUMPY, "Returns\n-------\n\v((none)).\v\n    Description."),
        (DocstringConvention.REST, ":rtype: \f((none)).\f"),
    ],
)
def test_type_slots_preserve_suspicious_control_characters(convention: DocstringConvention, value: str) -> None:
    """Keep form feeds and vertical tabs inside semantic type text for PDF004."""
    structure = structure_for(value, settings=CheckSettings(docstring_convention=convention))
    type_info = structure.entries[0].type_info

    assert type_info is not None
    slot = type_info.slot
    assert slot is not None
    assert type_info.text in {"\f((none)).\f", "\v((none)).\v"}


@pytest.mark.parametrize(
    ("field", "expected_kind", "expected_names", "expected_type", "expected_description"),
    [
        (":rtype: Mapping[str, Sequence[int]]", DocstringEntryKind.RETURN, (), "Mapping[str, Sequence[int]]", "Mapping[str, Sequence[int]]"),
        (":ytype: Iterator[tuple[str, int | None]]", DocstringEntryKind.YIELD, (), "Iterator[tuple[str, int | None]]", "Iterator[tuple[str, int | None]]"),
        (":raises mypkg.errors.CustomError: Bad value.", DocstringEntryKind.EXCEPTION, ("mypkg.errors.CustomError",), None, "Bad value."),
    ],
)
def test_rest_return_yield_and_raise_fields_preserve_generic_looking_type_text(
    field: str, expected_kind: DocstringEntryKind, expected_names: tuple[str, ...], expected_type: str | None, expected_description: str
) -> None:
    structure = structure_for(field, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    entry = structure.entries[0]

    assert (entry.kind, entry.names, entry_type_text(entry), entry.description) == (expected_kind, expected_names, expected_type, expected_description)


@pytest.mark.parametrize(
    ("field_text", "expected_kind"),
    [
        (":param value:", DocstringEntryKind.PARAMETER),
        (":parameter value:", DocstringEntryKind.PARAMETER),
        (":arg value:", DocstringEntryKind.PARAMETER),
        (":argument value:", DocstringEntryKind.PARAMETER),
        (":key value:", DocstringEntryKind.PARAMETER),
        (":keyword value:", DocstringEntryKind.PARAMETER),
        (":kwarg value:", DocstringEntryKind.PARAMETER),
        (":return:", DocstringEntryKind.RETURN),
        (":returns:", DocstringEntryKind.RETURN),
        (":rtype:", DocstringEntryKind.RETURN),
        (":yield:", DocstringEntryKind.YIELD),
        (":yields:", DocstringEntryKind.YIELD),
        (":ytype:", DocstringEntryKind.YIELD),
        (":raise ValueError:", DocstringEntryKind.EXCEPTION),
        (":raises ValueError:", DocstringEntryKind.EXCEPTION),
        (":except ValueError:", DocstringEntryKind.EXCEPTION),
        (":exception ValueError:", DocstringEntryKind.EXCEPTION),
        (":custom:", DocstringEntryKind.FIELD),
    ],
)
def test_all_rest_field_aliases_are_classified(field_text: str, expected_kind: DocstringEntryKind) -> None:
    entry = structure_for(f"{field_text} Description.", settings=CheckSettings(docstring_convention=DocstringConvention.REST)).entries[0]
    assert entry.kind == expected_kind


@pytest.mark.parametrize(
    ("value", "expected_kind"),
    [
        (":param: Description.", ConventionEntryIssueKind.REST_MISSING_ARGUMENT),
        (":raises: Description.", ConventionEntryIssueKind.REST_MISSING_ARGUMENT),
        (":returns result: Description.", ConventionEntryIssueKind.REST_UNEXPECTED_ARGUMENT),
        (":rtype result: Description.", ConventionEntryIssueKind.REST_UNEXPECTED_ARGUMENT),
    ],
)
def test_invalid_rest_field_arity_remains_structural_but_not_semantic(value: str, expected_kind: ConventionEntryIssueKind) -> None:
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert not structure.entries
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.REST_FIELD, 0, 1),)
    assert tuple(issue.kind for issue in structure.convention_entry_issues) == (expected_kind,)


def test_rest_field_continuation_and_tabbed_prefix_have_exact_reflow_indentation() -> None:
    structure = structure_for("\n\t:param value: First line.\n\t\tSecond line.", settings=CheckSettings(docstring_convention=DocstringConvention.REST, indent_width=2))
    entry = structure.entries[0]
    region = structure.reflow_regions[0]
    assert entry.description == "First line. Second line."
    assert reflow_texts(region.lines) == ("First line.", "Second line.")
    assert region.initial_indent == "\t:param value: "
    assert region.subsequent_indent == " " * 16


def test_rest_field_stops_before_a_peer_list_item() -> None:
    value = ":param value: Description.\n- Peer list item."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))
    assert tuple((entry.names, entry.start_line, entry.end_line) for entry in structure.entries) == ((("value",), 0, 1),)
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.REST_FIELD, 0, 1), (DocstringBlockKind.LIST_ITEM, 1, 2))


def test_rest_field_includes_indented_protected_body_without_reflowing_it() -> None:
    value = ":param value:\n    - First choice.\n      Continued choice.\n    - Second choice.\n:returns: Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((("value",), "", 0, 4), ((), "Result.", 4, 5))
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.REST_FIELD, 0, 4), (DocstringBlockKind.REST_FIELD, 4, 5))
    assert tuple((region.kind, region.start_line, region.end_line, reflow_texts(region.lines)) for region in structure.reflow_regions) == ((DocstringBlockKind.REST_FIELD, 4, 5, ("Result.",)),)


def test_rest_field_inline_description_reflow_stops_before_protected_body() -> None:
    value = ":param value: Intro text.\n    - First choice.\n      Continued choice.\n    - Second choice.\n:returns: Result."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert tuple((entry.names, entry.description, entry.start_line, entry.end_line) for entry in structure.entries) == ((("value",), "Intro text.", 0, 4), ((), "Result.", 4, 5))
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.REST_FIELD, 0, 4), (DocstringBlockKind.REST_FIELD, 4, 5))
    assert tuple((region.kind, region.start_line, region.end_line, reflow_texts(region.lines)) for region in structure.reflow_regions) == (
        (DocstringBlockKind.REST_FIELD, 0, 1, ("Intro text.",)),
        (DocstringBlockKind.REST_FIELD, 4, 5, ("Result.",)),
    )


def test_rest_fields_are_not_semantic_inside_google_sections() -> None:
    value = "Examples:\n    :param value: Description.\n    - Peer list item."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert structure.entries == ()
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == ((DocstringBlockKind.SECTION_HEADER, 0, 1), (DocstringBlockKind.VERBATIM, 1, 3))


@pytest.mark.parametrize("convention", tuple(DocstringConvention))
def test_structure_records_the_explicit_docstring_convention(convention: DocstringConvention) -> None:
    assert structure_for("Summary.", settings=CheckSettings(docstring_convention=convention)).convention is convention


@pytest.mark.parametrize(
    ("value", "expected_ranges", "expected_regions"),
    [
        ("- first\n  continuation\n+ second\n* third", ((0, 2), (2, 3), (3, 4)), (("- ", "  "), ("+ ", "  "), ("* ", "  "))),
        ("1. first\n   continuation\n2) second", ((0, 2), (2, 3)), (("1. ", "   "), ("2) ", "   "))),
        ("\n\t- tabbed\n\t\tcontinuation", ((1, 3),), (("\t- ", " " * 6),)),
    ],
)
def test_list_markers_boundaries_and_reflow_prefixes(value: str, expected_ranges: tuple[tuple[int, int], ...], expected_regions: tuple[tuple[str, str], ...]) -> None:
    structure = structure_for(value)
    blocks = tuple(block for block in structure.blocks if block.kind == DocstringBlockKind.LIST_ITEM)
    regions = tuple(region for region in structure.reflow_regions if region.kind == DocstringBlockKind.LIST_ITEM)
    assert tuple((block.start_line, block.end_line) for block in blocks) == expected_ranges
    assert tuple((region.initial_indent, region.subsequent_indent) for region in regions) == expected_regions


def test_empty_list_item_is_classified_without_an_empty_reflow_region() -> None:
    structure = structure_for("- ")
    assert tuple(block.kind for block in structure.blocks) == (DocstringBlockKind.LIST_ITEM,)
    assert structure.reflow_regions == ()


def test_block_quote_depth_and_spacing_split_distinct_reflow_regions() -> None:
    structure = structure_for("> first\n> second\n>> nested\n>  differently spaced")
    assert tuple((block.start_line, block.end_line) for block in structure.blocks) == ((0, 2), (2, 3), (3, 4))
    assert tuple((reflow_texts(region.lines), region.initial_indent, region.subsequent_indent) for region in structure.reflow_regions) == (
        (("first", "second"), "> ", "> "),
        (("nested",), ">> ", ">> "),
        (("differently spaced",), ">  ", ">  "),
    )


@pytest.mark.parametrize(
    ("value", "expected_end"), [("```python\ncode\n```\nafter", 3), ("````\n```\nstill code\n`````\nafter", 4), ("~~~text\ncode\n```\nstill code\n~~~\nafter", 5), ("```\nunclosed", 2)]
)
def test_code_fences_require_compatible_closing_delimiters(value: str, expected_end: int) -> None:
    block = structure_for(value).blocks[0]
    assert (block.kind, block.start_line, block.end_line) == (DocstringBlockKind.CODE_FENCE, 0, expected_end)


def test_doctest_consumes_nonblank_transcript_but_stops_at_blank_line() -> None:
    structure = structure_for(">>> value = 1\n>>> value + 1\n2\n\nFollowing paragraph.")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == (
        (DocstringBlockKind.DOCTEST, 0, 3),
        (DocstringBlockKind.BLANK, 3, 4),
        (DocstringBlockKind.PARAGRAPH, 4, 5),
    )


@pytest.mark.parametrize("prompt", [">>>> quoted", ">>>>>>> branch"])
def test_doctest_prompt_requires_trailing_whitespace(prompt: str) -> None:
    structure = structure_for(f"{prompt}\nfollowing prose")
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.BLOCK_QUOTE, 0, 1), (DocstringBlockKind.PARAGRAPH, 1, 2))
    assert DocstringBlockKind.DOCTEST not in block_kinds(structure.blocks)


def test_directives_and_literal_blocks_include_blank_lines_and_indented_bodies() -> None:
    directive = structure_for(".. warning:: title\n\n    First body line.\n        Nested.\nAfter.")
    literal = structure_for("Example::\n\n    value = 1\n    print(value)\nAfter.")
    assert tuple((block.kind, block.start_line, block.end_line) for block in directive.blocks) == ((DocstringBlockKind.DIRECTIVE, 0, 4), (DocstringBlockKind.PARAGRAPH, 4, 5))
    assert tuple((block.kind, block.start_line, block.end_line) for block in literal.blocks) == ((DocstringBlockKind.LITERAL_BLOCK, 0, 4), (DocstringBlockKind.PARAGRAPH, 4, 5))


def test_malformed_directive_issues_include_blank_lines_and_indented_bodies() -> None:
    structure = structure_for(".. custom:\n\n    Body.\n        Nested.\nAfter.")

    assert structure.directive_issues == (PDF_definition.DirectiveIssue(name="custom", start_line=0),)
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.DIRECTIVE_ISSUE, 0, 4), (DocstringBlockKind.PARAGRAPH, 4, 5))


def test_disabling_directive_parsing_removes_malformed_directive_issues() -> None:
    structure = structure_for(".. py:function: signature", settings=CheckSettings(docstring_parse_directives=False))

    assert structure.directive_issues == ()
    assert DocstringBlockKind.DIRECTIVE_ISSUE not in block_kinds(structure.blocks)


def test_literal_block_detection_compares_visual_indentation_with_tabs() -> None:
    shallower_spaces = structure_for("\n\tExample::\n    Not nested.")
    deeper_tab = structure_for("\n    Example::\n\tNested.")
    assert DocstringBlockKind.LITERAL_BLOCK not in block_kinds(shallower_spaces.blocks)
    assert tuple((block.kind, block.start_line, block.end_line) for block in deeper_tab.blocks) == ((DocstringBlockKind.BLANK, 0, 1), (DocstringBlockKind.LITERAL_BLOCK, 1, 3))


@pytest.mark.parametrize(
    ("value", "expected_end"),
    [("| A | B |\n| :--- | ---: |\n| 1 | 2 |\nAfter", 3), ("+---+---+\n| A | B |\n+===+===+\n| 1 | 2 |\n+---+---+\nAfter", 5), ("=== ===\nA   B\n--- ---\n1   2\n\nAfter", 4)],
)
def test_markdown_and_rest_table_variants_are_protected(value: str, expected_end: int) -> None:
    block = structure_for(value).blocks[0]
    assert (block.kind, block.start_line, block.end_line) == (DocstringBlockKind.TABLE, 0, expected_end)


@pytest.mark.parametrize(
    ("value", "expected_end"), [("# ATX heading\nAfter", 1), ("### Deeper heading ###\nAfter", 1), ("Setext heading\n===============\nAfter", 2), ("reST heading\n~~~~~~~~~~~~\nAfter", 2)]
)
def test_markdown_and_rest_heading_variants_are_protected(value: str, expected_end: int) -> None:
    block = structure_for(value).blocks[0]
    assert (block.kind, block.start_line, block.end_line) == (DocstringBlockKind.HEADING, 0, expected_end)


@pytest.mark.parametrize(
    ("value", "unexpected_kind"),
    [
        ("#Not a heading", DocstringBlockKind.HEADING),
        ("| A | B |\n| -- | --- |", DocstringBlockKind.TABLE),
        (".. note: not a directive", DocstringBlockKind.DIRECTIVE),
        ("Example::\nnot indented", DocstringBlockKind.LITERAL_BLOCK),
        ("Example::", DocstringBlockKind.LITERAL_BLOCK),
        (":param missing terminator", DocstringBlockKind.REST_FIELD),
        ("-missing marker space", DocstringBlockKind.LIST_ITEM),
        ("ordinary > embedded quote", DocstringBlockKind.BLOCK_QUOTE),
    ],
)
def test_malformed_structures_are_not_overclassified(value: str, unexpected_kind: DocstringBlockKind) -> None:
    assert unexpected_kind not in block_kinds(structure_for(value).blocks)


def test_malformed_rest_field_without_terminal_colon_is_not_parsed() -> None:
    structure = structure_for(":param missing terminator", settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert not structure.entries
    assert DocstringBlockKind.REST_FIELD not in block_kinds(structure.blocks)


def test_generic_structures_are_classified_and_protected_inside_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Examples:\n        ```python\n        print(value)\n        ```\n\n    - A list item continued on\n      another line.\n    > A quoted line\n    > continued.\n    :param value: A Sphinx description\n        continued.\n    """\n'
    structure = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure
    kinds = block_kinds(structure.blocks)
    assert DocstringBlockKind.CODE_FENCE in kinds
    assert DocstringBlockKind.LIST_ITEM in kinds
    assert DocstringBlockKind.BLOCK_QUOTE in kinds
    assert DocstringBlockKind.REST_FIELD not in kinds
    assert tuple(region.kind for region in structure.reflow_regions) == (DocstringBlockKind.SUMMARY, DocstringBlockKind.LIST_ITEM, DocstringBlockKind.BLOCK_QUOTE, DocstringBlockKind.PARAGRAPH)


def test_directives_literal_blocks_and_tables_are_opaque_to_section_entry_parsing() -> None:
    value = "Examples:\n    .. note::\n        field: Directive body.\n\n    Literal::\n\n        field: Literal body.\n\n    | Name | Value |\n    | --- | --- |\n    | field | Table body |"
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert structure.entries == ()
    assert tuple((child.kind, child.start_line, child.end_line) for child in structure.blocks[0].children) == (
        (DocstringBlockKind.SECTION_HEADER, 0, 1),
        (DocstringBlockKind.DIRECTIVE, 1, 3),
        (DocstringBlockKind.BLANK, 3, 4),
        (DocstringBlockKind.LITERAL_BLOCK, 4, 7),
        (DocstringBlockKind.BLANK, 7, 8),
        (DocstringBlockKind.TABLE, 8, 11),
    )


@pytest.mark.parametrize(
    ("settings", "source", "kind"),
    [
        (CheckSettings(docstring_parse_list_items=False), "- item", DocstringBlockKind.LIST_ITEM),
        (CheckSettings(docstring_parse_headings=False), "# Heading", DocstringBlockKind.HEADING),
        (CheckSettings(docstring_parse_doctests=False), ">>> call()", DocstringBlockKind.DOCTEST),
        (CheckSettings(docstring_parse_code_fences=False), "```python\nvalue = 1\n```", DocstringBlockKind.CODE_FENCE),
        (CheckSettings(docstring_parse_block_quotes=False), "> quote", DocstringBlockKind.BLOCK_QUOTE),
        (CheckSettings(docstring_parse_tables=False), "| A | B |\n| --- | --- |\n| 1 | 2 |", DocstringBlockKind.TABLE),
        (CheckSettings(docstring_parse_directives=False), ".. note::\n    body", DocstringBlockKind.DIRECTIVE),
        (CheckSettings(docstring_parse_literal_blocks=False), "Example::\n\n    value = 1", DocstringBlockKind.LITERAL_BLOCK),
    ],
)
def test_structure_recognizers_can_be_disabled(settings: CheckSettings, source: str, kind: DocstringBlockKind) -> None:
    enabled = PDF.prepare(category_context(f'"""{source}"""\n')).docstrings[0].structure
    disabled = PDF.prepare(category_context(f'"""{source}"""\n', settings=settings)).docstrings[0].structure
    assert kind in block_kinds(enabled.blocks)
    assert kind not in block_kinds(disabled.blocks)


def test_rest_field_recognition_is_controlled_by_docstring_convention() -> None:
    source = '""":param value: description"""\n'
    rest = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.REST))).docstrings[0].structure
    google = PDF.prepare(category_context(source, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))).docstrings[0].structure

    assert DocstringBlockKind.REST_FIELD in block_kinds(rest.blocks)
    assert rest.entries[0].names == ("value",)
    assert DocstringBlockKind.REST_FIELD not in block_kinds(google.blocks)
    assert google.entries == ()


def test_rest_field_metadata_preserves_field_names_and_arguments_for_rule_helpers() -> None:
    value = ":PARAM int value: Description.\n:type value: int\n:meta private: yes\n:raises errors.ValueError: Bad value."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.REST))

    assert tuple((entry.field_name, entry.field_argument, entry.names, entry_type_text(entry), entry.description) for entry in structure.entries) == (
        ("param", "int value", ("value",), "int", "Description."),
        ("type", "value", ("value",), "int", "int"),
        ("meta", "private", ("private",), None, "yes"),
        ("raises", "errors.ValueError", ("errors.ValueError",), None, "Bad value."),
    )


def test_disabling_directives_falls_back_to_literal_blocks_before_plain_text() -> None:
    value = ".. note::\n\n    Body."
    directive = structure_for(value)
    literal = structure_for(value, settings=CheckSettings(docstring_parse_directives=False))
    plain = structure_for(value, settings=CheckSettings(docstring_parse_directives=False, docstring_parse_literal_blocks=False))
    assert tuple(block.kind for block in directive.blocks) == (DocstringBlockKind.DIRECTIVE,)
    assert tuple(block.kind for block in literal.blocks) == (DocstringBlockKind.LITERAL_BLOCK,)
    assert tuple(block.kind for block in plain.blocks) == (DocstringBlockKind.COLON_HEADER, DocstringBlockKind.BLANK, DocstringBlockKind.VERBATIM)


def test_disabling_all_generic_recognizers_produces_one_plain_reflow_region() -> None:
    settings = CheckSettings(
        docstring_parse_list_items=False,
        docstring_parse_headings=False,
        docstring_parse_doctests=False,
        docstring_parse_code_fences=False,
        docstring_parse_block_quotes=False,
        docstring_parse_tables=False,
        docstring_parse_directives=False,
        docstring_parse_literal_blocks=False,
    )
    value = "# Heading\n>>> call()\n- item\n> quote\n:param value: description"
    structure = structure_for(value, settings=settings)
    assert tuple((block.kind, block.start_line, block.end_line) for block in structure.blocks) == ((DocstringBlockKind.SUMMARY, 0, 5),)
    assert structure.entries == ()
    assert tuple((region.kind, reflow_texts(region.lines)) for region in structure.reflow_regions) == ((DocstringBlockKind.SUMMARY, tuple(value.splitlines())),)


def test_convention_sections_remain_enabled_when_all_generic_recognizers_are_disabled() -> None:
    settings = CheckSettings(
        docstring_convention=DocstringConvention.GOOGLE,
        docstring_parse_list_items=False,
        docstring_parse_headings=False,
        docstring_parse_doctests=False,
        docstring_parse_code_fences=False,
        docstring_parse_block_quotes=False,
        docstring_parse_tables=False,
        docstring_parse_directives=False,
        docstring_parse_literal_blocks=False,
    )
    structure = structure_for("Args:\n    value: Description.", settings=settings)
    assert tuple(section.name for section in structure.sections) == ("Args",)
    assert tuple((entry.kind, entry.names, entry.description) for entry in structure.entries) == ((DocstringEntryKind.PARAMETER, ("value",), "Description."),)


def test_code_fence_setting_controls_whether_fenced_section_syntax_is_opaque() -> None:
    value = "Args:\n```text\nReturns:\n    fake: Fake result.\n```\nReturns:\n    str: Real result."
    enabled = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    disabled = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE, docstring_parse_code_fences=False))
    assert tuple(section.name for section in enabled.sections) == ("Args", "Returns")
    assert tuple(section.name for section in disabled.sections) == ("Args", "Returns", "Returns")


def test_indent_width_changes_generated_tab_prefix_width_without_changing_semantics() -> None:
    value = "\n\t- First line.\n\t\tContinuation."
    narrow = structure_for(value, settings=CheckSettings(indent_width=2))
    wide = structure_for(value, settings=CheckSettings(indent_width=8))
    assert narrow.blocks == wide.blocks
    assert narrow.entries == wide.entries
    assert narrow.reflow_regions[0].initial_indent == wide.reflow_regions[0].initial_indent == "\t- "
    assert narrow.reflow_regions[0].subsequent_indent == " " * 4
    assert wide.reflow_regions[0].subsequent_indent == " " * 10


def test_complex_mixed_structure_partitions_lines_and_orders_semantic_regions() -> None:
    value = "Summary first line.\nsummary second line.\n\nArgs:\n    value: Description.\n        - Choice one.\n        - Choice two.\n    other: Other description.\n    :param rst_field: Field description.\n\n    ```text\n    Returns:\n        fake: code\n    ```\n\nReturns:\n    tuple[str, int]: Result.\n\nTrailing section prose."
    structure = structure_for(value, settings=CheckSettings(docstring_convention=DocstringConvention.GOOGLE))
    assert_block_partition(structure.blocks, 0, len(structure.lines))
    assert tuple(section.start_line for section in structure.sections) == tuple(sorted(section.start_line for section in structure.sections))
    assert tuple(entry.start_line for entry in structure.entries) == tuple(sorted(entry.start_line for entry in structure.entries))
    assert tuple(region.start_line for region in structure.reflow_regions) == tuple(sorted(region.start_line for region in structure.reflow_regions))
    assert all(0 <= region.start_offset <= region.end_offset <= len(value) for region in structure.reflow_regions)
    assert all(structure.lines[region.start_line].start_offset == region.start_offset for region in structure.reflow_regions)
    assert all(structure.lines[region.end_line - 1].end_offset == region.end_offset for region in structure.reflow_regions)
    assert tuple(section.name for section in structure.sections) == ("Args", "Returns")
    assert tuple((entry.names, entry_type_text(entry)) for entry in structure.entries) == ((("value",), None), (("other",), None), ((), "tuple[str, int]"))
