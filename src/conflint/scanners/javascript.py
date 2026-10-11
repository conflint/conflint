"""JavaScript / TypeScript scanner.

Full JS/TS parsing would pull in a heavy parser (or shell out to Node), which
would hurt install size and startup time for the vast majority of repos.  The
idioms that read configuration are small, stable and regular, so a precise
regex pass over the *whole* file (not line-by-line, so multi-line destructuring
works) is both fast and accurate.  Recognised forms:

* ``process.env.KEY`` and ``process.env["KEY"]``
* ``import.meta.env.KEY`` (Vite) and ``Bun.env.KEY``
* ``Deno.env.get("KEY")``
* ``const { A, B: alias, C = "default" } = process.env``
* inline fallbacks: ``process.env.KEY ?? "d"`` / ``|| "d"``
"""

from __future__ import annotations

import re
from pathlib import Path

from conflint.models import Language, Location, Usage
from conflint.scanners.base import Scanner

__all__ = ["JavaScriptScanner"]

_ENV_OBJECTS = r"(?:process|import\.meta|Bun)"

_RE_DOTTED = re.compile(rf"\b{_ENV_OBJECTS}\.env\.([A-Za-z_][A-Za-z0-9_]*)")
_RE_BRACKET = re.compile(rf"\b{_ENV_OBJECTS}\.env\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]")
_RE_DENO = re.compile(r"\bDeno\.env\.get\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")
_RE_DESTRUCTURE = re.compile(rf"\b(?:const|let|var)\s*\{{([^}}]*)\}}\s*=\s*{_ENV_OBJECTS}\.env\b")
_RE_FALLBACK = re.compile(r"\s*(?:\?\?|\|\|)\s*(?P<default>'[^']*'|\"[^\"]*\"|[A-Za-z0-9_.]+)")


class JavaScriptScanner(Scanner):
    """Static scanner for ``.js``/``.ts`` (and JSX/TSX) files."""

    name = "javascript"
    language = Language.JAVASCRIPT
    extensions = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")

    def scan(self, path: Path, text: str) -> list[Usage]:
        usages: list[Usage] = []

        for match in _RE_DOTTED.finditer(text):
            name = match.group(1)
            usages.append(self._usage(path, text, name, match.end(), "process.env", match.start()))

        for match in _RE_BRACKET.finditer(text):
            usages.append(
                self._usage(path, text, match.group(1), match.end(), "process.env[]", match.start())
            )

        for match in _RE_DENO.finditer(text):
            usages.append(
                self._usage(path, text, match.group(1), match.end(), "Deno.env.get", match.start())
            )

        for match in _RE_DESTRUCTURE.finditer(text):
            usages.extend(self._scan_destructure(path, text, match.group(1), match.start()))

        return usages

    def _usage(self, path: Path, text: str, name: str, end: int, via: str, start: int) -> Usage:
        default, has_default = self._inline_default(text, end)
        return Usage(
            name=name,
            location=Location(path, self.line_of(text, start)),
            language=self.language,
            read_via=via,
            required=False,
            has_default=has_default,
            default=default,
        )

    def _inline_default(self, text: str, end: int) -> tuple[str | None, bool]:
        window = text[end : end + 40]
        match = _RE_FALLBACK.match(window)
        if not match:
            return None, False
        raw = match.group("default")
        if raw is None:
            return "<dynamic>", True
        if raw[0] in "\"'":
            return raw[1:-1], True
        return raw, True

    def _scan_destructure(self, path: Path, text: str, body: str, start: int) -> list[Usage]:
        usages: list[Usage] = []
        for raw_item in body.split(","):
            item = raw_item.strip()
            if not item:
                continue
            # ``NAME: alias = default`` -> keep NAME, note default presence.
            name_part, _, default_part = item.partition("=")
            name_part = name_part.split(":")[0].strip()
            name = name_part.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                continue
            has_default = "=" in item
            default: str | None = None
            if has_default:
                default = default_part.strip().strip("\"'") or "<dynamic>"
            usages.append(
                Usage(
                    name=name,
                    location=Location(path, self.line_of(text, start)),
                    language=self.language,
                    read_via="process.env (destructured)",
                    required=False,
                    has_default=has_default,
                    default=default,
                )
            )
        return usages
