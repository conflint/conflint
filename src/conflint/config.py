"""Project configuration (``conflint.toml`` / ``[tool.conflint]``).

Settings are merged from (highest precedence last):

1. built-in defaults
2. ``pyproject.toml`` -> ``[tool.conflint]``
3. ``conflint.toml`` / ``.conflint.toml`` in the project root
4. an explicit ``--config`` path
5. CLI overrides

Only TOML is supported, which keeps the parser tiny and matches the Python
ecosystem.  Unknown keys are rejected loudly so typos never pass silently.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from conflint.exceptions import ConfigError
from conflint.models import Severity

if sys.version_info >= (3, 11):
    import tomllib as _toml  # type: ignore[import-not-found]
else:  # pragma: no cover - exercised on 3.9/3.10
    import tomli as _toml

__all__ = ["DEFAULT_EXCLUDES", "DEFAULT_INCLUDES", "Settings", "load_settings"]

DEFAULT_INCLUDES: tuple[str, ...] = ("**/*",)

DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".git/**",
    ".hg/**",
    ".svn/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/venv/**",
    "**/env/**",
    "**/__pycache__/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.pytest_cache/**",
    "**/dist/**",
    "**/build/**",
    "**/*.min.js",
    "**/*.min.css",
    "**/vendor/**",
    "**/.terraform/**",
    "**/site/**",
)

# Files that represent "example/template" configuration rather than real values.
DEFAULT_EXAMPLE_FILES: tuple[str, ...] = (
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    "example.env",
    "sample.env",
    "env.example",
)

_ALLOWED_KEYS = {
    "include",
    "exclude",
    "scanners",
    "sources",
    "enable",
    "disable",
    "ignore-names",
    "ignore-paths",
    "fail-level",
    "example-files",
    "color",
    "entropy-threshold",
    "require-example",
    "reporters",
}


@dataclass
class Settings:
    """Effective, validated configuration for a run."""

    root: Path
    include: tuple[str, ...] = DEFAULT_INCLUDES
    exclude: tuple[str, ...] = DEFAULT_EXCLUDES
    scanners: tuple[str, ...] = ()  # empty => all
    sources: tuple[str, ...] = ()  # empty => all
    enable: dict[str, Severity] = field(default_factory=dict)
    disable: tuple[str, ...] = ()
    ignore_names: tuple[str, ...] = ()
    ignore_paths: tuple[str, ...] = ()
    fail_level: Severity = Severity.ERROR
    example_files: tuple[str, ...] = DEFAULT_EXAMPLE_FILES
    color: bool | None = None
    entropy_threshold: float = 3.5
    require_example: bool = True
    reporters: tuple[str, ...] = ("text",)
    origin_files: tuple[Path, ...] = ()

    def is_name_ignored(self, name: str) -> bool:
        import fnmatch

        return any(fnmatch.fnmatchcase(name, pattern) for pattern in self.ignore_names)

    def is_path_ignored(self, path: Path) -> bool:
        from fnmatch import fnmatch

        text = str(path).replace("\\", "/")
        return any(
            fnmatch(text, pattern) or fnmatch(path.name, pattern) for pattern in self.ignore_paths
        )

    def severity_for(self, rule_id: str) -> Severity | None:
        """Explicit severity override for ``rule_id`` (``None`` if not overridden).

        Disabled rules are reported separately by :meth:`is_disabled`; the
        engine falls back to the rule's own default severity when this is
        ``None``.
        """

        if rule_id in self.enable:
            return self.enable[rule_id]
        return None

    def is_disabled(self, rule_id: str) -> bool:
        return rule_id in self.disable


def _as_str_tuple(value: Any, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        if not all(isinstance(v, str) for v in value):
            raise ConfigError(f"'{key}' must be a list of strings")
        return tuple(value)
    raise ConfigError(f"'{key}' must be a string or list of strings")


def _coerce_severity(value: Any, key: str) -> Severity:
    try:
        return Severity.coerce(value)
    except ValueError as exc:
        raise ConfigError(
            f"'{key}': invalid severity {value!r} (expected error/warning/info)"
        ) from exc


def _read_toml(path: Path) -> Mapping[str, Any]:
    try:
        with path.open("rb") as handle:
            return cast(Mapping[str, Any], _toml.load(handle))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except OSError as exc:  # pragma: no cover - filesystem dependent
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    except _toml.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc


def _extract_table(data: Mapping[str, Any], path: Path, *, nested: bool) -> dict[str, Any]:
    if nested:
        table = data.get("tool", {}).get("conflint")
        if table is None:
            return {}
        if not isinstance(table, Mapping):
            raise ConfigError(f"[tool.conflint] in {path} must be a table")
        return dict(table)
    return dict(data)


def _apply(settings: Settings, table: Mapping[str, Any], path: Path) -> None:
    unknown = set(table) - _ALLOWED_KEYS
    if unknown:
        raise ConfigError(f"unknown configuration key(s) in {path}: {', '.join(sorted(unknown))}")

    if "include" in table:
        settings.include = _as_str_tuple(table["include"], "include")
    if "exclude" in table:
        settings.exclude = _as_str_tuple(table["exclude"], "exclude")
    if "scanners" in table:
        settings.scanners = _as_str_tuple(table["scanners"], "scanners")
    if "sources" in table:
        settings.sources = _as_str_tuple(table["sources"], "sources")
    if "disable" in table:
        settings.disable = _as_str_tuple(table["disable"], "disable")
    if "ignore-names" in table:
        settings.ignore_names = _as_str_tuple(table["ignore-names"], "ignore-names")
    if "ignore-paths" in table:
        settings.ignore_paths = _as_str_tuple(table["ignore-paths"], "ignore-paths")
    if "example-files" in table:
        settings.example_files = _as_str_tuple(table["example-files"], "example-files")
    if "reporters" in table:
        settings.reporters = _as_str_tuple(table["reporters"], "reporters")

    if "color" in table:
        value = table["color"]
        if not isinstance(value, bool):
            raise ConfigError("'color' must be a boolean")
        settings.color = value

    if "fail-level" in table:
        settings.fail_level = _coerce_severity(table["fail-level"], "fail-level")

    if "entropy-threshold" in table:
        value = table["entropy-threshold"]
        if not isinstance(value, (int, float)):
            raise ConfigError("'entropy-threshold' must be a number")
        settings.entropy_threshold = float(value)

    if "require-example" in table:
        value = table["require-example"]
        if not isinstance(value, bool):
            raise ConfigError("'require-example' must be a boolean")
        settings.require_example = value

    if "enable" in table:
        enable = table["enable"]
        if not isinstance(enable, Mapping):
            raise ConfigError("'enable' must be a table of rule id -> severity")
        merged = dict(settings.enable)
        for rule_id, sev in enable.items():
            merged[str(rule_id)] = _coerce_severity(sev, f"enable.{rule_id}")
        settings.enable = merged

    settings.origin_files = (*settings.origin_files, path)


def load_settings(
    root: Path,
    *,
    config_path: Path | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> Settings:
    """Build the effective :class:`Settings` for ``root``."""

    root = root.resolve()
    settings = Settings(root=root)

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        table = _extract_table(_read_toml(pyproject), pyproject, nested=True)
        if table:
            _apply(settings, table, pyproject)

    for candidate in (root / "conflint.toml", root / ".conflint.toml"):
        if candidate.is_file():
            _apply(
                settings, _extract_table(_read_toml(candidate), candidate, nested=False), candidate
            )

    if config_path is not None:
        path = Path(config_path)
        if not path.is_absolute():
            path = root / path
        _apply(settings, _extract_table(_read_toml(path), path, nested=False), path)

    if overrides:
        _apply(settings, {k: v for k, v in overrides.items() if v is not None}, root / "<cli>")

    return settings
