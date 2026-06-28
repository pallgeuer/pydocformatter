"""PDF302 non-imperative-summary rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.decorators as decorator_helpers
import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF302NonImperativeSummary(RuleBase):
    """Rule implementation for PDF302.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF302"),
        name="non-imperative-summary",
        message="Docstring summary should be in imperative mood",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for function summaries that are not imperative."""
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for target in data.summary_line_targets:
            owner = target.docstring.owner
            if not isinstance(owner, PDF_definition.DefinitionInfo) or owner.kind is not PDF_definition.DefinitionKind.FUNCTION or _is_test_function(owner) or _is_property_function(owner):
                continue
            word = summary_style.first_word_target(target)
            if word is None:
                continue
            normalized = summary_style.normalize_word(word.word)
            if normalized and _is_non_imperative(normalized):
                violations.append(rule_violations.diagnostic(cls.meta, summary_style.line_numbers(word), instance_message=f"Docstring summary first word '{word.word}' is not imperative"))
        return tuple(violations)


def _is_non_imperative(word: str) -> bool:
    """Return whether a normalized first word is known to be non-imperative."""
    return word in _BLACKLISTED_WORDS or word in _NON_IMPERATIVE_FORMS


def _third_person_forms(word: str) -> tuple[str, ...]:
    """Return common third-person singular forms for an imperative verb."""
    irregular = _IRREGULAR_THIRD_PERSON_FORMS.get(word)
    if irregular is not None:
        return irregular
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return (f"{word[:-1]}ies",)
    if word.endswith(("s", "x", "z", "ch", "sh", "o")):
        return (f"{word}es",)
    return (f"{word}s",)


def _is_test_function(definition: PDF_definition.DefinitionInfo) -> bool:
    """Return whether a function docstring belongs to a test-style function."""
    name = definition.name
    return name == "runTest" or name.startswith("test")


def _is_property_function(definition: PDF_definition.DefinitionInfo) -> bool:
    """Return whether a function docstring belongs to a property-like function."""
    return any((decorator_name := decorator_helpers.decorator_qualified_name(decorator.decorator)) is not None and _is_property_decorator_name(decorator_name) for decorator in definition.decorators)


def _is_property_decorator_name(decorator_name: str) -> bool:
    """Return whether a decorator name identifies a property-like decorator."""
    parent, _, accessor = decorator_name.rpartition(".")
    return decorator_name in _PROPERTY_DECORATORS or (bool(parent) and accessor in _PROPERTY_ACCESSOR_DECORATOR_NAMES)


_PROPERTY_DECORATORS = {
    "property",
    "builtins.property",
    "enum.property",
    "functools.cached_property",
    "abc.abstractproperty",
    "types.DynamicClassAttribute",
}
_PROPERTY_ACCESSOR_DECORATOR_NAMES = {"getter", "setter", "deleter"}
_IRREGULAR_THIRD_PERSON_FORMS = {
    "do": ("does",),
    "go": ("goes",),
    "have": ("has",),
}
_IMPERATIVE_WORDS = frozenset("""
accept access add adjust aggregate allow append apply archive assert assign attempt authenticate authorize break build cache calculate call cancel capture change check clean clear close collect combine commit compare compute configure confirm connect construct control convert copy count create customize declare decode decorate define delegate delete deprecate derive describe detect determine display do download drop dump emit empty enable encapsulate encode end ensure enumerate establish evaluate examine execute exit expand expect export extend extract feed fetch fill filter finalize find fire fix flag force format forward generate get give go group handle have help hold identify implement import indicate init initialise initialize initiate input insert instantiate intercept invoke iterate join keep launch list listen load log look make manage manipulate map mark match merge mock modify monitor move normalize note obtain open output override overwrite package pad parse partial pass perform persist pick plot poll populate post prepare print process produce provide publish pull put query raise read record refer refresh register reload remove rename render replace reply report represent request require reset resolve retrieve return roll rollback round run sample save scan search select send serialise serialize serve set show simulate source specify split start step stop store strip submit subscribe sum swap sync synchronise synchronize take tear test time transform translate transmit truncate try turn tweak update upload use validate verify view wait walk wrap write yield
""".split())
_BLACKLISTED_WORDS = frozenset("""
a an the action always api base basic business calculation callback collection common constructor convenience convenient current currently custom data default deprecated description dict dictionary dummy example factory false final formula function generic handler helper here hook implementation importantly internal it main method module new number optional placeholder reference result same schema setup should simple some special sql standard static string subclasses that these this true unique unit utility what wrapper
""".split())
_NON_IMPERATIVE_FORMS = frozenset(form for word in _IMPERATIVE_WORDS for form in _third_person_forms(word) if form not in _IMPERATIVE_WORDS)
