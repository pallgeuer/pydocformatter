from __future__ import annotations


def is_non_imperative(word: str) -> bool:
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
