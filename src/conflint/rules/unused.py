"""CL002 - a value is defined by a real source but never read by code."""

from __future__ import annotations

from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule

__all__ = ["UnusedRule"]


class UnusedRule(Rule):
    id = "CL002"
    name = "unused"
    severity = Severity.WARNING
    description = "A real configuration value is never read by the scanned code."
    fixable = False

    def check(self, config: Config, settings: Settings) -> list[Finding]:
        used = config.used_names()
        findings: list[Finding] = []
        # Only complain about names that a *real* source provides; an unused key
        # in an example file is covered by the drift/undocumented rules.
        seen = set()
        for entry in config.entries:
            if entry.is_example or entry.name in used or entry.name in seen:
                continue
            if settings.is_name_ignored(entry.name):
                continue
            seen.add(entry.name)
            findings.append(
                self.finding(
                    f"'{entry.name}' is defined in {entry.source} but never read by code",
                    key=entry.name,
                    location=entry.location,
                    help="Remove it, or add `ignore-names` if an external tool consumes it",
                    data={"source": entry.source},
                )
            )
        return findings
