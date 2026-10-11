"""Built-in reporters."""

from __future__ import annotations

from conflint.exceptions import ConfigError
from conflint.reporters.base import Reporter
from conflint.reporters.github import GithubReporter
from conflint.reporters.json import JsonReporter
from conflint.reporters.junit import JunitReporter
from conflint.reporters.sarif import SarifReporter
from conflint.reporters.text import TextReporter

__all__ = [
    "GithubReporter",
    "JsonReporter",
    "JunitReporter",
    "Reporter",
    "SarifReporter",
    "TextReporter",
    "create_reporter",
]

_ReporterClass = (
    type[TextReporter]
    | type[JsonReporter]
    | type[SarifReporter]
    | type[GithubReporter]
    | type[JunitReporter]
)

_REPORTER_CLASSES: dict[str, _ReporterClass] = {
    "text": TextReporter,
    "json": JsonReporter,
    "sarif": SarifReporter,
    "github": GithubReporter,
    "junit": JunitReporter,
}


def create_reporter(name: str) -> Reporter:
    """Instantiate a reporter by name (raises :class:`ConfigError` if unknown)."""
    if name not in _REPORTER_CLASSES:
        raise ConfigError(
            f"unknown reporter {name!r} (choose from {', '.join(sorted(_REPORTER_CLASSES))})"
        )
    return _REPORTER_CLASSES[name]()
