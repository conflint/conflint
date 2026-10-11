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
from collections.abc import Iterable, Sequence
from typing import Any

from conflint.exceptions import PluginError
from conflint.rules import Rule
from conflint.scanners import Scanner
from conflint.sources import ConfigSource

logger = logging.getLogger("conflint.registry")

__all__ = [
    "RULE_GROUP",
    "SCANNER_GROUP",
    "SOURCE_GROUP",
    "get_rules",
    "get_scanners",
    "get_sources",
    "iter_entry_points",
]

SCANNER_GROUP = "conflint.scanners"
SOURCE_GROUP = "conflint.sources"
RULE_GROUP = "conflint.rules"


def iter_entry_points(group: str) -> list[Any]:
    """Return entry points for ``group`` across Python versions."""

    from importlib import metadata

    try:
        eps = metadata.entry_points()
    except Exception as exc:  # pragma: no cover - defensive
        raise PluginError(f"could not enumerate entry points: {exc}") from exc

    if hasattr(eps, "select"):  # Python 3.10+
        return list(eps.select(group=group))
    return list(eps.get(group, []))  # Python 3.9


def _load_builtin_scanners() -> Sequence[type[Scanner]]:
    from conflint.scanners import (
        GoScanner,
        JavaScriptScanner,
        PythonScanner,
        RubyScanner,
    )

    return (PythonScanner, JavaScriptScanner, GoScanner, RubyScanner)


def _load_builtin_sources() -> Sequence[type[ConfigSource]]:
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


def _load_builtin_rules() -> Sequence[type[Rule]]:
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


def _load_plugins(group: str) -> list[type[Any]]:
    loaded: list[type[Any]] = []
    for ep in iter_entry_points(group):
        try:
            loaded.append(ep.load())
        except Exception as exc:
            logger.warning("skipping plugin %s: %s", getattr(ep, "name", ep), exc)
    return loaded


def get_scanners() -> list[Scanner]:
    """Instantiate every available scanner, built-in first."""

    classes: Iterable[type[Scanner]] = list(_load_builtin_scanners()) + _load_plugins(SCANNER_GROUP)
    return [cls() for cls in classes]


def get_sources() -> list[ConfigSource]:
    """Instantiate every available configuration source."""

    classes: Iterable[type[ConfigSource]] = list(_load_builtin_sources()) + _load_plugins(
        SOURCE_GROUP
    )
    return [cls() for cls in classes]


def get_rules(enabled: Sequence[str] | None = None) -> dict[str, Rule]:
    """Instantiate rules keyed by rule id, optionally filtered/enabled in order."""

    classes: Iterable[type[Rule]] = list(_load_builtin_rules()) + _load_plugins(RULE_GROUP)
    rules: dict[str, Rule] = {}
    for cls in classes:
        try:
            instance = cls()
        except Exception as exc:
            logger.warning("skipping rule %s: %s", cls, exc)
            continue
        rules[instance.id] = instance

    if enabled is not None:
        wanted = list(enabled)
        ordered: dict[str, Rule] = {}
        for rule_id in wanted:
            if rule_id in rules:
                ordered[rule_id] = rules[rule_id]
        # Preserve deterministic ordering of remaining rules after the
        # explicitly requested ones so output stays stable.
        for rule_id in sorted(rules):
            ordered.setdefault(rule_id, rules[rule_id])
        return ordered

    return dict(sorted(rules.items()))
