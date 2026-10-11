"""Ruby scanner.

Recognises:

* ``ENV["KEY"]``            -> optional; returns ``nil`` when unset
* ``ENV["KEY"] || "d"``     -> optional with default
* ``ENV.fetch("KEY")``      -> required; raises ``KeyError`` when missing
* ``ENV.fetch("KEY", "d")`` -> optional with default
* ``ENV.key?("KEY")`` / ``ENV["KEY"] =`` -> presence/write
"""

from __future__ import annotations

import re
from pathlib import Path

from conflint.models import Language, Location, Usage
from conflint.scanners.base import Scanner

__all__ = ["RubyScanner"]

_RE_FETCH = re.compile(r"\bENV\.fetch\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*(?P<rest>[\),])")
_RE_SUBSCRIPT = re.compile(r"\bENV\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]")
_RE_KEY = re.compile(
    r"\bENV\.(?:key\?|include\?|has_key\?|fetch)\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
)
_RE_FALLBACK = re.compile(r"\s*\|\|\s*(?P<default>'[^']*'|\"[^\"]*\")")


class RubyScanner(Scanner):
    """Static scanner for ``.rb`` files."""

    name = "ruby"
    language = Language.RUBY
    extensions = (".rb",)

    def scan(self, path: Path, text: str) -> list[Usage]:
        usages: list[Usage] = []

        for match in _RE_FETCH.finditer(text):
            name = match.group(1)
            has_default = match.group("rest") == ","
            default = None
            if has_default:
                tail = text[match.end() : match.end() + 40]
                dmatch = re.match(r"\s*(['\"][^'\"]*['\"])", tail)
                default = dmatch.group(1)[1:-1] if dmatch else "<dynamic>"
            usages.append(
                Usage(
                    name=name,
                    location=Location(path, self.line_of(text, match.start())),
                    language=Language.RUBY,
                    read_via="ENV.fetch",
                    required=not has_default,
                    has_default=has_default,
                    default=default,
                )
            )

        for match in _RE_SUBSCRIPT.finditer(text):
            default, has_default = self._inline_default(text, match.end())
            usages.append(
                Usage(
                    name=match.group(1),
                    location=Location(path, self.line_of(text, match.start())),
                    language=Language.RUBY,
                    read_via="ENV[]",
                    required=False,
                    has_default=has_default,
                    default=default,
                )
            )

        return usages

    def _inline_default(self, text: str, end: int) -> tuple[str | None, bool]:
        match = _RE_FALLBACK.match(text[end : end + 40])
        if not match:
            return None, False
        return match.group("default")[1:-1], True
