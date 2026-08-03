"""Shared documentation-order comparison."""

# Future imports
from __future__ import annotations

# Standard library imports
from collections.abc import Callable, Iterable
from typing import TypeVar


_DocumentedItemT = TypeVar("_DocumentedItemT")
_IssueT = TypeVar("_IssueT")
_OrderedItemT = TypeVar("_OrderedItemT")


def order_issues(
    ordered_items: Iterable[_OrderedItemT],
    documented_items: Iterable[_DocumentedItemT],
    *,
    ordered_key: Callable[[_OrderedItemT], str],
    documented_key: Callable[[_DocumentedItemT], str],
    issue_factory: Callable[[_DocumentedItemT, _OrderedItemT, _OrderedItemT], _IssueT],
) -> tuple[_IssueT, ...]:
    """Return documented items that do not follow the canonical order.

    Args:
        ordered_items (Iterable[_OrderedItemT]): Canonically ordered items available for documentation matching.
        documented_items (Iterable[_DocumentedItemT]): Documented items in their parsed order.
        ordered_key (Callable[[_OrderedItemT], str]): String key used to index canonical items.
        documented_key (Callable[[_DocumentedItemT], str]): String key used to match documented items.
        issue_factory (Callable[[_DocumentedItemT, _OrderedItemT, _OrderedItemT], _IssueT]): Constructor receiving the
            late documented item, its canonical item, and the highest-ranked canonical item documented earlier.

    Returns:
        tuple[_IssueT, ...]: Issues for late first occurrences of known documented items.
    """
    ordered_by_key = {ordered_key(item): (rank, item) for rank, item in enumerate(ordered_items)}
    seen_keys: set[str] = set()
    greatest_rank_and_item: tuple[int, _OrderedItemT] | None = None
    issues: list[_IssueT] = []
    for documented_item in documented_items:
        key = documented_key(documented_item)
        ranked_item = ordered_by_key.get(key)
        if ranked_item is None or key in seen_keys:
            continue
        seen_keys.add(key)
        rank, ordered_item = ranked_item
        if greatest_rank_and_item is not None and rank < greatest_rank_and_item[0]:
            issues.append(issue_factory(documented_item, ordered_item, greatest_rank_and_item[1]))
            continue
        greatest_rank_and_item = (rank, ordered_item)
    return tuple(issues)
