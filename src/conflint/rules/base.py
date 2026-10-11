"""Rule base class.

A rule receives the reconciled :class:`~conflint.models.Config` graph plus the
effective :class:`~conflint.config.Settings` and returns findings.  Rules are
pure: they never touch the filesystem and never mutate the model.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from conflint.config import Settings
from conflint.models import Config, Finding, Location, Severity

__all__ = ["Rule"]


class Rule(ABC):
    """Base class for lint rules."""

    #: Stable identifier (``CL001`` ...).  Shown in reports and used in config.
    id: str = "CL000"
    #: Short human name.
    name: str = "rule"
    #: Default severity; may be overridden per project.
    severity: Severity = Severity.WARNING
    #: One-line description used in ``confl rules`` output and docs.
    description: str = ""
    #: Whether ``confl check --fix`` can auto-remediate findings from this rule.
    fixable: bool = False

    @abstractmethod
    def check(self, config: Config, settings: Settings) -> list[Finding]:
        """Return findings for ``config``."""

    # -- helper ----------------------------------------------------------
    def finding(
        self,
        message: str,
        *,
        key: str | None = None,
        location: Location | None = None,
        help: str | None = None,
        severity: Severity | None = None,
        fixable: bool | None = None,
        data: dict[str, Any] | None = None,
    ) -> Finding:
        return Finding(
            rule_id=self.id,
            severity=severity or self.severity,
            message=message,
            key=key,
            location=location,
            help=help,
            fixable=self.fixable if fixable is None else fixable,
            data=data or {},
        )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<{type(self).__name__} id={self.id}>"
