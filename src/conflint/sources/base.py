"""Configuration source base class.

A *source* knows how to find and parse one kind of configuration storage:
``.env`` files, Docker Compose, GitHub Actions, Kubernetes manifests, Terraform.

Sources only produce :class:`Entry` objects — definitions of values.  Whether a
definition is an "example/template" is decided centrally by the engine (based on
the file name) so sources never need to special-case it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from conflint.models import Entry

__all__ = ["ConfigSource", "find_line"]


def find_line(text: str, needle: str, *, start: int = 0) -> int:
    """Return the 1-based line of the first occurrence of ``needle`` after ``start``.

    Used to attach approximate line numbers to values extracted from YAML/HCL
    where the parsed structure has already lost positional information.
    """

    index = text.find(needle, start)
    if index < 0:
        return 0
    return text.count("\n", 0, index) + 1


class ConfigSource(ABC):
    """Base class for configuration sources."""

    #: Stable identifier used by the ``sources`` config key and in reports.
    name: str = "base"
    #: Glob patterns (relative to the project root) used by discovery to locate
    #: candidate files.  These intentionally bypass ``.gitignore``.
    config_globs: tuple[str, ...] = ()

    def matches(self, path: Path) -> bool:
        """Whether this source is responsible for parsing ``path``."""

        return False

    @abstractmethod
    def parse(self, path: Path, text: str) -> list[Entry]:
        """Parse ``text`` into entries.  Must never raise on malformed input."""

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _norm_name(path: Path) -> str:
        return path.name.lower()

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<{type(self).__name__} name={self.name!r}>"

    @staticmethod
    def is_yaml(path: Path) -> bool:
        return path.suffix.lower() in {".yml", ".yaml"}

    def candidate_globs(self) -> Sequence[str]:
        return self.config_globs
