"""Kubernetes manifest source.

Extracts configuration keys from:

* ``ConfigMap.data`` / ``ConfigMap.binaryData`` keys
* ``Secret.stringData`` / ``Secret.data`` keys
* container ``env`` entries (``value`` or ``valueFrom``) in any workload
  (Deployment, StatefulSet, DaemonSet, Job, CronJob, Pod, ...)

The YAML is walked structurally so nested containers are found regardless of
where they live in the document.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from conflint.models import Entry, Location
from conflint.sources._yaml import load_documents
from conflint.sources.base import ConfigSource, find_line
from conflint.utils import is_sensitive_name

__all__ = ["KubernetesSource"]

_COMPOSE_NAMES = {"compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}


class KubernetesSource(ConfigSource):
    """Parser for Kubernetes manifests."""

    name = "kubernetes"
    config_globs = (
        "**/*.yaml",
        "**/*.yml",
        "*.yaml",
        "*.yml",
    )

    def matches(self, path: Path) -> bool:
        if not self.is_yaml(path):
            return False
        parts = [p.lower() for p in path.parts]
        if ".github" in parts and "workflows" in parts:
            return False
        return self._norm_name(path) not in _COMPOSE_NAMES

    def parse(self, path: Path, text: str) -> list[Entry]:
        entries: list[Entry] = []
        for document in load_documents(text):
            if not isinstance(document, Mapping):
                continue
            if not self._looks_like_k8s(document):
                continue
            entries.extend(self._parse_workload(path, text, document))
            entries.extend(self._parse_configmap_secret(path, text, document))
        return entries

    @staticmethod
    def _looks_like_k8s(document: Mapping[str, Any]) -> bool:
        return "kind" in document and ("apiVersion" in document or "metadata" in document)

    def _parse_workload(self, path: Path, text: str, document: Mapping[str, Any]) -> list[Entry]:
        entries: list[Entry] = []
        kind = str(document.get("kind", ""))
        for container in self._iter_containers(document):
            for env in container.get("env", []) or []:
                if not isinstance(env, Mapping):
                    continue
                name = str(env.get("name", ""))
                if not name:
                    continue
                if "value" in env:
                    value = env.get("value")
                    notes: tuple[str, ...] = (f"k8s:{kind}",)
                    value_str = None if value is None else str(value)
                else:
                    value_str = None
                    source_ref = _value_from_ref(env.get("valueFrom"))
                    notes = (f"k8s:{kind}", f"from:{source_ref}" if source_ref else "from:ref")
                entries.append(
                    Entry(
                        name=name,
                        value=value_str,
                        location=Location(path, find_line(text, name), 1),
                        source=self.name,
                        is_secret=is_sensitive_name(name),
                        notes=notes,
                    )
                )
        return entries

    def _parse_configmap_secret(
        self, path: Path, text: str, document: Mapping[str, Any]
    ) -> list[Entry]:
        kind = str(document.get("kind", ""))
        if kind not in {"ConfigMap", "Secret"}:
            return []
        entries: list[Entry] = []
        for field in ("data", "stringData", "binaryData"):
            mapping = document.get(field)
            if not isinstance(mapping, Mapping):
                continue
            for key, value in mapping.items():
                key = str(key)
                entries.append(
                    Entry(
                        name=key,
                        value=None if value is None else str(value),
                        location=Location(path, find_line(text, key), 1),
                        source=self.name,
                        is_secret=kind == "Secret" or is_sensitive_name(key),
                        notes=(f"k8s:{kind}.{field}",),
                    )
                )
        return entries

    def _iter_containers(self, node: Any) -> Iterator[Mapping[str, Any]]:
        if isinstance(node, Mapping):
            containers = node.get("containers")
            if isinstance(containers, list):
                for container in containers:
                    if isinstance(container, Mapping):
                        yield container
            init = node.get("initContainers")
            if isinstance(init, list):
                for container in init:
                    if isinstance(container, Mapping):
                        yield container
            for value in node.values():
                yield from self._iter_containers(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._iter_containers(value)


def _value_from_ref(value_from: Any) -> str:
    if not isinstance(value_from, Mapping):
        return ""
    for kind in ("secretKeyRef", "configMapKeyRef", "fieldRef"):
        if kind in value_from and isinstance(value_from[kind], Mapping):
            ref = value_from[kind]
            target = ref.get("name") or ref.get("fieldPath") or ""
            return f"{kind}:{target}" if target else kind
    return ""
