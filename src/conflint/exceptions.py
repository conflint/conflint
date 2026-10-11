"""Exception hierarchy for conflint.

Every error raised deliberately by conflint derives from :class:`ConflintError`
so the CLI can present a clean message instead of a traceback.
"""

from __future__ import annotations

__all__ = [
    "ConflintError",
    "ConfigError",
    "DiscoveryError",
    "ScanError",
    "SourceError",
    "RuleError",
    "ReporterError",
    "PluginError",
    "ExitCode",
]


class ConflintError(Exception):
    """Base class for all deliberate conflint failures."""


class ConfigError(ConflintError):
    """The project configuration is malformed or references unknown rules."""


class DiscoveryError(ConflintError):
    """File discovery failed (bad glob, unreadable directory, ...)."""


class ScanError(ConflintError):
    """A source-code scanner could not process a file."""


class SourceError(ConflintError):
    """A configuration source could not be parsed."""


class RuleError(ConflintError):
    """A lint rule raised while evaluating the project."""


class ReporterError(ConflintError):
    """A reporter could not render or write its output."""


class PluginError(ConflintError):
    """Loading an external plugin failed."""


class ExitCode:
    """Process exit codes used by the CLI (compatible with common linters)."""

    OK = 0
    FINDINGS = 1
    USAGE = 2
    INTERNAL = 3
