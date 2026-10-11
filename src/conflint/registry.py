"""Plugin registries.

Built-in scanners, sources and rules are always available.  Third parties can
extend conflint without touching its source by publishing entry points in the
``conflint.scanners``, ``conflint.sources`` and ``conflint.rules`` groups::

    [project.entry-points."conflint.rules"]
    CL100 = "my_pkg.rules:MyRule"

Loading is lazy and defensive: a broken third-party plugin is skipped with a
warning rather than taking down the whole run.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Sequence, Type

from conflint.exceptions import PluginError

logger = logging.getLogger("conflint.registry")

__all__ = [
    "get_scanners",
    "get_sources",
    "get_rules",
    "iter_entry_points",
    "SCANNER_GROUP",
    "SOURCE_GROUP",
    "RULE_GROUP",
]

SCANNER_GROUP = "conflint.scanners"
SOURCE_GROUP = "conflint.sources"
RULE_GROUP = "conflint.rules"


def iter_entry_points(group: str) -> List:
    """Return entry points for ``group`` across Python versions."""

    from importlib import metadata

    try:
        eps = metadata.entry_points()
    except Exception as exc:  # pragma: no cover - defensive
        raise PluginError(f"could not enumerate entry points: {exc}") from exc

    if hasattr(eps, "select"):  # Python 3.10+
        return list(eps.select(group=group))
    return list(eps.get(group, []))  # Python 3.9


def _load_builtin_scanners() -> Sequence[Type]:
    from conflint.scanners import (
        GoScanner,
        JavaScriptScanner,
        PythonScanner,
        RubyScanner,
    )

    return (PythonScanner, JavaScriptScanner, GoScanner, RubyScanner)


def _load_builtin_sources() -> Sequence[Type]:
    from conflint.sources import (
        DockerComposeSource,
        DotenvSource,
        GitHubActionsSource,
        KubernetesSource,
        TerraformSource,
    )

    return (
        DotenvSource,
        DockerComposeSource,
        GitHubActionsSource,
        KubernetesSource,
        TerraformSource,
    )


def _load_builtin_rules() -> Sequence[Type]:
    from conflint.rules import (
        DriftRule,
        DuplicateRule,
        EmptyValueRule,
        MissingRule,
        SecretLeakRule,
        TypoRule,
        UndocumentedRule,
        UnusedRule,
        WeakSecretRule,
    )

    return (
        MissingRule,
        UnusedRule,
        TypoRule,
        SecretLeakRule,
        DriftRule,
        EmptyValueRule,
        DuplicateRule,
        WeakSecretRule,
        UndocumentedRule,
    )


def _load_plugins(group: str) -> List:
    loaded = []
    for ep in iter_entry_points(group):
        try:
            loaded.append(ep.load())
        except Exception as exc:  # noqa: BLE001 - isolate plugin failures
            logger.warning("skipping plugin %s: %s", getattr(ep, "name", ep), exc)
    return loaded


def get_scanners() -> List:
    """Instantiate every available scanner, built-in first."""

    classes: Iterable[Type] = list(_load_builtin_scanners()) + _load_plugins(SCANNER_GROUP)
    return [cls() for cls in classes]


def get_sources() -> List:
    """Instantiate every available configuration source."""

    classes: Iterable[Type] = list(_load_builtin_sources()) + _load_plugins(SOURCE_GROUP)
    return [cls() for cls in classes]


def get_rules(enabled: Sequence[str] | None = None) -> Dict[str, object]:
    """Instantiate rules keyed by rule id, optionally filtered/enabled in order."""

    classes: Iterable[Type] = list(_load_builtin_rules()) + _load_plugins(RULE_GROUP)
    rules: Dict[str, object] = {}
    for cls in classes:
        try:
            instance = cls()
        except Exception as exc:  # noqa: BLE001 - isolate plugin failures
            logger.warning("skipping rule %s: %s", cls, exc)
            continue
        rules[instance.id] = instance

    if enabled is not None:
        wanted = [r for r in enabled]
        ordered: Dict[str, object] = {}
        for rule_id in wanted:
            if rule_id in rules:
                ordered[rule_id] = rules[rule_id]
        # Preserve deterministic ordering of remaining rules after the
        # explicitly requested ones so output stays stable.
        for rule_id in sorted(rules):
            ordered.setdefault(rule_id, rules[rule_id])
        return ordered

    return dict(sorted(rules.items()))
