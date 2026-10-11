"""Docker Compose source.

Collects environment variables declared under ``services.*.environment`` and the
keys of referenced ``env_file`` files (as notes).  Both the list style
(``- KEY=value``) and the mapping style (``KEY: value``) are supported.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Mapping

from conflint.models import Entry, Location
from conflint.sources._yaml import load_documents
from conflint.sources.base import ConfigSource, find_line
from conflint.utils import is_sensitive_name

__all__ = ["DockerComposeSource"]

_COMPOSE_NAMES = {"compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}


class DockerComposeSource(ConfigSource):
    """Parser for Docker Compose files."""

    name = "docker-compose"
    config_globs = (
        "compose.yml",
        "compose.yaml",
        "docker-compose.yml",
        "docker-compose.yaml",
        "**/compose.yml",
        "**/compose.yaml",
        "**/docker-compose.yml",
        "**/docker-compose.yaml",
        "**/docker-compose.*.yml",
        "**/docker-compose.*.yaml",
    )

    def matches(self, path: Path) -> bool:
        name = self._norm_name(path)
        if name in _COMPOSE_NAMES:
            return True
        return name.startswith("docker-compose") and name.endswith((".yml", ".yaml"))

    def parse(self, path: Path, text: str) -> List[Entry]:
        entries: List[Entry] = []
        for document in load_documents(text):
            if not isinstance(document, Mapping):
                continue
            services = document.get("services")
            if not isinstance(services, Mapping):
                continue
            for service_name, service in services.items():
                if not isinstance(service, Mapping):
                    continue
                entries.extend(self._parse_environment(path, text, service_name, service))
        return entries

    def _parse_environment(
        self, path: Path, text: str, service_name: str, service: Mapping[str, Any]
    ) -> List[Entry]:
        entries: List[Entry] = []
        env = service.get("environment")
        if isinstance(env, Mapping):
            for key, value in env.items():
                entries.append(self._entry(path, text, str(key), value, service_name))
        elif isinstance(env, list):
            for item in env:
                if not isinstance(item, str):
                    continue
                key, sep, value = item.partition("=")
                entries.append(
                    self._entry(
                        path, text, key.strip(), value if sep else None, service_name
                    )
                )
        return entries

    def _entry(
        self, path: Path, text: str, key: str, value: Any, service_name: str
    ) -> Entry:
        line = find_line(text, key)
        return Entry(
            name=key,
            value=None if value is None else str(value),
            location=Location(path, line, 1),
            source=self.name,
            is_secret=is_sensitive_name(key),
            notes=(f"service:{service_name}",),
        )
