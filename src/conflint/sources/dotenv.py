"""``.env`` family parser.

Handles ``.env``, ``.env.local``, ``.env.example`` and friends.  Deliberately
permissive, matching what real dotenv libraries accept:

* ``KEY=value`` and ``export KEY=value``
* optional surrounding single/double quotes
* ``#`` comments (whole-line and trailing, when unquoted)
* blank lines and ``KEY=`` (empty) values
* ``KEY`` with no ``=`` is ignored (not a valid assignment)
"""

from __future__ import annotations

import re
from pathlib import Path

from conflint.models import Entry, Location
from conflint.sources.base import ConfigSource
from conflint.utils import is_sensitive_name, strip_quotes

__all__ = ["DotenvSource"]

_ASSIGN = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_ENV_NAME = re.compile(r"^\.env(?:\.[A-Za-z0-9_.-]+)?$", re.IGNORECASE)


class DotenvSource(ConfigSource):
    """Parser for dotenv-format files."""

    name = "dotenv"
    config_globs = (
        ".env",
        ".env.*",
        "**/.env",
        "**/.env.*",
    )

    def matches(self, path: Path) -> bool:
        return bool(_ENV_NAME.match(self._norm_name(path)))

    def parse(self, path: Path, text: str) -> list[Entry]:
        entries: list[Entry] = []
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = _ASSIGN.match(line)
            if not match:
                continue
            key, value = match.group(1), match.group(2)
            value = self._strip_inline_comment(value)
            value = strip_quotes(value)
            entries.append(
                Entry(
                    name=key,
                    value=value,
                    location=Location(path, lineno, 1),
                    source=self.name,
                    is_secret=is_sensitive_name(key),
                )
            )
        return entries

    @staticmethod
    def _strip_inline_comment(value: str) -> str:
        """Remove a trailing ``# comment`` unless the value is quoted."""

        v = value.strip()
        if not v:
            return v
        if v[0] in "\"'":
            quote = v[0]
            end = v.find(quote, 1)
            if end != -1:
                return v[: end + 1]
            return v
        hash_index = v.find(" #")
        if hash_index == -1:
            hash_index = v.find("\t#")
        if hash_index != -1:
            return v[:hash_index]
        return v
