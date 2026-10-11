"""Terraform source.

Extracts configuration *variables* that correspond to runtime config:

* ``variable "NAME" { default = "..." }`` blocks in ``*.tf``
* ``environment = { KEY = "value", ... }`` blocks (container/env definitions)
* plain ``KEY = "value"`` assignments in ``*.tfvars`` / ``*.tfvars.json``

Terraform also surfaces variables to applications as ``TF_VAR_*``; conflint
records the bare name and does not attempt that prefix mapping (documented as a
known limitation).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from conflint.models import Entry, Location
from conflint.sources.base import ConfigSource, find_line
from conflint.utils import is_sensitive_name

__all__ = ["TerraformSource"]

_RE_VARIABLE = re.compile(r'\bvariable\s+"([A-Za-z_][A-Za-z0-9_]*)"\s*\{')
_RE_DEFAULT = re.compile(r'\bdefault\s*=\s*("(?:[^"\\]|\\.)*"|[A-Za-z0-9_.\-]+)')
_RE_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$", re.MULTILINE)
_RE_ENV_BLOCK = re.compile(r"\benvironment\s*=\s*\{")


class TerraformSource(ConfigSource):
    """Parser for Terraform ``.tf`` and ``.tfvars`` files."""

    name = "terraform"
    config_globs = (
        "**/*.tf",
        "**/*.tfvars",
        "**/*.tfvars.json",
        "*.tf",
        "*.tfvars",
    )

    def matches(self, path: Path) -> bool:
        name = self._norm_name(path)
        if name.endswith(".tfvars.json"):
            return True
        if name.endswith(".tf"):
            return True
        return name.endswith(".tfvars")

    def parse(self, path: Path, text: str) -> list[Entry]:
        name = self._norm_name(path)
        if name.endswith(".tfvars.json"):
            return self._parse_json_tfvars(path, text)
        if name.endswith(".tfvars") or name.endswith(".tf.json"):
            return self._parse_tfvars(path, text)
        return self._parse_tf(path, text)

    # -- .tf -------------------------------------------------------------
    def _parse_tf(self, path: Path, text: str) -> list[Entry]:
        entries: list[Entry] = []
        for match in _RE_VARIABLE.finditer(text):
            var_name = match.group(1)
            block = self._block_body(text, match.end())
            default_match = _RE_DEFAULT.search(block)
            default = _unquote(default_match.group(1)) if default_match else None
            entries.append(
                Entry(
                    name=var_name,
                    value=default,
                    location=Location(path, find_line(text, var_name), 1),
                    source=self.name,
                    is_secret=is_sensitive_name(var_name),
                    notes=("terraform:variable",),
                )
            )
        for key, value, offset in self._iter_env_blocks(text):
            entries.append(
                Entry(
                    name=key,
                    value=value,
                    location=Location(path, self._line_at(text, offset), 1),
                    source=self.name,
                    is_secret=is_sensitive_name(key),
                    notes=("terraform:environment",),
                )
            )
        return entries

    def _iter_env_blocks(self, text: str) -> Iterator[tuple[str, str, int]]:
        for match in _RE_ENV_BLOCK.finditer(text):
            body = self._block_body(text, match.end())
            for assign in _RE_ASSIGN.finditer(body):
                key = assign.group(1)
                value = _unquote(assign.group(2).rstrip(","))
                yield key, value, match.start()

    # -- .tfvars ---------------------------------------------------------
    def _parse_tfvars(self, path: Path, text: str) -> list[Entry]:
        entries: list[Entry] = []
        for lineno, raw in enumerate(text.splitlines(), start=1):
            if raw.lstrip().startswith(("#", "//")):
                continue
            match = _RE_ASSIGN.match(raw)
            if not match:
                continue
            key, value = match.group(1), _unquote(match.group(2).rstrip(","))
            entries.append(
                Entry(
                    name=key,
                    value=value,
                    location=Location(path, lineno, 1),
                    source=self.name,
                    is_secret=is_sensitive_name(key),
                    notes=("terraform:tfvars",),
                )
            )
        return entries

    def _parse_json_tfvars(self, path: Path, text: str) -> list[Entry]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, Mapping):
            return []
        entries: list[Entry] = []
        for key, value in data.items():
            entries.append(
                Entry(
                    name=str(key),
                    value=None if value is None else str(value),
                    location=Location(path, find_line(text, str(key)), 1),
                    source=self.name,
                    is_secret=is_sensitive_name(str(key)),
                    notes=("terraform:tfvars.json",),
                )
            )
        return entries

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _block_body(text: str, start: int) -> str:
        """Return the body of a ``{...}`` block beginning at ``start``."""

        depth = 1
        i = start
        while i < len(text) and depth:
            char = text[i]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            i += 1
        return text[start : i - 1]

    def _line_at(self, text: str, offset: int) -> int:
        return text.count("\n", 0, offset) + 1


def _unquote(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value
