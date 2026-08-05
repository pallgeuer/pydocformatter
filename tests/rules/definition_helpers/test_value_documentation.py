# Standard library imports
import itertools

# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import value_documentation
from pydocformatter.rules.definitions.PDF.PDF import ExceptionOccurrence, ExceptionOccurrenceOrigin


_NAMES = ("Error", "first.Error", "second.Error", "TypeError")


def exception_occurrences(names: tuple[str, ...]) -> tuple[ExceptionOccurrence, ...]:
    """Return source-ordered raise occurrences for exception names."""
    return tuple(ExceptionOccurrence(name=name, line_numbers=(index + 1,), origin=ExceptionOccurrenceOrigin.RAISE) for index, name in enumerate(names))


def documented_entries(names: tuple[str | None, ...]) -> tuple[value_documentation.DocumentedEntry, ...]:
    """Return source-ordered documented entries for exception names."""
    return tuple(value_documentation.DocumentedEntry(name=name, line_numbers=(index + 1,), has_content=True, has_value_entry=True) for index, name in enumerate(names))


@pytest.mark.parametrize("query", _NAMES)
def test_exception_name_index_matches_pairwise_semantics(query: str) -> None:
    for size in range(4):
        for indexed_names in itertools.product(_NAMES, repeat=size):
            index = value_documentation._ExceptionNameIndex(indexed_names)

            assert index.matches(query) is any(value_documentation.exception_names_match(query, indexed_name) for indexed_name in indexed_names)


def test_missing_exception_occurrences_match_reference_pairwise_algorithm_exhaustively() -> None:
    documented_name_groups = [names for size in range(3) for names in itertools.product(_NAMES, repeat=size)]
    for occurrence_size in range(5):
        for occurrence_names in itertools.product(_NAMES, repeat=occurrence_size):
            occurrences = exception_occurrences(occurrence_names)
            for names in documented_name_groups:
                seen_names: list[str] = []
                expected: list[ExceptionOccurrence] = []
                for occurrence in occurrences:
                    if any(value_documentation.exception_names_match(occurrence.name, seen_name) for seen_name in seen_names):
                        continue
                    seen_names.append(occurrence.name)
                    if not any(value_documentation.exception_names_match(occurrence.name, documented_name) for documented_name in names):
                        expected.append(occurrence)

                assert value_documentation.missing_exception_occurrences(occurrences, names) == tuple(expected)


def test_extraneous_exception_entries_match_reference_pairwise_algorithm_exhaustively() -> None:
    documented_name_groups = [names for size in range(4) for names in itertools.product((*_NAMES, None), repeat=size)]
    for occurrence_size in range(4):
        for occurrence_names in itertools.product(_NAMES, repeat=occurrence_size):
            occurrences = exception_occurrences(occurrence_names)
            for names in documented_name_groups:
                entries = documented_entries(names)
                expected = tuple(entry for entry in entries if entry.name is not None and not any(value_documentation.exception_names_match(occurrence.name, entry.name) for occurrence in occurrences))

                assert value_documentation.extraneous_exception_entries(entries, occurrences) == expected


def test_small_missing_exception_inventory_avoids_index_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    occurrences = exception_occurrences(("Error", "TypeError"))
    monkeypatch.setattr(value_documentation, "_ExceptionNameIndex", pytest.fail)

    assert value_documentation.missing_exception_occurrences(occurrences, ("Error",)) == (occurrences[1],)


def test_large_missing_exception_inventory_avoids_pairwise_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    occurrences = exception_occurrences(_NAMES)
    monkeypatch.setattr(value_documentation, "exception_names_match", pytest.fail)

    assert value_documentation.missing_exception_occurrences(occurrences, _NAMES) == ()


def test_eight_comparison_extraneous_inventory_avoids_index_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = documented_entries(_NAMES)
    monkeypatch.setattr(value_documentation, "_ExceptionNameIndex", pytest.fail)

    assert value_documentation.extraneous_exception_entries(entries, exception_occurrences(("first.Error", "TypeError"))) == (entries[2],)


def test_nine_comparison_extraneous_inventory_avoids_pairwise_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = documented_entries(("first.Error", "third.Error", "TypeError"))
    monkeypatch.setattr(value_documentation, "exception_names_match", pytest.fail)

    assert value_documentation.extraneous_exception_entries(entries, exception_occurrences(("first.Error", "second.Error", "ValueError"))) == entries[1:]
