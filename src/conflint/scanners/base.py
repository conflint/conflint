"""Scanner base class.

A scanner turns one source file into zero or more :class:`Usage` objects.  It
never touches the filesystem itself — the engine reads the file and hands over
``(path, text)`` — which keeps scanners trivial to unit test.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from conflint.models import Language, Usage

__all__ = ["Scanner"]


class Scanner(ABC):
    """Static analyser for a family of source files."""

    #: Human readable name, also used by the ``scanners`` config key.
    name: str = "base"
    #: The language reported on emitted usages.
    language: Language = Language.GENERIC
    #: Lower-case file extensions handled by this scanner (including the dot).
    extensions: tuple[str, ...] = ()

    def handles(self, path: Path) -> bool:
        """Whether this scanner should process ``path``."""

        return path.suffix.lower() in self.extensions

    @abstractmethod
    def scan(self, path: Path, text: str) -> list[Usage]:
        """Extract usages from ``text`` belonging to ``path``."""

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def line_of(text: str, offset: int) -> int:
        """1-based line number for a character ``offset`` in ``text``."""

        return text.count("\n", 0, offset) + 1

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<{type(self).__name__} name={self.name!r}>"

    def supported_extensions(self) -> Sequence[str]:
        return self.extensions
