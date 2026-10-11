"""File discovery.

Two very different notions of "should I look at this file" are needed:

* **Source code** is walked respecting ``.gitignore`` and the configured
  ``include``/``exclude`` globs, because we only care about files under version
  control.
* **Configuration files** (``.env``, compose, k8s, ...) are frequently
  *gitignored on purpose* — you must never skip a ``.env`` just because git
  ignores it.  Those are located directly and filtered only by ``exclude``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterator, List, Optional, Sequence

from conflint.config import Settings

logger = logging.getLogger("conflint.discovery")

__all__ = ["DiscoveredFiles", "discover", "is_excluded", "load_gitignore"]

try:
    import pathspec

    _HAS_PATHSPEC = True
except ModuleNotFoundError:  # pragma: no cover - pathspec is a hard dependency
    _HAS_PATHSPEC = False


@dataclass
class DiscoveredFiles:
    """Result of a discovery pass."""

    root: Path
    code_files: List[Path]
    config_files: List[Path]

    @property
    def all(self) -> List[Path]:
        seen = set()
        merged: List[Path] = []
        for path in [*self.code_files, *self.config_files]:
            if path not in seen:
                seen.add(path)
                merged.append(path)
        return merged


def load_gitignore(root: Path):
    """Return a compiled :class:`pathspec.PathSpec` for the repo, or ``None``."""

    if not _HAS_PATHSPEC:
        return None
    lines: List[str] = []
    for candidate in (root / ".gitignore", root / ".git" / "info" / "exclude"):
        if candidate.is_file():
            try:
                lines.extend(candidate.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:  # pragma: no cover - filesystem dependent
                continue
    if not lines:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def _norm(path: Path) -> str:
    return str(path).replace("\\", "/")


def is_excluded(path: Path, root: Path, settings: Settings) -> bool:
    """Whether ``path`` is excluded by ``settings.exclude`` (glob based)."""

    try:
        rel = path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        rel = path
    text = _norm(rel)
    name = path.name
    for pattern in settings.exclude:
        if fnmatch(text, pattern) or fnmatch("/" + text, pattern) or fnmatch(name, pattern):
            return True
    return False


def _matches_include(path: Path, root: Path, settings: Settings) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        rel = path
    text = _norm(rel)
    return any(fnmatch(text, pattern) or fnmatch("/" + text, pattern) for pattern in settings.include)


def _walk_files(root: Path, spec) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if spec is not None:
            try:
                rel = _norm(path.relative_to(root))
            except ValueError:
                rel = _norm(path)
            if spec.match_file(rel):
                continue
        yield path


def discover(root: Path, settings: Settings, *, config_globs: Sequence[str] = ()) -> DiscoveredFiles:
    """Walk the project and classify files.

    ``config_globs`` are additional glob patterns (relative to ``root``) that
    should be treated as configuration and therefore bypass ``.gitignore``.
    """

    root = root.resolve()
    spec = load_gitignore(root)

    code_files: List[Path] = []
    config_files: List[Path] = []
    seen_config = set()

    for path in _walk_files(root, spec):
        if is_excluded(path, root, settings):
            continue
        if _matches_include(path, root, settings):
            code_files.append(path)

    # Config files intentionally ignore .gitignore.
    for pattern in config_globs:
        for path in root.glob(pattern):
            if not path.is_file() or is_excluded(path, root, settings):
                continue
            resolved = path.resolve()
            if resolved in seen_config:
                continue
            seen_config.add(resolved)
            config_files.append(path)

    logger.debug(
        "discovered %d code files and %d config files under %s",
        len(code_files),
        len(config_files),
        root,
    )

    return DiscoveredFiles(
        root=root,
        code_files=sorted(code_files),
        config_files=sorted(config_files, key=lambda p: str(p)),
    )
