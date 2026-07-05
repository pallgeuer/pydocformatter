import libcst as cst

import pydocformatter.rules.definition_helpers.decorators as decorators


def test_decorator_qualified_name_unwraps_calls_and_attributes() -> None:
    assert decorators.decorator_qualified_name(cst.parse_expression("package.decorator()")) == "package.decorator"
    assert decorators.decorator_qualified_name(cst.parse_expression("package.decorator.extra")) == "package.decorator.extra"
    assert decorators.decorator_qualified_name(cst.parse_expression("decorator")) == "decorator"


def test_decorator_qualified_name_returns_none_for_dynamic_expression() -> None:
    assert decorators.decorator_qualified_name(cst.parse_expression("factory().decorator")) is None
    assert decorators.decorator_qualified_name(cst.parse_expression("typing().overload")) is None
    assert decorators.decorator_qualified_name(cst.parse_expression("factory()[0]")) is None


def test_is_property_accessor_decorator_name_requires_parent_and_accessor_suffix() -> None:
    assert decorators.is_property_accessor_decorator_name("value.getter")
    assert decorators.is_property_accessor_decorator_name("value.setter")
    assert decorators.is_property_accessor_decorator_name("value.deleter")
    assert not decorators.is_property_accessor_decorator_name("getter")
    assert not decorators.is_property_accessor_decorator_name("project.property")
    assert not decorators.is_property_accessor_decorator_name("project.Property.extra")
