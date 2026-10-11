"""GitHub Actions workflow source.

Every ``env:`` mapping found anywhere in a workflow (workflow-, job- and
step-level) defines variables your CI will provide.  Those definitions are what
lets conflint answer "will this variable exist in CI?" and "is this CI variable
dead?".
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from conflint.models import Entry, Location
from conflint.sources._yaml import load_documents
from conflint.sources.base import ConfigSource, find_line
from conflint.utils import is_sensitive_name

__all__ = ["GitHubActionsSource"]


class GitHubActionsSource(ConfigSource):
    """Parser for ``.github/workflows/*.yml`` files."""

    name = "github-actions"
    config_globs = (
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "**/.github/workflows/*.yml",
        "**/.github/workflows/*.yaml",
    )

    def matches(self, path: Path) -> bool:
        if not self.is_yaml(path):
            return False
        parts = [p.lower() for p in path.parts]
        return ".github" in parts and "workflows" in parts

    def parse(self, path: Path, text: str) -> list[Entry]:
        entries: list[Entry] = []
        for document in load_documents(text):
            for env_map in self._iter_env_maps(document):
                for key, value in env_map.items():
                    key = str(key)
                    if key == "_":
                        continue
                    entries.append(
                        Entry(
                            name=key,
                            value=_stringify(value),
                            location=Location(path, find_line(text, key), 1),
                            source=self.name,
                            is_secret=is_sensitive_name(key),
                            notes=("workflow-env",),
                        )
                    )
        return entries

    def _iter_env_maps(self, node: Any) -> Iterator[Mapping[str, Any]]:
        if isinstance(node, Mapping):
            env = node.get("env")
            if isinstance(env, Mapping):
                yield env
            for value in node.values():
                yield from self._iter_env_maps(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._iter_env_maps(value)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
