from __future__ import annotations

import functools
import operator
import os
from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast, overload

_R_co = TypeVar("_R_co", covariant=True)


class classproperty(Generic[_R_co]):
    """A descriptor that computes a read-only value from the owning class.

    Instance assignment/deletion is blocked. Class-level assignment/deletion can still replace/remove the descriptor
    unless the metaclass prevents it.
    """

    fget: Callable[[type[Any]], _R_co]
    __isabstractmethod__: bool

    def __init__(self, fget: Callable[[type[Any]], _R_co]) -> None:
        self.fget = fget
        functools.update_wrapper(cast(Callable[..., Any], self), fget)
        self.__isabstractmethod__ = getattr(fget, "__isabstractmethod__", False)

    @overload
    def __get__(self, obj: None, owner: type[Any]) -> _R_co: ...

    @overload
    def __get__(self, obj: object, owner: type[Any] | None = None) -> _R_co: ...

    def __get__(self, obj: object | None, owner: type[Any] | None = None) -> _R_co:
        if owner is None:
            if obj is None:
                raise TypeError("classproperty.__get__(None, None) is invalid")
            owner = type(obj)
        return self.fget(owner)

    def __set__(self, obj: Any, value: Any) -> None:
        name = getattr(self, "__name__", type(self).__name__)
        raise AttributeError(f"Cannot set read-only classproperty {name!r}")

    def __delete__(self, obj: Any) -> None:
        name = getattr(self, "__name__", type(self).__name__)
        raise AttributeError(f"Cannot delete read-only classproperty {name!r}")

    def __repr__(self) -> str:
        return f"<classproperty {self.fget!r}>"


def alias_to_class_field(field_path: str) -> classproperty[Any]:
    """Create a classproperty that delegates to a nested field path."""
    return classproperty(operator.attrgetter(field_path))


def auto_plural(count: int, word: str) -> str:
    """Return a singular or plural word for a count.

    Args:
        count (int): Count that determines whether the singular form should be used.
        word (str): Singular word to pluralize by appending `s`.

    Returns:
        str: `word` when count is one, otherwise `word` with a trailing `s`.
    """
    return word if count == 1 else f"{word}s"


def find_git_root_for_path(path: str, root_cache: dict[str, str | None] | None = None) -> str | None:
    """Find and optionally cache the nearest containing Git root for a path."""
    absolute_path = os.path.abspath(path)
    start_dir = absolute_path if os.path.isdir(absolute_path) else os.path.dirname(absolute_path)
    if root_cache is not None and start_dir in root_cache:
        return root_cache[start_dir]

    visited_dirs: list[str] = []
    current_dir = os.path.abspath(start_dir)
    while True:
        if root_cache is not None and current_dir in root_cache:
            git_root = root_cache[current_dir]
            for visited_dir in visited_dirs:
                root_cache[visited_dir] = git_root
            return git_root

        visited_dirs.append(current_dir)
        git_marker = os.path.join(current_dir, ".git")
        if _is_valid_git_marker(git_marker):
            if root_cache is not None:
                for visited_dir in visited_dirs:
                    root_cache[visited_dir] = current_dir
            return current_dir

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            if root_cache is not None:
                for visited_dir in visited_dirs:
                    root_cache[visited_dir] = None
            return None
        current_dir = parent_dir


def _is_valid_git_marker(path: str) -> bool:
    """Return whether a .git path looks like a worktree marker."""
    if os.path.isfile(path):
        return True
    elif not os.path.isdir(path):
        return False
    else:
        return os.path.exists(os.path.join(path, "HEAD"))


def format_line_ranges(line_numbers: list[int]) -> str:
    """Format sorted line numbers as compressed ranges.

    Args:
        line_numbers (list[int]): Sorted 1-based line numbers to compress.

    Returns:
        str: Comma-separated line ranges, such as `1-3, 7, 9-10`, or an empty string for no lines.
    """
    if not line_numbers:
        return ""

    ranges: list[str] = []
    start = line_numbers[0]
    end = line_numbers[0]

    for current in line_numbers[1:]:
        if current == end + 1:
            end = current
            continue
        ranges.append(f"{start}-{end}" if start != end else str(start))
        start = current
        end = current

    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ", ".join(ranges)
