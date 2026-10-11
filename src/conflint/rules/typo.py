"""CL003 - likely typo: an undefined name is one edit away from a known one."""

from __future__ import annotations

from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule
from conflint.utils import close_matches

__all__ = ["TypoRule"]


class TypoRule(Rule):
    id = "CL003"
    name = "typo"
    severity = Severity.WARNING
    description = "An undefined value closely matches a defined one (possible typo)."
    fixable = False

    def check(self, config: Config, settings: Settings) -> list[Finding]:
        defined = {entry.name for entry in config.entries}
        findings: list[Finding] = []
        for name, usages in config.usages_by_name().items():
            if name in defined or settings.is_name_ignored(name):
                continue
            matches = close_matches(name, defined, max_distance=2, limit=3)
            if not matches:
                continue
            suggestion, distance = matches[0]
            findings.append(
                self.finding(
                    f"'{name}' is undefined but resembles '{suggestion}' (distance {distance})",
                    key=name,
                    location=usages[0].location,
                    help=f"Did you mean '{suggestion}'?",
                    data={"suggestion": suggestion, "distance": distance},
                )
            )
        return findings
