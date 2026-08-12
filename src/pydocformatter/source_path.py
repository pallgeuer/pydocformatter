"""Precomputed source-path semantics shared by rules and caching."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import pathlib
import dataclasses


@dataclasses.dataclass(frozen=True)
class SourcePathContext:
    """Path spelling, physical target, package ancestry, and visibility for one source.

    Attributes:
        lexical_path (str): Normalized absolute lexical path before resolving symlinks.
        resolved_path (str): Normalized absolute real path after resolving symlinks where possible.
        module_parts (tuple[str, ...]): Ordered package and module name parts under current package-discovery semantics.
        package_parts (tuple[str, ...]): Ordered contiguous package-directory parts.
        filename_stem (str): Stem of the display-path filename.
        package_initializer (bool): Whether the display path names `__init__` source.
        existing (bool): Whether the display path existed when the context was constructed.
        public (bool): Whether every derived module path part is public.
    """

    lexical_path: str
    resolved_path: str
    module_parts: tuple[str, ...]
    package_parts: tuple[str, ...]
    filename_stem: str
    package_initializer: bool
    existing: bool
    public: bool

    @classmethod
    def for_path(cls, path: str) -> SourcePathContext:
        """Build path semantics through an ephemeral invocation-local builder.

        Args:
            path (str): Display path used for formatting and diagnostics.

        Returns:
            SourcePathContext: Stable source-path snapshot for rule execution and fingerprinting.
        """
        return SourcePathContextBuilder().for_path(path)


class SourcePathContextBuilder:
    """Build source-path contexts with invocation-local package-ancestry reuse."""

    def __init__(self) -> None:
        """Initialize an empty resolved-directory ancestry snapshot."""
        self._package_parts: dict[str, tuple[str, ...]] = {}

    def for_path(self, path: str) -> SourcePathContext:
        """Build path semantics while reusing observed physical package ancestry.

        Args:
            path (str): Display path used for formatting and diagnostics.

        Returns:
            SourcePathContext: Stable source-path snapshot for rule execution and fingerprinting.
        """
        pure_path = pathlib.PurePath(path)
        filename_stem = pure_path.stem
        package_initializer = filename_stem == "__init__"
        existing = os.path.exists(path)
        lexical_path = os.path.normcase(os.path.abspath(os.path.normpath(path)))
        resolved_physical_path = os.path.realpath(path)
        resolved_path = os.path.normcase(resolved_physical_path)

        if existing:
            package_parts = self._existing_package_parts(os.path.dirname(resolved_physical_path))
            module_parts = package_parts if package_initializer else (*package_parts, filename_stem)
        else:
            module_parts = _synthetic_module_path_parts(path)
            package_parts = module_parts if package_initializer else module_parts[:-1]

        return SourcePathContext(
            lexical_path=lexical_path,
            resolved_path=resolved_path,
            module_parts=module_parts,
            package_parts=package_parts,
            filename_stem=filename_stem,
            package_initializer=package_initializer,
            existing=existing,
            public=not any(part.startswith("_") for part in module_parts),
        )

    def _existing_package_parts(self, resolved_parent: str) -> tuple[str, ...]:
        """Return package parts using the first observation of each resolved directory."""
        requested_key = os.path.normcase(os.path.normpath(resolved_parent))
        if requested_key in self._package_parts:
            return self._package_parts[requested_key]

        pending: list[tuple[str, str]] = []
        current = resolved_parent
        while True:
            key = os.path.normcase(os.path.normpath(current))
            if key in self._package_parts:
                parts = self._package_parts[key]
                break
            parent = os.path.dirname(current)
            if parent == current:
                parts = ()
                self._package_parts[key] = parts
                break
            if not _package_initializer_exists(current):
                parts = ()
                self._package_parts[key] = parts
                break
            pending.append((key, current))
            current = parent

        for key, directory in reversed(pending):
            parts = (*parts, pathlib.Path(directory).name)
            self._package_parts[key] = parts
        return self._package_parts[requested_key]


def _package_initializer_exists(directory: str) -> bool:
    """Return whether a resolved directory contains a recognized package marker."""
    parent = pathlib.Path(directory)
    return (parent / "__init__.py").exists() or (parent / "__init__.pyi").exists()


def _synthetic_module_path_parts(path: str) -> tuple[str, ...]:
    """Return module parts for a display path that does not exist."""
    pure_path = pathlib.PurePath(path)
    path_parts = tuple(part for part in pure_path.parts if part not in {"", ".", "..", pure_path.anchor})
    module_parts: list[str] = []
    for index, part in enumerate(path_parts):
        if index == len(path_parts) - 1:
            stem = pathlib.PurePath(part).stem
            if stem != "__init__":
                module_parts.append(stem)
        else:
            module_parts.append(part)
    return tuple(module_parts)
