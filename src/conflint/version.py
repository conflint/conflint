"""Version resolution.

The published version is derived from git tags (hatch-vcs) into
``conflint._version``.  During a plain source checkout that module may not
exist, so we fall back to installed distribution metadata and finally to a
development sentinel.
"""

from __future__ import annotations

from importlib import metadata

__all__ = ["__version__"]


def _resolve_version() -> str:
    try:  # pragma: no cover - generated at build time
        from conflint._version import __version__ as generated

        return generated
    except Exception:
        pass

    try:
        return metadata.version("conflint")
    except metadata.PackageNotFoundError:
        return "0.0.0.dev0"


__version__ = _resolve_version()
