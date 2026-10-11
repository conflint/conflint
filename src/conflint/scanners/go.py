"""Go scanner.

Recognises the ``os`` package configuration idioms:

* ``os.Getenv("KEY")``   -> optional; returns ``""`` when unset
* ``os.LookupEnv("KEY")`` -> optional; the ``ok`` result signals presence
* ``os.Setenv("KEY", v)`` -> records a written/default value
* ``os.Unsetenv("KEY")``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from conflint.models import Language, Location, Usage
from conflint.scanners.base import Scanner

__all__ = ["GoScanner"]

_RE_CALL = re.compile(
    r"\bos\.(Getenv|LookupEnv|Setenv|Unsetenv)\(\s*\"([A-Za-z_][A-Za-z0-9_]*)\""
)


class GoScanner(Scanner):
    """Static scanner for ``.go`` files."""

    name = "go"
    language = Language.GO
    extensions = (".go",)

    def scan(self, path: Path, text: str) -> List[Usage]:
        usages: List[Usage] = []
        for match in _RE_CALL.finditer(text):
            func, name = match.group(1), match.group(2)
            notes = ()
            required = False
            if func == "LookupEnv":
                notes = ("presence-checked",)
            elif func in {"Setenv", "Unsetenv"}:
                notes = ("write",)
            usages.append(
                Usage(
                    name=name,
                    location=Location(path, self.line_of(text, match.start())),
                    language=Language.GO,
                    read_via=f"os.{func}",
                    required=required,
                    has_default=False,
                    default=None,
                    notes=notes,
                )
            )
        return usages
