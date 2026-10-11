"""Reporter base class.

A reporter turns a :class:`~conflint.models.Report` into a string (rendered) and
optionally writes it somewhere (stdout, a file).  Rendering must be pure so
every format can be unit-tested against a fixed string.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TextIO

from conflint.config import Settings
from conflint.models import Report

__all__ = ["Reporter"]


class Reporter(ABC):
    """Base class for output formats."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def render(self, report: Report, settings: Settings) -> str:
        """Render the report as a string (never writes to stdout)."""

    def write(self, report: Report, settings: Settings, stream: TextIO) -> None:
        stream.write(self.render(report, settings))
        stream.flush()
